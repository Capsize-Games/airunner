"""Compatibility exports for daemon route helper functions."""

from .daemon_runtime_actions import (
    cancel_runtime_action,
    ensure_success,
    invoke_runtime_action,
    resolve_runtime_client,
    runtime_failure_status,
)
from .daemon_runtime_health import (
    health_fields,
    infer_loaded_state,
    loaded_model_names,
    runtime_loaded,
    supports_cancellation,
)
from .daemon_runtime_registry import (
    client_key,
    get_runtime_registry,
    parse_runtime_kind,
    require_runtime_registry,
    route_alias,
)
from .daemon_runtime_summary import (
    build_runtime_summary,
    collect_runtime_summaries,
)
from .daemon_vram import ensure_vram_available_for

__all__ = [
    "build_runtime_summary",
    "cancel_runtime_action",
    "client_key",
    "collect_runtime_summaries",
    "ensure_success",
    "ensure_vram_available_for",
    "get_runtime_registry",
    "health_fields",
    "infer_loaded_state",
    "invoke_runtime_action",
    "loaded_model_names",
    "parse_runtime_kind",
    "require_runtime_registry",
    "resolve_runtime_client",
    "route_alias",
    "runtime_failure_status",
    "runtime_loaded",
    "supports_cancellation",
]
