"""Canvas layer CRUD routes for the Layers panel."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from airunner_services.database.models.canvas_layer import CanvasLayer
from airunner_services.database.session import session_scope

router = APIRouter()


@router.get("/layers")
async def list_layers():
    """Return all canvas layers ordered by their stack position."""
    with session_scope() as session:
        layers = (
            session.query(CanvasLayer)
            .order_by(CanvasLayer.order.asc())
            .all()
        )
        return {
            "layers": [
                {
                    "id": layer.id,
                    "name": layer.name,
                    "visible": bool(layer.visible),
                    "locked": bool(layer.locked),
                    "order": layer.order,
                    "opacity": layer.opacity,
                    "blend_mode": layer.blend_mode,
                }
                for layer in layers
            ],
        }


@router.post("/layers")
async def create_layer(name: Optional[str] = None):
    """Create a new canvas layer at the top of the stack."""
    with session_scope() as session:
        max_order = (
            session.query(CanvasLayer.order)
            .order_by(CanvasLayer.order.desc())
            .first()
        )
        next_order = (max_order[0] if max_order else -1) + 1
        layer_name = name or f"Layer {next_order + 1}"
        layer = CanvasLayer(
            name=layer_name,
            order=next_order,
            visible=True,
            locked=False,
            opacity=100,
            blend_mode="normal",
        )
        session.add(layer)
        session.flush()
        return {
            "id": layer.id,
            "name": layer.name,
            "visible": bool(layer.visible),
            "locked": bool(layer.locked),
            "order": layer.order,
            "opacity": layer.opacity,
            "blend_mode": layer.blend_mode,
        }


@router.patch("/layers/{layer_id}")
async def update_layer(
    layer_id: int,
    visible: Optional[bool] = None,
    locked: Optional[bool] = None,
    name: Optional[str] = None,
    opacity: Optional[int] = None,
    blend_mode: Optional[str] = None,
):
    """Update one canvas layer's properties."""
    with session_scope() as session:
        layer = session.query(CanvasLayer).filter_by(id=layer_id).first()
        if layer is None:
            raise HTTPException(status_code=404, detail="Layer not found")
        if visible is not None:
            layer.visible = visible
        if locked is not None:
            layer.locked = locked
        if name is not None:
            layer.name = name
        if opacity is not None:
            layer.opacity = max(0, min(100, opacity))
        if blend_mode is not None:
            layer.blend_mode = blend_mode
        session.commit()
        return {
            "id": layer.id,
            "name": layer.name,
            "visible": bool(layer.visible),
            "locked": bool(layer.locked),
            "order": layer.order,
            "opacity": layer.opacity,
            "blend_mode": layer.blend_mode,
        }


@router.delete("/layers/{layer_id}")
async def delete_layer(layer_id: int):
    """Delete one canvas layer."""
    with session_scope() as session:
        layer = session.query(CanvasLayer).filter_by(id=layer_id).first()
        if layer is None:
            raise HTTPException(status_code=404, detail="Layer not found")
        deleted_order = layer.order
        session.delete(layer)
        # Re-order remaining layers
        remaining = (
            session.query(CanvasLayer)
            .filter(CanvasLayer.order > deleted_order)
            .order_by(CanvasLayer.order.asc())
            .all()
        )
        for i, rem in enumerate(remaining):
            rem.order = deleted_order + i
        session.commit()
        return {"status": "deleted"}


@router.post("/layers/{layer_id}/move")
async def move_layer(
    layer_id: int,
    direction: str = Query(..., regex="^(up|down)$"),
):
    """Move one layer up or down in the stack."""
    with session_scope() as session:
        layer = session.query(CanvasLayer).filter_by(id=layer_id).first()
        if layer is None:
            raise HTTPException(status_code=404, detail="Layer not found")

        if direction == "up":
            # Swap with the layer above (lower order value)
            swap = (
                session.query(CanvasLayer)
                .filter(CanvasLayer.order < layer.order)
                .order_by(CanvasLayer.order.desc())
                .first()
            )
        else:
            # Swap with the layer below (higher order value)
            swap = (
                session.query(CanvasLayer)
                .filter(CanvasLayer.order > layer.order)
                .order_by(CanvasLayer.order.asc())
                .first()
            )

        if swap is None:
            return {"status": "at_boundary"}

        layer.order, swap.order = swap.order, layer.order
        session.commit()
        return {
            "status": "moved",
            "layer_id": layer.id,
            "new_order": layer.order,
        }


@router.post("/layers/merge-visible")
async def merge_visible_layers():
    """Merge all visible layers into one (stub for canvas integration)."""
    with session_scope() as session:
        visible_layers = (
            session.query(CanvasLayer)
            .filter_by(visible=True)
            .order_by(CanvasLayer.order.asc())
            .all()
        )
        if len(visible_layers) < 2:
            raise HTTPException(
                status_code=400,
                detail="Need at least 2 visible layers to merge",
            )
        # Keep the bottom-most visible layer, delete the rest
        keep = visible_layers[0]
        for layer in visible_layers[1:]:
            session.delete(layer)
        keep.name = "Merged"
        session.commit()
        return {"status": "merged", "layer_id": keep.id}
