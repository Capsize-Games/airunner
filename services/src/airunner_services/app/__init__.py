"""Service-owned application helpers."""

from airunner_common.startup_env import (
    configure_early_torch_allocator_environment,
)


# Issue #2241: the allocator env vars must be set before torch is first
# imported, and headless_runtime_mixin pulls torch transitively. Reaching
# service_app's configure call only after the mixin import (as before)
# sets the env after torch has parsed it as native; the runtime re-parse
# then sees cudaMallocAsync, tripping CUDAAllocatorConfig.cpp:44 and
# segfaulting the first CUDA malloc in full-tree pytest collection.
configure_early_torch_allocator_environment()

from airunner_services.app.headless_runtime_mixin import HeadlessRuntimeMixin
from airunner_services.app.service_app import ServiceApp

__all__ = ["HeadlessRuntimeMixin", "ServiceApp"]