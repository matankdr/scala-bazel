import json
import os
from typing import List, Optional

from bazelwrapper.bi.profile import PROFILE_INFO_FILE_EXTENSION, \
    profiles_dir_path, pending_profile_path_for, profile_path
from bazelwrapper.bi.schema import build_event_info_with
from bazelwrapper.context import Context
from bazelwrapper.utils.feature_flags import Flag
from bazelwrapper.utils.subproc_launcher import PySubprocessLauncher
from bazelwrapper.bi.entrypoint import main as run_reporter

_APPLICABLE_COMMANDS = ['build', 'test', 'run', 'clean']

# A cascading flag to turn on BI reporting
_bi_flag = Flag(
    full_cli_flag="--wix_bi",
    marker_file_name=".bienabled",
    env_var_name="WIX_DEVEX_BI_ENABLED",
    default_value=False,
)

_bi_noreporter_flag = Flag(
    full_cli_flag="--wix_bi_noreport",
    env_var_name="WIX_DEVEX_BI_REPORT_DISABLED",
    default_value=False,
)


def resolve_profile_flags(ctx: Context) -> List[str]:
    def is_bi_enabled() -> bool:
        return _bi_flag.on(ctx)

    if is_bi_enabled() and \
            ctx.bazel_command() in _APPLICABLE_COMMANDS and \
            not _is_user_request_profile(ctx.user_args):

        os.makedirs(profiles_dir_path(ctx), exist_ok=True)
        if ctx.profile_path_override:
            profile_file = ctx.profile_path_override
        else:
            profile_file = pending_profile_path_for(profile_path(ctx))

        return [
            "--profile=" + profile_file,
            "--experimental_profile_include_target_label"
        ]
    else:
        return []


def maybe_create_profile_info_file(bazel_exit_code: int, ctx: Context) -> Optional[str]:
    if ctx.profile_path_override:
        _create_build_info_file(ctx.profile_path_override, bazel_exit_code, ctx)
        return ctx.profile_path_override

    path = profile_path(ctx)
    pending_profile_path = pending_profile_path_for(path)

    # Only launch the reporter process if there is a profile file to process for the current command.
    if os.path.exists(pending_profile_path):
        os.rename(pending_profile_path, path)
        _create_build_info_file(path, bazel_exit_code, ctx)
        return path
    return None


def start_bi_reporter(ctx: Context, run_sync: bool):
    if _bi_noreporter_flag.off(ctx):
        if run_sync:
            run_reporter() # runs the reporter script main function directly
        else:
            _launch_bi_reporter(ctx) # creates a subprocess that runs the reporter script
            
    else:
        ctx.logger.debug("BI reporter is disabled and will not be executed.")

def _launch_bi_reporter(ctx: Context):
    launcher = PySubprocessLauncher(
        title="BI reporter",
        main_py_script_path=os.path.join(ctx.workspace_dir, 'tools', 'reporter')
    )
    launcher.launch(ctx)


def _create_build_info_file(prof_path: str, bazel_exit_code: int, ctx: Context):
    path = "{path}.{ext}".format(path=prof_path, ext=PROFILE_INFO_FILE_EXTENSION)

    ctx.logger.debug("Creating env info snapshot file '{path}'".format(path=path))

    with open(path, "w") as file:
        build_info = build_event_info_with(bazel_exit_code, ctx)

        json.dump(build_info, file, indent=2)


def _is_user_request_profile(user_args):
    for arg in user_args:
        if arg.startswith('--profile='):
            return True

    return False
