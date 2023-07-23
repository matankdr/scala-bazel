#!/usr/bin/env python3

import subprocess
import os
import sys

from virtualmonorepo.log import logger

# TODO: Change this one
FOLDER_OF_SCRIPT = os.path.dirname(sys.argv[0])


def run(splitted_command, fail_msg):
    logger.debug("Running process: {}".format(' '.join(splitted_command)))

    working_dir = FOLDER_OF_SCRIPT if FOLDER_OF_SCRIPT != "" else os.getcwd()
    process = subprocess.Popen(splitted_command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               cwd=working_dir)

    encoded_out, err = process.communicate()
    out = encoded_out.decode("utf-8")
    if err:
        msg = "{}. stderr = {}".format(fail_msg, err)
        logger.error(msg)
        raise Exception(msg)

    logger.debug("Process output:\t%s" % out)
    return out
