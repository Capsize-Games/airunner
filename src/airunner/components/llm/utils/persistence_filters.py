"""Helpers for filtering non-user-facing persisted message payloads."""

from typing import Any, Dict, Mapping, Optional


def is_internal_stage_metadata(metadata: Optional[Mapping[str, Any]]) -> bool:
    """Return whether metadata marks one hidden internal LLM stage."""
    return (
        isinstance(metadata, Mapping)
        and str(metadata.get("kind") or "").strip() == "llm_stage_settings"
    )


def is_internal_stage_message_dict(message: Optional[Dict[str, Any]]) -> bool:
    """Return whether one stored assistant row is internal-stage only."""
    if not isinstance(message, dict):
        return False
    if str(message.get("role") or "").strip() not in {"assistant", "bot"}:
        return False
    return is_internal_stage_metadata(message.get("thinking_metadata"))