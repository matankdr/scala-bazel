import os
import sys
from abc import abstractmethod
from typing import Iterable
from bazelwrapper.context import Context
from bazelwrapper.utils.io_utils import IOUtils
from bazelwrapper.utils.string_utils import StringUtils

class _RemoteCacheFlagsResolver:
    """
    We used to have several different implementations of this class and decided to keep the abstraction.
    """

    # IMPORTANT:
    # This is used only for debug purposes! We cannot rely on the existence of user defined environment variables in the
    # bazel wrapper, because we don't have any guarantee that shell environment variables will be present in any bazel
    # environment (generally it depends on the parent process environment, user and such)
    _BAZEL_REMOTE_CACHE_BASE_URL_ENV_VAR_NAME = "WIX_BAZEL_REMOTE_CACHE_BASE_URL"

    # Things to consider when changing shared cache location:
    # 1. Does is server all offices well?
    # 2. Use http://www.gcping.com/ to determine which Google DC provides the best latency for all offices.
    # 3. Do you want to pre-warm the new location cache?
    _DEFAULT_REMOTE_CACHE_BASE_URL = "https://storage.googleapis.com"
    _DEFAULT_BUILDBUDDY_CACHE_URL = "grpcs://buildbuddy-remote.wixpress.com"
    _DEFAULT_ENGFLOW_CACHE_URL = "grpcs://engflow.wixpress.com"

    _DEFAULT_REMOTE_CACHE_BUCKET_NAME = "bazel-dev-remote-cache"

    # Used for testing in order to override the default bucket
    _BAZEL_REMOTE_CACHE_BUCKET_NAME_ENV_VAR_NAME = "WIX_BAZEL_REMOTE_CACHE_BUCKET_NAME"

    @abstractmethod
    def resolve(self, ctx: Context) -> Iterable[str]: pass

    @classmethod
    def _remote_cache_base_url(cls):
        return os.getenv(
            cls._BAZEL_REMOTE_CACHE_BASE_URL_ENV_VAR_NAME,
            cls._DEFAULT_REMOTE_CACHE_BASE_URL
        )

    @classmethod
    def _remote_cache_bucket_name(cls):
        return os.getenv(
            cls._BAZEL_REMOTE_CACHE_BUCKET_NAME_ENV_VAR_NAME,
            cls._DEFAULT_REMOTE_CACHE_BUCKET_NAME
        )

class WixCachePopsRemoteCacheFlagsResolver(_RemoteCacheFlagsResolver):
    def resolve(self, ctx: Context) -> Iterable[str]:
        flags = [
            "--remote_cache={base_url}/{bucket_name}".format(
                base_url=self._remote_cache_base_url(),
                bucket_name=self._remote_cache_bucket_name(),
            ),
            "--config=uniform_remote_cache"  # declared in 'tools/bazelrc/.bazelrc.managed.dev.env'
        ]

        if ctx.gcloud_creds_filepath and os.path.exists(ctx.gcloud_creds_filepath):
            flags.append("--google_credentials={}".format(ctx.gcloud_creds_filepath))
            ctx.logger.debug("GCloud credentials file was found, added as an additional bazel remote flag. path: {}".format(ctx.gcloud_creds_filepath))
        else:
            ctx.logger.debug("GCloud credentials file is missing, please run wixtaller. path: {}".format(ctx.gcloud_creds_filepath))

        return flags


class Collaborators:
    string_utils: StringUtils
    io: IOUtils

class FlagsResolverCollaborators(Collaborators):
    def __init__(self) -> None:
        self.string_utils = StringUtils()
        self.io = IOUtils()

class BuildBuddyRemoteCacheFlagsResolver(_RemoteCacheFlagsResolver):

    def __init__(self, collaborators: Collaborators):
        self.collaborators = collaborators

    def _read_api_key(self, file_path: str, ctx: Context):
        api_key_file_content = self.collaborators.io.read_file_safe_func(file_path, ctx)
        api_key_formatted = self.collaborators.string_utils.remove_whitespaces_func(api_key_file_content)
        return api_key_formatted

    def resolve(self, ctx: Context) -> Iterable[str]:
        flags = [
            "--config=uniform_remote_cache"  # declared in 'tools/bazelrc/.bazelrc.managed.dev.env'
        ]

        if ctx.buildbuddy_api_key_filepath and self.collaborators.io.file_exists_func(ctx.buildbuddy_api_key_filepath):
            ctx.logger.debug("Reading Buildbuddy credentials file. path: {}".format(ctx.buildbuddy_api_key_filepath))
            api_key = self._read_api_key(ctx.buildbuddy_api_key_filepath, ctx)
            flags.append("--remote_cache={}".format(self._DEFAULT_BUILDBUDDY_CACHE_URL))
            flags.append("--remote_header={}".format(api_key))
            ctx.logger.debug("Buildbuddy credentials file was found, added as an additional bazel remote flag. path: {}".format(ctx.buildbuddy_api_key_filepath))
        else:
            ctx.logger.debug("Buildbuddy credentials file is missing, please run wixtaller. path: {}".format(ctx.buildbuddy_api_key_filepath))

        return flags

class EngflowRemoteCacheFlagsResolver(_RemoteCacheFlagsResolver):

    def __init__(self, collaborators: Collaborators):
        self.collaborators = collaborators

    def _read_api_key(self, file_path: str, ctx: Context):
        api_key_file_content = self.collaborators.io.read_file_safe_func(file_path, ctx)
        api_key_formatted = self.collaborators.string_utils.remove_whitespaces_func(api_key_file_content)
        return api_key_formatted

    def resolve(self, ctx: Context) -> Iterable[str]:
        flags = [
            "--config=uniform_remote_cache"  # declared in 'tools/bazelrc/.bazelrc.managed.dev.env'
        ]

        if ctx.engflow_api_key_filepath and self.collaborators.io.file_exists_func(ctx.engflow_api_key_filepath):
            api_key_engflow = self._read_api_key(ctx.engflow_api_key_filepath, ctx)
            flags.append("--remote_cache={}".format(self._DEFAULT_ENGFLOW_CACHE_URL))
            flags.append(f"--bes_header=x-engflow-auth-method=jwt-v0")
            flags.append(f"--bes_header=x-engflow-auth-token={api_key_engflow}")
            flags.append(f"--remote_header=x-engflow-auth-method=jwt-v0")
            flags.append(f"--remote_header=x-engflow-auth-token={api_key_engflow}")
            ctx.logger.debug("Engflow credentials file was found, added as an additional bazel remote flag. path: {}".format(ctx.engflow_api_key_filepath))
        else:
            ctx.logger.debug("Engflow credentials files are missing, please run wixtaller.")
            ctx.logger.debug("Engflow api key file was not found, path: {}".format(ctx.engflow_api_key_filepath))

        return flags

def create(ctx: Context):
    if 'REMOTE_CACHE_USE_WIX_CACHE_POPS' not in os.environ:
        return EngflowRemoteCacheFlagsResolver(FlagsResolverCollaborators())
    else:
        return WixCachePopsRemoteCacheFlagsResolver()
