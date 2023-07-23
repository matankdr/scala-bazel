#!/usr/bin/env python3

import json

from virtualmonorepo.log import logger


class Differ:

    @staticmethod
    def get_repositories_diff_by_content(previous_vector_data,
                                         current_vector_data) -> dict:
        """ Return a dictionary of <name, repository> out of a resolved vector data bzl format
            The repository is the raw vector object
        """

        try:
            prev_repos = _create_name_to_repo_dict(previous_vector_data)
            curr_repos = _create_name_to_repo_dict(current_vector_data)
            logger.debug(
                "Parsed successfully both current and resolved vectors into ordered dictionaries"
            )
            return _diff_vectors(prev_repos, curr_repos)

        except Exception as e:
            logger.error(
                "Failed to resolve vector discrepancies (different vector versions/rule types?). error: {}"
                .format(e))
            # Do nothing
            return None

    @staticmethod
    def extract_vector_metadata(vector_txt):
        """ Extract metadata object from current vector format

            meta_data = {
                "os": "macos",
                "arch": "amd64",
                "vectorMode": "LATEST",
            }
        """
        # splitlines(True) - specifies if the line breaks should be included
        lines = vector_txt.splitlines(True)
        meta_data_found = False
        meta_data_str = ""
        for line in lines:
            if "meta_data = " in line:
                meta_data_str = "{"
                meta_data_found = True
                continue

            if "}" in line and meta_data_str != "":
                meta_data_str = meta_data_str.strip()
                if meta_data_str.endswith(","):
                    meta_data_str = meta_data_str.rstrip(",")

            if meta_data_found:
                meta_data_str += line

            if meta_data_found and line == '\n':
                break

        if meta_data_str == "":
            return None

        return json.loads(meta_data_str)


def _create_name_to_repo_dict(vector_data: str) -> dict:
    if vector_data is None:
        return None

    repos_json_str = _try_parse_from_both_vector_formats(vector_data)
    if repos_json_str is None:
        return None

    name_to_repo = dict()
    for repo in repos_json_str:
        name_to_repo[repo["name"]] = repo

    ordered_repos_dict = dict(
        sorted(
            name_to_repo.items(),
            key=lambda repo: repo[0]))  # parameter is a tuple of (name, repo)

    return ordered_repos_dict


def _try_parse_from_both_vector_formats(vector_data: str):
    """ Return repositories tuples formatted as follows:
        [
            (
                "ecom",
                {
                    "name": "ecom",
                    "url": "git@github.com:wix-private/ecom.git",
                    "revision": "a478addb1e9d36b24313bad624f985c45e851d70",
                    "pushedAtInSeconds": "1618152081"
                }
            )
        ]

        Important: url and pushedAtInSeconds won't appear when processing previous vector format
    """
    response = _extract_repos_str_from_current_format(vector_data)
    if response is None:
        response = _extract_repos_str_from_previous_format(vector_data)
    return response


def _extract_repos_str_from_previous_format(vector_data: str):
    """ Extract repositories raw content from previous vector formatted file and return it in a JSON format

        adi_server_version="800591ddf17ff9500cb0c9e84a11a4f0ba365330"
        app_market_version="9567af287fa02abf293a32e5f9f9104e601beca6"
        automation_tests_version="0817fc52666c88e368df07efd1a6ee9f4f627f7b"
        bazel_tooling_version="b09631f039693fd1a9d2e9bef9acd5ff709cbc01"
        cashier_version="cfda93da45e291741d4c125f89a7eceb50e64a26"
    """

    lines = vector_data.splitlines(True)
    only_repos = "["

    repo_template = """
    {
        "name": "%(name)s",
        "revision": %(revision)s
    },"""

    for line in lines:
        if "resolved" in line:
            break

        repo_rev = line.split("=")
        if len(repo_rev) == 2:
            only_repos += repo_template % {
                "name": repo_rev[0][:repo_rev[0].index("_version")],
                "revision": repo_rev[1]
            }

    if only_repos == "[":
        return None
    else:
        # Remove trailing comma and append closing bracket
        only_repos = only_repos[:len(only_repos) - 1] + "]"

    return json.loads(only_repos)


def _extract_repos_str_from_current_format(vector_data: str):
    """ Extract repositories raw content from current vector formatted file and return it in a JSON format

        repos = [
            {
                "name": "ecom",
                "url": "git@github.com:wix-private/ecom.git",
                "revision": "a478addb1e9d36b24313bad624f985c45e851d70",
                "pushedAtInSeconds": "1618152081"
            }
        ]
    """
    # splitlines(True) - specifies if the line breaks should be included
    lines = vector_data.splitlines(True)
    repos_found = False
    only_repos = ""
    for line in lines:
        if "repos = " in line:
            only_repos = "["
            repos_found = True
            continue

        if repos_found:
            only_repos += line

        if repos_found and line == '\n':
            break

    if only_repos == "":
        return None

    return json.loads(only_repos)


def _diff_vectors(prev_repos, curr_repos):
    """ Return the differences between two vectors revisions
    """
    if prev_repos is None and curr_repos is None:
        return None

    if prev_repos is None:
        return curr_repos

    if curr_repos is None:
        return prev_repos

    diff = dict()
    for repo_name in curr_repos:
        # Verify repository exists since vectors might be miss-aligned due to repositories detachment from VMR
        if repo_name in prev_repos and (curr_repos[repo_name]["revision"] !=
                                        prev_repos[repo_name]["revision"]):
            diff[repo_name] = curr_repos[repo_name]

    # Both dictionaries are sorted, no need to sort again
    return diff
