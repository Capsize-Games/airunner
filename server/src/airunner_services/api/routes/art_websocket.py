"""Art WebSocket endpoint for real-time generation, cancel, and control."""

from __future__ import annotations

import asyncio
import json
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from airunner_services.api.routes.art_contracts import GenerationRequest
from airunner_services.api.routes.art_job_response import run_art_job
from airunner_services.api.routes.art_runtime import (
    require_runtime_registry,
    resolve_art_client,
    unload_llm_before_art,
)
from airunner_services.api.routes.art_runtime_control import (
    build_control_request,
)
from airunner_services.api.routes.art_runtime_registry import (
    require_runtime_registry as require_art_runtime_registry,
    resolve_art_client as resolve_art_runtime_client,
)
from airunner_services.runtimes.contracts import RuntimeAction
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.job_tracker import (
    JobStatus as JobState,
    JobTracker,
)

router = APIRouter()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

# In-flight generation tasks keyed by job_id so cancel can signal them.
_active_generations: dict[str, asyncio.Task] = {}
_active_job_ids: dict[str, str] = {}  # ws client identifier → job_id


def _resolve_seed(seed: Optional[int]) -> int:
    if seed is not None:
        return int(seed)
    return secrets.randbelow(2**31 - 1)


async def _track_model(
    tracker: JobTracker,
    job_id: str,
    model_path: str,
    model_version: str,
) -> None:
    """Track model in the shared external-models list."""
    import os as _os

    from airunner_services.api.routes.models_status import (  # noqa: PLC0415
        _external_models,
        _external_models_lock,
        _notify_status_subscribers,
    )

    model_name = _os.path.basename(model_path.rstrip("/")) or model_path
    with _external_models_lock:
        _external_models[model_path] = {
            "model_id": model_path,
            "model_type": model_version or "art",
            "status": "loading",
            "can_unload": True,
            "vram_gb": 0.0,
            "ram_gb": 0.0,
            "name": model_name,
        }
    _notify_status_subscribers(
        {
            "type": "model_status",
            "model_type": model_version or "art",
            "model_id": model_path,
            "status": "loading",
        }
    )

    terminal = {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}
    while True:
        state = await tracker.get_status(job_id)
        if state is None or state.status in terminal:
            break
        await asyncio.sleep(1)

    # Only update model status on completion — cancel/failure leave
    # the model loaded in VRAM and shouldn't remove it from the UI.
    if state is not None and state.status == JobState.COMPLETED:
        with _external_models_lock:
            if model_path in _external_models:
                _external_models[model_path]["status"] = "loaded"
                _external_models[model_path]["can_unload"] = True
        _notify_status_subscribers(
            {
                "type": "model_status",
                "model_type": model_version or "art",
                "model_id": model_path,
                "status": "loaded",
            }
        )


async def _run_generation(
    ws: WebSocket,
    msg: dict,
    job_id: str,
) -> None:
    """Run generation as a background task and push progress through WS."""
    prompt = str(msg.get("prompt", "")).strip()
    if not prompt:
        await ws.send_json({"type": "error", "error": "No prompt provided"})
        return

    art_request = GenerationRequest(
        prompt=prompt,
        negative_prompt=str(msg.get("negative_prompt", "")),
        width=int(msg.get("width", 1024)),
        height=int(msg.get("height", 1024)),
        steps=int(msg.get("steps", 20)),
        cfg_scale=float(msg.get("cfg_scale", 7.5)),
        seed=_resolve_seed(msg.get("seed")),
        num_images=int(msg.get("num_images", 1)),
        model=str(msg.get("model")) if msg.get("model") else None,
        version=str(msg.get("version")) if msg.get("version") else None,
        scheduler=str(msg.get("scheduler")) if msg.get("scheduler") else None,
    )

    msg_id = msg.get("_id", job_id)
    tracker = JobTracker()

    # Send ack immediately so the frontend shows an indeterminate
    # progress bar while the model loads.
    await ws.send_json({"type": "ack", "job_id": job_id})

    try:
        await unload_llm_before_art(ws, source="art_ws_generate")
    except HTTPException as exc:
        await ws.send_json(
            {"type": "error", "job_id": msg_id, "error": exc.detail}
        )
        return

    try:
        client = resolve_art_client(require_runtime_registry(ws))
    except HTTPException as exc:
        await ws.send_json(
            {"type": "error", "job_id": msg_id, "error": exc.detail}
        )
        return

    if art_request.model:
        asyncio.create_task(
            _track_model(
                tracker,
                job_id,
                art_request.model,
                art_request.version or "",
            ),
        )

    run_task = asyncio.create_task(
        run_art_job(tracker, job_id, art_request, client),
    )
    _active_generations[job_id] = run_task

    terminal = {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}
    last_pct = -1
    try:
        while not run_task.done():
            state = await tracker.get_status(job_id)
            if state is not None:
                pct = int(state.progress)
                if pct != last_pct:
                    last_pct = pct
                    await ws.send_json(
                        {
                            "type": "progress",
                            "job_id": msg_id,
                            "progress": pct,
                        }
                    )
                if state.status in terminal:
                    break
            await asyncio.sleep(0.25)

        final = await tracker.get_status(job_id)
        if final is not None and final.status == JobState.COMPLETED:
            raw = (final.result or {}).get("image_bytes")
            if raw:
                import base64

                image_b64 = (
                    base64.b64encode(raw).decode("ascii")
                    if isinstance(raw, bytes)
                    else str(raw)
                )
                await ws.send_json(
                    {
                        "type": "complete",
                        "job_id": msg_id,
                        "image": image_b64,
                    }
                )
            else:
                await ws.send_json(
                    {
                        "type": "error",
                        "job_id": msg_id,
                        "error": "No image in result",
                    }
                )
        elif final is not None and final.status == JobState.CANCELLED:
            await ws.send_json(
                {
                    "type": "cancelled",
                    "job_id": msg_id,
                }
            )
        else:
            await ws.send_json(
                {
                    "type": "error",
                    "job_id": msg_id,
                    "error": final.error if final else "Unknown error",
                }
            )
    except asyncio.CancelledError:
        # Generation was cancelled via the task — send cancelled event
        try:
            await ws.send_json(
                {
                    "type": "cancelled",
                    "job_id": msg_id,
                }
            )
        except Exception:
            logger.debug(
                "Failed to send cancelled event — connection may "
                "already be closed",
                exc_info=True,
            )
    finally:
        _active_generations.pop(job_id, None)


