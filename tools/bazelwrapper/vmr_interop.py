from typing import Optional

from bazelwrapper.context import Context as WrapperContext
from virtualmonorepo.main import update_vector, read_vector
from virtualmonorepo.cli import ResolveVectorArgs, LocalVectorArgs
from virtualmonorepo.vector import VectorData

# This interop class is being used by the Bazel wrapper to use
# the VMR Client source code directly

class FakeArgsParser:
    workspace_dir = None
    vector_provider_url = None
    build_type = None
    build_branch_override = None
    force_update = None
    dry_run = None
    verbose = None
    silent = None
    bazel_context = None
    metadata = None

class BazelVmrInterop:
    
    @staticmethod
    def resolve_vector(
            ctx: WrapperContext,
            vmr_vector_provider_url: str,
            build_type: str,
            is_silent: bool,
            build_branch_override: Optional[str] = None) -> None:

        args = FakeArgsParser()
        args.workspace_dir = ctx.workspace_dir
        args.vector_provider_url = vmr_vector_provider_url
        args.build_type = build_type
        args.build_branch_override = build_branch_override
        args.force_update = False
        args.bazel_context = True
        args.silent = is_silent
        args.verbose = False

        try:
            update_vector(ResolveVectorArgs(args))
        except Exception as ex:
            ctx.logger.debug(f"VMR client failed to read or update the vector. error: {ex}")
            raise ex

    @staticmethod
    def read_local_vector(
            ctx: WrapperContext,
            is_silent: bool,
            metadata_only: bool = True,
            build_type: Optional[str] = None,
            build_branch_override: Optional[str] = None) -> VectorData:

        args = FakeArgsParser()
        args.workspace_dir = ctx.workspace_dir
        args.metadata = metadata_only
        args.build_type = build_type
        args.build_branch_override = build_branch_override
        args.silent = is_silent
        args.verbose = False

        try:
            result = read_vector(LocalVectorArgs(args))
        except Exception as ex:
            ctx.logger.debug(f"VMR client failed to read local vector. error: {ex}")
            raise ex

        return result