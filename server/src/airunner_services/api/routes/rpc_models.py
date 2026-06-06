"""RPC handlers: models_active + models_unload."""

from __future__ import annotations

from typing import Any

from airunner_services.api.routes.events import _rpc_register
from airunner_services.api.routes.rpc_handlers import logger


@_rpc_register("GET", "/api/v1/models/active")
async def _rpc_models_active(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Return all currently active models.

    Merges models tracked by ``ModelResourceManager`` (LLM, etc.) with
    externally-tracked models (art, embedding) from ``_external_models``.
    """
    try:
        from airunner_services.model_management import ModelResourceManager

        resource_mgr = ModelResourceManager()
        models: list[dict[str, Any]] = []
        for m in resource_mgr.get_active_models():
            models.append(
                {
                    "model_id": m.model_id,
                    "model_type": m.model_type,
                    "status": m.state.value,
                    "can_unload": m.can_unload,
                    "vram_gb": m.vram_allocated_gb,
                    "ram_gb": m.ram_allocated_gb,
                    "name": m.name or "",
                }
            )
        try:
            from airunner_services.api.routes.models_status import (  # noqa: PLC0415
                _external_models,
                _external_models_lock,
            )

            seen_ids = {m["model_id"] for m in models}
            with _external_models_lock:
                for ext in _external_models.values():
                    if ext["model_id"] not in seen_ids:
                        models.append(
                            {
                                "model_id": ext["model_id"],
                                "model_type": ext["model_type"],
                                "status": ext["status"],
                                "can_unload": ext.get("can_unload", False),
                                "vram_gb": ext.get("vram_gb", 0.0),
                                "ram_gb": ext.get("ram_gb", 0.0),
                                "name": ext.get("name", ""),
                            }
                        )
                        seen_ids.add(ext["model_id"])
        except Exception:
            pass
        return {"status": 200, "body": {"models": models}}
    except Exception as exc:
        logger.warning("Failed to read active models: %s", exc)
        return {"status": 200, "body": {"models": []}}


@_rpc_register("POST", "/api/v1/models/unload")
async def _rpc_models_unload(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Request one model to be unloaded."""
    from airunner_services.contract_enums import SignalCode
    from airunner_services.utils.application.signal_mediator import (
        SignalMediator,
    )

    model_id = str(body.get("model_id", ""))
    model_type = str(body.get("model_type", ""))
    model_type_lower = model_type.strip().lower() or model_id.strip().lower()
    if "embedding" in model_type_lower:
        SignalMediator().emit_signal(
            SignalCode.RAG_INDEX_CANCEL,
            {"unload_embedding": True},
        )
        return {"status": 200, "body": {"status": "accepted"}}
    if "llm" in model_type_lower:
        SignalMediator().emit_signal(
            SignalCode.LLM_UNLOAD_SIGNAL,
            {},
        )
        return {"status": 200, "body": {"status": "accepted"}}
    return {"status": 200, "body": {"status": "accepted"}}
