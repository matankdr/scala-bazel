import json
import os
from shutil import disk_usage
from typing import Generator

from bazelwrapper.context import Context
from bazelwrapper.env.info import resolve_wixtaller_version
from bazelwrapper.utils.feature_flags import Flag
from bazelwrapper.utils.safe_exec import safe

_FALLBACK_ACTUAL_VERSION = "0.0.0"

_env_checks_disabled_flag = Flag(
    env_var_name="WIX_BAZEL_WRAPPER_ENV_CHECK_DISABLED",
    env_var_required_value="1"
)

_FREE_DISK_SPACE_WARNING_THRESHOLD_IN_GIGABYTES = 10


def inspect(ctx: Context) -> Generator:
    """
    Returns a generator of inspection warning messages
    """

    yield_ij_troubleshooting_message = False

    if _env_checks_enabled(ctx):

        free_disk_space = _free_disk_space_gb()
        ctx.logger.debug("Free disk space: {}GB".format(free_disk_space))
        ctx.logger.debug("Disk space warning threshold is {}GB".format(_FREE_DISK_SPACE_WARNING_THRESHOLD_IN_GIGABYTES))

        if _free_disk_space_gb() < _FREE_DISK_SPACE_WARNING_THRESHOLD_IN_GIGABYTES:
            yield "Your system has only {actual}GB of free disk space under '/'. " \
                  "You may want to run some cleanups soon to avoid problems." \
                .format(actual=free_disk_space)

        if ctx.bazel_command() in ["build", "test"] and "//..." in ctx.user_args:
            yield_ij_troubleshooting_message = True
            yield "Building the entire workspace is not recommended for obvious performance reasons! See: " \
                  "https://ci-kb.wixanswers.com/en/article/local-devex " \
                  "for Bazel and IntelliJ related docs."

        if ctx.bazel_command() == "clean":
            yield_ij_troubleshooting_message = True
            yield \
                "'clean' and 'clean --expunge' is rarely the cure for local development issues and will cost you a " \
                "lot of time."

        if yield_ij_troubleshooting_message:
            yield \
                "Please see: " \
                "https://github.com/wix-private/wix-intellij-plugin/blob/master/docs/plugin-troubleshooting.md for " \
                "IntelliJ issues troubleshooting."

        if is_update_required(ctx):
            yield \
                "[ACTION REQUIRED] Your Bazel environment needs to be updated! Please run 'wixtaller' from your " \
                "terminal and follow the instructions. See: " \
                "https://github.com/wix-private/wix-ci/blob/master/localdev_new/tools/wixtaller/docs/" \
                "wixtaller-getting-started.md"


def is_update_required(ctx: Context) -> bool:
    if _env_checks_enabled(ctx):
        return safe(
            fn=_unsafe_is_update_required,
            default_value=False,
            ctx=ctx
        )
    else:
        return False


def _free_disk_space_gb():
    _, _, free = disk_usage("/")
    return _b_to_gb(free)


def _env_checks_enabled(ctx):
    return not _env_checks_disabled_flag.on(ctx)


def _unsafe_is_update_required(ctx):
    ctx.logger.debug("Running environment compatibility check...")

    actual_wixtaller_version = safe(
        fn=resolve_wixtaller_version,
        default_value=_FALLBACK_ACTUAL_VERSION,
        ctx=ctx)

    if actual_wixtaller_version is None:
        actual_wixtaller_version = _FALLBACK_ACTUAL_VERSION

    return safe(
        fn=_is_update_required_fn(actual_wixtaller_version),
        default_value=True,
        ctx=ctx
    )


def _minimum_required_wixtaller_version(ctx: Context):
    config_file_path = os.path.join(ctx.workspace_dir, "tools", "info", "wixtaller.json")

    with open(config_file_path, mode='r') as wixtaller_json_file:
        return json.load(wixtaller_json_file)["minimumRequiredVersion"]


def _is_update_required_fn(actual_wixtaller_version: str):
    def run(ctx: Context):
        expected_major, expected_minor, expected_patch = _minimum_required_wixtaller_version(ctx).split(".")
        actual_major, actual_minor, actual_patch = actual_wixtaller_version.split(".")

        ctx.logger.debug("Expected minimum wixtaller version: {maj}.{min}.{patch}".format(
            maj=expected_major,
            min=expected_minor,
            patch=expected_patch
        ))

        return \
            int(actual_major) != int(expected_major) or \
            int(actual_minor) != int(expected_minor) or \
            int(actual_patch) < int(expected_patch)

    return run


def _b_to_gb(value):
    return int(value / (1024 ** 3))
