"""Helpers for art catalog resource-store queries."""

from __future__ import annotations

from typing import Optional, Sequence

from airunner.daemon_client.resource_store import (
    GuiResourceStore,
    ResourceRecord,
    get_resource_store,
)


def _store(store: Optional[GuiResourceStore] = None) -> GuiResourceStore:
    """Return the shared resource store when one was not provided."""
    return store or get_resource_store()


def get_ai_model(
    model_id: Optional[int],
    *,
    store: Optional[GuiResourceStore] = None,
) -> Optional[ResourceRecord]:
    """Return one art model by primary key."""
    return _store(store).get("AIModels", model_id)


def list_ai_models(
    *,
    store: Optional[GuiResourceStore] = None,
) -> list[ResourceRecord]:
    """Return all persisted art models."""
    return _store(store).query("AIModels")


def find_ai_models(
    *,
    category: Optional[str] = None,
    version: Optional[str] = None,
    pipeline_actions: Optional[Sequence[str]] = None,
    enabled: Optional[bool] = None,
    is_default: Optional[bool] = None,
    store: Optional[GuiResourceStore] = None,
) -> list[ResourceRecord]:
    """Return art models filtered with simple client-side predicates."""
    models = list_ai_models(store=store)
    matched: list[ResourceRecord] = []
    action_set = set(pipeline_actions or [])
    for model in models:
        if category is not None:
            if getattr(model, "category", None) != category:
                continue
        if version is not None and getattr(model, "version", None) != version:
            continue
        if action_set:
            if getattr(model, "pipeline_action", None) not in action_set:
                continue
        if enabled is not None:
            if bool(getattr(model, "enabled", None)) != enabled:
                continue
        if is_default is not None:
            default_val = bool(getattr(model, "is_default", None))
            if default_val != is_default:
                continue
        matched.append(model)
    return matched


def list_schedulers(
    *,
    store: Optional[GuiResourceStore] = None,
) -> list[ResourceRecord]:
    """Return all scheduler catalog entries."""
    return _store(store).query("Schedulers")


def find_scheduler(
    display_name: str,
    *,
    store: Optional[GuiResourceStore] = None,
) -> Optional[ResourceRecord]:
    """Return one scheduler by display name."""
    return _store(store).first(
        "Schedulers",
        filters={"display_name": display_name},
    )