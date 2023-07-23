#!/usr/bin/env python3

from bazelwrapper.utils.io_utils import IOUtils

class FakeIOUtils:
    @staticmethod
    def _create_fake() -> IOUtils:
        io = IOUtils()
        io.read_file_safe_func = lambda file_path, ctx: "random-text"
        io.file_exists_func = lambda file_path: True
        return io

    @staticmethod
    def create() -> IOUtils:
        return FakeIOUtils._create_fake()
