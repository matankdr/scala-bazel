#!/usr/bin/env python3

import json

from virtualmonorepo.log import logger
from virtualmonorepo.differ import Differ
from virtualmonorepo.context import Context
from virtualmonorepo.extensions import VmrExtensions
from virtualmonorepo.linker import VectorLinker
from virtualmonorepo.paths import PathsBuilder
from virtualmonorepo.templates import TemplateGenerator
from virtualmonorepo.vector_provider import VectorProvider


class ResolvedVectorResponse:

    def __init__(self,
                 v_path,
                 v_symlink,
                 v_data,
                 output_message,
                 diff: dict = {}):
        self.vector_path = v_path
        self.symlink_path = v_symlink
        self.vector_data = v_data
        self.output_message = output_message
        self.diff = diff


class ResolverActions:

    def __init__(self, v_provider: VectorProvider, v_linker: VectorLinker,
                 v_templategen: TemplateGenerator, paths_builder: PathsBuilder):

        self.v_provider = v_provider
        self.v_linker = v_linker
        self.v_templategen = v_templategen
        self.paths_builder = paths_builder

    def point_symlink_to_existing_vector(self) -> ResolvedVectorResponse:
        branched_vector_path = self.paths_builder.branched_vector_file_path()
        symlink_path = self.paths_builder.vector_symlink_path()

        resolved = self.point_symlink_to_vector(branched_vector_path,
                                                symlink_path)
        vector_filename = self.read_vector_filename(symlink_path)
        output_message = "Vector file kept the same revisions. file: {}".format(
            vector_filename)

        return ResolvedVectorResponse(
            branched_vector_path, symlink_path, resolved,
            output_message) if resolved is not None else None

    def create_vector_from_symlink_content(self) -> ResolvedVectorResponse:
        branched_vector_path = self.paths_builder.branched_vector_file_path()
        symlink_path = self.paths_builder.vector_symlink_path()

        # Read symlink real path before re-assigning to new path
        previous_vector_filename = self.read_vector_filename(symlink_path)
        resolved = self.copy_symlink_content_to_vector(branched_vector_path,
                                                       symlink_path)
        vector_filename = self.read_vector_filename(symlink_path)
        output_message = "Vector file adjusted from previous symlink pointer. from: {}, to: {}".format(
            previous_vector_filename, vector_filename)

        return ResolvedVectorResponse(
            branched_vector_path, symlink_path, resolved,
            output_message) if resolved is not None else None

    def download_vector_from_remote_server(self) -> ResolvedVectorResponse:
        branched_vector_path = self.paths_builder.branched_vector_file_path()
        symlink_path = self.paths_builder.vector_symlink_path()
        prev_vector_data = self.v_linker.read_file_content(symlink_path)

        resolved = self.download_and_process_vector(branched_vector_path,
                                                    symlink_path)
        vector_filename = self.read_vector_filename(branched_vector_path)
        output_message = "Vector file resolved from remote server latest revisions. file: {}".format(
            vector_filename)

        diff = Differ.get_repositories_diff_by_content(prev_vector_data,
                                                       resolved)

        return ResolvedVectorResponse(
            branched_vector_path,
            symlink_path,
            resolved,
            output_message,
            diff=diff) if resolved is not None else None

    def point_symlink_to_fixed_vector(self) -> ResolvedVectorResponse:
        fixed_vector_path = self.paths_builder.git_tracked_vector_path()
        symlink_path = self.paths_builder.vector_symlink_path()

        resolved = self.point_symlink_to_vector(fixed_vector_path, symlink_path)
        vector_filename = self.read_vector_filename(fixed_vector_path)
        output_message = "Vector pointer adjusted to fixed git tracked vector. file: {}".format(
            vector_filename)

        return ResolvedVectorResponse(
            fixed_vector_path, symlink_path, resolved,
            output_message) if resolved is not None else None

    def create_vector_from_ci_lock_file(self) -> ResolvedVectorResponse:
        symlink_path = self.paths_builder.vector_symlink_path()
        ci_lockfile_path = self.paths_builder.ci_generated_lock_file_path()

        vector_file_path = self.paths_builder.branched_vector_file_path(
            ignore_branch_override=True)

        resolved = self.create_vector_from_lock_file(ci_lockfile_path,
                                                     vector_file_path,
                                                     symlink_path)

        vector_filename = self.read_vector_filename(vector_file_path)
        ci_lock_filename = self.read_vector_filename(ci_lockfile_path)
        output_message = "Vector pointer adjusted to CI generated lock vector. source: {}, dest: {}".format(
            ci_lock_filename, vector_filename)

        return ResolvedVectorResponse(
            vector_file_path, symlink_path, resolved,
            output_message) if resolved is not None else None

    def is_vector_changed(self, symlink_path, branched_vector_path) -> bool:
        symlink_vector_filename = self.read_vector_filename(symlink_path)
        branched_vector_filename = self.read_vector_filename(
            branched_vector_path)
        return branched_vector_filename != symlink_vector_filename

    def vector_exists_at_path(self, path: str) -> bool:
        return self.v_linker.file_exists(path)

    def symlink_is_valid(self, path: str) -> bool:
        return self.v_linker.symlink_exists(path)

    def read_vector_filename(self, path: str) -> str:
        return self.v_linker.read_filename_from_path(path)

    def copy_symlink_content_to_vector(self, file_path: str,
                                       symlink_path: str) -> str:
        self.v_linker.overwrite_file_with_symlink_content(
            file_path, symlink_path)
        return self.v_linker.read_symlink(symlink_path)

    def point_symlink_to_vector(self, file_path: str, symlink_path: str) -> str:
        self.v_linker.write_symlink(file_path, symlink_path)
        return self.v_linker.read_symlink(symlink_path)

    def create_vector_from_lock_file(self, lockfile_path: str, dest_file: str,
                                     symlink_path: str) -> str:
        return self.v_linker.copy_file_and_symlink(lockfile_path, dest_file,
                                                   symlink_path)

    def download_and_process_vector(self, file_path: str,
                                    symlink_path: str) -> str:
        raw_vector = self.v_provider.provide()
        if raw_vector is None:
            return None

        resolved_vector = self.process_raw_vector_json(raw_vector)

        self.v_linker.create_file_and_symlink(file_path, resolved_vector,
                                              symlink_path)
        return resolved_vector

    def process_raw_vector_json(self, raw_vector: str) -> str:
        result = None
        try:
            # Make sure raw vector is JSON formatted
            raw_vector_json = json.loads(raw_vector)
            result = self.v_templategen.generate(raw_vector_json)
        except Exception as err:
            logger.error(
                "Failed deserializing raw vector as JSON. error: {}\n{}".format(
                    err, raw_vector))
            raise err

        return result


