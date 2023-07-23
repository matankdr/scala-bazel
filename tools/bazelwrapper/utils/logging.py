import logging
import os
from logging import handlers, Logger

_RED = "\u001b[31m"
_GREEN = "\u001b[32m"
_YELLOW = "\u001b[33m"
_PURPLE = "\u001b[35m"
_RESET = "\u001b[0m"

DEFAULT_LOGGER_NAME = "bazelwrapper"


def get_default_logger():
    return logging.getLogger(DEFAULT_LOGGER_NAME)


def create_logger(level: int, handler=None, name: str=DEFAULT_LOGGER_NAME) -> Logger:
    logger = logging.getLogger(name)

    # Prevent log messages from reaching parent loggers to avoid duplicating messages. This will normally happen if
    # some other script configures the root logger.
    logger.parent = None
    logger.handlers.clear()
    logger.addHandler(console_log_handler())

    if handler is not None:
        logger.addHandler(handler)

    logger.setLevel(level)

    return logger


def console_log_handler():
    # following bazel's color scheme...
    template = "{color}{level}:" + _RESET
    _set_log_level_names_format(template)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(levelname)s [wix] %(message)s"))

    return stream_handler


def daily_log_file_handler(log_path, backups=7):
    template = "{color}{level}" + _RESET
    _set_log_level_names_format(template)

    handler = handlers.TimedRotatingFileHandler(filename=log_path, when="d", interval=1, backupCount=backups)

    pid = os.getpid()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [pid={pid}] [%(levelname)s]: %(message)s".format(pid=pid)))

    return handler


def _set_log_level_names_format(template):
    logging.addLevelName(
        logging.DEBUG, template.format(color=_YELLOW, level=logging.getLevelName(logging.DEBUG))
    )
    logging.addLevelName(
        logging.INFO, template.format(color=_GREEN, level=logging.getLevelName(logging.INFO))
    )
    logging.addLevelName(
        logging.WARNING, template.format(color=_PURPLE, level=logging.getLevelName(logging.WARNING))
    )
    logging.addLevelName(
        logging.ERROR, template.format(color=_RED, level=logging.getLevelName(logging.ERROR))
    )
