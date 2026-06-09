"""RPC handlers: saved art prompts."""

from __future__ import annotations

from typing import Any

from airunner_services.api.routes.events import _rpc_register


@_rpc_register("GET", "/api/v1/art/saved-prompts")
async def _rpc_saved_prompts_list(body: dict, **kw: Any) -> dict[str, Any]:
    try:
        from airunner_services.database.models.saved_prompt import SavedPrompt
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            items = session.query(SavedPrompt).all()
            return {
                "status": 200,
                "body": {
                    "prompts": [
                        {
                            "id": item.id,
                            "prompt": item.prompt or "",
                            "secondary_prompt": item.secondary_prompt or "",
                            "negative_prompt": item.negative_prompt or "",
                            "secondary_negative_prompt": item.secondary_negative_prompt
                            or "",
                        }
                        for item in items
                    ]
                },
            }
    except Exception:
        return {"status": 200, "body": {"prompts": []}}


@_rpc_register("POST", "/api/v1/art/saved-prompts")
async def _rpc_saved_prompts_create(body: dict, **kw: Any) -> dict[str, Any]:
    try:
        from airunner_services.database.models.saved_prompt import SavedPrompt
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            item = SavedPrompt(
                prompt=body.get("prompt", ""),
                secondary_prompt=body.get("secondary_prompt", ""),
                negative_prompt=body.get("negative_prompt", ""),
                secondary_negative_prompt=body.get(
                    "secondary_negative_prompt", ""
                ),
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return {
                "status": 201,
                "body": {
                    "id": item.id,
                    "prompt": item.prompt or "",
                    "secondary_prompt": item.secondary_prompt or "",
                    "negative_prompt": item.negative_prompt or "",
                    "secondary_negative_prompt": item.secondary_negative_prompt
                    or "",
                },
            }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("DELETE", "/api/v1/art/saved-prompts/{prompt_id}")
async def _rpc_saved_prompts_delete(body: dict, **kw: Any) -> dict[str, Any]:
    pp: dict = kw.get("path_params", {})
    raw_id = pp.get("prompt_id", "")
    if not raw_id.isdigit():
        return {"status": 400, "body": {"error": "Invalid ID"}}
    try:
        from airunner_services.database.models.saved_prompt import SavedPrompt
        from airunner_services.database.session import session_scope

        with session_scope() as session:
            item = (
                session.query(SavedPrompt)
                .filter(SavedPrompt.id == int(raw_id))
                .first()
            )
            if not item:
                return {"status": 404, "body": {"error": "Not found"}}
            session.delete(item)
            session.commit()
            return {"status": 200, "body": {"ok": True}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}
