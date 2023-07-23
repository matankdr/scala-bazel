from typing import Callable

from bazelwrapper.context import Context


def safe(fn: Callable[[Context], any], default_value, ctx: Context):
    try:
        return fn(ctx)
    except BaseException as err:
        ctx.logger.warning(
            "Failed to execute {fn}. Using default value: {default}".format(fn=fn, default=default_value))
        ctx.logger.debug(err)

        return default_value
