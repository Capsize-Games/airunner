"""Native legacy endpoints migrated onto the versioned FastAPI surface.

These paths were previously served by the retired ``BaseHTTPRequestHandler``
server.  They are kept so headless clients that still call the non-versioned
native paths continue to work, but they now dispatch through the same
runtime registry and app-state plumbing as the versioned routes.
"""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from airunner_common.contract_enums import LLMActionType
from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.llm.llm_request import LLMRequest
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

from .legacy_contracts import LegacyLLMGenerateRequest
from .legacy_llm_compat import get_airunner_app
from .legacy_llm_helpers import build_llm_request, parse_action
from .legacy_llm_routes import legacy_llm_generate
from .stt_helpers import require_runtime_registry, resolve_stt_client, response_status_is
from .tts_helpers import build_tts_envelope, require_runtime_registry as require_tts_registry
from .tts_helpers import resolve_tts_client
from .tts_models import TTSRequest

router = APIRouter()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# ---------------------------------------------------------------------------
# POST /llm (alias for /llm/generate)
# ---------------------------------------------------------------------------


@router.post("/llm")
def legacy_llm_alias(body: LegacyLLMGenerateRequest, req: Request):
    """Alias the native LLM endpoint onto the legacy generate handler."""
    return legacy_llm_generate(body, req)


# ---------------------------------------------------------------------------
# POST /llm/generate_batch
# ---------------------------------------------------------------------------


_BATCH_PARAM_MAPPING = {
    "temperature": "temperature",
    "max_tokens": "max_new_tokens",
    "top_p": "top_p",
    "top_k": "top_k",
    "repetition_penalty": "repetition_penalty",
    "use_memory": "use_memory",
    "tool_categories": "tool_categories",
}


def _map_batch_top_level_params(
    data: dict[str, Any], llm_request_data: dict[str, Any]
) -> None:
    """Map supported batch top-level parameters into llm_request data."""
    excluded = {"prompts", "system_prompt", "action", "stream", "async", "llm_request"}
    for client_param, llm_param in _BATCH_PARAM_MAPPING.items():
        if client_param in data and client_param not in excluded:
            llm_request_data[llm_param] = data[client_param]


@router.post("/llm/generate_batch")
def legacy_llm_generate_batch(body: dict, req: Request):
    """Serve the native batch LLM endpoint."""
    app = get_airunner_app(req)
    prompts = body.get("prompts")
    if not prompts or not isinstance(prompts, list):
        raise HTTPException(
            status_code=400, detail="Missing or invalid 'prompts' field"
        )

    system_prompt = body.get("system_prompt")
    action = parse_action(body.get("action", "CHAT"))
    is_async = body.get("async", False)
    llm_request_data = dict(body.get("llm_request") or {})
    _map_batch_top_level_params(body, llm_request_data)
    llm_request = build_llm_request(llm_request_data)
    if system_prompt:
        llm_request.system_prompt = system_prompt

    if is_async:
        return {
            "batch_id": str(uuid.uuid4()),
            "status": "processing",
            "total": len(prompts),
        }

    responses = _batch_results(app, prompts, action, llm_request)
    return {
        "responses": responses,
        "total": len(prompts),
        "successful": sum(1 for item in responses if item["success"]),
        "failed": sum(1 for item in responses if not item["success"]),
    }


def _batch_results(app, prompts: list, action: LLMActionType, llm_request: LLMRequest):
    """Process one batch request in parallel and return sorted results."""
    responses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_process_single_prompt, app, index, prompt, action, llm_request): index
            for index, prompt in enumerate(prompts)
        }
        for future in as_completed(futures):
            try:
                responses.append(future.result())
            except Exception as error:
                index = futures[future]
                responses.append(
                    {
                        "index": index,
                        "prompt": prompts[index],
                        "text": "",
                        "success": False,
                        "error": str(error),
                        "duration": 0.0,
                    }
                )
    responses.sort(key=lambda item: item["index"])
    return responses


def _process_single_prompt(app, index: int, prompt: str, action: LLMActionType, llm_request: LLMRequest):
    """Process one prompt in a synchronous batch request."""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    complete_message: list[str] = []
    done = threading.Event()

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if not response:
            return
        complete_message.append(response.message)
        if response.is_end_of_message:
            done.set()

    app.llm.send_request(
        prompt=prompt,
        action=action,
        llm_request=llm_request,
        request_id=request_id,
        callback=callback,
    )
    if done.wait(timeout=60):
        return {
            "index": index,
            "prompt": prompt,
            "text": "".join(complete_message),
            "success": True,
            "error": None,
            "duration": time.time() - start_time,
        }
    return {
        "index": index,
        "prompt": prompt,
        "text": "",
        "success": False,
        "error": "Request timeout",
        "duration": time.time() - start_time,
    }


# ---------------------------------------------------------------------------
# POST /stt and POST /tts (native base64/queued compat)
# ---------------------------------------------------------------------------


@router.post("/stt")
def legacy_stt(body: dict, req: Request):
    """Serve the native base64 STT endpoint via the STT runtime."""
    audio_b64 = body.get("audio", "")
    if not audio_b64:
        raise HTTPException(
            status_code=400, detail="Missing 'audio' field (base64 encoded)"
        )
    try:
        audio_bytes = base64.b64decode(audio_b64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 audio") from exc

    client = resolve_stt_client(require_runtime_registry(req))
    response = client.invoke(
        RequestEnvelope(
            runtime=RuntimeKind.STT,
            action=RuntimeAction.INVOKE,
            provider="local",
            payload={
                "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
                "mime_type": body.get("format") == "wav"
                and "audio/wav"
                or "application/octet-stream",
            },
        )
    )
    if not response_status_is(response, EnvelopeStatus.SUCCEEDED):
        detail = response.error.message if response.error else "STT request failed"
        raise HTTPException(status_code=500, detail=detail)
    return {
        "transcription": response.payload.get("text", ""),
        "status": "success",
    }


@router.post("/tts")
def legacy_tts(body: dict, req: Request):
    """Serve the native text TTS endpoint via the TTS runtime."""
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Missing 'text' field")

    request_model = TTSRequest(
        text=text,
        voice=body.get("voice"),
        speed=float(body.get("speed", 1.0)),
    )
    client = resolve_tts_client(require_tts_registry(req))
    response = client.invoke(build_tts_envelope(request_model))
    if response.status is not EnvelopeStatus.SUCCEEDED:
        detail = response.error.message if response.error else "TTS request failed"
        raise HTTPException(status_code=500, detail=detail)
    return {
        "status": "queued",
        "message": "Text queued for speech synthesis",
        "text_length": len(text),
    }
