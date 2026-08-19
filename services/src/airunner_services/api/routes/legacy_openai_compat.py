"""OpenAI-compatible endpoints served by the versioned FastAPI surface.

These routes reproduce the product-facing OpenAI compatibility surface that
previously lived in the retired ``BaseHTTPRequestHandler`` server and its
``legacy_openai_*`` handlers, so BYOK clients (e.g. VS Code Copilot) can keep
pointing at AIRunner.
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from typing import Any, Callable, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from airunner_common.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest
from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

from .legacy_llm_compat import ensure_llm_model_loaded

router = APIRouter()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

TOOL_CALL_PATTERN = re.compile(
    r'\{[\s]*"tool_call"[\s]*:[\s]*\{[^}]+\}[\s]*\}',
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# /v1/models
# ---------------------------------------------------------------------------


@router.get("/v1/models")
def openai_models() -> dict[str, Any]:
    """Handle the OpenAI /v1/models endpoint."""
    return {
        "object": "list",
        "data": [
            {
                "id": "airunner",
                "object": "model",
                "created": 1700000000,
                "owned_by": "airunner",
                "permission": [],
                "root": "airunner",
                "parent": None,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Tool-call formatting helpers
# ---------------------------------------------------------------------------


def _extract_prompt_and_system(
    messages: list[dict[str, Any]],
) -> tuple[str, str]:
    """Return the last user prompt and latest system prompt."""
    system_prompt = ""
    last_user_content = ""
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "system":
            system_prompt = content
        if role == "user":
            last_user_content = content
    return last_user_content, system_prompt


def _tool_description_lines(tool: dict[str, Any]) -> list[str]:
    """Return formatted prompt lines for one function tool definition."""
    if tool.get("type") != "function":
        return []
    function = tool.get("function", {})
    lines = [f"\n**{function.get('name', '')}**: {function.get('description', '')}"]
    parameters = function.get("parameters", {})
    properties = parameters.get("properties") or {}
    if not properties:
        return lines
    lines.append("  Parameters:")
    for name, info in properties.items():
        param_type = info.get("type", "any")
        required = " (required)" if name in parameters.get("required", []) else " (optional)"
        description = info.get("description", "")
        lines.append(f"    - {name}: {param_type}{required} - {description}")
    return lines


def _format_tools_for_prompt(tools: list[dict[str, Any]]) -> str:
    """Render OpenAI-style tool definitions into prompt instructions."""
    if not tools:
        return ""
    lines = ["You have access to the following tools:"]
    for tool in tools:
        lines.extend(_tool_description_lines(tool))
    lines.extend(
        [
            "\nTo use a tool, respond with a JSON object in this format:",
            '{"tool_call": {"name": "tool_name", "arguments": {"arg1": "value1"}}}',
            "\nOnly use a tool if it's necessary to answer the user's question.",
        ]
    )
    return "\n".join(lines)


def _enhance_system_prompt(
    system_prompt: str, tools: list[dict[str, Any]]
) -> str:
    """Append tool descriptions to the system prompt when provided."""
    if not tools:
        return system_prompt
    sections = [section for section in [system_prompt, _format_tools_for_prompt(tools)] if section]
    return "\n\n".join(sections)


def _parsed_tool_call_match(match: str) -> dict[str, Any] | None:
    """Return one parsed tool-call entry from a JSON snippet."""
    try:
        parsed = json.loads(match)
    except json.JSONDecodeError:
        return None
    if "tool_call" not in parsed:
        return None
    tool_call = parsed["tool_call"]
    return {
        "id": f"call_{uuid.uuid4().hex[:8]}",
        "type": "function",
        "function": {
            "name": tool_call.get("name", ""),
            "arguments": json.dumps(tool_call.get("arguments", {})),
        },
    }


def _parse_tool_calls_from_response(
    response_text: str | None,
    tools: list[dict[str, Any]] | None,
) -> tuple[str | None, list[dict[str, Any]]]:
    """Extract tool calls from model text and strip them from content."""
    if not tools or not response_text:
        return response_text, []
    tool_calls = [
        entry
        for match in TOOL_CALL_PATTERN.findall(response_text)
        if (entry := _parsed_tool_call_match(match)) is not None
    ]
    if not tool_calls:
        return response_text, []
    content = TOOL_CALL_PATTERN.sub("", response_text).strip()
    return content or None, tool_calls


def _build_usage(prompt: str, completion: str) -> dict[str, int]:
    """Return the OpenAI-style token usage payload."""
    return {
        "prompt_tokens": len(prompt) // 4,
        "completion_tokens": len(completion) // 4,
        "total_tokens": (len(prompt) + len(completion)) // 4,
    }


def _chunk_id(request_id: str) -> str:
    """Return the OpenAI-style chunk id for one request."""
    return f"chatcmpl-{request_id[:8]}"


def _build_openai_request(
    data: dict[str, Any],
    prompt: str,
    system_prompt: str,
    tools: list[dict[str, Any]],
) -> LLMRequest:
    """Create the internal LLM request for one OpenAI chat completion."""
    enhanced_prompt = _enhance_system_prompt(system_prompt, tools)
    llm_request = LLMRequest()
    llm_request.temperature = data.get("temperature", 0.7)
    llm_request.max_new_tokens = data.get("max_tokens", 2048)
    # Serve the model the way a real OpenAI-compatible server does:
    # only the caller's own messages, no default companion-chatbot
    # persona, no mood/datetime/style/memory injection, and no tool
    # categories forced in behind the caller's back.
    llm_request.raw_mode = True
    if enhanced_prompt:
        llm_request.system_prompt = enhanced_prompt
    llm_request.use_memory = False
    # Caller-supplied tools are handled entirely via the prompt-
    # injection + _parse_tool_calls_from_response mechanism above, not
    # the desktop app's internal tool_categories system. Binding the
    # internal 26-tool set here (tool_categories=None) confused the
    # model into degenerate output when it was never told about those
    # tools' existence via the (external-tools-only) prompt.
    llm_request.tool_categories = []
    return llm_request


def _dispatch_request(
    app,
    prompt: str,
    llm_request: LLMRequest,
    request_id: str,
    callback: Callable[[dict[str, Any]], None],
) -> None:
    """Dispatch one LLM chat request through the service API."""
    app.llm.send_request(
        prompt=prompt,
        action=LLMActionType.CHAT,
        llm_request=llm_request,
        request_id=request_id,
        callback=callback,
        # The OpenAI API has no concept of TTS. Leaving this at its
        # do_tts_reply=True default silently selects the
        # "combined_tts" GGUF runtime profile for a plain text
        # completion request, which uses different generation/stop
        # handling than the "default" profile.
        do_tts_reply=False,
    )


# ---------------------------------------------------------------------------
# Streaming response builders
# ---------------------------------------------------------------------------


def _content_chunk(model: str, request_id: str, message: str) -> dict[str, Any]:
    """Return one streaming content chunk payload."""
    return {
        "id": _chunk_id(request_id),
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": message},
            "finish_reason": None,
        }],
    }


def _tool_call_chunk(
    model: str, request_id: str, tool_calls: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return one streaming tool-call chunk payload."""
    return {
        "id": _chunk_id(request_id),
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"tool_calls": tool_calls},
            "finish_reason": "tool_calls",
        }],
    }


