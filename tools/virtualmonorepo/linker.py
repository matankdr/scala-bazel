#!/usr/bin/env python3

from virtualmonorepo.log import logger
from virtualmonorepo import ioutils


class VectorLinker:

    def __init__(self):
        pass

    def file_exists(self, file_path: str) -> bool:
        return ioutils.file_exists(file_path)

    def symlink_exists(self, symlink_path: str) -> bool:
        return ioutils.symlink_exists(symlink_path)

    def read_symlink(self, symlink_path: str) -> str:
        return ioutils.read_symlink(symlink_path)

    def read_filename_from_path(self, path: str) -> str:
        path_to_parse = ioutils.get_symlink_real_path(
            path) if ioutils._is_symlink(path) else path
        split = path_to_parse.split("/")
        return split[len(split) - 1]

    def read_file_content(self, path: str) -> str:
        path_to_read = ioutils.get_symlink_real_path(
            path) if ioutils._is_symlink(path) else path
        return ioutils.read_file_safe(path_to_read)

    def write_symlink(self, file_path: str, symlink_path: str):
        pass

    def overwrite_file_with_symlink_content(self, file_path: str,
                                            symlink_path: str):
        pass

    def create_file_and_symlink(self, file_path, content, symlink_path) -> str:
        pass

    def copy_file_and_symlink(self, source_file, dest_file,
                              symlink_path) -> str:
        pass


class FileSystemVectorLinker(VectorLinker):

    def __init__(self):
        pass

    def write_symlink(self, file_path: str, symlink_path: str):
        ioutils.remove_symlink(symlink_path)
        ioutils.write_symlink(file_path, symlink_path)

    def overwrite_file_with_symlink_content(self, file_path: str,
                                            symlink_path: str):
        content = ioutils.read_symlink(symlink_path)
        ioutils.write_file(file_path, content)
        self.write_symlink(file_path, symlink_path)

    def create_file_and_symlink(self, file_path, content, symlink_path) -> str:
        ioutils.write_file(file_path, content)
        self.write_symlink(file_path, symlink_path)

    def copy_file_and_symlink(self, source_file, dest_file,
                              symlink_path) -> str:
        content = ioutils.read_file_safe(source_file)
        ioutils.write_file(dest_file, content)
        self.write_symlink(dest_file, symlink_path)
        return content


class DryRunVectorLinker(VectorLinker):

    def __init__(self):
        pass

    def write_symlink(self, file_path: str, symlink_path: str):
        logger.info("Skipping writing symlink to vector file")
        pass

    def overwrite_file_with_symlink_content(self, file_path: str,
                                            symlink_path: str):
        logger.info("Skipping overwriting vector file with symlink content")
        pass

    def create_file_and_symlink(self, file_path, content, symlink_path) -> str:
        logger.info("Skipping creation of new vector file and symlink")
        pass

    def copy_file_and_symlink(self, source_file, dest_file,
                              symlink_path) -> str:
        logger.info("Skipping copying vector file from another and symlinking")
        pass
