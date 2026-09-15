"""Shared, dependency-light foundation for AIRunner packages.

This package is the single source of truth for values and helpers that must
agree across the desktop GUI (``src/``), the headless service daemon
(``services/``) and the native launcher (``native/``):

* ``settings`` — environment-derived runtime constants
* ``startup_env`` — process-startup environment configuration
* ``dev_build_token`` — stale-daemon detection token
* ``linux_bundle_layout`` — relocatable Linux bundle path helpers
* ``contract_enums`` — cross-process and cross-layer contracts
* ``logging_utils`` — shared logging configuration helpers

Nothing here imports from ``airunner``, ``airunner_services`` or
``airunner_native`` so that all three packages can depend on it without a
cycle.
"""

from __future__ import annotations

__all__ = [
    "contract_enums",
    "dev_build_token",
    "linux_bundle_layout",
    "logging_utils",
    "settings",
    "startup_env",
]
