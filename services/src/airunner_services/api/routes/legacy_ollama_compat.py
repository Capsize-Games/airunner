"""Ollama-compatible endpoints served by the versioned FastAPI surface.

These routes reproduce the product-facing Ollama compatibility surface that
previously lived in the retired ``BaseHTTPRequestHandler`` server and its
``legacy_ollama_*`` handlers, so VS Code / Continue.dev and other Ollama
clients can keep pointing at AIRunner.
"""

from __future__ import annotations

import json
import os
import random
import re
import threading
import time
import uuid
from typing import Any, Callable, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from airunner_common.contract_enums import LLMActionType
from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_services.llm.llm_request import LLMRequest
from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

from .legacy_llm_compat import ensure_llm_model_loaded

router = APIRouter()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# ---------------------------------------------------------------------------
# Model metadata helpers
# ---------------------------------------------------------------------------


def configured_model_basename() -> str:
    """Return the basename of the configured model path, if any."""
    try:
        settings = LLMGeneratorSettings.objects.first()
        if settings and settings.model_version:
            return os.path.basename(settings.model_version)
    except Exception as exc:
        logger.debug("Could not get model settings: %s", exc)
    return ""


def metadata_from_name(model_name: str) -> dict[str, Any]:
    """Return family, size, and quantization metadata for a model name."""
    name_lower = model_name.lower()
    parameter_size = parameter_size_from_name(name_lower)
    quantization = quantization_from_name(name_lower)
    family = model_family(name_lower)
    return {
        "family": family,
        "families": [family],
        "model_name": model_name,
        "parameter_size": parameter_size,
        "quantization_level": quantization,
        "size_bytes": model_size_bytes(parameter_size, quantization),
    }


def configured_model_metadata() -> dict[str, Any]:
    """Return metadata for the configured local model, if any."""
    model_basename = configured_model_basename()
    if not model_basename:
        return metadata_from_name("airunner:latest")
    return metadata_from_name(f"{model_basename}:latest")


def model_family(name_lower: str) -> str:
    """Return the inferred Ollama family for a model name."""
    if "qwen" in name_lower:
        return "qwen"
    if "mistral" in name_lower:
        return "mistral"
    if "phi" in name_lower:
        return "phi"
    return "llama"


def parameter_size_from_name(name_lower: str) -> str:
    """Return the inferred parameter size for a model name."""
    size_match = re.search(r"(\d+\.?\d*)b", name_lower)
    if size_match:
        return f"{size_match.group(1).upper()}B"
    return "8B"


def quantization_from_name(name_lower: str) -> str:
    """Return the inferred quantization level for a model name."""
    if "4bit" in name_lower or "q4" in name_lower:
        return "Q4_K_M"
    if "8bit" in name_lower or "q8" in name_lower:
        return "Q8_0"
    if "fp16" in name_lower or "f16" in name_lower:
        return "F16"
    return "Q4_K_M"


def model_size_bytes(parameter_size: str, quantization: str) -> int:
    """Return an approximate byte size for one parameter count."""
    parameter_count = float(parameter_size.replace("B", ""))
    if quantization.startswith("Q4"):
        return int(parameter_count * 0.5 * 1e9)
    if quantization.startswith("Q8"):
        return int(parameter_count * 1.0 * 1e9)
    return int(parameter_count * 2.0 * 1e9)


