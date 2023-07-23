#!/usr/bin/env python3

from virtualmonorepo.vector_provider import VectorProvider
from virtualmonorepo.linker import VectorLinker
from virtualmonorepo.templates import TemplateGenerator
from virtualmonorepo.paths import PathsBuilder
from virtualmonorepo.extensions import VmrExtensions


class InjectionsRegistry:

    vector_provider: VectorProvider
    vector_file_linker: VectorLinker
    template_generator: TemplateGenerator
    paths_builder: PathsBuilder
    vmr_extensions: VmrExtensions
