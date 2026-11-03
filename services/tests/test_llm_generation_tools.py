"""Bounded stateless function-tool contract through the fake runtime."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from airunner_services.api.routes.llm_generation_routes import chat_completion
from airunner_services.api.routes.llm_contracts import ChatCompletionRequest
from airunner_services.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner_services.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)


TOOL = {
    "type": "function",
    "function": {
        "name": "lookup",
        "description": "Look up a key",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    },
}
CALL = {
    "id": "call-1",
    "type": "function",
    "function": {"name": "lookup", "arguments": '{"key":"x"}'},
}


class FakeClient:
    def __init__(self, mode=RuntimeMode.SIDECAR):
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.LLM,
            provider="local",
            mode=mode,
            transport=TransportKind.HTTP,
        )
        self.requests = []

    def invoke(self, envelope):
        self.requests.append(envelope)
        return ResponseEnvelope(
            request_id="r",
            status=EnvelopeStatus.SUCCEEDED,
            payload={
                "content": "",
                "finish_reason": "tool_calls",
                "tools": [CALL],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            },
        )


class FakeRegistry:
    def __init__(self, client):
        self.client = client

    def resolve(self, *_args, **_kwargs):
        return self.client


def _runtime_and_request(runtime_mode=RuntimeMode.SIDECAR):
    runtime = FakeClient(runtime_mode)
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(runtime_registry=FakeRegistry(runtime))
        )
    )
    return request, runtime


def _tool_roundtrip_request():
    return {
        "messages": [
            {"role": "user", "content": "Find x"},
            {"role": "assistant", "content": None, "tool_calls": [CALL]},
            {
                "role": "tool",
                "tool_call_id": "call-1",
                "name": "lookup",
                "content": "value: 42",
            },
        ],
        "tools": [TOOL],
        "tool_choice": {"type": "function", "function": {"name": "lookup"}},
    }


def test_chat_forwards_tool_roundtrip_and_returns_calls_and_usage(monkeypatch):
    async def run_inline(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(
        "airunner_services.api.routes.llm_runtime.asyncio.to_thread", run_inline
    )
    request, runtime = _runtime_and_request()
    response = asyncio.run(
        chat_completion(
            ChatCompletionRequest.model_validate(_tool_roundtrip_request()), request
        )
    )

    assert response.model_dump(exclude_none=True) == {
        "content": "",
        "model": "default",
        "finish_reason": "tool_calls",
        "tool_calls": [CALL],
        "usage": {"prompt_tokens": 7, "completion_tokens": 3},
    }
    payload = runtime.requests[0].payload
    assert payload["tools"] == [TOOL]
    assert payload["tool_choice"] == {
        "type": "function",
        "function": {"name": "lookup"},
    }
    assert payload["messages"][1]["content"] is None
    assert payload["messages"][1]["tool_calls"] == [CALL]
    assert payload["messages"][2]["tool_call_id"] == "call-1"
    assert payload["messages"][2]["content"] == "value: 42"


def test_chat_rejects_oversized_tool_schema_before_runtime():
    _request_obj, runtime = _runtime_and_request()
    request = _tool_roundtrip_request()
    request["tools"] = [TOOL] * 17

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(request)
    assert runtime.requests == []


def test_chat_rejects_stream_flag_before_runtime_invocation():
    request, runtime = _runtime_and_request()
    payload = {"messages": [{"role": "user", "content": "hi"}], "stream": True}

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            chat_completion(ChatCompletionRequest.model_validate(payload), request)
        )

    assert exc.value.status_code == 400
    assert "/api/v1/llm/stream" in exc.value.detail
    assert runtime.requests == []


@pytest.mark.parametrize(
    "message",
    [
        {"role": "user", "content": "x", "tool_calls": [CALL]},
        {"role": "tool", "content": "x"},
        {"role": "assistant", "content": "x", "tool_call_id": "call-1"},
        {"role": "user", "content": None},
    ],
)
def test_chat_rejects_invalid_tool_message_shapes(message):
    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate({"messages": [message]})
    _request_obj, runtime = _runtime_and_request()
    assert runtime.requests == []


def test_tool_calls_are_rejected_by_local_fallback_without_invocation():
    request, runtime = _runtime_and_request(RuntimeMode.LOCAL_FALLBACK)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            chat_completion(
                ChatCompletionRequest.model_validate(_tool_roundtrip_request()),
                request,
            )
        )
    assert exc.value.status_code == 501
    assert runtime.requests == []


def test_basic_chat_response_keeps_optional_tool_fields_absent(monkeypatch):
    async def run_inline(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(
        "airunner_services.api.routes.llm_runtime.asyncio.to_thread", run_inline
    )
    request, runtime = _runtime_and_request()
    runtime.invoke = lambda envelope: ResponseEnvelope(
        request_id="r",
        status=EnvelopeStatus.SUCCEEDED,
        payload={"content": "hello", "finish_reason": "stop"},
    )

    response = asyncio.run(
        chat_completion(
            ChatCompletionRequest.model_validate(
                {"messages": [{"role": "user", "content": "hi"}]}
            ),
            request,
        )
    )

    assert response.model_dump(exclude_none=True) == {
        "content": "hello",
        "model": "default",
        "finish_reason": "stop",
    }