def model_details(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return the shared Ollama details payload."""
    return {
        "parent_model": "",
        "format": "gguf",
        "family": metadata["family"],
        "families": metadata["families"],
        "parameter_size": metadata["parameter_size"],
        "quantization_level": metadata["quantization_level"],
    }


def model_digest(model_name: str) -> str:
    """Return a deterministic placeholder digest for a model name."""
    digest = "".join(f"{ord(char):02x}" for char in model_name[:32])
    return f"sha256:{digest.ljust(64, '0')}"


def model_capabilities(name_lower: str) -> list[str]:
    """Return the Ollama capabilities for a model name."""
    capabilities = ["completion", "tools"]
    if "-vl" in name_lower or "vl-" in name_lower or "vision" in name_lower:
        capabilities.append("vision")
    return capabilities


def model_context_length(name_lower: str) -> int:
    """Return the default context length for a model name."""
    if "qwen3" not in name_lower:
        return 4096
    if any(token in name_lower for token in ["30b", "235b", "4b"]):
        return 262144
    return 40960


def modelfile_text(model_name: str, context_length: int) -> str:
    """Return the simplified Ollama modelfile text."""
    return (
        f"FROM {model_name}\n"
        "PARAMETER temperature 0.7\n"
        f"PARAMETER num_ctx {context_length}"
    )


def model_template() -> str:
    """Return the placeholder Ollama chat template."""
    return (
        "{{ if .System }}<|im_start|>system\n{{ .System }}<|im_end|>\n"
        "{{ end }}{{ if .Prompt }}<|im_start|>user\n{{ .Prompt }}"
        "<|im_end|>\n{{ end }}<|im_start|>assistant\n{{ .Response }}"
        "<|im_end|>"
    )


def parameter_count(parameter_size: str) -> int:
    """Return the integer parameter count for a parameter-size string."""
    cleaned = parameter_size.replace(".", "").replace("B", "")
    if cleaned.isdigit():
        return int(float(parameter_size.replace("B", "")) * 1e9)
    return 8000000000


def model_info(
    metadata: dict[str, Any], context_length: int
) -> dict[str, Any]:
    """Return the Ollama show model_info payload."""
    return {
        "general.architecture": metadata["family"],
        "general.file_type": 15,
        "general.parameter_count": parameter_count(metadata["parameter_size"]),
        "general.quantization_version": 2,
        "tokenizer.ggml.model": "gpt2",
        "context_length": context_length,
    }


def _created_at() -> str:
    """Return the formatted Ollama timestamp."""
    return time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime())


def _ollama_timings(
    start_time: float,
    prompt: str,
    response_text: str,
    use_response_length: bool,
) -> dict[str, int]:
    """Return the common Ollama duration and token counters."""
    duration_ns = int((time.time() - start_time) * 1e9)
    eval_count = len(response_text) // 4 if use_response_length else 100
    return {
        "total_duration": duration_ns,
        "load_duration": 0,
        "prompt_eval_count": len(prompt) // 4,
        "prompt_eval_duration": duration_ns // 10,
        "eval_count": eval_count,
        "eval_duration": duration_ns,
    }


# ---------------------------------------------------------------------------
# Read-only metadata endpoints
# ---------------------------------------------------------------------------


@router.get("/api/tags")
def ollama_tags() -> dict[str, Any]:
    """Handle the Ollama /api/tags endpoint."""
    metadata = configured_model_metadata()
    return {
        "models": [
            {
                "name": metadata["model_name"],
                "model": metadata["model_name"],
                "modified_at": "2024-12-01T00:00:00.000000000Z",
                "size": metadata["size_bytes"],
                "digest": model_digest(metadata["model_name"]),
                "details": model_details(metadata),
            }
        ]
    }


@router.get("/api/version")
def ollama_version() -> dict[str, str]:
    """Handle the Ollama /api/version endpoint."""
    return {"version": "0.9.0"}


@router.get("/api/ps")
def ollama_ps(req: Request) -> dict[str, Any]:
    """Handle the Ollama /api/ps endpoint."""
    from .legacy_llm_compat import is_llm_model_loaded

    app = getattr(req.app.state, "airunner_app", None)
    metadata = configured_model_metadata()
    if app is None or not is_llm_model_loaded(app):
        return {"models": []}
    return {
        "models": [
            {
                "name": metadata["model_name"],
                "model": metadata["model_name"],
                "size": metadata["size_bytes"],
                "digest": model_digest(metadata["model_name"]),
                "details": model_details(metadata),
                "expires_at": "2099-12-31T23:59:59.000000000Z",
                "size_vram": metadata["size_bytes"],
            }
        ]
    }


@router.post("/api/show")
def ollama_show(body: dict) -> dict[str, Any]:
    """Handle the Ollama /api/show endpoint."""
    model_name = body.get("name", "airunner:latest")
    metadata = metadata_from_name(model_name)
    context_length = model_context_length(model_name.lower())
    return {
        "modelfile": modelfile_text(model_name, context_length),
        "parameters": f"temperature 0.7\nnum_ctx {context_length}",
        "template": model_template(),
        "license": "Apache 2.0",
        "modified_at": "2024-12-01T00:00:00.000000000Z",
        "details": model_details(metadata),
        "model_info": model_info(metadata, context_length),
        "capabilities": model_capabilities(model_name.lower()),
    }


# ---------------------------------------------------------------------------
# Streaming plumbing
# ---------------------------------------------------------------------------


def _ndjson_line(payload: dict[str, Any]) -> bytes:
    """Return one NDJSON line for the given payload dict."""
    return json.dumps(payload).encode("utf-8") + b"\n"


def _collect_text(
    app,
    prompt: str,
    llm_request: LLMRequest,
    request_id: str,
    callback: Callable[[dict[str, Any]], None],
) -> None:
    """Dispatch one chat request through the shared app LLM interface."""
    app.llm.send_request(
        prompt=prompt,
        action=LLMActionType.CHAT,
        llm_request=llm_request,
        request_id=request_id,
        callback=callback,
        # Ollama's API has no concept of TTS. Leaving this at its
        # do_tts_reply=True default silently selects the
        # "combined_tts" GGUF runtime profile for a plain text
        # completion request, which uses different generation/stop
        # handling than the "default" profile.
        do_tts_reply=False,
    )


def _chat_prompt_parts(
    messages: list[dict[str, Any]],
) -> tuple[str, str]:
    """Return the system prompt and latest user prompt from chat history."""
    system_prompt = ""
    last_user_content = ""
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "system":
            system_prompt = content
        elif role == "user":
            last_user_content = content
    return system_prompt, last_user_content


def _ollama_chat_request(
    options: dict[str, Any],
    system_prompt: str,
    tools: list[dict[str, Any]],
    think: Any = None,
) -> LLMRequest:
    """Build the LLMRequest used by Ollama chat endpoints."""
    llm_request = LLMRequest()
    llm_request.temperature = options.get("temperature", 0.7)
    llm_request.max_new_tokens = options.get("num_predict", 2048)
    # Serve the model the way a real Ollama server does: only the
    # caller's own messages, no default companion-chatbot persona, no
    # mood/datetime/style/memory injection, and no tool categories
    # forced in behind the caller's back.
    llm_request.raw_mode = True
    if system_prompt:
        llm_request.system_prompt = system_prompt
    llm_request.use_memory = False
    if isinstance(think, bool):
        llm_request.enable_thinking = think
    if tools:
        llm_request.tools = tools
        llm_request.tool_categories = None
    else:
        llm_request.tool_categories = []
    return llm_request


# ---------------------------------------------------------------------------
# /api/chat
# ---------------------------------------------------------------------------


@router.post("/api/chat")
def ollama_chat(body: dict, req: Request):
    """Handle the Ollama /api/chat endpoint."""
    app = ensure_llm_model_loaded(req)
    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="messages is required")
    tools = body.get("tools", [])
    model = body.get("model", "airunner:latest")
    stream = body.get("stream", True)
    options = body.get("options", {})
    system_prompt, prompt = _chat_prompt_parts(messages)
    llm_request = _ollama_chat_request(
        options, system_prompt, tools, body.get("think")
    )
    request_id = str(uuid.uuid4())

    if not stream:
        return _ollama_chat_non_stream(app, prompt, model, llm_request, request_id)
    return StreamingResponse(
        _ollama_chat_stream(app, prompt, model, llm_request, request_id),
        media_type="application/x-ndjson",
    )


def _ollama_chat_stream(app, prompt: str, model: str, llm_request: LLMRequest, request_id: str):
    """Yield one streaming Ollama chat response."""
    done = threading.Event()
    start_time = time.time()
    queue: List[bytes] = []

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if not response:
            return
        # "thinking"-type events carry the model's chain-of-thought, not
        # the visible reply — including them (and, worse, treating a
        # thinking-phase is_end_of_message as the whole response being
        # done) truncates the reply right at the thinking/answer
        # boundary, before the actual answer has even been generated.
        if getattr(response, "message_type", None) == "thinking":
            return
        content = response.message
        is_final = response.is_end_of_message
        if is_final:
            final_visible = getattr(response, "final_visible_message", None)
            if final_visible:
                content = final_visible
        message: dict[str, Any] = {
            "role": "assistant",
            "content": content,
        }
        if getattr(response, "tool_calls", None):
            message["tool_calls"] = response.tool_calls
            message["content"] = ""
        payload = {
            "model": model,
            "created_at": _created_at(),
            "message": message,
            "done": is_final,
        }
        if is_final:
            payload.update(
                _ollama_chat_timings(start_time, prompt, content, False)
            )
            payload["done_reason"] = "stop"
            done.set()
        queue.append(_ndjson_line(payload))

    try:
        _collect_text(app, prompt, llm_request, request_id, callback)
    except Exception as exc:
        logger.error("Ollama chat error: %s", exc, exc_info=True)
        yield _ndjson_line(
            _ollama_chat_error(
                model, {"role": "assistant", "content": ""}, str(exc)
            )
        )
        return

    while not done.wait(timeout=0.25):
        if queue:
            yield queue.pop(0)
    while queue:
        yield queue.pop(0)


def _ollama_chat_non_stream(app, prompt: str, model: str, llm_request: LLMRequest, request_id: str):
    """Return one non-streaming Ollama chat response."""
    done = threading.Event()
    complete_message: List[str] = []
    tool_calls_result: List[Any] = []
    start_time = time.time()

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if not response:
            return
        # "thinking"-type events carry the model's chain-of-thought, not
        # the visible reply — including them (and, worse, treating a
        # thinking-phase is_end_of_message as the whole response being
        # done) truncates the reply right at the thinking/answer
        # boundary, before the actual answer has even been generated.
        if getattr(response, "message_type", None) == "thinking":
            return
        if response.message:
            complete_message.append(response.message)
        if getattr(response, "tool_calls", None):
            tool_calls_result.extend(response.tool_calls)
        if response.is_end_of_message:
            final_visible = getattr(response, "final_visible_message", None)
            if final_visible:
                complete_message.clear()
                complete_message.append(final_visible)
            done.set()

    try:
        _collect_text(app, prompt, llm_request, request_id, callback)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not done.wait(timeout=300):
        raise HTTPException(status_code=504, detail="Request timeout")

    full_response = "".join(complete_message)
    message: dict[str, Any] = {"role": "assistant", "content": full_response}
    if tool_calls_result:
        message["tool_calls"] = tool_calls_result
        message["content"] = ""
    return {
        "model": model,
        "created_at": _created_at(),
        "message": message,
        "done_reason": "stop",
        "done": True,
        **_ollama_chat_timings(start_time, prompt, full_response, True),
    }


def _ollama_chat_error(
    model: str, message: dict[str, Any], error: str
) -> dict[str, Any]:
    """Return one terminal Ollama chat error payload."""
    return {
        "model": model,
        "created_at": _created_at(),
        "message": message,
        "done": True,
        "error": error,
    }


def _ollama_chat_timings(
    start_time: float,
    prompt: str,
    response_text: str,
    use_response_length: bool,
) -> dict[str, int]:
    """Return the common Ollama chat duration and token counters."""
    return _ollama_timings(start_time, prompt, response_text, use_response_length)


# ---------------------------------------------------------------------------
# /api/generate
# ---------------------------------------------------------------------------


def _ollama_generate_request(data: dict[str, Any]) -> LLMRequest:
    """Build the LLMRequest used by Ollama generate endpoints."""
    llm_request = LLMRequest()
    options = data.get("options", {})
    llm_request.temperature = options.get("temperature", 0.7)
    llm_request.max_new_tokens = options.get("num_predict", 2048)
    system = data.get("system", "")
    if system:
        llm_request.system_prompt = system
    return llm_request


@router.post("/api/generate")
def ollama_generate(body: dict, req: Request):
    """Handle the Ollama /api/generate endpoint."""
    app = ensure_llm_model_loaded(req)
    prompt = body.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    llm_request = _ollama_generate_request(body)
    request_id = str(uuid.uuid4())
    model = body.get("model", "airunner:latest")

    if body.get("stream", True):
        return StreamingResponse(
            _ollama_generate_stream(app, prompt, model, llm_request, request_id),
            media_type="application/x-ndjson",
        )
    return _ollama_generate_non_stream(
        app, prompt, model, llm_request, request_id
    )


def _ollama_generate_stream(app, prompt: str, model: str, llm_request: LLMRequest, request_id: str):
    """Yield one streaming Ollama generate response."""
    done = threading.Event()
    start_time = time.time()
    queue: List[bytes] = []

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if not response:
            return
        payload = {
            "model": model,
            "created_at": _created_at(),
            "response": response.message,
            "done": response.is_end_of_message,
        }
        if response.is_end_of_message:
            payload.update(_ollama_timings(start_time, prompt, response.message, False))
            done.set()
        queue.append(_ndjson_line(payload))

    try:
        _collect_text(app, prompt, llm_request, request_id, callback)
    except Exception as exc:
        logger.error("Ollama generate error: %s", exc, exc_info=True)
        yield _ndjson_line(_ollama_generate_error(model, str(exc)))
        return

    while not done.wait(timeout=0.25):
        if queue:
            yield queue.pop(0)
    while queue:
        yield queue.pop(0)


def _ollama_generate_non_stream(app, prompt: str, model: str, llm_request: LLMRequest, request_id: str):
    """Return one non-streaming Ollama generate response."""
    done = threading.Event()
    complete_message: List[str] = []
    start_time = time.time()

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if not response:
            return
        complete_message.append(response.message)
        if response.is_end_of_message:
            done.set()

    try:
        _collect_text(app, prompt, llm_request, request_id, callback)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not done.wait(timeout=300):
        raise HTTPException(status_code=504, detail="Request timeout")

    full_response = "".join(complete_message)
    return {
        "model": model,
        "created_at": _created_at(),
        "response": full_response,
        "done": True,
        **_ollama_timings(start_time, prompt, full_response, True),
    }


def _ollama_generate_error(model: str, message: str) -> dict[str, Any]:
    """Return one terminal Ollama generate error payload."""
    return {
        "model": model,
        "created_at": _created_at(),
        "response": "",
        "done": True,
        "error": message,
    }


# ---------------------------------------------------------------------------
# /api/embed, /api/pull, /api/copy, /api/create
# ---------------------------------------------------------------------------


def _embedding_vector() -> list[float]:
    """Return one placeholder embedding vector."""
    return [random.uniform(-1, 1) for _ in range(384)]


@router.post("/api/embed")
@router.post("/api/embeddings")
def ollama_embed(body: dict) -> dict[str, Any]:
    """Handle the Ollama /api/embed endpoint with placeholder embeddings."""
    input_text = body.get("input", body.get("prompt", ""))
    if isinstance(input_text, list):
        embeddings = [_embedding_vector() for _ in input_text]
    else:
        embeddings = [_embedding_vector()]
    return {
        "model": body.get("model", "airunner:latest"),
        "embeddings": embeddings,
        "total_duration": 1000000,
        "load_duration": 100000,
        "prompt_eval_count": len(str(input_text)) // 4,
    }


@router.post("/api/pull")
def ollama_pull(body: dict):
    """Handle the Ollama /api/pull endpoint."""
    model = body.get("model", "airunner:latest")
    responses = [
        {"status": "pulling manifest"},
        {"status": f"pulling {model}"},
        {"status": "verifying sha256 digest"},
        {"status": "writing manifest"},
        {"status": "success"},
    ]
    return _stream_or_success(body.get("stream", True), responses)


@router.post("/api/copy")
def ollama_copy(_body: dict) -> dict[str, str]:
    """Handle the Ollama /api/copy endpoint."""
    return {"status": "success"}


@router.post("/api/create")
def ollama_create(body: dict):
    """Handle the Ollama /api/create endpoint."""
    responses = [
        {"status": "reading model metadata"},
        {"status": "creating system layer"},
        {"status": "writing manifest"},
        {"status": "success"},
    ]
    return _stream_or_success(body.get("stream", True), responses)


def _stream_or_success(stream: bool, responses: list[dict[str, Any]]):
    """Return either one streamed NDJSON response or one success object."""
    if not stream:
        return {"status": "success"}
    return StreamingResponse(
        (_ndjson_line(response) for response in responses),
        media_type="application/x-ndjson",
    )
