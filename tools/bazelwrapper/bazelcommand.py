import json
import os
from typing import Iterable, Optional, List

import bazelwrapper.bi.wrapper_api as bi
import bazelwrapper.remotecache.wrapper_api as remotecache
from bazelwrapper.context import Context, WixFlags, ENGFLOW_CONFIG_ROOT, ENV_VAR_RBE_ACTIVE_PROVIDER, OUTPUT_BASE_DIR
from bazelwrapper.env.info import is_local_dev


def _bazel_command(ctx: Context, params: [str]):
    bazel_real = os.environ["BAZEL_REAL"]  # this is a contract with the bazel binary
    ctx.logger.debug("Real bazel: {}".format(bazel_real))

    real_bazel_command = [bazel_real] + params

    ctx.logger.debug("Resolved bazel command: {}".format(json.dumps(real_bazel_command, indent=2)))

    return real_bazel_command


def build_bazel_command(ctx: Context):
    params = [
        *_generate_startup_flags(ctx),
        *_inject_command_flags(ctx.user_args, _generate_command_flags(ctx))
    ]

    return _bazel_command(ctx, params)

def build_bep_parser_bazel_command(ctx: Context):
    user_args = ["run",
                 "@wix_ci//localdev_new/tools/bazel/build/bep:bep-runner",
                 "--ui_event_filters=-info,-stdout,-stderr,-debug",
                 "--noshow_progress",
                 "--",
                 f"--bep_file={ctx.bep_file_path}",
                 "--skipped_targets=True"]

    params = [
        *_generate_startup_flags(ctx),
        *_inject_command_flags(user_args, _generate_command_flags(ctx, main_command=False))
    ]

    return _bazel_command(ctx, params)

def analyze_bazel_command(ctx: Context, profile_path):
    params = [
        "analyze-profile",
        profile_path
    ]

    return _bazel_command(ctx, params)


def _inject_command_flags(user_args: List[str], flags: Iterable[str]) -> list:
    final_arguments = []
    command_found = False


    # WARNING: this logic is flawed as it assumes that the first argument that doens't start with `--` is the command
    # This is corrent for the case of `bazel --some_flag=some_value build //...`
    # This is incorrect for the case of `bazel --some_flag some_value build //...` as it will think that some_value is the command
    for user_arg in user_args:
        if user_arg.startswith(WixFlags.PREFIX):
            continue
        elif not user_arg.startswith("--") and not command_found:
            command_found = True  # assuming this arg to be the bazel command
            final_arguments.append(user_arg)
            final_arguments.extend(flags)  # builtin flags has lowest priority
        else:
            final_arguments.append(user_arg)

    return final_arguments


def _use_no_sandbox_test_strategy(ctx: Context):
    if ctx.bazel_command() != "test":
        return False

    test_strategy_var_name = "WIX_BAZEL_USE_SANDBOX_TEST_STRATEGY"
    if test_strategy_var_name in os.environ:
        return os.environ[test_strategy_var_name].lower() not in ["yes", "true", "1"]

    for arg in ctx.user_args:
        if arg.startswith("--tool_tag=ijwb:"):
            return True

    return False


def _generate_startup_flags(ctx: Context) -> Iterable[str]:
    managed_rc_path = os.path.expanduser(
        os.path.join(ctx.config_dir, "managed.bazelrc")
    )

    output_base_dir = os.environ.get(OUTPUT_BASE_DIR)
    if output_base_dir:
        yield "--output_base={output_dir}".format(output_dir=output_base_dir)

    if os.path.exists(managed_rc_path):
        yield "--bazelrc={rc_file_path}".format(rc_file_path=managed_rc_path)


def _try_generate_engflow_bes_metadata(ctx: Context) -> Optional[List[str]]:
    rbe_active_provider = os.environ.get(ENV_VAR_RBE_ACTIVE_PROVIDER)
    if rbe_active_provider != "engflow":
        return []

    bes_metadata = []
    buildkite_build_url = os.environ["BUILDKITE_BUILD_URL"]
    if buildkite_build_url and len(buildkite_build_url) > 0:
        bes_metadata.append(f"--bes_keywords=engflow:CiCdUri={buildkite_build_url}")

    buildkite_pipeline_name = os.environ["BUILDKITE_PIPELINE_SLUG"]
    if buildkite_pipeline_name and len(buildkite_pipeline_name) > 0:
        bes_metadata.append(f"--bes_keywords=engflow:CiCdPipelineName='{buildkite_pipeline_name}'")

    buildkite_build_message = os.environ["BUILDKITE_MESSAGE"]
    if buildkite_build_message and len(buildkite_build_message) > 0:
        bes_metadata.append(f"--bes_keywords=engflow:CiCdJobName='{buildkite_build_message}'")

    return bes_metadata

