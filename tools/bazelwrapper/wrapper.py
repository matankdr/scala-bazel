import json
import os
import signal
import subprocess
import sys

#
# IMPORTANT:
# We cannot rely on the existence of user defined environment variables in the bazel wrapper, because we don't have any
# guarantee that shell environment variables will be present in any bazel environment (generally it depends on the
# parent process environment, user and such)
#
from logging import DEBUG

import bazelwrapper.bi.wrapper_api as bi
from bazelwrapper.bazelcommand import build_bazel_command, build_bep_parser_bazel_command
from bazelwrapper.cmd_interceptor import intercept_command
from bazelwrapper.context import create_cli_context, Context
from bazelwrapper.env.inspector import inspect
from bazelwrapper.vmr_interop import BazelVmrInterop
from bazelwrapper.env.info import is_local_dev
import tempfile

# Dummy commit for re-triggering across the VMR repos (due to Kafka VMR stale topics issue)
custom_bazel_env = {
    # here we can take control over the PATH or set env variables for other tools and bazel rules.
    # these are currently laid over the global shell env.

    # NOTE! bazelisk 'USE_BAZEL_VERSION' cannot be used in a wrapper script, because when that script executes, bazelisk
    # has already determined the version and we do not want to make recursive calls, or implement bazelisk logic
    # ourselves.
}


def bazel_env(context: Context):
    final_custom_vars = {**custom_bazel_env, **try_load_custom_build_env_variables(context)}
    return {**os.environ, **final_custom_vars}


def update_second_party_repositories(env, ctx: Context):

    # Do not try to resolve a VMR vector when analyzing a build profile since
    # the build already executed
    if ctx.bazel_command() in ["analyze-profile"]:
        return

    def suppress_prints():
        return ctx.bazel_command() in ["info", "query", "aquery", "cquery"]

    if not ctx.is_bypassed_command:
        if env.get("VMR_REPO_RULE_TYPE", "") == "git_cached_repository":
            # Log git version to stdout to understand where it originates from XCode or manually installed
            run_git_version_safe(ctx)

        # CI relies on a Buildkite VMR plugin to resolve a vector from env vars
        #   - gcb-trigger sending the vector via request meta-data i.e. VMR_<repo_name> for each 2nd party
        #   - Buildkite VMR plugin reads the meta-data and create a 2nd_parties vector lock file
        #     under path: <WORKSPACE>/tools/2nd_party_resolved_dependencies.bzl.lock

        # VMR client should run in order to align vector symlinks (local, override, locked)

        # Available build types:
        #  - branch_only   (branch vector override or lock file based)
        #  - build_master  (lock file based)
        #  - cross_repo    (lock file based)
        #  - merge_dry_run (lock file based)
        build_type = env.get("BUILD_TYPE", "")

        # Some platforms that run a Bazel build don't have access to bo.wix.com such as Buildkite
        # We have to allow an override for the VMR vector provider URL
        # to allow vmr-server communication (through DC 42 for example)
        default_vmr_vector_url = "https://bo.wix.com/virtual-mono-repo-server/vector?name=bazel"
        vmr_vector_provider_url = env.get("VMR_VECTOR_PROVIDER_URL", default_vmr_vector_url)
        if default_vmr_vector_url != vmr_vector_provider_url:
            ctx.logger.info(f"Overriding VMR vector provider URL. path: {vmr_vector_provider_url}")

        # VMR client relies on git branch name to compose a vector override file name <branch_name>_<vector_suffix>.bzl
        # Buildkite is using a detached HEAD with commit revision, as a result the git client won't return
        # the expected branch name. To overcome this limitation, we are reading the branch name from env var.
        build_branch_override = env.get("BUILDKITE_BRANCH", None)

        BazelVmrInterop.resolve_vector(
            ctx=ctx,
            vmr_vector_provider_url=vmr_vector_provider_url,
            build_type=build_type,
            is_silent=suppress_prints(),
            build_branch_override=build_branch_override)


def try_load_custom_build_env_variables(context: Context):
    env_file_path = os.path.join(context.config_base_dir, ".bazelbuildenv.json")

    try:
        with open(env_file_path) as env_file:
            env_vars = json.load(env_file)
    except FileNotFoundError as err:
        context.logger.debug(
            "Failed to load custom build env variables. {error}".format(
                error=err
            )
        )
        env_vars = {}

    return env_vars


def main():
    context = create_cli_context()

    intercept_command(context)

    bazel_exit_code = -1
    try:
        bazel_exit_code = _execute_bazel_command(context)

    except BaseException as err:
        bazel_exit_code = 1
        context.logger.debug("Failed to execute bazel command. Error: {error}".format(error=err))

    finally:
        _run_post_bazel_command_actions(bazel_exit_code, context)

    exit(bazel_exit_code)


def _run_post_bazel_command_actions(bazel_exit_code, context: Context):
    context.logger.debug("Bazel finished with return code {bazel_exit_code}".format(bazel_exit_code=bazel_exit_code))

    profile_path = bi.maybe_create_profile_info_file(bazel_exit_code, context)
    if profile_path:
        bi.start_bi_reporter(context, context.bi_reporter_run_sync)

    if is_local_dev(context) and context.bazel_command() in ("build", "test"):
        _execute_bep_parser_bazel_command(context)

    for warning in inspect(context):
        context.logger.warn(warning)

def _execute_bazel_command(context: Context):
    bazel_command = build_bazel_command(context)

    env = bazel_env(context)
    if context.logger.isEnabledFor(DEBUG):
        context.logger.debug("Resolved build env: {envars}".format(envars=json.dumps(env, indent=2)))

    update_second_party_repositories(env, context)

    p = None
    try:
        p = subprocess.Popen(args=bazel_command, env=env)
        return p.wait()

    except KeyboardInterrupt:
        context.logger.debug("Keyboard interrupt received. Sending 'SIGINT' to the bazel process.")
        p.send_signal(signal.SIGINT)

        return p.wait()

def _execute_bep_parser_bazel_command(context: Context):
    bazel_command = build_bep_parser_bazel_command(context)

    env = bazel_env(context)

    if context.logger.isEnabledFor(DEBUG):
        context.logger.debug("Resolved build env: {envars}".format(envars=json.dumps(env, indent=2)))

    p = None
    try:
        p = subprocess.Popen(args=bazel_command, env=env)
        return p.wait()

    except KeyboardInterrupt:
        context.logger.debug("Keyboard interrupt received. Sending 'SIGINT' to the bazel process.")
        p.send_signal(signal.SIGINT)

        return p.wait()


FOLDER_OF_SCRIPT = os.path.dirname(sys.argv[0])


def run_shell(ctx, splitted_command, fail_msg):
    ctx.logger.debug("Running:\t{}".format(' '.join(splitted_command)))

    process = subprocess.Popen(splitted_command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               cwd=FOLDER_OF_SCRIPT)

    encoded_out, err = process.communicate()
    out = encoded_out.decode("utf-8")
    ctx.logger.info(out)
    if err:
        msg = "{}. stderr = {}".format(fail_msg, err)
        ctx.logger.error(msg)
        raise Exception(msg)

    return out


def run_git_version_safe(ctx: Context):
    git_ver_cmd = ['git', "version"]
    try:
        run_shell(ctx, git_ver_cmd, "could not resolve git version")
    except Exception as ex:
        ctx.logger.debug("git version failed. error: {}", ex)
        # Do nothing, do not fail
        pass

