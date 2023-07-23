import json
import multiprocessing
import os
import platform
import re
import time
import sys
from pathlib import Path
from uuid import uuid4
from pathlib import Path
import subprocess

from bazelwrapper.context import Context
from bazelwrapper.utils.env_vars import non_empty_env_var_value
from bazelwrapper.utils.feature_flags import Flag
from bazelwrapper.utils.safe_exec import safe

from bazelwrapper.vmr_interop import BazelVmrInterop
from virtualmonorepo.vector import VectorData

_DEFAULT_ENV_TYPE = "default"
_DEVEX_ENV_TYPE_ENV_VAR_NAME = "WIX_DEVEX_ENVTYPE"
_DEVEX_ENV_ID_VAR_NAME = "WIX_DEVEX_ENV_ID"

_ID_REGEX_PATTERN = "^([a-z0-9])([a-z0-9-]{4,49})$"
_ENV_ID_VALIDATION_REGEX = re.compile(pattern=_ID_REGEX_PATTERN)

_TOOLS_VERSION_FILE_PATH = os.path.join("tools", "info", ".toolsversion")

# this path is coordinated with wixtaller
_WIXTALLER_SUMMARY_FILE_NAME = "last_summary.json"

LOCAL_DEV_FLAG = Flag(
    full_cli_flag="--wix_localdev",
    marker_file_name=".localdev",
    env_var_name="WIX_DEVEX_LOCALDEV_WORKSTATION",
    default_value=False,
)


def is_local_dev(ctx: Context):
    return LOCAL_DEV_FLAG.on(ctx)


def get_id(ctx: Context):
    return non_empty_env_var_value(
        name=_DEVEX_ENV_ID_VAR_NAME,
        default_fn=_resolve_default_id,
        ctx=ctx
    )


def build_info_snapshot(ctx: Context):
    return {
        "build_command": ctx.bazel_command(),
        "build_command_targets": " ".join(ctx.bazel_command_targets()),
        "correlation_id": ctx.unique_id,
        "timestamp": time.time(),
        "env_id": get_id(ctx),
        "env_type": resolve_env_type(ctx),
        "build_type": resolve_build_type(ctx),
        "tools_version": safe(fn=resolve_tools_version, default_value=None, ctx=ctx),
        "wixtaller_version": safe(fn=resolve_wixtaller_version, default_value=None, ctx=ctx),
        "vmr_repo_rule_type": safe(fn=resolve_vmr_repo_rule_type, default_value=None, ctx=ctx),
        "vmr_build_post_invalidation": safe(fn=resolve_vmr_build_post_invalidation, default_value=False, ctx=ctx),
        "vmr_vector_mode": safe(fn=resolve_vmr_vector_mode, default_value=None, ctx=ctx),
        "os_family": platform.system().lower(),
        "os_version": safe(_os_version, "", ctx),
        "cpus": multiprocessing.cpu_count(),
        "total_ram": safe(_total_memory, -1, ctx),
        "proccessor_architecture": safe(resolve_architecture, "", ctx),
        "python_version": platform.python_version(),
        "repository": safe(_repository, "", ctx),
        "remote_cache_provider": safe(fn=resolve_remote_cache_provider, default_value=None, ctx=ctx),
    }

def resolve_architecture(ctx: Context) -> str:
    return platform.machine() or platform.processor() or platform.architecture()[0]

def create_envid(path, ctx: Context) -> str:
    ctx.logger.debug("Creating a new envid file '{}'".format(path))

    uid = uuid4()
    with open(path, "w") as file:
        file.write(str(uid))

    return str(uid)


def resolve_env_type(ctx: Context):
    return non_empty_env_var_value(
        name=_DEVEX_ENV_TYPE_ENV_VAR_NAME,
        default_fn=lambda x: _DEFAULT_ENV_TYPE,
        ctx=ctx
    )

def resolve_build_type(ctx: Context) -> str:
    return non_empty_env_var_value(
        name="WIX_DEVEX_BUILD_TYPE",
        default_fn=lambda x: "",
        ctx=ctx
    )


def resolve_tools_version(ctx: Context):
    version_file_path = os.path.join(ctx.workspace_dir, _TOOLS_VERSION_FILE_PATH)
    resolved_tools_version = None
    try:
        if os.path.exists(version_file_path):
            with open(version_file_path) as version_file:
                resolved_tools_version = version_file.read().strip()

    except OSError as e:
        ctx.logger.warning("Failed to read tools version from '{}'".format(version_file), e)
        ctx.logger.debug("", e)

    return resolved_tools_version


def resolve_vmr_repo_rule_type(ctx: Context):
    env_var = os.getenv("VMR_REPO_RULE_TYPE", "http_archive")
    ctx.logger.debug("Virtual monorepo repository rule type is set to: {}".format(env_var))
    return env_var


