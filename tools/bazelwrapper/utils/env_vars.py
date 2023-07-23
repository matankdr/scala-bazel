import os
from typing import Callable

from bazelwrapper.context import Context


def non_empty_env_var_value(name, default_fn: Callable[[Context], str], ctx: Context):
    resolved = ""

    if name in os.environ:
        value = os.environ[name]

        ctx.logger.debug("Found env-var '{name}={value}'".format(name=name, value=value))
        resolved = value.strip()

    else:
        ctx.logger.debug("Env-var '{name}' does not exist.".format(name=name))

    if resolved == "":
        resolved = default_fn(ctx).strip()
        ctx.logger.debug("Using default value '{value}'".format(name=name, value=resolved))

    return resolved
