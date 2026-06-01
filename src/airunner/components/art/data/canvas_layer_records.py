"""Helpers for canvas-layer resource-store access."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from airunner.daemon_client.resource_store import (
    GuiResourceStore,
    ResourceRecord,
    get_resource_store,
)


LAYER_SETTING_RESOURCES = (
    "DrawingPadSettings",
    "ControlnetSettings",
    "ImageToImageSettings",
    "OutpaintSettings",
)


def _store(store: Optional[GuiResourceStore] = None) -> GuiResourceStore:
    """Return the shared resource store when one was not provided."""
    return store or get_resource_store()


def ordered_canvas_layers(
    *,
    store: Optional[GuiResourceStore] = None,
) -> list[ResourceRecord]:
    """Return canvas layers ordered from bottom to top."""
    return _store(store).query(
        "CanvasLayer",
        order_by=[{"field": "order", "direction": "asc"}],
    )


def all_canvas_layers(
    *,
    store: Optional[GuiResourceStore] = None,
) -> list[ResourceRecord]:
    """Return all persisted canvas layers without ordering overrides."""
    return _store(store).query("CanvasLayer")


def first_canvas_layer(
    *,
    store: Optional[GuiResourceStore] = None,
) -> Optional[ResourceRecord]:
    """Return the first persisted canvas layer by order."""
    return _store(store).first(
        "CanvasLayer",
        order_by=[{"field": "order", "direction": "asc"}],
    )


def find_canvas_layer_by_name(
    name: str,
    *,
    store: Optional[GuiResourceStore] = None,
) -> Optional[ResourceRecord]:
    """Return one canvas layer by exact name."""
    return _store(store).first("CanvasLayer", filters={"name": name})


def get_canvas_layer(
    layer_id: Optional[int],
    *,
    store: Optional[GuiResourceStore] = None,
) -> Optional[ResourceRecord]:
    """Return one canvas layer by primary key."""
    return _store(store).get("CanvasLayer", layer_id)


def create_canvas_layer(
    values: dict[str, Any],
    *,
    store: Optional[GuiResourceStore] = None,
) -> ResourceRecord:
    """Create one canvas layer record."""
    return _store(store).create("CanvasLayer", values)


def update_canvas_layer(
    layer_id: Optional[int],
    values: dict[str, Any],
    *,
    store: Optional[GuiResourceStore] = None,
) -> Optional[ResourceRecord]:
    """Update one canvas layer by primary key."""
    return _store(store).update("CanvasLayer", layer_id, values)


def delete_canvas_layer(
    layer_id: Optional[int],
    *,
    store: Optional[GuiResourceStore] = None,
) -> bool:
    """Delete one canvas layer by primary key."""
    return _store(store).delete("CanvasLayer", layer_id)


def first_layer_setting(
    resource_name: str,
    layer_id: int,
    *,
    store: Optional[GuiResourceStore] = None,
) -> Optional[ResourceRecord]:
    """Return one existing layer-scoped settings record."""
    return _store(store).first(
        resource_name,
        filters={"layer_id": layer_id},
    )


def ensure_layer_setting(
    resource_name: str,
    layer_id: int,
    *,
    store: Optional[GuiResourceStore] = None,
) -> ResourceRecord:
    """Return one layer-scoped settings record, creating it when needed."""
    return _store(store).get_layer(resource_name, layer_id)


def update_layer_setting(
    resource_name: str,
    layer_id: int,
    values: dict[str, Any],
    *,
    store: Optional[GuiResourceStore] = None,
) -> ResourceRecord:
    """Update one layer-scoped settings record."""
    return _store(store).update_layer(resource_name, layer_id, values)


def delete_layer_setting(
    resource_name: str,
    layer_id: int,
    *,
    store: Optional[GuiResourceStore] = None,
) -> int:
    """Delete all settings records for one layer/resource pair."""
    return _store(store).delete_many(
        resource_name,
        filters={"layer_id": layer_id},
    )


def delete_layer_bundle(
    layer_id: int,
    *,
    store: Optional[GuiResourceStore] = None,
    include_layer: bool = True,
    extra_resources: Iterable[str] = (),
) -> None:
    """Delete one layer and its layer-scoped settings records."""
    layer_store = _store(store)
    for resource_name in (*LAYER_SETTING_RESOURCES, *tuple(extra_resources)):
        layer_store.delete_many(
            resource_name,
            filters={"layer_id": layer_id},
        )
    if include_layer:
        layer_store.delete("CanvasLayer", layer_id)


def invalidate_layer_caches(
    shared_instance: Any,
    layer_id: int,
    *,
    resource_names: Iterable[str] = (),
) -> None:
    """Drop any cached layer-scoped settings for one layer id."""
    cache_by_key = getattr(shared_instance, "_settings_cache_by_key", None)
    if not isinstance(cache_by_key, dict):
        return
    names = (*LAYER_SETTING_RESOURCES, *tuple(resource_names))
    for resource_name in names:
        cache_by_key.pop(f"{resource_name}_layer_{layer_id}", None)


def serialize_record(record: Optional[ResourceRecord]) -> Optional[dict[str, Any]]:
    """Convert one resource record into a plain dict when present."""
    if record is None:
        return None
    return record.to_dict()


def restore_record(
    resource_name: str,
    data: dict[str, Any],
    *,
    store: Optional[GuiResourceStore] = None,
) -> Optional[ResourceRecord]:
    """Restore one snapshot record by update-or-create semantics."""
    if not data:
        return None
    layer_store = _store(store)
    record_id = data.get("id")
    if record_id is not None and layer_store.get(resource_name, record_id):
        return layer_store.update(resource_name, record_id, data)
    return layer_store.create(resource_name, data)


def capture_layer_snapshot(
    layer_id: int,
    *,
    store: Optional[GuiResourceStore] = None,
) -> Optional[dict[str, Any]]:
    """Capture one canvas layer and its settings for undo/redo."""
    layer = get_canvas_layer(layer_id, store=store)
    if layer is None:
        return None
    snapshot = {"layer": serialize_record(layer)}
    snapshot["drawing_pad"] = serialize_record(
        first_layer_setting("DrawingPadSettings", layer_id, store=store)
    )
    snapshot["controlnet"] = serialize_record(
        first_layer_setting("ControlnetSettings", layer_id, store=store)
    )
    snapshot["image_to_image"] = serialize_record(
        first_layer_setting("ImageToImageSettings", layer_id, store=store)
    )
    snapshot["outpaint"] = serialize_record(
        first_layer_setting("OutpaintSettings", layer_id, store=store)
    )
    return snapshot


def restore_layer_snapshot(
    snapshot: dict[str, Any],
    *,
    store: Optional[GuiResourceStore] = None,
) -> None:
    """Restore one canvas layer snapshot into the resource store."""
    layer_data = snapshot.get("layer") or {}
    if layer_data:
        restore_record("CanvasLayer", layer_data, store=store)
    mapping = {
        "drawing_pad": "DrawingPadSettings",
        "controlnet": "ControlnetSettings",
        "image_to_image": "ImageToImageSettings",
        "outpaint": "OutpaintSettings",
    }
    for key, resource_name in mapping.items():
        data = snapshot.get(key) or {}
        if data:
            restore_record(resource_name, data, store=store)


def apply_layer_orders(
    orders: Iterable[dict[str, int]],
    *,
    store: Optional[GuiResourceStore] = None,
) -> None:
    """Apply one ordered list of layer ids and order values."""
    for entry in orders:
        layer_id = entry.get("layer_id")
        order_value = entry.get("order")
        if layer_id is None or order_value is None:
            continue
        update_canvas_layer(
            layer_id,
            {"order": order_value},
            store=store,
        )