from logging import Logger
import logging
import os
import platform
import sys
import tempfile
from uuid import uuid4
from typing import List, Optional
from pathlib import Path

from bazelwrapper.utils.list_utils import split_after
from bazelwrapper.utils.logging import create_logger


#  underscore flags notation follows bazel's practice
class WixFlags:
    PREFIX = "--wix"
    DEBUG = "{prefix}_debug".format(prefix=PREFIX)
    BI_REPORTER_RUN_SYNC = "{prefix}_bi_reporter_run_sync".format(prefix=PREFIX)
    PROFILE_PATH_OVERRIDE = "{prefix}_profile_path_override".format(prefix=PREFIX)

_BYPASSED_COMMANDS = {"version", "shutdown"}

_WIXTALLER_CONFIG_DIR_PATH = ".config/wix/wixtaller"
_WRAPPER_CONFIG_DIR_PATH = ".config/wix/bazelwrapper"

_CONFIG_BASE_DIR = os.path.expanduser(
    os.getenv("WIX_DEVEX_CONFIG_BASE_DIR", "~")
)

OUTPUT_BASE_DIR = "BAZEL_OUTPUT_BASE_DIR"

_GCLOUD_CREDS_FILEPATH = "~/.config/gcloud/application_default_credentials.json"
_BUILDBUDDY_API_KEY_FILEPATH = "~/.config/bazelwrapper/buildbuddy_remote_cache_key.txt"

ENV_VAR_RBE_ACTIVE_PROVIDER = "RBE_ACTIVE_PROVIDER"
ENGFLOW_CONFIG_ROOT = "~/.config/engflow-rbe"
_ENGFLOW_API_KEY_FILEPATH = f"{ENGFLOW_CONFIG_ROOT}/engflow_remote_cache_key.txt"
_ENGFLOW_TLS_KEY_FILEPATH = f"{ENGFLOW_CONFIG_ROOT}/engflow.key"
_ENGFLOW_TLS_CRT_FILEPATH = f"{ENGFLOW_CONFIG_ROOT}/engflow.crt"

class Context:
    def __init__(self,
                 user_args: List[str],
                 config_base_dir=_CONFIG_BASE_DIR,
                 system_name=platform.system(),
                 workspace_dir=None,
                 debug=False,
                 bypassed_commands=None,
                 logger: Optional[Logger]=None,
                 bi_reporter_run_sync: bool=True,
                 profile_path_override: Optional[str]=None,
                 bep_file_path: Optional[str]=None):
        if bypassed_commands is None:
            bypassed_commands = _BYPASSED_COMMANDS

        log_level = logging.DEBUG if debug else logging.INFO
        self.logger = logger if logger is not None else create_logger(log_level)
        self.user_args = user_args
        self.config_base_dir = config_base_dir
        self.gcloud_creds_filepath = os.path.expanduser(_GCLOUD_CREDS_FILEPATH)
        self.buildbuddy_api_key_filepath = os.path.expanduser(_BUILDBUDDY_API_KEY_FILEPATH)
        self.engflow_api_key_filepath = os.path.expanduser(_ENGFLOW_API_KEY_FILEPATH)
        self.engflow_tls_key_filepath = os.path.expanduser(_ENGFLOW_TLS_KEY_FILEPATH)
        self.engflow_tls_crt_filepath = os.path.expanduser(_ENGFLOW_TLS_CRT_FILEPATH)
        self.system_name = system_name
        self.workspace_dir = workspace_dir
        self.wixtaller_config_dir = os.path.join(self.config_base_dir, _WIXTALLER_CONFIG_DIR_PATH)
        self.config_dir = config_dir(config_base_dir)
        self._bazel_command = self._find_bazel_command()
        self.is_bypassed_command = bypassed_commands.__contains__(self._bazel_command)
        self.bi_reporter_run_sync = bi_reporter_run_sync
        self.unique_id = str(uuid4())
        self.profile_path_override = profile_path_override
        self.bep_file_path = bep_file_path

        if self.is_bypassed_command:
            self.logger.debug("This command is expected to be bypassed by the wrapper.")

    def bazel_command(self) -> Optional[str]:
        if self._bazel_command:
            return self._bazel_command.lower()
        else:
            return self._bazel_command

    # BUG: given "bazel --option option_value build //...", it will take "option_value" as the bazel command. It should take "build".
    # The problem is that you cannot distinguish beetwen flags and options.
    # Option to fix this is: have a static list of all the build commands and match it with that, and then fallback to this value of not found.
    def _find_bazel_command(self):
        # finding the first argument that is not a flag
        for arg in self.user_args:
            if not arg.startswith("--"):
                return arg

        return None

    # BUG: given "bazel build //... --option option_value ", it will take "//..." and "option_value"
    # The problem is that you cannot distinguish beetwen flags and options.
    # Option to fix this is: have a static list of all the build commands and match it with that?
    def bazel_command_targets(self):
        if self.bazel_command() in ("build", "test"):
            after_command = list(split_after(self.user_args, lambda v: v == self.bazel_command()))[-1]
            return [arg for arg in after_command if not arg.startswith("--")]
        return []

