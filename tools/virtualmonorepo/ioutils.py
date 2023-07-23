#!/usr/bin/env python3

import os
from pathlib import Path

from virtualmonorepo.log import logger
from virtualmonorepo.processexec import run


def get_home_directory():
    # Python 3.5+
    return str(Path.home())


def create_directory(folder_path):
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        os.makedirs(folder_path, exist_ok=True)


def write_file(file_path, content):
    try:
        with open(file_path, "w+") as opened_file:
            opened_file.write(content)
            opened_file.close()
            logger.debug("Created file. path: {}".format(file_path))

    except Exception as error:
        logger.debug("Error = {}\nFailed to create file. path: {}".format(
            error, file_path))
        raise error


def read_file_safe(file_path):
    content = None
    try:
        with open(file_path, "r+") as opened_file:
            content = opened_file.read()
            opened_file.close()
            logger.debug("Read current vector file. path: {}".format(file_path))

    except Exception as error:
        # Debug log level on purpose since read failures might be legit in some cases
        logger.debug(error)

    return content


def write_symlink(file_path, symlink_path):
    run(['ln', '-sf', file_path, symlink_path],
        fail_msg="Failed to write symlink {} => {}".format(
            symlink_path, file_path))
    logger.debug("Created symlink. path: {}".format(symlink_path))


def read_symlink(symlink_path):
    real_path = get_symlink_real_path(symlink_path)
    return read_file_safe(real_path)


def get_symlink_real_path(symlink_path):
    return os.readlink(symlink_path) if os.path.islink(
        symlink_path) else symlink_path


def remove_symlink(symlink_path):
    if _is_empty(symlink_path) and _is_symlink(symlink_path):
        os.remove(symlink_path)
        logger.debug("Deleted symlink. path: {}".format(symlink_path))


def symlink_exists(symlink_path):
    return os.path.exists(symlink_path)


def file_exists(file_path):
    return os.path.exists(file_path)


def _is_empty(file_path):
    return os.path.isfile(file_path) and os.stat(file_path).st_size == 0


def _is_symlink(file_path):
    return os.path.islink(file_path)