async def _handle_generate(
    ws: WebSocket,
    msg: dict,
) -> str | None:
    """Start generation as a non-blocking background task.

    Returns the job_id so _active_job_ids can track it.
    """
    prompt = str(msg.get("prompt", "")).strip()
    if not prompt:
        await ws.send_json({"type": "error", "error": "No prompt provided"})
        return None

    # Create the job ID first so cancel can use it immediately.
    tracker = JobTracker()
    job_id = await tracker.create_job(metadata={})
    await tracker.update_progress(job_id, 1.0, JobState.RUNNING)
    msg["_id"] = job_id

    # Fire generation as a background task — does not block the WS loop.
    task = asyncio.create_task(
        _run_generation(ws, msg, job_id),
    )
    _active_generations[job_id] = task
    return job_id


async def _handle_cancel(
    ws: WebSocket,
    msg: dict,
) -> None:
    """Cancel a running generation task immediately."""
    job_id = str(msg.get("job_id", ""))
    if not job_id:
        await ws.send_json({"type": "error", "error": "No job_id"})
        return

    # Cancel the tracker
    tracker = JobTracker()
    await tracker.cancel_job(job_id)

    # Cancel the generation task (this raises CancelledError in _run_generation)
    task = _active_generations.pop(job_id, None)
    if task is not None and not task.done():
        task.cancel()

    # Also cancel via the runtime client
    try:
        client = resolve_art_client(require_runtime_registry(ws))
        await asyncio.to_thread(client.cancel, job_id)
    except Exception:
        logger.debug(
            "Runtime client cancel failed — continuing with "
            "best-effort cancellation",
            exc_info=True,
        )

    await ws.send_json({"type": "cancelled", "job_id": job_id})


async def _handle_unload(
    ws: WebSocket,
    msg: dict,
) -> None:
    """Handle an unload request — fires background task, responds instantly."""
    model_id = str(msg.get("model_id", ""))

    async def _bg():
        # Notify frontend immediately so the model disappears from the
        # UI without waiting for the runtime cleanup (which may be slow).
        from airunner_services.api.routes.models_status import (  # noqa: PLC0415
            _external_models,
            _external_models_lock,
            _notify_status_subscribers,
        )

        with _external_models_lock:
            _external_models.pop(model_id, None)
        _notify_status_subscribers(
            {
                "type": "model_status",
                "model_id": model_id,
                "model_type": "art",
                "status": "unloaded",
            }
        )

        try:
            client = resolve_art_runtime_client(
                require_art_runtime_registry(ws),
            )
            envelope = build_control_request(
                RuntimeAction.UNLOAD_MODEL,
                None,
                None,
            )
            await asyncio.to_thread(client.invoke, envelope)
        except Exception as exc:
            logger.warning("Bg unload failed: %s", exc)

    asyncio.create_task(_bg())
    await ws.send_json(
        {
            "type": "ack",
            "action": "unload",
            "model_id": model_id,
        }
    )


@router.websocket("/ws")
async def art_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time art operations.

    Client → Server:
      {"type":"generate","prompt":"...","width":512,"height":512}
      {"type":"cancel","job_id":"..."}
      {"type":"unload","model_id":"..."}

    Server → Client:
      {"type":"ack","job_id":"..."}
      {"type":"progress","job_id":"...","progress":42}
      {"type":"complete","job_id":"...","image":"<base64>"}
      {"type":"cancelled","job_id":"..."}
      {"type":"error","job_id":"...","error":"..."}
    """
    await websocket.accept()
    logger.info("Art WebSocket connected")

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = str(msg.get("type", ""))

            if msg_type == "generate":
                # Fire-and-forget — does not block the main message loop
                job_id = await _handle_generate(websocket, msg)
                if job_id:
                    _active_job_ids[id(websocket)] = job_id
            elif msg_type == "cancel":
                await _handle_cancel(websocket, msg)
            elif msg_type == "unload":
                await _handle_unload(websocket, msg)
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": f"Unknown type: {msg_type}",
                    }
                )
    except WebSocketDisconnect:
        logger.info("Art WebSocket disconnected")
    except Exception as exc:
        logger.error("Art WebSocket error: %s", exc)
    finally:
        # Cancel any in-flight generations for this connection
        for jid, task in list(_active_generations.items()):
            if not task.done():
                task.cancel()
