load("//tools:2nd_party_resolved_dependencies_current_branch.bzl", "resolved")
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("@virtual_monorepo//:defs.bzl", "git_cached_repository_wrapper", "http_archive_wrapper")

def load_local_repository(name, path):
    native.local_repository(
        name = name,
        path = path,
    )

def load_2nd_party_repositories():
    for repo in resolved:
        if "path" in repo["attributes"]:
            load_local_repository(repo["attributes"]["name"], repo["attributes"]["path"])
        elif repo["rule_class"] == "vmr.git_cached_repository_wrapper":
            git_cached_repository_wrapper(**(repo["attributes"]))
        elif repo["rule_class"] == "vmr.http_archive_wrapper":
            http_archive_wrapper(**(repo["attributes"]))
        elif repo["rule_class"] == "@bazel_tools//tools/build_defs/repo:git.bzl%http_archive":
            http_archive(**(repo["attributes"]))