class Resolver:

    def __init__(self):
        pass

    def resolve(self, ctx: Context) -> ResolvedVectorResponse:
        pass


class ServerResolver(Resolver):
    vmr_ext: VmrExtensions

    def __init__(self,
                 v_provider,
                 v_linker,
                 v_templategen,
                 paths_builder,
                 vmr_ext=None):
        self.actions = ResolverActions(v_provider, v_linker, v_templategen,
                                       paths_builder)
        self.vmr_ext = vmr_ext

    def resolve(self, ctx: Context) -> ResolvedVectorResponse:
        result = self.actions.download_vector_from_remote_server()

        if self.vmr_ext is not None:
            logger.debug(
                "VMR Invalidation identified and notified. reason: pull from remote server"
            )
            self.vmr_ext.notify_invalidation()

        return result


class LocalResolver(Resolver):
    vmr_ext: VmrExtensions

    def __init__(self,
                 v_provider,
                 v_linker,
                 v_templategen,
                 paths_builder,
                 vmr_ext=None):
        self.actions = ResolverActions(v_provider, v_linker, v_templategen,
                                       paths_builder)
        self.paths_builder = paths_builder
        self.vmr_ext = vmr_ext

    def resolve(self, ctx: Context) -> ResolvedVectorResponse:
        """ Check if vector already exists for current branch and adjust vector symlink accordingly.
            In case there is no available vector but symlink is valid, we'll copy the symlink content as the branched vector and adjust symlink.
            Otherwise we'll create a branched vector from server.
        """
        branched_vector_path = self.paths_builder.branched_vector_file_path()
        symlink_path = self.paths_builder.vector_symlink_path()
        response: ResolvedVectorResponse

        if self.actions.vector_exists_at_path(branched_vector_path):
            logger.debug(
                "Local vector file exists, pointing symlink to vector. path: {}"
                .format(branched_vector_path))

            # Switch branch should notify on invalidation
            should_notify_invalidation = self.actions.is_vector_changed(
                symlink_path, branched_vector_path)
            invalidation_reason = "switch branch" if should_notify_invalidation else ""
            response = self.actions.point_symlink_to_existing_vector()

        elif self.actions.symlink_is_valid(symlink_path):
            logger.debug(
                "Local vector file is missing, copying symlink content to vector file. from: {} to: {}"
                .format(symlink_path, branched_vector_path))
            response = self.actions.create_vector_from_symlink_content()
            should_notify_invalidation = True
            invalidation_reason = "missing branched vector" if should_notify_invalidation else ""
        else:
            logger.debug(
                "Local vector file is missing and symlink is stale, downloading from server..."
            )
            response = self.actions.download_vector_from_remote_server()
            should_notify_invalidation = True
            invalidation_reason = "pull from remote server"

        if should_notify_invalidation and self.vmr_ext is not None:
            logger.debug(
                "VMR Invalidation identified and notified. reason: {}".format(
                    invalidation_reason))
            self.vmr_ext.notify_invalidation()
        else:
            logger.debug("No VMR invalidation notification took place")

        return response


