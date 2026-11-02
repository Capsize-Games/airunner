"""A terminal backend failure must not become a successful API completion."""

import json

import pytest
from fastapi import HTTPException

from airunner_common.contract_enums import LLMActionType
from airunner_common.llm_response import LLMResponse
from airunner_services.api.routes import legacy_llm_nonstream as legacy
from airunner_services.api.routes import legacy_ollama_compat as ollama
from airunner_services.api.routes import legacy_openai_compat as openai
from airunner_services.api.routes.legacy_contracts import LegacyLLMGenerateRequest
from airunner_services.llm.llm_request import LLMRequest


def _install_callbacks(monkeypatch, events):
    def collect(*args):
        callback = args[-1]
        for event in events:
            callback({"response": event})

    monkeypatch.setattr(ollama, "_collect_text", collect)
    monkeypatch.setattr(legacy, "send_legacy_llm_request", collect)
    monkeypatch.setattr(openai, "_dispatch_request", collect)


@pytest.mark.parametrize("message_type", [None, "error"])
@pytest.mark.parametrize("route", ["chat", "generate", "legacy", "openai"])
def test_nonstream_terminal_failure_returns_generic_http_error(
    monkeypatch, route, message_type,
):
    _install_callbacks(monkeypatch, [LLMResponse(
        message="SYNTHETIC_PRIVATE_BACKEND_DETAIL", is_system_message=True,
        is_end_of_message=True, message_type=message_type,
    )])
    with pytest.raises(HTTPException) as error:
        if route == "legacy":
            legacy.collect_non_stream_response(
                object(), LegacyLLMGenerateRequest(prompt="fixture"),
                "fixture", LLMActionType.CHAT, LLMRequest(), "request",
            )
        elif route == "openai":
            openai._openai_chat_non_stream(
                object(), "fixture", "model", LLMRequest(), "request", None,
            )
        else:
            handler = getattr(ollama, f"_ollama_{route}_non_stream")
            handler(object(), "fixture", "model", LLMRequest(), "request")
    assert error.value.status_code == 500
    assert error.value.detail == "LLM generation failed"


@pytest.mark.parametrize("route", ["chat", "generate"])
def test_stream_terminal_failure_has_error_and_no_success_message(monkeypatch, route):
    _install_callbacks(monkeypatch, [LLMResponse(
        message="SYNTHETIC_PRIVATE_BACKEND_DETAIL", is_system_message=True,
        is_end_of_message=True,
    ), LLMResponse(message="late success", is_end_of_message=True)])
    handler = getattr(ollama, f"_ollama_{route}_stream")
    rows = list(handler(object(), "fixture", "model", LLMRequest(), "request"))
    assert len(rows) == 1
    payload = json.loads(rows[0])
    assert payload["done"] is True
    assert payload["error"] == "LLM generation failed"
    assert "SYNTHETIC_PRIVATE_BACKEND_DETAIL" not in rows[0].decode()


def test_openai_stream_failure_cannot_be_followed_by_success(monkeypatch):
    _install_callbacks(monkeypatch, [
        LLMResponse(message="private detail", is_system_message=True,
                    is_end_of_message=True),
        LLMResponse(message="late success", is_end_of_message=True),
    ])
    rows = list(openai._openai_chat_stream(
        object(), "fixture", "model", LLMRequest(), "request", None,
    ))
    assert len(rows) == 1
    assert json.loads(rows[0].decode().removeprefix("data: ")) == {
        "error": {"message": "LLM generation failed"},
    }


@pytest.mark.parametrize("route", ["chat", "generate", "openai"])
def test_nonterminal_status_does_not_pollute_successful_reply(monkeypatch, route):
    _install_callbacks(monkeypatch, [
        LLMResponse(message="internal load status", is_system_message=True),
        LLMResponse(message="answer", message_type="assistant"),
        LLMResponse(message="", message_type="assistant", is_end_of_message=True),
    ])
    if route == "openai":
        payload = openai._openai_chat_non_stream(
            object(), "fixture", "model", LLMRequest(), "request", None,
        )
        answer = payload["choices"][0]["message"]["content"]
    else:
        handler = getattr(ollama, f"_ollama_{route}_non_stream")
        payload = handler(object(), "fixture", "model", LLMRequest(), "request")
        answer = payload["message"]["content"] if route == "chat" else payload["response"]
    assert answer == "answer"


def test_legacy_tool_only_completion_remains_successful(monkeypatch):
    _install_callbacks(monkeypatch, [LLMResponse(
        message="", tools=["synthetic_tool"], is_end_of_message=True,
        message_type="assistant",
    )])
    result = legacy.collect_non_stream_response(
        object(), LegacyLLMGenerateRequest(prompt="fixture"), "fixture",
        LLMActionType.CHAT, LLMRequest(), "request",
    )
    assert result == {"message": "", "tools": ["synthetic_tool"],
                      "tool_calls": ["synthetic_tool"]}


@pytest.mark.parametrize("path,module,body", [
    ("/api/generate", ollama, {"prompt": "fixture"}),
    ("/api/chat", ollama, {"messages": [{"role": "user", "content": "fixture"}]}),
    ("/v1/chat/completions", openai, {"messages": [{"role": "user", "content": "fixture"}]}),
])
def test_http_nonstream_failure_is_not_status_200(monkeypatch, path, module, body):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    _install_callbacks(monkeypatch, [LLMResponse(
        message="private backend detail", is_end_of_message=True,
        is_system_message=True,
    )])
    monkeypatch.setattr(module, "ensure_llm_model_loaded", lambda req: object())
    app = FastAPI()
    app.include_router(module.router)
    with TestClient(app) as client:
        response = client.post(path, json={"model": "fixture", "stream": False, **body})
    assert response.status_code == 500
    assert response.json() == {"detail": "LLM generation failed"}
