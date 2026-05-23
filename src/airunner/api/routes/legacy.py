"""Legacy/compatibility endpoints.

Some existing consumers historically talk to the headless server using:
- GET  /health
- GET  /llm/models
- POST /llm/generate  (streams NDJSON)
- POST /art           (sync, returns base64 PNGs)
- POST /admin/*

When running headless under FastAPI/uvicorn, we keep these endpoints so the
rest of the stack doesn't need a coordinated flag-day migration.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import queue
import signal
import time
import threading
import uuid
from typing import Any, Dict, Optional, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict

from airunner.components.model_management.model_registry import ModelRegistry
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.enums import LLMActionType, SignalCode
from airunner.api.routes.health import build_health_payload
from airunner.utils.application.signal_mediator import SignalMediator


router = APIRouter()


logger = logging.getLogger(__name__)


def _get_airunner_api(req: Request):
    api = getattr(req.app.state, "airunner_app", None)
    if api is None:
        raise HTTPException(status_code=503, detail="AI Runner app not available")
    return api


def _daemon_llm_worker(req: Request):
    """Return the live daemon LLM worker when one is available."""
    api = _get_airunner_api(req)
    worker_manager = getattr(api, "_worker_manager", None)
    if worker_manager is None:
        lifecycle = getattr(req.app.state, "lifecycle_service", None)
        worker_manager = getattr(lifecycle, "worker_manager", None)
    if worker_manager is None:
        return None
    worker = getattr(worker_manager, "_llm_generate_worker", None)
    if worker is not None:
        return worker
    return getattr(worker_manager, "llm_generate_worker", None)


def _queue_daemon_llm_unload(req: Request) -> bool:
    """Interrupt and queue unload on the live daemon LLM worker."""
    worker = _daemon_llm_worker(req)
    if worker is None:
        return False

    payload = {"source": "daemon_admin_unload"}
    request_unload = getattr(worker, "request_unload_after_interrupt", None)
    if callable(request_unload):
        return bool(request_unload(payload))

    interrupt = getattr(worker, "llm_on_interrupt_process_signal", None)
    queue_unload = getattr(worker, "add_to_queue", None)
    if not callable(interrupt) or not callable(queue_unload):
        return False

    interrupt(payload)
    queue_unload({"_message_type": "llm_unload", "data": payload})
    return True


@router.get("/health")
async def legacy_health() -> Dict[str, Any]:
    return {
        **build_health_payload("ready"),
        "services": {
            "llm": os.environ.get("AIRUNNER_LLM_ON", "1") == "1",
            "art": os.environ.get("AIRUNNER_SD_ON", "0") == "1",
            "tts": os.environ.get("AIRUNNER_TTS_ON", "0") == "1",
            "stt": os.environ.get("AIRUNNER_STT_ON", "0") == "1",
        },
    }


def _schedule_process_shutdown(delay_seconds: float = 0.1) -> None:
    """Terminate the current process after the response is returned."""
    timer = threading.Timer(delay_seconds, _terminate_current_process)
    timer.daemon = True
    timer.start()


def _terminate_current_process() -> None:
    """Send SIGTERM to the current process for graceful daemon shutdown."""
    os.kill(os.getpid(), signal.SIGTERM)


@router.get("/llm/models")
def legacy_llm_models() -> Dict[str, Any]:
    try:
        registry = ModelRegistry()
        models = []
        for model_id, model_spec in registry.models.items():
            if getattr(getattr(model_spec, "model_type", None), "value", None) == "llm":
                models.append(
                    {
                        "id": model_id,
                        "name": getattr(model_spec, "name", model_id),
                        "loaded": False,
                        "size_mb": getattr(model_spec, "size_mb", None),
                    }
                )
        return {"models": models}
    except Exception:
        return {"models": []}


class LegacyLLMGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    prompt: str
    action: str = "CHAT"
    stream: bool = True
    do_tts_reply: bool = False
    system_prompt: Optional[str] = None
    search_hints: Optional[Dict[str, Any]] = None
    conversation_id: Optional[int] = None
    node_id: Optional[str] = None


class LegacyInterruptRequest(BaseModel):
    kind: Literal["process", "image"] = "process"


def _parse_action(action_str: str) -> LLMActionType:
    try:
        return LLMActionType[action_str]
    except Exception:
        return LLMActionType.CHAT


def _build_llm_request(data: Dict[str, Any]) -> LLMRequest:
    llm_request = LLMRequest()

    # Common parameter aliases
    if "max_tokens" in data and "max_new_tokens" not in data:
        data = {**data, "max_new_tokens": data.get("max_tokens")}

    # Provider alias used by some clients.
    if "provider" in data and "model_service" not in data:
        data = {**data, "model_service": data.get("provider")}

    for key, value in data.items():
        if value is None:
            continue
        if hasattr(llm_request, key):
            try:
                setattr(llm_request, key, value)
            except Exception:
                # Ignore invalid types rather than rejecting the whole request.
                pass

    # If an API backend is selected, treat "model" as an API model name, not a local model path.
    model_service = getattr(llm_request, "model_service", None)
    if model_service in ("openrouter", "ollama"):
        if getattr(llm_request, "api_model", None) is None and getattr(llm_request, "model", ""):
            llm_request.api_model = llm_request.model
            llm_request.model = ""

    return llm_request


@router.post("/llm/generate")
def legacy_llm_generate(body: LegacyLLMGenerateRequest, req: Request):
    api = _get_airunner_api(req)

    # This route is used by headless/HTTP streaming clients.
    # Ensure the LLM streaming pipeline does not suppress JSON/tool-call markup in a
    # way that would prevent tokens from reaching NDJSON clients.
    os.environ.setdefault("AIRUNNER_HEADLESS", "1")

    def _interrupt_llm_async() -> None:
        try:
            threading.Thread(target=api.llm.interrupt, daemon=True).start()
        except Exception:
            pass

    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing 'prompt' field")

    action = _parse_action(body.action)
    provided_request_id = (req.headers.get("x-request-id") or "").strip()
    request_id = provided_request_id or str(uuid.uuid4())

    raw = body.model_dump()
    llm_request = _build_llm_request(raw)
    if body.system_prompt:
        llm_request.system_prompt = body.system_prompt

    logger.info(
        "llm/generate received request_id=%s stream=%s prompt_len=%d action=%s",
        request_id,
        bool(body.stream),
        len(prompt),
        str(getattr(action, "name", None) or getattr(action, "value", action)),
    )

    if not body.stream:
        # Non-streaming: collect chunks and return once.
        complete: list[str] = []
        done = threading.Event()

        def collect_cb(data: dict):
            response = data.get("response")
            if not response:
                return
            complete.append(getattr(response, "message", "") or "")
            if getattr(response, "is_end_of_message", False):
                done.set()

        try:
            api.llm.send_request(
                prompt=prompt,
                action=action,
                llm_request=llm_request,
                do_tts_reply=body.do_tts_reply,
                request_id=request_id,
                callback=collect_cb,
                search_hints=body.search_hints,
                conversation_id=body.conversation_id,
                node_id=body.node_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        if not done.wait(timeout=300):
            raise HTTPException(status_code=504, detail="Request timeout")

        return {"message": "".join(complete)}

    q: queue.Queue[bytes] = queue.Queue()
    done = threading.Event()
    action_str = str(getattr(action, "name", None) or getattr(action, "value", action))
    # Timestamp of the last *meaningful* output enqueued for the HTTP stream.
    # Do not update this for filtered system/status callbacks, otherwise the
    # stream can hang forever while only keepalives are emitted.
    last_callback_at = [time.monotonic()]

    def stream_cb(data: dict):
        response = data.get("response")
        if not response:
            return

        # System/status messages are useful for GUI, but some NDJSON clients
        # treat streamed responses as assistant tokens.
        # Drop non-terminal system messages so we don't pollute chat output.
        try:
            if getattr(response, "is_system_message", False) and not getattr(
                response, "is_end_of_message", False
            ):
                return
        except Exception:
            pass

        # Only treat callbacks that we actually forward to the client as
        # progress for the purposes of the idle timeout.
        last_callback_at[0] = time.monotonic()
        conversation_id=body.conversation_id,
        node_id=body.node_id,

        action_val = getattr(response, "action", None)
        if action_val is None:
            action_val = action
        action_val_str = getattr(action_val, "name", None) or getattr(action_val, "value", action_val)

        tools = getattr(response, "tools", None)
        usage_obj = None
        try:
            pt = getattr(response, "prompt_tokens", None)
            ct = getattr(response, "completion_tokens", None)
            tt = getattr(response, "total_tokens", None)
            if pt is not None or ct is not None or tt is not None:
                usage_obj = {
                    "prompt_tokens": int(pt) if pt is not None else None,
                    "completion_tokens": int(ct) if ct is not None else None,
                    "total_tokens": int(tt) if tt is not None else None,
                }
        except Exception:
            usage_obj = None

        payload = {
            "message": getattr(response, "message", "") or "",
            "is_first_message": bool(getattr(response, "is_first_message", False)),
            "is_end_of_message": bool(getattr(response, "is_end_of_message", False)),
            # Convenience flag used by some clients.
            "done": bool(getattr(response, "is_end_of_message", False)),
            "sequence_number": int(getattr(response, "sequence_number", 0) or 0),
            "action": str(action_val_str),
            # Newer clients expect tool_calls; keep tools for compatibility.
            "tool_calls": tools,
            "tools": tools,
        }

        if usage_obj is not None and payload.get("is_end_of_message"):
            payload["usage"] = usage_obj

        q.put((JSONResponse(content=payload).body or b"") + b"\n")

        if payload["sequence_number"] in (0, 1) or payload["is_end_of_message"]:
            logger.info(
                "llm/generate stream_cb request_id=%s seq=%s done=%s msg_len=%d",
                request_id,
                payload["sequence_number"],
                payload["is_end_of_message"],
                len(payload.get("message") or ""),
            )

        if payload["is_end_of_message"]:
            done.set()
            try:
                SignalMediator().unregister_pending_request(request_id)
            except Exception:
                pass

    def kickoff():
        try:
            logger.info("llm/generate kickoff send_request start request_id=%s", request_id)
            api.llm.send_request(
                prompt=prompt,
                action=action,
                llm_request=llm_request,
                do_tts_reply=body.do_tts_reply,
                request_id=request_id,
                callback=stream_cb,
                search_hints=body.search_hints,
                conversation_id=body.conversation_id,
                node_id=body.node_id,
            )
            logger.info("llm/generate kickoff send_request returned request_id=%s", request_id)
        except Exception as exc:
            logger.exception("llm/generate kickoff send_request failed request_id=%s", request_id)
            err = {
                "message": f"Error invoking LLM: {exc}",
                "is_first_message": True,
                "is_end_of_message": True,
                "sequence_number": 0,
                "action": action_str,
                "error": True,
            }
            q.put((JSONResponse(content=err).body or b"") + b"\n")
            done.set()

    threading.Thread(target=kickoff, daemon=True).start()

    def _cleanup_pending_request() -> None:
        try:
            SignalMediator().unregister_pending_request(request_id)
        except Exception:
            pass

    def gen():
        # Keep the connection alive even if the model is slow to produce tokens.
        last_yield = time.monotonic()
        keepalive_interval = 5.0
        # Prevent indefinite hangs if the internal callback never fires.
        # This is intentionally an "idle" timeout (no callback activity), not a
        # read timeout; keepalives would otherwise keep the client waiting forever.
        # Allow long cold-start model loads (GGUF can take a while to mmap and warm up).
        try:
            idle_timeout = float(
                os.environ.get("AIRUNNER_LLM_STREAM_IDLE_TIMEOUT_SECONDS", "600")
            )
        except Exception:
            idle_timeout = 600.0
        logger.info("llm/generate gen start request_id=%s", request_id)
        try:
            while True:
                try:
                    line = q.get(timeout=0.25)
                    yield line
                    last_yield = time.monotonic()
                except queue.Empty:
                    now = time.monotonic()
                    if done.is_set():
                        logger.info("llm/generate gen done request_id=%s", request_id)
                        break

                    if now - last_callback_at[0] >= idle_timeout:
                        logger.warning(
                            "llm/generate idle-timeout request_id=%s idle=%.1fs timeout=%.1fs",
                            request_id,
                            now - last_callback_at[0],
                            idle_timeout,
                        )
                        timeout_err = {
                            "message": "Error invoking LLM: request timed out waiting for model output.",
                            "is_first_message": True,
                            "is_end_of_message": True,
                            "done": True,
                            "sequence_number": 0,
                            "action": action_str,
                            "error": True,
                        }
                        yield (JSONResponse(content=timeout_err).body or b"") + b"\n"
                        done.set()
                        _cleanup_pending_request()
                        # Attempt to stop any ongoing generation and clear queued work,
                        # but don't risk blocking the web server loop.
                        _interrupt_llm_async()
                        break

                    if now - last_yield >= keepalive_interval:
                        keepalive = {
                            "message": "",
                            "is_first_message": False,
                            "is_end_of_message": False,
                            "done": False,
                            "sequence_number": 0,
                            "action": action_str,
                            "keepalive": True,
                        }
                        yield (JSONResponse(content=keepalive).body or b"") + b"\n"
                        last_yield = now
        finally:
            # If the client disconnects (generator is garbage-collected/closed),
            # ensure we don't leave a long-running generation blocking later requests.
            _cleanup_pending_request()
            # Only interrupt if the stream ended *before* we reached a terminal message.
            # Unconditionally interrupting here can race with the next request and cause
            # subsequent generations to never start producing output.
            if not done.is_set():
                logger.warning(
                    "llm/generate gen closed early; interrupting request_id=%s",
                    request_id,
                )
                _interrupt_llm_async()
            else:
                logger.info(
                    "llm/generate gen cleanup after done; not interrupting request_id=%s",
                    request_id,
                )

    return StreamingResponse(gen(), media_type="application/x-ndjson")


class LegacyArtRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    steps: int = 20
    scale: Optional[float] = None
    cfg_scale: Optional[float] = None
    seed: Optional[int] = None
    random_seed: Optional[bool] = None
    n_samples: int = 1


@router.post("/art")
def legacy_art_generate(body: LegacyArtRequest, req: Request):
    _ = _get_airunner_api(req)  # Ensure app is available; actual work is signal-based.

    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing 'prompt' field")

    cfg_scale = (
        float(body.cfg_scale)
        if body.cfg_scale is not None
        else float(body.scale) if body.scale is not None else 7.5
    )

    want_random = bool(body.random_seed) if body.random_seed is not None else body.seed is None
    seed = None if want_random else int(body.seed) if body.seed is not None else None
    num_images = max(1, int(body.n_samples or 1))

    mediator = SignalMediator()
    done = threading.Event()
    error_holder: dict[str, str] = {"error": ""}
    images: list[Any] = []

    def on_image_generated(data: dict):
        img = data.get("image")
        if img is not None:
            images.append(img)
        if len(images) >= num_images:
            done.set()

    def on_error(data: dict):
        error_holder["error"] = str(data.get("message") or "Unknown error")
        done.set()

    mediator.register(SignalCode.SD_IMAGE_GENERATED_SIGNAL, on_image_generated)
    mediator.register(SignalCode.APPLICATION_ERROR_SIGNAL, on_error)

    try:
        mediator.emit_signal(
            SignalCode.SD_GENERATE_IMAGE_SIGNAL,
            {
                "prompt": prompt,
                "negative_prompt": body.negative_prompt or "",
                "width": int(body.width),
                "height": int(body.height),
                "steps": int(body.steps),
                "cfg_scale": float(cfg_scale),
                "seed": seed,
                "num_images": int(num_images),
            },
        )

        if not done.wait(timeout=300):
            raise HTTPException(status_code=504, detail="Image generation timeout")

        if error_holder["error"]:
            raise HTTPException(status_code=500, detail=error_holder["error"])

        if not images:
            raise HTTPException(status_code=500, detail="No image returned")

        encoded: list[str] = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            encoded.append(base64.b64encode(buf.getvalue()).decode("utf-8"))

        return {
            "images": encoded,
            "metadata": {},
            "seed": body.seed,
            "summary": "Generated image(s) returned as base64 strings.",
        }
    finally:
        try:
            mediator.unregister(SignalCode.SD_IMAGE_GENERATED_SIGNAL, on_image_generated)
            mediator.unregister(SignalCode.APPLICATION_ERROR_SIGNAL, on_error)
        except Exception:
            pass


@router.post("/admin/reset_memory")
def legacy_admin_reset_memory() -> Dict[str, Any]:
    return {"status": "ok"}


@router.post("/admin/interrupt")
def legacy_admin_interrupt(body: Optional[LegacyInterruptRequest] = None) -> Dict[str, Any]:
    kind = getattr(body, "kind", None) or "process"
    mediator = SignalMediator()

    if kind == "image":
        mediator.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL, {})
    else:
        mediator.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})

    return {"status": "ok"}


@router.post("/admin/llm/unload")
def legacy_admin_unload_llm(req: Request) -> Dict[str, Any]:
    if _queue_daemon_llm_unload(req):
        return {"status": "ok", "queued": True}

    mediator = SignalMediator()
    mediator.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})
    mediator.emit_signal(
        SignalCode.LLM_UNLOAD_SIGNAL,
        {"source": "daemon_admin_unload"},
    )
    return {"status": "ok", "queued": True}


@router.post("/admin/reset_database")
def legacy_admin_reset_database() -> Dict[str, Any]:
    return {"status": "ok"}


@router.post("/admin/shutdown")
def legacy_admin_shutdown() -> Dict[str, Any]:
    _schedule_process_shutdown()
    return {"status": "ok", "shutting_down": True}
