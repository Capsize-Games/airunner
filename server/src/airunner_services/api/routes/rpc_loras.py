"""RPC handlers: LoRA models."""

from __future__ import annotations

from typing import Any

from airunner_services.api.routes.events import _rpc_register


@_rpc_register("GET", "/api/v1/art/loras")
async def _rpc_loras_list(body: dict, **kw: Any) -> dict[str, Any]:
    """List all LoRA models."""
    try:
        from airunner_services.database.models.lora import Lora
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            items = session.query(Lora).all()
            return {
                "status": 200,
                "body": {
                    "loras": [
                        {
                            "id": item.id,
                            "name": item.name or "",
                            "path": item.path or "",
                            "enabled": bool(item.enabled),
                            "trigger_words": item.trigger_words or [],
                            "weight": (
                                float(item.weight) if item.weight else 1.0
                            ),
                        }
                        for item in items
                    ]
                },
            }
    except Exception:
        return {"status": 200, "body": {"loras": []}}


@_rpc_register("PATCH", "/api/v1/art/loras/{lora_id}")
async def _rpc_loras_update(body: dict, **kw: Any) -> dict[str, Any]:
    """Update a LoRA model."""
    pp: dict = kw.get("path_params", {})
    raw_id = pp.get("lora_id", "")
    if not raw_id.isdigit():
        return {"status": 400, "body": {"error": "Invalid ID"}}
    try:
        from airunner_services.database.models.lora import Lora
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            item = session.query(Lora).filter(Lora.id == int(raw_id)).first()
            if not item:
                return {"status": 404, "body": {"error": "Not found"}}
            for key in ("enabled", "trigger_words", "weight"):
                if key in body:
                    setattr(item, key, body[key])
            session.commit()
            return {
                "status": 200,
                "body": {
                    "id": item.id,
                    "name": item.name or "",
                    "enabled": bool(item.enabled),
                    "trigger_words": item.trigger_words or [],
                    "weight": float(item.weight) if item.weight else 1.0,
                },
            }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}
