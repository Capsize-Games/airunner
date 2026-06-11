"""RPC handlers: embeddings."""

from __future__ import annotations

from typing import Any

from airunner_services.api.routes.events import _rpc_register


@_rpc_register("GET", "/api/v1/art/embeddings")
async def _rpc_embeddings_list(body: dict, **kw: Any) -> dict[str, Any]:
    """List all embeddings."""
    try:
        from airunner_services.database.models.embedding import Embedding
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            items = session.query(Embedding).all()
            return {
                "status": 200,
                "body": {
                    "embeddings": [
                        {
                            "id": e.id,
                            "name": e.name or "",
                            "path": e.path or "",
                            "enabled": bool(e.enabled),
                            "trigger_words": e.trigger_words or [],
                        }
                        for e in items
                    ]
                },
            }
    except Exception:
        return {"status": 200, "body": {"embeddings": []}}


@_rpc_register("PATCH", "/api/v1/art/embeddings/{embedding_id}")
async def _rpc_embeddings_update(body: dict, **kw: Any) -> dict[str, Any]:
    """Update an embedding."""
    pp: dict = kw.get("path_params", {})
    raw_id = pp.get("embedding_id", "")
    if not raw_id.isdigit():
        return {"status": 400, "body": {"error": "Invalid ID"}}
    try:
        from airunner_services.database.models.embedding import Embedding
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            item = (
                session.query(Embedding)
                .filter(Embedding.id == int(raw_id))
                .first()
            )
            if not item:
                return {"status": 404, "body": {"error": "Not found"}}
            for key in ("enabled", "trigger_words"):
                if key in body:
                    setattr(item, key, body[key])
            session.commit()
            return {
                "status": 200,
                "body": {
                    "id": item.id,
                    "name": item.name or "",
                    "path": item.path or "",
                    "enabled": bool(item.enabled),
                    "trigger_words": item.trigger_words or [],
                },
            }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}
