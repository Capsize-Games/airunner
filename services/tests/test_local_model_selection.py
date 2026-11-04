"""Documented default local model selection.

With nothing configured, the effective selection is the
documented default GGUF model; an explicit selection always
wins. A default selection is configured state only and never
implies the model is loaded. No model, network, or DB access.
"""

from __future__ import annotations

from types import SimpleNamespace

from airunner_services.api.routes.llm_model_routes import (
    selected_model_id,
)
from airunner_services.llm.local_capability import (
    build_local_capability,
)
from airunner_services.llm.local_model_selection import (
    DEFAULT_LOCAL_MODEL_ID,
    default_local_model_id,
    effective_local_model_id,
)
from airunner_services.llm.provider_config import LLMProviderConfig


def test_default_is_a_supported_gguf_candidate() -> None:
    """The documented default is supported and GGUF-loadable."""
    assert DEFAULT_LOCAL_MODEL_ID == "qwen3.5-9b"
    supported = LLMProviderConfig.get_models_for_provider("local")
    assert DEFAULT_LOCAL_MODEL_ID in supported
    gguf = LLMProviderConfig.get_gguf_info("local", DEFAULT_LOCAL_MODEL_ID)
    assert gguf is not None
    assert default_local_model_id() == DEFAULT_LOCAL_MODEL_ID


def test_effective_selection_defaults_when_none_configured() -> None:
    """Empty or unresolvable configuration selects the default."""
    assert effective_local_model_id() == DEFAULT_LOCAL_MODEL_ID
    assert effective_local_model_id("") == DEFAULT_LOCAL_MODEL_ID
    assert effective_local_model_id("nope") == DEFAULT_LOCAL_MODEL_ID


def test_effective_selection_keeps_explicit_model() -> None:
    """An explicit supported selection wins over the default."""
    assert effective_local_model_id("gpt-oss-20b") == "gpt-oss-20b"
    assert effective_local_model_id("qwen3.5-9b") == "qwen3.5-9b"


def test_selected_model_id_defaults_without_settings() -> None:
    """No settings row still yields the documented default."""
    assert selected_model_id(None) == DEFAULT_LOCAL_MODEL_ID
    empty = SimpleNamespace(model_id=None, model_version=None, model_path=None)
    assert selected_model_id(empty) == DEFAULT_LOCAL_MODEL_ID


def test_selected_model_id_keeps_persisted_selection() -> None:
    """A persisted selection is returned unchanged."""
    settings = SimpleNamespace(
        model_id="gpt-oss-20b", model_version=None, model_path=None
    )
    assert selected_model_id(settings) == "gpt-oss-20b"


def test_default_selection_is_configured_not_loaded() -> None:
    """The default shows as configured, never as loaded."""
    payload = build_local_capability(
        configured_model_id=selected_model_id(None)
    )
    entry = next(
        m for m in payload["models"] if m["id"] == DEFAULT_LOCAL_MODEL_ID
    )
    assert entry["configured"] is True
    assert entry["loaded"] is False
    assert not any(m["loaded"] for m in payload["models"])
