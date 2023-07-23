load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load(":virtual_monorepo.bzl", "create_vmr_definitions")

wix_build_tools_version = "d02ea178fc8e73447a19f258894cd381598db8e6"
wix_build_tools_version_sha256 = "a7c618692433aa2843b4067cc17ff6988fecfb5cfa8cd51bf1b75d834d85ef7e"

def virtual_monorepo_setup():
    http_archive(
        name = "wix_build_tools",
        urls = ["https://github.com/wix-playground/wix_build_tools/archive/%s.zip" % wix_build_tools_version],
        strip_prefix = "wix_build_tools-%s" % wix_build_tools_version,
        sha256 = wix_build_tools_version_sha256,
    )

    create_vmr_definitions()
