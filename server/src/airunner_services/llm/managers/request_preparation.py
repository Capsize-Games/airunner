"""Helpers for normalizing request-scoped LLM inputs."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any, Optional


DTYPE_ALIASES = {
    "4-bit": "4bit",
    "4bit": "4bit",
    "8-bit": "8bit",
    "8bit": "8bit",
    "32-bit": "32bit",
    "32bit": "32bit",
    "auto": "auto",
}
VALID_MODEL_SERVICES = {"local", "openrouter", "ollama"}


@dataclass(frozen=True)
class WorkflowRequestSetup:
    """Request-scoped workflow configuration extracted from one request."""

    tool_categories: Optional[list[str]] = None
    force_tool: Optional[str] = None
    response_format: Optional[str] = None
    include_mood: Optional[bool] = None
    include_datetime: Optional[bool] = None
    include_style: Optional[bool] = None
    include_memory: Optional[bool] = None
    include_ui_context: Optional[bool] = None


@dataclass(frozen=True)
class RequestSettingsSnapshot:
    """Original manager settings captured before request overrides."""

    dtype: Any = None
    use_openrouter: bool = False
    use_ollama: bool = False
    use_local_llm: bool = False
    model: Any = None
    ollama_model: Any = None


def _normalize_text(value: Any) -> Optional[str]:
    """Return a stripped lowercase string when possible."""
    if not isinstance(value, str):
        return None

    normalized = value.strip().lower()
    return normalized or None


def normalize_requested_dtype(value: Any) -> Optional[str]:
    """Return the normalized request dtype or ``None`` when invalid."""
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return DTYPE_ALIASES.get(normalized)


def normalize_requested_service(value: Any) -> Optional[str]:
    """Return the normalized model service override when valid."""
    normalized = _normalize_text(value)
    if normalized in VALID_MODEL_SERVICES:
        return normalized
    return None


def extract_request_tool_defaults(
    request_data: Mapping[str, Any],
) -> dict[str, Any]:
    """Build default tool kwargs from request search hints."""
    defaults: dict[str, Any] = {}
    search_hints = request_data.get("search_hints")
    if not isinstance(search_hints, Mapping):
        return defaults

    locale = search_hints.get("locale")
    if not isinstance(locale, Mapping):
        return defaults

    for key in ("country", "language"):
        value = locale.get(key)
        if isinstance(value, str) and value.strip():
            defaults[key] = value.strip()

    return defaults


def build_workflow_request_setup(
    llm_request: Any,
) -> WorkflowRequestSetup:
    """Return the workflow-scoped options from one request object."""
    if llm_request is None:
        return WorkflowRequestSetup()

    tool_categories = getattr(llm_request, "tool_categories", None)
    if tool_categories is not None:
        tool_categories = list(tool_categories)

    return WorkflowRequestSetup(
        tool_categories=tool_categories,
        force_tool=getattr(llm_request, "force_tool", None),
        response_format=getattr(llm_request, "response_format", None),
        include_mood=getattr(llm_request, "include_mood", None),
        include_datetime=getattr(llm_request, "include_datetime", None),
        include_style=getattr(llm_request, "include_style", None),
        include_memory=getattr(llm_request, "include_memory", None),
        include_ui_context=getattr(
            llm_request,
            "include_ui_context",
            None,
        ),
    )


def extract_request_images(llm_request: Any) -> Optional[list[Any]]:
    """Return request images when present."""
    if llm_request is None:
        return None

    images = getattr(llm_request, "images", None)
    if not images:
        return None

    return list(images)


def capture_request_settings_snapshot(manager: Any) -> RequestSettingsSnapshot:
    """Capture the persisted settings values before one request runs."""
    generator_settings = getattr(manager, "llm_generator_settings", None)
    llm_settings = getattr(manager, "llm_settings", None)

    return RequestSettingsSnapshot(
        dtype=getattr(generator_settings, "dtype", None),
        use_openrouter=bool(getattr(llm_settings, "use_openrouter", False)),
        use_ollama=bool(getattr(llm_settings, "use_ollama", False)),
        use_local_llm=bool(getattr(llm_settings, "use_local_llm", False)),
        model=getattr(llm_settings, "model", None),
        ollama_model=getattr(llm_settings, "ollama_model", None),
    )


def restore_request_settings_snapshot(
    manager: Any,
    snapshot: RequestSettingsSnapshot,
) -> None:
    """Restore persisted settings after one request-scoped override."""
    generator_settings = getattr(manager, "llm_generator_settings", None)
    llm_settings = getattr(manager, "llm_settings", None)

    if generator_settings is not None:
        generator_settings.dtype = snapshot.dtype

    if llm_settings is None:
        return

    llm_settings.use_openrouter = snapshot.use_openrouter
    llm_settings.use_ollama = snapshot.use_ollama
    llm_settings.use_local_llm = snapshot.use_local_llm
    llm_settings.model = snapshot.model
    llm_settings.ollama_model = snapshot.ollama_model