"""Rule for creating virtual monorepo definitions."""

# CI environment should use env var 'VMR_REPO_RULE_TYPE'
# to allow the 'http_archive' repository rule
_default_rule_type = "git_cached_repository"
_env_var_rule_type = "VMR_REPO_RULE_TYPE"
_env_var_enable_verbosity = "VMR_DEFS_ENABLE_VERBOSITY"

def _is_verbosity_enabled(env_vars):
    return env_vars.get(_env_var_enable_verbosity, "") == "True"

def _log(ctx, message, report_progress = False):
    if report_progress:
        ctx.report_progress(message)

    if _is_verbosity_enabled(ctx.os.environ):
        print(message)

def _get_active_rule_type(env_vars):
    return env_vars.get(_env_var_rule_type, _default_rule_type)

def _create_build_file(repo_ctx):
    repo_ctx.file(
        "BUILD.bazel",
        """package(default_visibility = ["//visibility:public"])
        """,
    )

def _prepare_definitions_content(repo_ctx):
    active_rule_type = _get_active_rule_type(repo_ctx.os.environ)

    return """load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("@wix_build_tools//rules/git:git_cached_repository.bzl", "git_cached_repository")

active_rule_type="{}"

def git_cached_repository_wrapper(**repo):
    return git_cached_repository(
        name = repo["name"],
        remote_url = repo["url"],
        branch = repo.get("branch", "master"),
        commit = repo["revision"],
        shallow_since = "4 weeks ago",
    )


def http_archive_wrapper(**repo):
    (owner,name) = repo["url"].rsplit(":")[1][:-4].split("/")
    version = repo["revision"]
    return http_archive(
        name = repo["name"],
        type = "tar.gz",
        urls = [
            "https://github-proxy.wixprod.net/%s/%s/tar.gz/%s" % (owner, name, version),
            "https://bo.wix.com/git-bazel-proxy/%s/%s/%s/tar.gz" % (owner, name, version),
        ],
        strip_prefix = "%s-%s" % (name, version),
    )
""".format(active_rule_type)

def _create_definitions_file(repo_ctx, content):
    repo_ctx.file(
        "defs.bzl",
        """{}
        """.format(content),
    )

def _virtual_monorepo_impl(repo_ctx):
    _create_build_file(repo_ctx)
    defs_content = _prepare_definitions_content(repo_ctx)
    _create_definitions_file(repo_ctx, defs_content)

_virtual_monorepo = repository_rule(
    implementation = _virtual_monorepo_impl,
    environ = [_env_var_rule_type, _env_var_enable_verbosity],
)

def create_vmr_definitions():
    """ Allows any extension file to address the virtual monorepo definitions
        Usage:
            load("@virtual_monorepo//:defs.bzl", "active_rule_type", "git_cached_repository_wrapper", "http_archive_wrapper")
    """
    _virtual_monorepo(name = "virtual_monorepo")
