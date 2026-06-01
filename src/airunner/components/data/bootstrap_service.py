"""Bootstrap data service — fetches model/pipeline metadata from daemon.

On first access, queries the daemon's ``GET /api/v1/art/bootstrap``
endpoint and caches the result for the process lifetime.  Falls back
to a local import when the daemon is unreachable (e.g. during setup
wizard before services are running).
"""

from __future__ import annotations

from typing import Any, List

_cache: dict[str, Any] | None = None


def _fetch_bootstrap() -> dict[str, Any]:
    """Query the daemon for bootstrap data, falling back to local files."""
    try:
        from airunner.daemon_client.gui_daemon_client import (
            GuiDaemonClient,
        )

        client = GuiDaemonClient()
        if not client.is_available():
            return _local_fallback()
        return client.get_bootstrap_data()
    except Exception:
        return _local_fallback()


def _local_fallback() -> dict[str, Any]:
    """Return bootstrap data from the local package when daemon is down."""
    try:
        from airunner.components.data.bootstrap.model_bootstrap_data import (  # noqa: E501
            model_bootstrap_data,
        )
        from airunner.components.data.bootstrap.pipeline_bootstrap_data import (  # noqa: E501
            pipeline_bootstrap_data,
        )
        from airunner.components.data.bootstrap.unified_model_files import (  # noqa: E501
            UNIFIED_MODEL_FILES,
        )

        return {
            "models": model_bootstrap_data,
            "pipelines": pipeline_bootstrap_data,
            "unified_model_files": UNIFIED_MODEL_FILES,
        }
    except ImportError:
        return {"models": [], "pipelines": [], "unified_model_files": {}}


def get_bootstrap_data() -> dict[str, Any]:
    """Return the cached bootstrap data, fetching on first access."""
    global _cache
    if _cache is None:
        _cache = _fetch_bootstrap()
    return _cache


def get_model_bootstrap_data() -> List[dict[str, Any]]:
    """Return just the model bootstrap list."""
    return get_bootstrap_data().get("models", [])


def get_pipeline_bootstrap_data() -> List[dict[str, Any]]:
    """Return just the pipeline bootstrap list."""
    return get_bootstrap_data().get("pipelines", [])


def get_required_files_for_model(
    model_type: str,
    model_id: str,
    version: str | None = None,
    pipeline_action: str | None = None,
) -> dict[str, Any]:
    """Return required files for one model type/id pair."""
    unified = get_bootstrap_data().get("unified_model_files", {})
    model_files = unified.get(model_type, {})
    if not isinstance(model_files, dict):
        return {}
    # Try model_id first, then model_id with version
    result = model_files.get(model_id)
    if result is not None:
        return result
    if version:
        version_key = f"{model_id}__{version}"
        result = model_files.get(version_key)
        if result is not None:
            return result
    if pipeline_action:
        action_key = f"{model_id}__{pipeline_action}"
        result = model_files.get(action_key)
        if result is not None:
            return result
    return {}


__all__ = [
    "get_bootstrap_data",
    "get_model_bootstrap_data",
    "get_pipeline_bootstrap_data",
    "get_required_files_for_model",
]