def resolve_vmr_build_post_invalidation(ctx: Context):
    is_invalidated = False
    home_folder = str(Path.home())
    vmr_invalidation_marker_file_path = "{}/.config/wix/virtual-monorepo/ext/vmr-invalidation-marker".format(
        home_folder)
    try:
        if os.path.exists(vmr_invalidation_marker_file_path):
            is_invalidated = True
            os.remove(vmr_invalidation_marker_file_path)
            ctx.logger.debug("Identified that a virtual monorepo invalidation occurred, "
                             "reported and removed the marker file for future builds")
        else:
            ctx.logger.debug("Did not identify that a virtual monorepo invalidation occurred")

    except Exception as e:
        ctx.logger.debug("Failed to identify VMR marker file. path: {}, error: {}".format(
            vmr_invalidation_marker_file_path, e))

    return is_invalidated

def resolve_vmr_vector_mode(ctx: Context):
    vector_mode = "LATEST"

    try:
        # Available build types:
        #  - branch_only   (branch vector override or lock file based)
        #  - build_master  (lock file based)
        #  - cross_repo    (lock file based)
        #  - merge_dry_run (lock file based)
        build_type = os.getenv("BUILD_TYPE", "")

        # VMR client relies on git branch name to compose a vector override file name <branch_name>_<vector_suffix>.bzl
        # Buildkite is using a detached HEAD with commit revision, as a result the git client won't return
        # the expected branch name. To overcome this limitation, we are reading the branch name from env var.
        build_branch_override = os.getenv("BUILDKITE_BRANCH", "http_archive")

        vector_data: VectorData = BazelVmrInterop.read_local_vector(
            ctx=ctx, is_silent=True, metadata_only=True,
            build_type=build_type, build_branch_override=build_branch_override)

        if vector_data is not None and vector_data.metadata is not None:
            vector_mode = vector_data.metadata.vector_mode
        else:
            ctx.logger.debug("Vector data retrieval was successful, but vector metadata was not resolved. "
                             "Resolved vector data: {}", vector_data)
    except Exception as e:
        ctx.logger.debug("Failed to load VMR vector. Error: {}".format(e))

    return vector_mode

def resolve_remote_cache_provider(ctx: Context):
    if _get_os == 'linux' and 'REMOTE_CACHE_USE_WIX_CACHE_POPS' not in os.environ:
        return "BuildBuddy"
    else:
        return "WixCachePops"

def resolve_wixtaller_version(ctx: Context):
    wixtaller_summary_file_path = os.path.join(ctx.wixtaller_config_dir, _WIXTALLER_SUMMARY_FILE_NAME)
    if os.path.exists(wixtaller_summary_file_path):
        with open(wixtaller_summary_file_path) as json_file:
            data = json.load(json_file)
            extracted_wixtaller_version = data["version"]
            ctx.logger.debug("Last recorded wixtaller version: {}".format(extracted_wixtaller_version))

            return extracted_wixtaller_version
    else:
        ctx.logger.debug("Wixtaller summary file '{}' does not exist".format(wixtaller_summary_file_path))
        return None


def _resolve_default_id(ctx: Context):
    envid_path = os.path.join(ctx.config_dir, ".envid")
    _id = None

    if os.path.exists(envid_path):
        with open(envid_path) as file:
            content = file.read()

            id_validation_match = _ENV_ID_VALIDATION_REGEX.match(string=content)
            if id_validation_match is not None:
                _id = id_validation_match.string

            else:
                ctx.logger.debug("Invalid env id value parsed from .envid file. '{}'".format(content))
                ctx.logger.debug("Env ID should match the pattern: '{}'".format(_ID_REGEX_PATTERN))

    else:
        ctx.logger.debug("'{}' not found and will be generated.".format(envid_path))

    if _id is None:
        _id = create_envid(envid_path, ctx)

    return _id


def _os_version(ctx: Context):
    system = platform.system().lower()
    if 'darwin' == system:
        return platform.mac_ver()[0]
    elif 'linux' == system:
        if os.path.exists('/usr/bin/lsb_release'):
            return subprocess.check_output(["/usr/bin/lsb_release", "-d"]).decode("utf-8").strip().split("\n")[0].split("\t")[1]
        else:
            return "{},{},{}".format(platform.system(), platform.release(), platform.version())
    else:
        return ",".join(platform.uname())

def _total_memory(ctx: Context) -> int:
    mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')  # e.g. 4015976448
    return int(mem_bytes/(1024.**3))

def _repository(ctx: Context) -> str:
    workspace_file_path = os.path.join(ctx.workspace_dir, "WORKSPACE")
    with open(workspace_file_path, "r") as workspace_file:
        for line in workspace_file:
            match = re.match("""\s*repository_name\s*=\s*"([^"]+)"\s*""", line)
            if match:
                return match.group(1)

def _get_os(ctx: Context) -> str:
    return sys.platform