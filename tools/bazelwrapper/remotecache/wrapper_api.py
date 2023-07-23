from typing import Iterable

import bazelwrapper.remotecache.flagsresolver as flagsresolver
from bazelwrapper.context import Context
from bazelwrapper.utils.feature_flags import Flag

# A white list of commands that we are going to apply remote-cache on
_INCLUDE_COMMANDS = {"build", "test", "run", "coverage", "cquery", "aquery"}

# A cascading flag to turn off remote-caching
_nocache_flag = Flag(
    full_cli_flag="--wix_nocache",
    marker_file_name=".nocache",
    env_var_name="WIX_BAZEL_REMOTE_CACHE_DISABLED",
    default_value=False
)
_rbe_based_config = Flag(
    full_cli_flag="--config=rbe_based"
)


def resolve_remote_cache_flags(ctx: Context) -> Iterable[str]:
    if _is_command_eligible_for_caching(ctx):
        ctx.logger.debug("Command '{}' is eligible for remote caching.".format(ctx.bazel_command()))
        return _remote_cache_flags_for(ctx)
    else:
        return iter(())


def _is_command_eligible_for_caching(ctx):
    return not _is_cache_disabled(ctx) and _INCLUDE_COMMANDS.__contains__(ctx.bazel_command())


def _remote_cache_flags_for(ctx) -> Iterable[str]:
    return flagsresolver \
        .create(ctx) \
        .resolve(ctx)


def _is_cache_disabled(ctx):
    """
    Cache is disabled if one of the following is true:
    1. --wix_nocache has been passed to the bazel command
    2. 'WIX_BAZEL_REMOTE_CACHE_DISABLED' env var is set (any value)
    3. ~/.config/wix/bazelwrapper/.nocache exists
    4. The CLI command contains the RBE config flag, which is being passed in CI
    5. The user command contains an explicit remote_cache flag
    """
    return _rbe_based_config.on(ctx) or _nocache_flag.on(ctx) or _is_user_request_remote_cache(ctx.user_args)


def _is_user_request_remote_cache(user_args):
    for arg in user_args:
        if arg.startswith('--remote_cache='):
            return True

    return False
