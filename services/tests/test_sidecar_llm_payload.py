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
