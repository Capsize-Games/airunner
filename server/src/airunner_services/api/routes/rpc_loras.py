"""RPC handlers: LoRA models."""

from __future__ import annotations

from typing import Any

from airunner_services.api.routes.events import _rpc_register


def _split_trigger_words(value: Any) -> list[str]:
    """Normalize a stored trigger_words value into a list of words.

    The column persists a comma-separated string, but the API contract
    exposes an array. Tolerates None, an existing list, or a raw string.
    """
    if isinstance(value, list):
        return [str(w).strip() for w in value if str(w).strip()]
    if not value:
        return []
    return [w.strip() for w in str(value).split(",") if w.strip()]


def _join_trigger_words(value: Any) -> str:
    """Normalize an incoming trigger_words value to the stored string form."""
    if isinstance(value, list):
        return ",".join(str(w).strip() for w in value if str(w).strip())
    return str(value or "")


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
                            "trigger_words": _split_trigger_words(
                                item.trigger_words
                            ),
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
                    value = (
                        _join_trigger_words(body[key])
                        if key == "trigger_words"
                        else body[key]
                    )
                    setattr(item, key, value)
            session.commit()
            return {
                "status": 200,
                "body": {
                    "id": item.id,
                    "name": item.name or "",
                    "path": item.path or "",
                    "enabled": bool(item.enabled),
                    "trigger_words": _split_trigger_words(item.trigger_words),
                    "weight": float(item.weight) if item.weight else 1.0,
                },
            }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}
