import os

from bazelwrapper.context import Context
from bazelwrapper.env.info import get_id

_PERSONAL_DASHBOARD_URL_TEMPLATE = \
    "https://grafana.wixpress.com/d/jASkdh9Zk/my-bazel-experience-dashboard?" \
    "var-env_id={env_id}"


def intercept_command(ctx: Context):
    if ctx.bazel_command() == "dashboard":
        _handle_dashboard_command(ctx)


def _handle_dashboard_command(ctx):
    env_id = get_id(ctx)
    ctx.logger.debug("Resolved env_id={env_id}".format(env_id=env_id))

    url = _PERSONAL_DASHBOARD_URL_TEMPLATE.format(env_id=env_id)
    ctx.logger.debug("Resolved dashboard URL is {url}".format(url=url))

    if ctx.system_name == "Darwin":
        ctx.logger.info("Opening your personal Bazel dashboard...")
        os.system("open \"{url}\"".format(url=url))
    else:
        ctx.logger.info("Please open {url}".format(url=url))

    exit(0)
