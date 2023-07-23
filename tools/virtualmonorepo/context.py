#!/usr/bin/env python3

from typing import Optional
from virtualmonorepo.registry import InjectionsRegistry
from virtualmonorepo.cli import LocalVectorArgs, ResolveVectorArgs


class Context:

    registry: InjectionsRegistry
    resolve_vector_args: ResolveVectorArgs
    local_vector_args: LocalVectorArgs

    def __init__(self,
                 registry: InjectionsRegistry,
                 resolve_vector_args: Optional[ResolveVectorArgs] = None,
                 local_vector_args: Optional[LocalVectorArgs] = None):
        self.registry = registry
        self.resolve_vector_args = resolve_vector_args
        self.local_vector_args = local_vector_args
