#!/usr/bin/env python3

import json
from typing import Optional
from virtualmonorepo.log import logger

from virtualmonorepo.context import Context
from virtualmonorepo.differ import Differ
from virtualmonorepo.ioutils import read_file_safe, file_exists
from virtualmonorepo.resolver import (Resolver, BranchOnlyResolver,
                                      BuildMasterResolver,
                                      CrossRepoOnlyResolver,
                                      MergeDryRunResolver, LocalResolver,
                                      ServerResolver, ResolvedVectorResponse)


class VectorMetadata:
    os: str
    arch: str
    vector_mode: str

    def __init__(self, os: str, arch: str, vector_mode: str):
        self.os = os
        self.arch = arch
        self.vector_mode = vector_mode


class VectorData:
    metadata: VectorMetadata = None

    def __init__(self, metadata: Optional[VectorMetadata] = None):
        self.metadata = metadata

    def toJSON(self):
        return json.dumps(self,
                          default=lambda o: o.__dict__,
                          sort_keys=True,
                          indent=4)


def resolve(ctx: Context, build_type: str) -> ResolvedVectorResponse:
    if ctx.resolve_vector_args.force_update:
        r = server_resolver(ctx)
    else:
        r = resolver_by_build_type(ctx, build_type)

    logger.info("Resolving 2nd party vector. resolver: {}".format(
        type(r).__name__))

    return r.resolve(ctx)


def server_resolver(ctx: Context):
    return ServerResolver(ctx.registry.vector_provider,
                          ctx.registry.vector_file_linker,
                          ctx.registry.template_generator,
                          ctx.registry.paths_builder,
                          ctx.registry.vmr_extensions)


def resolver_by_build_type(ctx: Context, build_type: str) -> Resolver:
    v_provider = ctx.registry.vector_provider
    v_linker = ctx.registry.vector_file_linker
    v_templategen = ctx.registry.template_generator
    v_paths_builder = ctx.registry.paths_builder
    vmr_ext = ctx.registry.vmr_extensions

    mapper = {
        'branch_only': BranchOnlyResolver,
        'build_master': BuildMasterResolver,
        'cross_repo': CrossRepoOnlyResolver,
        'merge_dry_run': MergeDryRunResolver,
    }

    resolver = mapper.get(build_type, LocalResolver)
    return resolver(v_provider, v_linker, v_templategen, v_paths_builder,
                    vmr_ext)


def read_local_vector(ctx: Context) -> VectorData:
    local_branched_vector_path = ctx.registry.paths_builder.branched_vector_file_path(
    )
    if file_exists(local_branched_vector_path):
        vector_txt = read_file_safe(file_path=local_branched_vector_path)
        metadata = None
        if ctx.local_vector_args.metadata:
            vector_json = Differ.extract_vector_metadata(vector_txt)
            if vector_json != None and vector_json != "":
                metadata = VectorMetadata(
                    os=vector_json["os"],
                    arch=vector_json["arch"],
                    vector_mode=vector_json["vectorMode"])

        return VectorData(metadata=metadata)
    else:
        logger.error(
            f"Local VMR vector does not exist. path: {local_branched_vector_path}"
        )
        return None