def _try_resolve_engflow_secrets(ctx: Context) -> Optional[List[str]]:
    secret_flags = []

    engflow_api_key_env_var_name = "API_KEY_ENGFLOW"
    api_key_engflow = os.environ.get(engflow_api_key_env_var_name)
    if api_key_engflow is not None:
        ctx.logger.info("Identified EngFlow API Token, adding as Bazel flag.")
        secret_flags.append(f"--bes_header=x-engflow-auth-method=jwt-v0")
        secret_flags.append(f"--bes_header=x-engflow-auth-token={api_key_engflow}")
        secret_flags.append(f"--remote_header=x-engflow-auth-method=jwt-v0")
        secret_flags.append(f"--remote_header=x-engflow-auth-token={api_key_engflow}")
        return secret_flags

    if ctx.engflow_tls_key_filepath is not None and ctx.engflow_tls_crt_filepath is not None:
        if os.path.exists(ctx.engflow_tls_key_filepath) and os.path.exists(ctx.engflow_tls_crt_filepath):
            ctx.logger.info("Identified EngFlow TLS crt and key, adding as Bazel flags.")
            secret_flags.append(f"--tls_client_key={ctx.engflow_tls_key_filepath}")
            secret_flags.append(f"--tls_client_certificate={ctx.engflow_tls_crt_filepath}")
            return secret_flags
        else:
            ctx.logger.info(f"No EngFlow TLS crt and key could be found on machine. path: {ctx.engflow_tls_key_filepath}")

    ctx.logger.warning(f"No EngFlow secrets declared on Bazel wrapper config")
    return None

def _try_resolve_buildbuddy_secrets(ctx: Context) -> Optional[List[str]]:
    secret_flags = []
    buildbuddy_api_key_env_var_name = "API_KEY_BUILDBUDDY"
    api_key_buildbuddy = os.environ.get(buildbuddy_api_key_env_var_name)
    if api_key_buildbuddy is not None:
        ctx.logger.info("Identified a BuildBuddy secret API KEY, adding as a Bazel flag. flag name: --remote_header")
        secret_flags.append(f"--remote_header={api_key_buildbuddy}")
        return secret_flags
    else:
        ctx.logger.debug("No BuildBuddy API KEY secret identified via env var API_KEY_BUILDBUDDY, no RBE access should be available")
    return None

def _generate_bazel_flags_with_secrets(ctx: Context) -> Iterable[str]:
    """
    RBE providers secrets priority:
      1. EngFlow
      2. BuildBuddy
    """
    rbe_active_provider = os.environ.get(ENV_VAR_RBE_ACTIVE_PROVIDER)
    if rbe_active_provider == "engflow":
        engflow_secerts = _try_resolve_engflow_secrets(ctx)
        if engflow_secerts and len(engflow_secerts) > 0:
            return engflow_secerts
    elif rbe_active_provider == "google-rbe":
        ctx.logger.error("Google RBE is not yet supported")
    # elif rbe_active_provider == "buildbuddy":
    else:
        buildbuddy_secrets = _try_resolve_buildbuddy_secrets(ctx)
        if buildbuddy_secrets and len(buildbuddy_secrets) > 0:
            return buildbuddy_secrets

    return iter(())

def _generate_command_flags(ctx: Context, main_command=True) -> Iterable[str]:
    if not ctx.is_bypassed_command:
        yield from _generate_bazel_flags_with_secrets(ctx)
        yield from _try_generate_engflow_bes_metadata(ctx)
        yield from bi.resolve_profile_flags(ctx)

        if is_local_dev(ctx):
            yield "--config=localdev"
            yield from remotecache.resolve_remote_cache_flags(ctx)
        else:  # this is legacy behaviour that will be dropped in the future.
            yield "--config=wix"

        if is_local_dev(ctx) and main_command:
            yield f"--build_event_binary_file={ctx.bep_file_path}"
            yield "--nobuild_event_binary_file_path_conversion"

        if _use_no_sandbox_test_strategy(ctx):
            yield "--config=sandbox-off"

        yield "--config=overrides"