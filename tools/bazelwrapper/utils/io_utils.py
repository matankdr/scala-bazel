#!/usr/bin/env python3

import os

from bazelwrapper.context import Context

class IOUtils:
    def _read_file_safe(self, file_path: str, ctx: Context):
        content = None
        try:
            with open(file_path, "r+") as opened_file:
                content = opened_file.read()
                opened_file.close()
                ctx.logger.debug("Read file. path: {}".format(file_path))

        except Exception as error:
            # Debug log level on purpose since read failures might be legit in some cases
            ctx.logger.debug(error)

        return content

    def _file_exists(self, file_path):
        return os.path.exists(file_path)

    read_file_safe_func = _read_file_safe
    file_exists_func = _file_exists
