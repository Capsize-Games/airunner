"""Qwen GGUF handlers must pass per-request thinking flags into GGUF templates."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
HANDLER_PATH = (
    REPOSITORY_ROOT
    / "services/src/airunner_services/llm/adapters/chat_gguf_hf_chat_handler.py"
)
_spec = importlib.util.spec_from_file_location(
    "chat_gguf_hf_chat_handler_under_test", HANDLER_PATH
)
handler_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(handler_module)


@pytest.fixture
def llama_chat_format():
    return pytest.importorskip("llama_cpp.llama_chat_format")


class _FakeLlama:
    def __init__(self, native_handler):
        self.chat_format = "chat_template.default"
        self._chat_handlers = {self.chat_format: native_handler}
        self.chat_handler = None
        self.prompt_bytes = None
        self.completion_kwargs = None

    def tokenize(self, prompt: bytes, *, add_bos: bool, special: bool):
        self.prompt_bytes = prompt
        assert add_bos is False
        assert special is True
        return [7]

    def create_completion(self, **kwargs):
        self.completion_kwargs = kwargs
        return {
            "id": "fake",
            "object": "text_completion",
            "created": 1,
            "model": "qwen-gguf",
            "choices": [
                {
                    "text": "42",
                    "finish_reason": "stop",
                    "logprobs": None,
                }
            ],
            "usage": {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
        }


def _adapter(llama, *, thinking: bool):
    return SimpleNamespace(
        _llama=llama,
        model_path="/models/Qwen/Qwen3.5-9B.gguf",
        enable_thinking=thinking,
        logger=SimpleNamespace(info=lambda *args, **kwargs: None),
    )


def _native_handler(llama_chat_format):
    template = (
        "{{ bos_token }}"
        "{% for message in messages %}"
        "{% if message.role == 'user' %}<|im_start|>user\n{{ message.content }}<|im_end|>"
        "{% elif message.role == 'assistant' %}<|im_start|>assistant\n{{ message.content }}"
        "{% for call in message.tool_calls or [] %}"
        "<tool_call>{{ call.function.name }}:"
        "{% for key, value in call.function.arguments.items() %}{{ key }}={{ value }};{% endfor %}"
        "</tool_call>"
        "{% endfor %}<|im_end|>"
        "{% elif message.role == 'tool' %}<|im_start|>tool\n{{ message.content }}<|im_end|>"
        "{% endif %}"
        "{% endfor %}"
        "{% if tools %}TOOLS={{ tools|length }}{% endif %}"
        "{% if tool_choice %}CHOICE={{ tool_choice }}{% endif %}"
        "{% if enable_thinking %}THINKING=on{% else %}THINKING=off{% endif %}"
        "{% if add_generation_prompt %}<|im_start|>assistant\n"
        "{% if enable_thinking %}<think>\n{% endif %}{% endif %}"
    )
    formatter = llama_chat_format.Jinja2ChatFormatter(
        template=template,
        eos_token="<|im_end|>",
        bos_token="<|begin_of_text|>",
        stop_token_ids=[91],
    )
    return formatter.to_chat_handler()


def test_embedded_template_gets_current_thinking_and_keeps_history_tools(
    monkeypatch, llama_chat_format
):
    native = _FakeLlama(_native_handler(llama_chat_format))
    adapter = _adapter(native, thinking=False)
    monkeypatch.setattr(handler_module, "chat_template_repo_id", lambda _adapter: "Qwen/Qwen3.5-9B")
    monkeypatch.setattr(
        handler_module,
        "load_chat_template_tokenizer",
        lambda *_args, **_kwargs: pytest.fail("embedded GGUF template should avoid HF loading"),
    )

    handler_module.configure_chat_handler(adapter)
    messages = [
        {"role": "user", "content": "Find three items"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "search",
                        "arguments": '{"limit": 3}',
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-1", "content": "three results"},
    ]
    tools = [
        {"type": "function", "function": {"name": "search", "parameters": {"type": "object"}}}
    ]
    native.chat_handler(
        llama=native,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        stop=["custom-stop"],
        temperature=0.17,
    )
    no_think_prompt = native.prompt_bytes.decode()
    assert "<|begin_of_text|>" in no_think_prompt
    assert "<think>" not in no_think_prompt
    assert "THINKING=off" in no_think_prompt
    assert "search:limit=3;" in no_think_prompt
    assert "TOOLS=1" in no_think_prompt
    assert "CHOICE=auto" in no_think_prompt
    assert native.completion_kwargs["stop"] == ["custom-stop", "<|im_end|>"]
    assert native.completion_kwargs["temperature"] == 0.17
    assert native.completion_kwargs["stopping_criteria"] is not None

    adapter.enable_thinking = True
    native.chat_handler(
        llama=native,
        messages=[{"role": "user", "content": "Return 77"}],
    )
    think_prompt = native.prompt_bytes.decode()
    assert "THINKING=on" in think_prompt
    assert think_prompt.endswith("<|im_start|>assistant\n")
    assert "<think>" not in think_prompt


def test_hf_handler_remains_supported_and_receives_dynamic_flag(monkeypatch):
    calls = []
    base = lambda *args, **kwargs: calls.append((args, kwargs)) or "formatted"
    native = SimpleNamespace(chat_format=None, _chat_handlers={}, chat_handler=None)
    adapter = _adapter(native, thinking=False)
    monkeypatch.setattr(handler_module, "chat_template_repo_id", lambda _adapter: "Qwen/Qwen3.5-9B")
    monkeypatch.setattr(handler_module, "_embedded_chat_template_handler", lambda _llama: None)
    monkeypatch.setattr(handler_module, "build_hf_chat_handler", lambda *_args: base)

    handler_module.configure_chat_handler(adapter)
    result = native.chat_handler(messages=[{"role": "user", "content": "hi"}], tools=[{"name": "search"}])

    assert result == "formatted"
    assert calls[0][1]["enable_thinking"] is False
    assert calls[0][1]["tools"] == [{"name": "search"}]
