"""Art catalog ``loaded`` is catalog-configured state only.

``registry_model_info`` sets ``loaded`` when the configured art
model equals the registry entry. No art runtime health is
probed, unlike the LLM READY-plus-metadata loaded proof, and
the wire shape stays ``{id, name, loaded, type}``.
"""

from __future__ import annotations

from types import SimpleNamespace

from airunner_services.api.routes.art_catalog_routes import (
    registry_model_info,
)


def _model(huggingface_id: str = "org/model-a") -> SimpleNamespace:
    """Return a fake registry model entry."""
    return SimpleNamespace(
        huggingface_id=huggingface_id,
        name="Model A",
        model_type=SimpleNamespace(value="text_to_image"),
    )


def test_configured_match_sets_catalog_loaded_flag() -> None:
    """A configured match is the documented catalog scope."""
    info = registry_model_info("org/model-a", _model())
    assert info.loaded is True
    assert info.model_dump() == {
        "id": "org/model-a",
        "name": "Model A",
        "loaded": True,
        "type": "text_to_image",
    }


def test_unconfigured_or_mismatched_is_not_loaded() -> None:
    """No configuration (or a different one) clears the flag."""
    assert registry_model_info("", _model()).loaded is False
    assert registry_model_info("org/other", _model()).loaded is False