def config_dir(config_base_dir=_CONFIG_BASE_DIR):
    return os.path.join(config_base_dir, _WRAPPER_CONFIG_DIR_PATH)

def _extract_profile_path_override(user_args: List[str]):
    # PROFILE_PATH_OVERRIDE is in the form of --wix_profile_path_override=<path>
    return _extract_property_value(WixFlags.PROFILE_PATH_OVERRIDE, user_args)

def _extract_bep_file_path(user_args: List[str]):
    bep_file = _extract_property_value('build_event_binary_file', user_args, False)

    if bep_file is None:
        bep_file_dir = tempfile.gettempdir()
        bep_file_name = tempfile.gettempprefix()
        bep_file = Path(bep_file_dir, bep_file_name).with_suffix(".bes")

    return bep_file

def _extract_property_value(name, user_args, remove_arg=True):
    property_value = next((arg for arg in user_args if name in arg), None)
    if property_value is not None:
        if remove_arg:
            user_args.remove(property_value)
        property_value = property_value.split("=")[1]
    return property_value

def create_cli_context(logger=None):
    user_args = sys.argv[1:]
    debug = WixFlags.DEBUG in user_args
    bi_reporter_run_sync = WixFlags.BI_REPORTER_RUN_SYNC in user_args
    profile_path_override = _extract_profile_path_override(user_args)
    bep_file_path = _extract_bep_file_path(user_args)

    if profile_path_override and not profile_path_override.endswith(".prof.gz"):
        # this was done because bi profile processor needs the file to end with .prof.gz :/
        raise Exception("Profile path override must end with .prof.gz")

    ctx = Context(
        user_args=user_args,
        debug=debug,
        workspace_dir=_resolve_workspace_dir(),
        logger=logger,
        bi_reporter_run_sync=bi_reporter_run_sync,
        profile_path_override=profile_path_override,
        bep_file_path=bep_file_path
    )

    ensure_directories(ctx)

    return ctx


def ensure_directories(ctx):
    assert os.path.exists(ctx.config_base_dir), "The configuration base directory '{name}' is expected to exist." \
        .format(name=ctx.config_base_dir)

    os.makedirs(ctx.config_dir, exist_ok=True)
    os.makedirs(ctx.wixtaller_config_dir, exist_ok=True)


def _resolve_workspace_dir() -> str:
    current_dir = os.getcwd()
    ws_dir = current_dir
    while ws_dir != "/":
        if os.path.exists(os.path.join(ws_dir, "WORKSPACE")):
            return ws_dir
        else:
            ws_dir = os.path.abspath(os.path.join(ws_dir, os.pardir))

    return ws_dir
