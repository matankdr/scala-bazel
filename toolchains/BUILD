load(
    "@core_server_build_tools//dependencies/rules_scala:wix_scala_toolchain.bzl",
    "wix_scala_toolchain",
)

wix_scala_toolchain(
    name = "unused_deps_toolchain_impl",
    dependency_tracking_strict_deps_patterns = [
        "@//",
    ],
    strict_deps_mode = "error",
    unused_dependency_checker_mode = "off",
    visibility = ["//visibility:public"],
)

toolchain(
    name = "unused_deps_toolchain",
    toolchain = "unused_deps_toolchain_impl",
    toolchain_type = "@io_bazel_rules_scala//scala:toolchain_type",
    visibility = ["//visibility:public"],
)