class BranchOnlyResolver(Resolver):
    vmr_ext: VmrExtensions

    def __init__(self,
                 v_provider,
                 v_linker,
                 v_templategen,
                 paths_builder,
                 vmr_ext=None):
        self.actions = ResolverActions(v_provider, v_linker, v_templategen,
                                       paths_builder)
        self.paths_builder = paths_builder
        self.vmr_ext = vmr_ext

    def resolve(self, ctx: Context) -> ResolvedVectorResponse:
        """ Try to symlink a fixed branched vector which is git tracked. Since vector is branch oriented, we'll rely on 
            branch name override as an argument to check vector existence and adjust vector symlink accordingly.

            In case the branched vector is not git tracked, we'll perform one of the following:
                - Check for vector lock file and adjust vector symlink accordingly
                - Try to resolve from a compressed vector and adjust vector symlink accordingly
        """
        fixed_vector_path = self.paths_builder.git_tracked_vector_path()
        ci_lockfile_path = self.paths_builder.ci_generated_lock_file_path()
        response: ResolvedVectorResponse

        if self.actions.vector_exists_at_path(fixed_vector_path):
            logger.debug(
                "Fixed git tracked vector file exists, pointing symlink to vector. path: {}"
                .format(fixed_vector_path))
            response = self.actions.point_symlink_to_fixed_vector()
        elif self.actions.vector_exists_at_path(ci_lockfile_path):
            logger.debug(
                "Fixed git tracked vector file is missing, found CI generated lockfile. path: {}"
                .format(ci_lockfile_path))
            response = self.actions.create_vector_from_ci_lock_file()
        else:
            logger.error(
                "Git tracked vector file is missing and no lock file as fallback, cannot resolve vector"
            )
            response = None

        return response


class CrossRepoOnlyResolver(Resolver):
    vmr_ext: VmrExtensions

    def __init__(self,
                 v_provider,
                 v_linker,
                 v_templategen,
                 paths_builder,
                 vmr_ext=None):
        self.actions = ResolverActions(v_provider, v_linker, v_templategen,
                                       paths_builder)
        self.paths_builder = paths_builder
        self.vmr_ext = vmr_ext

    def resolve(self, ctx: Context) -> ResolvedVectorResponse:
        return resolve_based_on_lockfile(self.actions, self.paths_builder)


class BuildMasterResolver(Resolver):

    def __init__(self,
                 v_provider,
                 v_linker,
                 v_templategen,
                 paths_builder,
                 vmr_ext=None):
        self.actions = ResolverActions(v_provider, v_linker, v_templategen,
                                       paths_builder)
        self.paths_builder = paths_builder
        self.vmr_ext = vmr_ext

    def resolve(self, ctx: Context) -> ResolvedVectorResponse:
        return resolve_based_on_lockfile(self.actions, self.paths_builder)


class MergeDryRunResolver(Resolver):
    vmr_ext: VmrExtensions

    def __init__(self,
                 v_provider,
                 v_linker,
                 v_templategen,
                 paths_builder,
                 vmr_ext=None):
        self.actions = ResolverActions(v_provider, v_linker, v_templategen,
                                       paths_builder)
        self.paths_builder = paths_builder
        self.vmr_ext = vmr_ext

    def resolve(self, ctx: Context) -> ResolvedVectorResponse:
        return resolve_based_on_lockfile(self.actions, self.paths_builder)


def resolve_based_on_lockfile(
        resolver_actions: ResolverActions,
        paths_builder: PathsBuilder) -> ResolvedVectorResponse:
    ci_lockfile_path = paths_builder.ci_generated_lock_file_path()

    if resolver_actions.vector_exists_at_path(ci_lockfile_path):
        logger.debug("CI generated vector lockfile found. path: {}".format(
            ci_lockfile_path))
        return resolver_actions.create_vector_from_ci_lock_file()
    else:
        logger.error(
            "CI generated vector lockfile is missing, cannot resolve vector")
        return None
