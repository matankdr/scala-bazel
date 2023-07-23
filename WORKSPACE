
###############################################################################
#                                                                             #
# Generated file. DIRECTLY COMMITTED CHANGES WILL BE OVERWRITTEN.             #
#                                                                             #
# If you need changes in WORKSPACE, ask at #bazel-support                     #
# Since: 2023 Apr. 25                                                         #
#                                                                             #
###############################################################################

repository_name = "bazel_template"
workspace(name = repository_name)

load("//tools/virtualmonorepo/rules:virtual_monorepo_setup.bzl", "virtual_monorepo_setup")

virtual_monorepo_setup()

register_toolchains("//toolchains:unused_deps_toolchain")

load("//tools:load_2nd_party_repositories.bzl", "load_2nd_party_repositories")

load_2nd_party_repositories()

load("@core_server_build_tools//dependencies/rules_license:rules_license.bzl", "rules_license")

rules_license()

load("@core_server_build_tools//dependencies/rules_pkg:rules_pkg.bzl", "rules_pkg")

rules_pkg()

load("@bazel_tooling//rules:define_repository_name.bzl", "define_repository_name")

define_repository_name(repository_name)

load("@core_server_build_tools//toolchains:toolchains_defs.bzl", "toolchains_repositories")

toolchains_repositories()

load("@core_server_build_tools//dependencies/rules_scala:rules_scala.bzl", "rules_scala")

rules_scala()

load("@core_server_build_tools//:repositories.bzl", "scala_repositories")

scala_repositories()

load("@core_server_build_tools//test-agent/src/shared:tests_external_repository.bzl", "tests_external_repository")

tests_external_repository(name = "tests")

load("@core_server_build_tools//dependencies/bazel_skylib:bazel_skylib.bzl", "bazel_skylib")

bazel_skylib()

load("@core_server_build_tools//dependencies/rules_python:rules_python.bzl", "rules_python")

rules_python()

load("@core_server_build_tools//dependencies/rules_python:rules_python_toolchains.bzl", "rules_python_toolchains")

rules_python_toolchains()

load("@core_server_build_tools//dependencies/rules_python:python_setup.bzl", "install_deps")

install_deps()

load("@core_server_build_tools//dependencies/rules_python:python_pip_setup.bzl", "install_pip_deps")

install_pip_deps()

# Protobuf expects an //external:python_headers label which would contain the
# Python headers if fast Python protos is enabled. Currently binds to dummy target
bind(
    name = "python_headers",
    actual = "@core_server_build_tools//dependencies/rules_python:python_headers",
)

load("@core_server_build_tools//dependencies/rules_docker:rules_docker.bzl", "rules_docker")

rules_docker()

load("@core_server_build_tools//dependencies/rules_go:rules_go.bzl", "rules_go")

rules_go()

load("@core_server_build_tools//dependencies/rules_docker:docker_repositories.bzl", "docker_repositories")

docker_repositories()

load("@core_server_build_tools//dependencies/rules_go:go_repositories.bzl", "go_repositories")

go_repositories()

load("@core_server_build_tools//:downloaders/mysql_downloader.bzl", "mysql", "mysql_default_version", "mysql_repositories")

mysql_repositories()

mysql_default_version()

mysql("5.6", "latest")

load("@core_server_build_tools//:downloaders/mongo_downloader.bzl", "mongo", "mongo_default_version", "mongo_repositories")

mongo_repositories()

mongo_default_version()

mongo("3.3.1")

register_toolchains("@core_server_build_tools//toolchains:wix_defaults_global_toolchain")

load("@core_server_build_tools//dependencies/rules_proto:rules_proto.bzl", "rules_proto")

rules_proto()

load("@core_server_build_tools//dependencies/google_protobuf:google_protobuf.bzl", "google_protobuf")

google_protobuf()

load("@core_server_build_tools//dependencies/rules_proto_grpc:rules_proto_grpc.bzl", "rules_proto_grpc")

rules_proto_grpc()

load("@core_server_build_tools//dependencies/rules_proto_grpc:rules_proto_grpc_setup.bzl", "rules_proto_grpc_setup")

rules_proto_grpc_setup()

load("@core_server_build_tools//:third_party.bzl", "managed_third_party_dependencies")

managed_third_party_dependencies()

load("@core_server_build_tools//third_party/docker_images:docker_images.bzl", managed_docker_images = "docker_images")

managed_docker_images()

load("@core_server_build_tools//dependencies/jar_jar:jar_jar.bzl", "jar_jar")

jar_jar()

load("@core_server_build_tools//dependencies/jar_jar:jar_jar_repositories.bzl", "jar_jar_repositories")

jar_jar_repositories()

load("@core_server_build_tools//dependencies/kube:kube_repositories.bzl", "kube_repositories")

kube_repositories()

register_execution_platforms(
    "@core_server_build_tools//platforms:my_host_platform",
)

load("@core_server_build_tools//dependencies/global_external_files:global_external_files.bzl", "global_external_files")

global_external_files()

load("@core_server_build_tools//dependencies/rules_nodejs:rules_nodejs.bzl", "rules_nodejs")

rules_nodejs()

load("@core_server_build_tools//dependencies/rules_nodejs:nodejs_repositories.bzl", "nodejs_repositories")

nodejs_repositories()

load("@core_server_build_tools//dependencies/flynt:flynt_repositories.bzl", "flynt_repositories")

flynt_repositories()

load(":large_files.bzl", "large_files")

large_files()

load("@core_server_build_tools//toolchains/cc:repositories.bzl", "cc_repositories")

cc_repositories()

load("@core_server_build_tools//toolchains/cc:toolchains.bzl", "cc_toolchains")

cc_toolchains()

load("@core_server_build_tools//dependencies/rules_maven_third_party:rules_maven_third_party.bzl", "rules_maven_third_party")

rules_maven_third_party()
