"""RPC handlers: models_active + models_unload."""

from __future__ import annotations

import asyncio
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
    if any(
        keyword in model_type_lower
        for keyword in (
            "art",
            "sd",
            "stablediffusion",
            "z-image",
            "turbo",
            "text_to_image",
        )
    ):
        ws = kwargs.get("ws")
        if ws is not None:
            from fastapi import Request as FastAPIRequest  # noqa: PLC0415
            from airunner_services.api.routes.art_runtime_registry import (  # noqa: PLC0415
                require_runtime_registry,
                resolve_art_client,
            )
            from airunner_services.ipc.messages import (  # noqa: PLC0415
                RequestEnvelope,
            )
            from airunner_services.runtimes.contracts import (  # noqa: PLC0415
                RuntimeAction,
                RuntimeKind,
            )

            async def _fire_art_unload():
                try:
                    mock_req = FastAPIRequest(
                        {
                            "type": "http",
                            "app": getattr(ws, "app", None),
                        }
                    )
                    client = resolve_art_client(
                        require_runtime_registry(mock_req),
                    )
                    envelope = RequestEnvelope(
                        request_id="unload",
                        runtime=RuntimeKind.ART,
                        action=RuntimeAction.UNLOAD_MODEL,
                        payload={},
                        metadata={},
                    )
                    await asyncio.to_thread(client.invoke, envelope)
                except Exception as exc:
                    logger.warning(
                        "Background art unload failed: %s",
                        exc,
                    )
                SignalMediator().emit_signal(
                    SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                    {
                        "model_id": model_id,
                        "model_type": model_type or "art",
                        "status": "unloaded",
                    },
                )

            asyncio.create_task(_fire_art_unload())
            logger.info(
                "Unload requested for art model %s (type=%s)",
                model_id,
                model_type,
            )
        return {"status": 200, "body": {"status": "accepted"}}
    return {"status": 200, "body": {"status": "accepted"}}


@_rpc_register("POST", "/api/v1/models/load")
async def _rpc_models_load(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Request one model to be loaded."""
    from airunner_services.contract_enums import SignalCode
    from airunner_services.utils.application.signal_mediator import (
        SignalMediator,
    )

    model_type = str(body.get("model_type", "")).lower()
    if "embedding" in model_type:
        SignalMediator().emit_signal(
            SignalCode.RAG_LOAD_EMBEDDING,
            {},
        )
        return {"status": 200, "body": {"status": "accepted"}}
    if "llm" in model_type:
        SignalMediator().emit_signal(
            SignalCode.LLM_LOAD_SIGNAL,
            {"model_path": body.get("model_id", "")},
        )
        return {"status": 200, "body": {"status": "accepted"}}
    if "art" in model_type:
        SignalMediator().emit_signal(
            SignalCode.SD_LOAD_SIGNAL,
            {"model_path": body.get("model_id", "")},
        )
        return {"status": 200, "body": {"status": "accepted"}}
    if "stt" in model_type:
        SignalMediator().emit_signal(
            SignalCode.STT_LOAD_SIGNAL,
            {},
        )
        return {"status": 200, "body": {"status": "accepted"}}
    if "tts" in model_type:
        SignalMediator().emit_signal(
            SignalCode.TTS_ENABLE_SIGNAL,
            {},
        )
        return {"status": 200, "body": {"status": "accepted"}}
    return {"status": 200, "body": {"status": "accepted"}}
