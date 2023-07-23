#!/usr/bin/env python3

TOOLS_FOLDER = "tools"
SECOND_PARTIES_FOLDER = "2nd_party_resolved_dependencies"
GIT_TRACKED_FOLDER = "fixed_2nd_party_resolved_dependencies"
FILE_VECTOR_SUFFIX = "2nd_party_resolved_dependencies.bzl"

VECTOR_DIRECTORY_PATH = "{workspace_dir}/{tools_folder}/{2nd_parties_folder}"
VECTOR_GIT_TRACKED_DIRECTORY_PATH = "{workspace_dir}/{tools_folder}/{git_tracked_folder}"
VECTOR_SYMLINK_PATH = "{workspace_dir}/{tools_folder}/2nd_party_resolved_dependencies_current_branch.bzl"

CI_GENERATED_LOCK_FILE_PATH = "{workspace_dir}/{tools_folder}/2nd_party_resolved_dependencies.bzl.lock"
BRANCHED_VECTOR_FILE_PATH = "{workspace_dir}/{tools_folder}/{2nd_parties_folder}/{branch_name}_{vector_suffix}"
GIT_TRACKED_VECTOR_PATH = "{workspace_dir}/{tools_folder}/{git_tracked_folder}/{branch_name}_{vector_suffix}"

# TODO: What are these ???
JSON_FILE_PATH_OVERRIDE_EMPTY_PLACEHOLDER = "EMPTY"
JSON_FILE_PATH_OVERRIDE_ENV_VAR_NAME = "RESOLVED_2ND_DEPENDENCIES_JSON_PATH"
DEFAULT_JSON_FILE_NAME = "2nd_party_resolved_dependencies.json"


class PathsBuilder:

    def __init__(self, workspace_dir, branch, working_branch=None):
        self.named_params = {
            "workspace_dir": workspace_dir,
            "tools_folder": TOOLS_FOLDER,
            "2nd_parties_folder": SECOND_PARTIES_FOLDER,
            "git_tracked_folder": GIT_TRACKED_FOLDER,
            "vector_suffix": FILE_VECTOR_SUFFIX,
        }
        self.branch = branch
        self.working_branch = branch if working_branch is None else working_branch

    # <workspace-path>/tools/2nd_party_resolved_dependencies_current_branch.bzl
    def vector_symlink_path(self):
        return VECTOR_SYMLINK_PATH.format(**self.named_params)

    # <workspace-path>/tools/2nd_party_resolved_dependencies
    def vector_directory_path(self):
        return VECTOR_DIRECTORY_PATH.format(**self.named_params)

    # <workspace-path>/tools/2nd_party_resolved_dependencies/<branch>_2nd_party_resolved_dependencies.bzl
    def branched_vector_file_path(self, ignore_branch_override=False):
        branch_name = self.working_branch if ignore_branch_override else self.branch
        branched_params = {"branch_name": branch_name}
        branched_params.update(self.named_params)
        return BRANCHED_VECTOR_FILE_PATH.format(**branched_params).replace(
            "\n", "")

    # <workspace-path>/tools/fixed_2nd_party_resolved_dependencies/<branch>_2nd_party_resolved_dependencies.bzl
    def git_tracked_vector_path(self, ignore_branch_override=False):
        branch_name = self.working_branch if ignore_branch_override else self.branch
        branched_params = {"branch_name": branch_name}
        branched_params.update(self.named_params)
        return GIT_TRACKED_VECTOR_PATH.format(**branched_params).replace(
            "\n", "")

    # <workspace-path>/tools/2nd_party_resolved_dependencies.bzl.lock
    def ci_generated_lock_file_path(self):
        return CI_GENERATED_LOCK_FILE_PATH.format(**self.named_params)
