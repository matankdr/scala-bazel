#!/usr/bin/env python3

import argparse
import sys

from virtualmonorepo.log import logger

CLIENT_VERSION = "0.0.0"


def parse_args(args):
    root_parser = argparse.ArgumentParser()
    set_global_arguments(root_parser)
    sub_parser = root_parser.add_subparsers(title="action",
                                            dest="vector_action")

    define_vector_action(sub_parser)
    define_local_vector_action(sub_parser)

    if len(args) == 0:
        root_parser.print_help(sys.stderr)
        sys.exit(1)

    return root_parser.parse_args(args)


def set_global_arguments(root_parser):
    root_parser.add_argument(
        '--verbose',
        dest='verbose',
        action='store_true',
        help='Allow verbose output (default: false)',
    )

    root_parser.add_argument(
        '--silent',
        dest='silent',
        action='store_true',
        help='Suppress all output (default: false)',
    )

    root_parser.add_argument(
        '--bazel-context',
        dest='bazel_context',
        action='store_true',
        help='Indirect execution via Bazel context (default: false)',
    )

    root_parser.add_argument('--version',
                             action='version',
                             version=CLIENT_VERSION)


def define_local_vector_action(sub_parser):
    local_vector_command = sub_parser.add_parser("local-vector")
    local_vector_command.add_argument(
        '--workspace-dir',
        dest="workspace_dir",
        required=True,
        help=
        'Directory path of a workspace that contains the 2nd parties vector',
    )
    local_vector_command.add_argument(
        '--metadata',
        dest="metadata",
        required=False,
        action='store_true',
        help='Read only the metadata part from the local vector',
    )
    build_type_choices = [
        'local', 'branch_only', 'build_master', 'cross_repo', 'merge_dry_run'
    ]
    local_vector_command.add_argument(
        '--build-type',
        dest='build_type',
        choices=build_type_choices,
        default=build_type_choices[0],
        help=
        'Bazel build type that controls the vector generation flow (default: {})'
        .format(build_type_choices[0]),
        )

    local_vector_command.add_argument(
        '--build-branch-override',
        dest='build_branch_override',
        required="--build-type={}".format(build_type_choices[1]) in sys.argv,
        help=
        'Bazel build type that controls the vector generation flow (default: none)',
    )


def define_vector_action(sub_parser):
    resolve_command = sub_parser.add_parser("resolve-vector")
    resolve_command.add_argument(
        '--workspace-dir',
        dest="workspace_dir",
        required=True,
        help=
        'Directory path of a workspace that should get its 2nd parties resolved',
    )

    resolve_command.add_argument(
        '--vector-provider-url',
        dest='vector_provider_url',
        required=True,
        help='Provider that return a raw vector in a JSON format',
    )

    build_type_choices = [
        'local', 'branch_only', 'build_master', 'cross_repo', 'merge_dry_run'
    ]
    resolve_command.add_argument(
        '--build-type',
        dest='build_type',
        choices=build_type_choices,
        default=build_type_choices[0],
        help=
        'Bazel build type that controls the vector generation flow (default: {})'
        .format(build_type_choices[0]),
    )

    resolve_command.add_argument(
        '--build-branch-override',
        dest='build_branch_override',
        required="--build-type={}".format(build_type_choices[1]) in sys.argv,
        help=
        'Bazel build type that controls the vector generation flow (default: none)',
    )

    resolve_command.add_argument(
        '--force-update',
        dest='force_update',
        action='store_true',
        help='Force update 2nd parties VMR vector (default: false)',
    )

    resolve_command.add_argument(
        '--dry-run',
        dest='dry_run',
        action='store_true',
        help=
        'Return a list of 2nd party repositories that should get invalidated without file system changes',
    )


class ResolveVectorArgs:

    workspace_dir = None
    vector_provider_url = None
    build_type = None
    build_branch_override = None
    force_update = None
    dry_run = None

    # Globals
    verbose = None
    silent = None
    bazel_context = None

    def __init__(self, arguments):
        if arguments is not None:
            self.workspace_dir = arguments.workspace_dir
            self.vector_provider_url = arguments.vector_provider_url
            self.build_type = arguments.build_type
            self.build_branch_override = arguments.build_branch_override
            self.force_update = arguments.force_update
            self.dry_run = arguments.dry_run
            self.verbose = arguments.verbose
            self.silent = arguments.silent
            self.bazel_context = arguments.bazel_context

    def print(self):
        logger.debug("Resolving 2nd parties from the virtual monorepo. \n"
                     "  workspace_dir: {}\n"
                     "  vector_provider_url: {}\n"
                     "  build_type: {}\n"
                     "  build_branch_override: {}\n"
                     "  force_update: {}\n"
                     "  dry_run: {}\n"
                     "  verbose: {}\n"
                     "  silent: {}\n"
                     "  bazel_context: {}".format(
                         self.workspace_dir, self.vector_provider_url,
                         self.build_type, self.build_branch_override,
                         self.force_update, self.dry_run, self.verbose,
                         self.silent, self.bazel_context))


class LocalVectorArgs:

    workspace_dir = None
    metadata = None
    build_type = None
    build_branch_override = None

    # Globals
    verbose = None
    silent = None
    bazel_context = None

    def __init__(self, arguments):
        if arguments is not None:
            self.workspace_dir = arguments.workspace_dir
            self.metadata = arguments.metadata
            self.build_type = arguments.build_type
            self.build_branch_override = arguments.build_branch_override
            self.verbose = arguments.verbose
            self.silent = arguments.silent
            self.bazel_context = arguments.bazel_context

    def print(self):
        logger.debug("Reading local 2nd parties vector. \n"
                     "  workspace_dir: {}\n"
                     "  metadata: {}\n"
                     "  build_type: {}\n"
                     "  build_branch_override: {}\n"
                     "  verbose: {}\n"
                     "  silent: {}\n"
                     "  bazel_context: {}").format(self.workspace_dir,
                                                   self.metadata,
                                                   self.build_type,
                                                   self.build_branch_override,
                                                   self.verbose,
                                                   self.silent,
                                                   self.bazel_context)


class ProgramArgs:

    vector_action = None
    is_valid = False

    resolve_vector_args: ResolveVectorArgs = None
    local_vector_args: LocalVectorArgs = None

    def __init__(self, arguments):
        if arguments is not None and arguments.vector_action is not None:
            self.vector_action = arguments.vector_action
            if arguments.vector_action == "resolve-vector":
                self.resolve_vector_args = ResolveVectorArgs(arguments)
                self.is_valid = True
            elif arguments.vector_action == "local-vector":
                self.local_vector_args = LocalVectorArgs(arguments)
                self.is_valid = True


def read_program_args(sys_args) -> ProgramArgs:
    parser_args = parse_args(sys_args)
    return ProgramArgs(parser_args)
