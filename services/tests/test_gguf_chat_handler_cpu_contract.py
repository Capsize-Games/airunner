"""CPU-safe GGUF chat-handler contracts without loading llama.cpp native code."""

from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
HANDLER_PATH = (
    ROOT
    / "services/src/airunner_services/llm/adapters/chat_gguf_hf_chat_handler.py"
)


def _load_handler(name: str = "cpu_chat_handler_under_test"):
    spec = importlib.util.spec_from_file_location(name, HANDLER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_module_import_does_not_touch_llama_cpp(monkeypatch):
    """A CPU process can import the handler without loading native bindings."""
    original_import = builtins.__import__
    attempts: list[str] = []

    def guarded_import(name, *args, **kwargs):
        if name == "llama_cpp" or name.startswith("llama_cpp."):
            attempts.append(name)
            raise OSError("native llama.cpp library unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    _load_handler("cpu_chat_handler_import_guard")
    assert attempts == []


def test_embedded_handler_forwards_thinking_and_tool_arguments(monkeypatch):
    """Embedded GGUF formatting stays independent of HF/native formatter imports."""
    module = _load_handler()
    captured: dict = {}

    def embedded_handler(**kwargs):
        captured.update(kwargs)
        return "embedded-result"

    llama = SimpleNamespace(
        chat_format="chat_template.default",
        _chat_handlers={"chat_template.default": embedded_handler},
        chat_handler=None,
    )
    adapter = SimpleNamespace(
        _llama=llama,
        model_path="/models/Qwen3.5-9B.gguf",
        enable_thinking=False,
        logger=SimpleNamespace(info=lambda *_args, **_kwargs: None),
    )
    monkeypatch.setattr(
        module, "chat_template_repo_id", lambda _adapter: "Qwen/Qwen3.5"
    )
    monkeypatch.setattr(
        module,
        "_load_llama_chat_format",
        lambda: pytest.fail("embedded template must not import HF formatter"),
    )
    monkeypatch.setattr(
        module,
        "load_chat_template_tokenizer",
        lambda *_args, **_kwargs: pytest.fail(
            "embedded template must not load HF tokenizer"
        ),
    )

    module.configure_chat_handler(adapter)
    result = llama.chat_handler(
        messages=[
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "function": {
                            "name": "search",
                            "arguments": '{"limit": 3}',
                        },
                    }
                ],
            }
        ],
        tools=[{"type": "function", "function": {"name": "search"}}],
        tool_choice="auto",
        stop=["end"],
    )

    assert result == "embedded-result"
    assert captured["enable_thinking"] is False
    assert captured["messages"][0]["tool_calls"][0]["function"][
        "arguments"
    ] == {"limit": 3}
    assert captured["tools"][0]["function"]["name"] == "search"
    assert captured["tool_choice"] == "auto"
    assert captured["stop"] == ["end"]


def test_lazy_formatter_native_error_is_typed_model_load_error(monkeypatch):
    """A native formatter failure during fallback remains a typed load error."""
    from airunner_services.llm.adapters import (
        chat_gguf_model_loading as loading,
    )

    handler_module = _load_handler("cpu_chat_handler_load_error")
    adapter = SimpleNamespace(
        _llama=None,
        model_path="/models/Qwen3.5-9B.gguf",
        enable_thinking=True,
        logger=SimpleNamespace(info=lambda *_args, **_kwargs: None),
        n_ctx=512,
    )
    runtime_instances = []

    class FakeLlama:
        chat_format = None
        _chat_handlers = {}

        def close(self):
            self.closed = True
            raise RuntimeError("simulated close failure")

    monkeypatch.setattr(
        loading, "_raise_for_unsupported_architecture", lambda _a: None
    )
    monkeypatch.setattr(
        loading, "_prepare_runtime_load", lambda _a: (object, False)
    )
    monkeypatch.setattr(
        loading, "_resolve_and_log_runtime_signature", lambda _a: {}
    )
    monkeypatch.setattr(loading, "_build_llama_kwargs", lambda _a, _t: {})
    monkeypatch.setattr(loading, "_log_llama_tuning", lambda _a, _t: None)
    monkeypatch.setattr(loading, "_log_estimated_kv_cache", lambda _a: None)
    monkeypatch.setattr(
        loading,
        "_load_llama_runtime_instance",
        lambda target, _cls, _kwargs: _load_fake_runtime(target),
    )

    def _load_fake_runtime(target):
        runtime = FakeLlama()
        runtime_instances.append(runtime)
        target._llama = runtime

    monkeypatch.setattr(
        handler_module, "chat_template_repo_id", lambda _a: "Qwen/Qwen3.5"
    )
    monkeypatch.setattr(handler_module, "AutoTokenizer", object())
    monkeypatch.setattr(
        loading,
        "configure_chat_handler",
        handler_module.configure_chat_handler,
    )
    attempts: list[str] = []

    def fail_native_formatter(name: str):
        attempts.append(name)
        raise OSError("native CUDA library unavailable")

    monkeypatch.setattr(
        handler_module.importlib, "import_module", fail_native_formatter
    )

    with pytest.raises(loading.ModelLoadError) as error:
        loading.load_model(adapter)

    assert isinstance(error.value.__cause__, OSError)
    assert attempts == ["llama_cpp.llama_chat_format"]
    assert runtime_instances[0].closed is True
    assert adapter._llama is None
    assert any(
        "simulated close failure" in note
        for note in error.value.__cause__.__notes__
    )

    monkeypatch.setattr(
        loading, "configure_chat_handler", lambda _adapter: None
    )
    loading.load_model(adapter)
    assert len(runtime_instances) == 2
    assert adapter._llama is runtime_instances[1]

    preexisting = FakeLlama()
    adapter._llama = preexisting
    loading.load_model(adapter)
    assert not hasattr(preexisting, "closed")
    assert len(runtime_instances) == 2
