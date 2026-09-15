"""Compatibility re-export shim for runtime directory layout helpers.

The canonical implementation lives in ``airunner.runtimes.runtime_layout``
(which in turn delegates bind-host policy to
``airunner.runtimes.runtime_bind_host``). That module mirrors the services
canonical ``airunner_services.config.runtime_layout``. This module is kept as
a thin re-export shim so older imports of ``airunner.runtime_layout`` keep
working without drifting (issue #2048).
"""

from __future__ import annotations

from airunner.runtimes.runtime_bind_host import (
    DEFAULT_RUNTIME_HOST,
    LOGGER,
    _allow_remote_runtime_bind,
    _is_loopback_host,
    _validated_bind_host,
    resolve_runtime_bind_host,
)
from airunner.runtimes.runtime_layout import (
    RuntimeDirectoryLayout,
    _resolve_directory,
    build_runtime_directory_layout,
)

__all__ = [
    "DEFAULT_RUNTIME_HOST",
    "LOGGER",
    "RuntimeDirectoryLayout",
    "build_runtime_directory_layout",
    "resolve_runtime_bind_host",
]
