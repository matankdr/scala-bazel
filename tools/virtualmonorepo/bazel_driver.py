#!/usr/bin/env python3

from virtualmonorepo.log import logger
from virtualmonorepo.ioutils import file_exists


def create_build_files_if_needed(workspace_dir):
    workspace_bazel_build_filepath = workspace_dir + "/BUILD.bazel"
    if not file_exists(workspace_bazel_build_filepath):
        logger.debug("Generating {}".format(workspace_dir + "/BUILD.bazel"))
        open(workspace_bazel_build_filepath, 'a').close()

    tools_folder_bazel_build_filepath = workspace_dir + "/tools/BUILD.bazel"
    if not file_exists(tools_folder_bazel_build_filepath):
        logger.debug("Generating {}".format(workspace_dir +
                                            "/tools/BUILD.bazel"))
        open(tools_folder_bazel_build_filepath, 'a').close()
