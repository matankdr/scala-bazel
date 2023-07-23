#!/usr/bin/env python3

import json


class TemplateGenerator:

    def __init__(self):
        pass

    def generate(self, raw_vector_json) -> str:
        pass


class VectorTemplateGenerator(TemplateGenerator):

    def __init__(self):
        pass

    def generate(self, raw_vector_json) -> str:
        vector_json_raw = raw_vector_json.get("vector")

        vector_repos_raw = vector_json_raw.get("repos")
        repos_json = json.dumps(vector_repos_raw, indent=4)

        metadata_raw = vector_json_raw.get("metaData", "")
        metadata_starlark = ""
        if metadata_raw != "":
            metadata_json = json.dumps(metadata_raw, indent=4)
            metadata_starlark = f"meta_data = {metadata_json}"

        return _vector_bzl_template % {
            "load_defs":
                _vector_bzl_load_def,
            "vector_repos":
                repos_json,
            "vector_metadata":
                metadata_starlark,
        }


_vector_bzl_load_def = """load("@virtual_monorepo//:defs.bzl", "active_rule_type")"""

_vector_bzl_template = """%(load_defs)s

# IMPORTANT !

# When using a 'git_cached_repository' VMR rule type, the default branch in use is 'master'.
# To update a branched revision, an additional 'branch' attribute is required.

# Example:
# {
#     "name": "some_repo",
#     "url": "git@github.com:wix-private/some_repo.git",
#     "revision": "6e12c4",
#     "branch": "<branch-name>",
#     "pushedAtInSeconds": "12345",
# }

# Hint:
# To check the active VMR rule type in use run the following command from the WORKSPACE root folder: 
# ./tools/vmr config

# Loading a second party from a local clone is done as following:
# {
#     "name": "some_repo",
#     "path": "/path/to/some_repo",
# }

%(vector_metadata)s

repos = %(vector_repos)s

rule_class = "vmr.git_cached_repository_wrapper" if active_rule_type == "git_cached_repository" else "vmr.http_archive_wrapper"

# Backwards compatible to the previous VMR loader implementation
resolved = [{"rule_class": rule_class, "attributes": repo} for repo in repos]
"""
