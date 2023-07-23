import gzip
import json
import os
import time
from os import path, listdir
from typing import Generator

from bazelwrapper.context import Context
from bazelwrapper.utils.env_vars import non_empty_env_var_value

PROFILE_INFO_FILE_EXTENSION = "info"
PROFILE_FILE_EXTENSION = "prof.gz"
PENDING_PROFILE_FILE_EXTENSION = "prof-pending.gz"

_PROFILES_DIR = "profiles"
_STALE_FILE_INTERVAL_SEC = 60 * 60 * 24 * 2
_PROFILE_FILE_NAME_SUFFIX = "." + PROFILE_FILE_EXTENSION
_PENDING_PROFILE_FILE_NAME_SUFFIX = "." + PENDING_PROFILE_FILE_EXTENSION

_DEVEX_PROFILES_PATH_ENV_VAR_NAME = "WIX_DEVEX_BI_PROFILES_PATH"


def profiles_dir_path(ctx: Context):
    def default(c):
        return os.path.join(c.config_dir, _PROFILES_DIR)

    return os.path.expanduser(
        non_empty_env_var_value(
            name=_DEVEX_PROFILES_PATH_ENV_VAR_NAME,
            default_fn=default,
            ctx=ctx
        )
    )


def profile_path(ctx: Context):
    return os.path.join(profiles_dir_path(ctx), _profile_name(ctx))


def pending_profile_path_for(prof_path):
    return "{profile_path}.{ext}".format(
        profile_path=prof_path,
        ext=PENDING_PROFILE_FILE_EXTENSION
    )


def _profile_name(ctx: Context):
    return "{unique_id}.{ext}".format(unique_id=ctx.unique_id, ext=PROFILE_FILE_EXTENSION)


def _load_json_file(file_path):
    if file_path.endswith(".gz"):
        with gzip.open(file_path, "rt") as file:
            return json.load(file)
    else:
        with open(file_path) as file:
            return json.load(file)


class Profile:
    def __init__(self, file_path, info_file_path=None, info=None, data=None):
        self.file_path = file_path
        _info_filepath = info_file_path if info_file_path is not None else file_path
        self.info_file_path = "{filepath}.{ext}".format(filepath=_info_filepath, ext=PROFILE_INFO_FILE_EXTENSION)
        self._info = info
        self._data = data

    def is_ready(self) -> bool:
        return self.file_path.endswith(_PROFILE_FILE_NAME_SUFFIX) and \
               path.isfile(self.file_path) and \
               path.isfile(self.info_file_path)

    def is_stale(self) -> bool:
        is_profile_file = \
            self.file_path.endswith(_PROFILE_FILE_NAME_SUFFIX) or \
            self.file_path.endswith(_PENDING_PROFILE_FILE_NAME_SUFFIX)

        return is_profile_file and \
               path.isfile(self.file_path) and \
               path.getmtime(self.file_path) < time.time() - _STALE_FILE_INTERVAL_SEC

    def info(self):
        if self._info is None:
            self._info = _load_json_file(self.info_file_path)

        return self._info

    def data(self):
        if self._data is None:
            self._data = _load_json_file(self.file_path)

        return self._data

    def trace_events(self):
        return self.data()["traceEvents"]

    def build_id(self):
        return self.data()["otherData"]["build_id"]


def list_all_by_mtime(ctx: Context) -> Generator:
    profiles_path = profiles_dir_path(ctx)

    profile_paths = [
        path.join(profiles_path, name)
        for name in listdir(profiles_path)
        if name.endswith(_PROFILE_FILE_NAME_SUFFIX) or name.endswith(_PENDING_PROFILE_FILE_NAME_SUFFIX)
    ]
    profile_paths.sort(key=os.path.getmtime)

    return (Profile(profile_path) for profile_path in profile_paths)
