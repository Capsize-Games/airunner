"""Sidecar chat payload must omit unset optional message fields.

The llama.cpp chat parser rejects ``"name": null`` ("type must
be string, but is null"), so a bare ``model_dump()`` on
``ChatMessage`` made every sidecar generation fail before any
token was produced (W16 census section 7). These tests pin the
wire shape: unset optionals are absent, set optionals survive.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from airunner_services.runtimes.contracts import (
    ChatMessage,
    LLMInvocationRequest,
)
from airunner_services.runtimes.llama_cpp_runtime_settings import (
    LlamaCppRuntimeSettings,
)
from airunner_services.runtimes import llama_cpp_runtime_settings
from airunner_services.runtimes.sidecar_launcher import (
    SidecarLauncher,
)
from airunner_services.runtimes.sidecar_llm_client import (
    SidecarLLMClient,
)
from airunner_services.llm.provider_config import LLMProviderConfig


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


def test_function_tool_messages_and_choice_survive_sidecar_serialization() -> None:
	"""Tool definitions and assistant/tool-result turns reach llama.cpp."""
	call = {
		"id": "call-1",
		"type": "function",
		"function": {"name": "lookup", "arguments": '{"key":"x"}'},
	}
	tool = {
		"type": "function",
		"function": {"name": "lookup", "parameters": {"type": "object"}},
	}
	invocation = LLMInvocationRequest(
		messages=[
			ChatMessage(role="assistant", content=None, tool_calls=[call]),
			ChatMessage(role="tool", content="value: 42", tool_call_id="call-1"),
		],
		tools=[tool],
		tool_choice={"type": "function", "function": {"name": "lookup"}},
	)

	payload = _client()._chat_payload(invocation)

	assert payload["messages"] == [
		{"role": "assistant", "content": None, "tool_calls": [call]},
		{"role": "tool", "content": "value: 42", "tool_call_id": "call-1"},
	]
	assert payload["tools"] == [tool]
	assert payload["tool_choice"] == {
		"type": "function",
		"function": {"name": "lookup"},
	}


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


def test_completion_payload_preserves_tool_only_completion():
    tool_calls = [{"id": "call-1", "type": "function"}]
    payload = SidecarLLMClient._completion_payload(
        {
            "choices": [{
                "finish_reason": "tool_calls",
                "message": {"content": "", "tool_calls": tool_calls},
            }],
            "usage": {"prompt_tokens": 4},
        }
    )
    assert payload["content"] == ""
    assert payload["tools"] == tool_calls
    assert payload["finish_reason"] == "tool_calls"
    assert payload["usage"] == {"prompt_tokens": 4}


def test_qwen_profile_has_only_explicit_server_tuning() -> None:
    """Qwen's named profile carries its chosen llama-server settings."""
    profile = LLMProviderConfig.get_gguf_runtime_profile(
        "local", "qwen3.5-9b", "default"
    )
    assert profile["n_batch"] == 256
    assert profile["llama_server"] == {
        "batch_size": 256,
        "flash_attn": True,
        "cache_type_k": "q8_0",
        "cache_type_v": "q8_0",
        "repeat_last_n": 4096,
    }

    other_profile = LLMProviderConfig.get_gguf_runtime_profile(
        "local", "qwen2.5-7b", "default"
    )
    assert "llama_server" not in other_profile


def test_settings_resolver_applies_only_nested_sidecar_profile(monkeypatch):
    profile = LLMProviderConfig.get_gguf_runtime_profile(
        "local", "qwen3.5-9b", "default"
    )

    class ProviderConfig:
        @staticmethod
        def get_gguf_runtime_profile(*_args, **_kwargs):
            return profile

    monkeypatch.setattr(
        llama_cpp_runtime_settings,
        "_candidate_model_id",
        lambda _: "qwen3.5-9b",
    )
    monkeypatch.setattr(
        llama_cpp_runtime_settings, "_context_length", lambda *_: 32768
    )
    monkeypatch.setattr(
        llama_cpp_runtime_settings, "_gpu_layers", lambda *_: 0
    )
    monkeypatch.setattr(
        llama_cpp_runtime_settings, "_resolve_model_path", lambda *_: None
    )
    monkeypatch.setattr(
        llama_cpp_runtime_settings,
        "_load_provider_config",
        lambda: ProviderConfig,
    )
    monkeypatch.setattr(
        llama_cpp_runtime_settings,
        "resolve_runtime_executable",
        lambda *_: "llama-server",
    )
    monkeypatch.setattr(
        llama_cpp_runtime_settings,
        "resolve_runtime_bind_host",
        lambda *_: "127.0.0.1",
    )

    settings = llama_cpp_runtime_settings.resolve_llama_cpp_runtime_settings(
        llm_settings=object(),
        path_settings=SimpleNamespace(base_path="/tmp"),
    )

    assert settings.n_batch == 256
    assert settings.flash_attn is True
    assert settings.cache_type_k == "q8_0"
    assert settings.cache_type_v == "q8_0"
    assert settings.repeat_last_n == 4096


def test_launcher_appends_optional_profile_flags(tmp_path) -> None:
    """Optional profile settings become CLI args; defaults stay omitted."""
    model = tmp_path / "model.gguf"
    model.write_bytes(b"fixture")
    base = LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=18080,
        model_path=str(model),
        model_id="qwen3.5-9b",
        runtime_profile="default",
        n_ctx=4096,
        n_gpu_layers=0,
        startup_timeout_seconds=1,
        n_batch=256,
        flash_attn=True,
        cache_type_k="q8_0",
        cache_type_v="q8_0",
        repeat_last_n=4096,
    )
    command = SidecarLauncher(base).command()
    expected = [
        "--batch-size", "256",
        "--flash-attn", "on",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
        "--repeat-last-n", "4096",
    ]
    assert command[-len(expected):] == expected

    defaults = SidecarLauncher(
        LlamaCppRuntimeSettings(
            executable="llama-server",
            host="127.0.0.1",
            port=18080,
            model_path=str(model),
            model_id="other",
            runtime_profile="default",
            n_ctx=4096,
            n_gpu_layers=0,
            startup_timeout_seconds=1,
        )
    ).command()
    assert not any(
        flag in defaults
        for flag in (
            "--batch-size",
            "--flash-attn",
            "--cache-type-k",
            "--cache-type-v",
            "--repeat-last-n",
        )
    )