def _stop_chunk(model: str, request_id: str) -> dict[str, Any]:
    """Return one terminal stop chunk payload."""
    return {
        "id": _chunk_id(request_id),
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop",
        }],
    }


def _sse_line(payload: dict[str, Any]) -> bytes:
    """Return one SSE payload line."""
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


def _openai_chat_stream(
    app,
    prompt: str,
    model: str,
    llm_request: LLMRequest,
    request_id: str,
    tools: list[dict[str, Any]] | None,
):
    """Yield one streaming OpenAI chat completion."""
    done = threading.Event()
    accumulated_response: List[str] = []
    queue: List[bytes] = []

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if response is None:
            return
        # "thinking"-type events carry the model's chain-of-thought, not
        # the visible reply — including them (and, worse, treating a
        # thinking-phase is_end_of_message as the whole response being
        # done) truncates the reply right at the thinking/answer
        # boundary, before the actual answer has even been generated.
        if getattr(response, "message_type", None) == "thinking":
            return
        accumulated_response.append(response.message)
        if response.is_end_of_message:
            final_visible = getattr(response, "final_visible_message", None)
            full_text = final_visible or "".join(accumulated_response)
            content, tool_calls = _parse_tool_calls_from_response(full_text, tools)
            if tool_calls:
                queue.append(_sse_line(_tool_call_chunk(model, request_id, tool_calls)))
            else:
                queue.append(_sse_line(_stop_chunk(model, request_id)))
            queue.append(b"data: [DONE]\n\n")
            done.set()
            return
        queue.append(_sse_line(_content_chunk(model, request_id, response.message)))

    try:
        _dispatch_request(app, prompt, llm_request, request_id, callback)
    except Exception as exc:
        logger.error("OpenAI chat stream error: %s", exc, exc_info=True)
        yield _sse_line({"error": {"message": str(exc)}})
        return

    while not done.wait(timeout=0.25):
        if queue:
            yield queue.pop(0)
    while queue:
        yield queue.pop(0)


def _completion_message(
    full_response: str,
    content: str | None,
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the assistant message payload for a completion response."""
    message: dict[str, Any] = {"role": "assistant", "content": full_response}
    if tool_calls:
        message["content"] = content
        message["tool_calls"] = tool_calls
    return message


def _openai_chat_non_stream(
    app,
    prompt: str,
    model: str,
    llm_request: LLMRequest,
    request_id: str,
    tools: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Return one non-streaming OpenAI chat completion."""
    done = threading.Event()
    complete_message: List[str] = []

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if response is None:
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
        if response.is_end_of_message:
            final_visible = getattr(response, "final_visible_message", None)
            if final_visible:
                complete_message.clear()
                complete_message.append(final_visible)
            done.set()

    try:
        _dispatch_request(app, prompt, llm_request, request_id, callback)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not done.wait(timeout=300):
        raise HTTPException(status_code=504, detail="Request timeout")

    full_response = "".join(complete_message)
    content, tool_calls = _parse_tool_calls_from_response(full_response, tools)
    return {
        "id": _chunk_id(request_id),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": _completion_message(full_response, content, tool_calls),
            "finish_reason": "tool_calls" if tool_calls else "stop",
        }],
        "usage": _build_usage(prompt, full_response),
    }


# ---------------------------------------------------------------------------
# /v1/chat/completions
# ---------------------------------------------------------------------------


@router.post("/v1/chat/completions")
def openai_chat_completions(body: dict, req: Request):
    """Handle OpenAI /v1/chat/completions requests."""
    app = ensure_llm_model_loaded(req)
    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="messages is required")
    prompt, system_prompt = _extract_prompt_and_system(messages)
    tools = body.get("tools", [])
    model = body.get("model", "airunner")
    llm_request = _build_openai_request(body, prompt, system_prompt, tools)
    request_id = str(uuid.uuid4())

    if body.get("stream", False):
        return StreamingResponse(
            _openai_chat_stream(app, prompt, model, llm_request, request_id, tools),
            media_type="text/event-stream",
        )
    return _openai_chat_non_stream(app, prompt, model, llm_request, request_id, tools)
