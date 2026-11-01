"""Sidecar chat payload must omit unset optional message fields.

The llama.cpp chat parser rejects ``"name": null`` ("type must
be string, but is null"), so a bare ``model_dump()`` on
``ChatMessage`` made every sidecar generation fail before any
token was produced (W16 census section 7). These tests pin the
wire shape: unset optionals are absent, set optionals survive.
"""

from __future__ import annotations

import json

from airunner_services.runtimes.contracts import (
    ChatMessage,
    LLMInvocationRequest,
)
from airunner_services.runtimes.llama_cpp_runtime_settings import (
    LlamaCppRuntimeSettings,
)
from airunner_services.runtimes.sidecar_launcher import (
    SidecarLauncher,
)
from airunner_services.runtimes.sidecar_llm_client import (
    SidecarLLMClient,
)


def _client() -> SidecarLLMClient:
    """Build a client whose launcher is never started."""
    settings = LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=18080,
        model_path=None,
        model_id=None,
        runtime_profile="default",
        n_ctx=4096,
        n_gpu_layers=0,
        startup_timeout_seconds=1.0,
    )
    return SidecarLLMClient(
        settings=settings, launcher=SidecarLauncher(settings)
    )


def test_unset_name_is_absent_from_payload() -> None:
    """A message without a name sends no ``name`` key at all."""
    invocation = LLMInvocationRequest(
        messages=[ChatMessage(role="user", content="hi")]
    )

    payload = _client()._chat_payload(invocation)

    assert payload["messages"] == [
        {"role": "user", "content": "hi"}
    ]
    assert '"name": null' not in json.dumps(payload)


def test_set_name_survives_into_payload() -> None:
    """A message with a name keeps it on the wire."""
    invocation = LLMInvocationRequest(
        messages=[
            ChatMessage(role="user", content="hi", name="bob")
        ]
    )

    payload = _client()._chat_payload(invocation)

    assert payload["messages"][0]["name"] == "bob"


def test_thinking_kwargs_absent_by_default() -> None:
    """An unset ``enable_thinking`` sends no template kwargs.

    W21: the sidecar payload must stay byte-identical for callers
    that never opt in, so hosted defaults cannot drift.
    """
    invocation = LLMInvocationRequest(
        messages=[ChatMessage(role="user", content="hi")]
    )

    payload = _client()._chat_payload(invocation)

    assert "chat_template_kwargs" not in payload


def test_thinking_disabled_reaches_template_kwargs() -> None:
    """``enable_thinking=False`` forwards to llama.cpp kwargs.

    W21: without this, a thinking model spends a small token
    budget entirely on reasoning and returns empty content.
    """
    invocation = LLMInvocationRequest(
        messages=[ChatMessage(role="user", content="hi")],
        enable_thinking=False,
    )

    payload = _client()._chat_payload(invocation)

    assert payload["chat_template_kwargs"] == {
        "enable_thinking": False
    }


def test_completion_payload_keeps_length_finish_reason() -> None:
    """A truncated reply keeps ``finish_reason="length"``.

    W21: the budget-exhausted shape (empty content, reasoning
    only) must not be normalized into a clean stop.
    """
    data = {
        "choices": [{
            "finish_reason": "length",
            "message": {"content": "", "reasoning_content": "x"},
        }],
        "usage": {"completion_tokens": 32},
    }

    payload = SidecarLLMClient._completion_payload(data)

    assert payload["content"] == ""
    assert payload["finish_reason"] == "length"


def test_completion_payload_defaults_finish_reason() -> None:
    """A payload without a finish reason still reports stop."""
    data = {"choices": [{"message": {"content": "pong"}}]}

    payload = SidecarLLMClient._completion_payload(data)

    assert payload["content"] == "pong"
    assert payload["finish_reason"] == "stop"
