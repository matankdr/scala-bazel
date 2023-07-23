#!/usr/bin/env python3

import logging

VERBOSE = False
SILENT = False
DRY_RUN = False
BAZEL_CONTEXT = False

COLOR_RED = '\033[0;31m'
COLOR_GREEN = '\033[0;32m'
COLOR_YELLOW = "\033[0;33m"
COLOR_PURPLE = "\u001b[35m"
COLOR_WHITE = '\033[1;37m'
COLOR_RESET = '\033[0m'


def _set_log_level_names_format(template):
    logging.addLevelName(
        logging.DEBUG,
        template.format(color=COLOR_WHITE,
                        level=logging.getLevelName(logging.DEBUG)))
    logging.addLevelName(
        logging.INFO,
        template.format(color=COLOR_GREEN,
                        level=logging.getLevelName(logging.INFO)))
    logging.addLevelName(
        logging.WARNING,
        template.format(color=COLOR_YELLOW,
                        level=logging.getLevelName(logging.WARNING)))
    logging.addLevelName(
        logging.ERROR,
        template.format(color=COLOR_RED,
                        level=logging.getLevelName(logging.ERROR)))


def init_logger(is_silent: bool, is_verbose: bool, is_dry_run: bool,
                is_bazel_context: bool):
    global SILENT
    if is_silent:
        SILENT = True
        return

    global VERBOSE
    global DRY_RUN
    global BAZEL_CONTEXT
    VERBOSE = is_verbose
    DRY_RUN = is_dry_run
    BAZEL_CONTEXT = is_bazel_context

    if BAZEL_CONTEXT:
        # When executed from Bazel wrapper, initializing logger fails the invocation, use custom prints instead
        return

    try:
        template = "{color}{level}" + COLOR_RESET
        _set_log_level_names_format(template)
        default_level = logging.DEBUG if VERBOSE else logging.INFO
        dry_run_format = "(Dry Run) " if DRY_RUN else ""
        logging.basicConfig(level=default_level,
                            format='%(levelname)s: ' + dry_run_format +
                            '%(message)s')
        logging.getLogger().setLevel(default_level)
    except Exception as err:
        print("Logger failed to initialize. error: " + str(err))


class logger:

    @staticmethod
    def info(message: str):
        if SILENT:
            return

        if BAZEL_CONTEXT:
            print("{}INFO:{} {}".format(COLOR_GREEN, COLOR_RESET, message))
        else:
            logging.info(message)

    @staticmethod
    def debug(message: str):
        if SILENT:
            return

        if VERBOSE:
            if BAZEL_CONTEXT:
                print("{}DEBUG:{} {}".format(COLOR_YELLOW, COLOR_RESET,
                                             message))
            else:
                logging.debug(message)

    @staticmethod
    def warning(message: str):
        if SILENT:
            return

        if BAZEL_CONTEXT:
            print("{}WARNING:{} {}".format(COLOR_PURPLE, COLOR_RESET, message))
        else:
            logging.warning(message)

    @staticmethod
    def error(message: str, std_out=False):
        if BAZEL_CONTEXT or std_out:
            print("{}ERROR:{} {}".format(COLOR_RED, COLOR_RESET, message))
        else:
            logging.error(message)
