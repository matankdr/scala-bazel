#!/usr/bin/env python3

import json
import sys
import os

from virtualmonorepo.log import init_logger, logger
from virtualmonorepo.context import Context
from virtualmonorepo.git import read_current_branch
from virtualmonorepo.registry import InjectionsRegistry
from virtualmonorepo.vector_provider import HttpVectorProvider
from virtualmonorepo.linker import FileSystemVectorLinker, DryRunVectorLinker
from virtualmonorepo.templates import VectorTemplateGenerator
from virtualmonorepo.paths import PathsBuilder
from virtualmonorepo.extensions import FileBasedVmrExtensions, DryRunVmrExtensions
from virtualmonorepo.bazel_driver import create_build_files_if_needed
from virtualmonorepo.vector import resolve, read_local_vector, VectorData
from virtualmonorepo.cli import read_program_args, ProgramArgs, ResolveVectorArgs, LocalVectorArgs

# Skip generating .pyc files
sys.dont_write_bytecode = True


def main():
    # Ignore the 1st element of sys.argv that represents the script name
    arguments: ProgramArgs = read_program_args(sys.argv[1:])
    if not arguments.is_valid:
        logger.error(
            "Program arguments for the vmr client are missing, cannot proceed",
            std_out=True)
        sys.exit(1)

    if arguments.vector_action == "resolve-vector":
        update_vector(arguments.resolve_vector_args)
    elif arguments.vector_action == "local-vector":
        vector_data = read_vector(arguments.local_vector_args)
        if vector_data is not None:
            print(vector_data.toJSON())


def update_vector(arguments: ResolveVectorArgs):
    init_logger(is_silent=arguments.silent,
                is_verbose=arguments.verbose,
                is_dry_run=arguments.dry_run,
                is_bazel_context=arguments.bazel_context)

    if not arguments.silent:
        arguments.print()

    ctx = create_context(arguments)
    # Create vectors directory, if it does not exist
    create_vector_directory(ctx.registry.paths_builder.vector_directory_path())
    update_2nd_parties_vector(ctx)


def calculate_build_branch(workspace_dir, build_type, build_branch_override):
    # Remove empty characters from optional branch override
    stripped_branch_override = build_branch_override.strip(
    ) if build_branch_override is not None else None
    if build_type == "branch_only" and stripped_branch_override is not None:
        build_branch_override = build_branch_override.replace("/", "_")
        logger.debug(
            "Branch override identified as: {}".format(build_branch_override))
        return build_branch_override
    else:
        git_branch = read_current_branch(workspace_dir)
        logger.debug("Git branch identified as: {}".format(git_branch))
        return git_branch


def create_context(arguments: ResolveVectorArgs):
    build_branch = calculate_build_branch(arguments.workspace_dir,
                                          arguments.build_type,
                                          arguments.build_branch_override)
    logger.debug("Selected build branch identified as: {}".format(build_branch))

    registry = InjectionsRegistry()
    registry.vector_provider = HttpVectorProvider(arguments.vector_provider_url)
    registry.vector_file_linker = DryRunVectorLinker(
    ) if arguments.dry_run else FileSystemVectorLinker()
    registry.template_generator = VectorTemplateGenerator()
    registry.paths_builder = PathsBuilder(arguments.workspace_dir, build_branch,
                                          build_branch)
    registry.vmr_extensions = DryRunVmrExtensions(
    ) if arguments.dry_run else FileBasedVmrExtensions()

    return Context(registry, resolve_vector_args=arguments)


def update_2nd_parties_vector(ctx: Context):
    """ Prepare a new vector containing all 2nd parties to invalidate. 
        When vector is being force-updated to the latest HEAD, build type is ignored.
    """
    response = resolve(ctx, ctx.resolve_vector_args.build_type)
    if response is None:
        logger.error("Exiting with system code 1 due to unresolved vector")
        sys.exit(1)

    _log_diff(response.diff)

    if not ctx.resolve_vector_args.dry_run:
        #  TODO: why??
        create_build_files_if_needed(ctx.resolve_vector_args.workspace_dir)

    logger.info(response.output_message)


def _log_diff(diff: dict):
    if diff is None:
        logger.info("Could not identify vector differences to log, skipping")
        return

    repos_to_invalidate = len(diff)
    result = ""
    if repos_to_invalidate == 0:
        result += "No differences were found with previous vector revisions"
    else:
        result += "There are {} repositories to invalidate post VMR update:\n\n".format(
            repos_to_invalidate)
        for repo in diff.items():
            result += "  {} = {}\n".format(repo[1]["name"], repo[1]["revision"])

    logger.info(result)


def create_vector_directory(vector_dir_path):
    if not os.path.exists(vector_dir_path):
        logger.debug(
            "VMR vector directory is missing, creating at path: {}".format(
                vector_dir_path))
        os.makedirs(vector_dir_path)


def read_vector(arguments: LocalVectorArgs) -> VectorData:
    init_logger(is_silent=arguments.silent,
                is_verbose=arguments.verbose,
                is_dry_run=False,
                is_bazel_context=arguments.bazel_context)

    git_branch = calculate_build_branch(workspace_dir=arguments.workspace_dir,
                                        build_type=arguments.build_type,
                                        build_branch_override=arguments.build_branch_override)

    registry = InjectionsRegistry()
    registry.paths_builder = PathsBuilder(arguments.workspace_dir,
                                          branch=git_branch)

    ctx = Context(registry, local_vector_args=arguments)
    return read_local_vector(ctx)


if __name__ == "__main__":
    main()
