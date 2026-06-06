"""RPC handlers: canvas document + layers."""

from __future__ import annotations

from typing import Any

from airunner_services.api.routes.events import _rpc_register


@_rpc_register("GET", "/api/v1/canvas/document")
async def _rpc_canvas_doc_get(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Return the saved canvas document string."""
    try:
        from airunner_services.database.models import CanvasSetting
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            record = session.query(CanvasSetting).first()
            doc = (
                str(record.document) if (record and record.document) else None
            )
            return {"status": 200, "body": {"document": doc}}
    except Exception:
        return {"status": 200, "body": {"document": None}}


@_rpc_register("PUT", "/api/v1/canvas/document")
async def _rpc_canvas_doc_save(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Save the canvas document string."""
    doc_str: str = body.get("document", "")
    try:
        from airunner_services.database.models import CanvasSetting
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            record = session.query(CanvasSetting).first()
            if record:
                record.document = doc_str
            else:
                session.add(CanvasSetting(document=doc_str))
            session.commit()
        return {"status": 200, "body": {"status": "saved"}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("GET", "/api/v1/canvas/layers")
async def _rpc_canvas_layers_list(body: dict, **kwargs: Any) -> dict[str, Any]:
    """List all canvas layers."""
    try:
        from airunner_services.database.models import Layer
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            layers = session.query(Layer).order_by(Layer.order).all()
            return {
                "status": 200,
                "body": {
                    "layers": [
                        {
                            "id": layer.id,
                            "name": str(layer.name) if layer.name else "",
                            "visible": bool(layer.visible),
                            "locked": bool(layer.locked),
                            "order": int(layer.order),
                            "opacity": float(layer.opacity),
                            "blend_mode": (
                                str(layer.blend_mode)
                                if layer.blend_mode
                                else "normal"
                            ),
                        }
                        for layer in layers
                    ]
                },
            }
    except Exception:
        return {"status": 200, "body": {"layers": []}}
