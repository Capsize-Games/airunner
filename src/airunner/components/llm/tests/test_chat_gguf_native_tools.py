from unittest.mock import patch

import pytest

from langchain_core.messages import HumanMessage, SystemMessage

from airunner.components.llm.adapters.chat_gguf import (
    ChatGGUF,
    UnsupportedGGUFArchitectureError,
    _detect_chat_format,
    detect_known_unsupported_architecture,
)
from packaging.version import Version
from airunner.components.llm.tools.system_tools import get_current_datetime


class FakeLlama:
    def __init__(self, response=None, stream_chunks=None):
        self.response = response or {"choices": [{"message": {"content": ""}}]}
        self.stream_chunks = stream_chunks or []
        self.calls = []

    def create_chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return iter(self.stream_chunks)
        return self.response


def _build_chat_gguf(fake_llama, model_path="/tmp/fake.gguf"):
    def fake_load_model(self):
        self._llama = fake_llama

    with patch.object(ChatGGUF, "_load_model", fake_load_model):
        return ChatGGUF(model_path=model_path)


class TestChatGGUFNativeTools:
    def test_gpt_oss_prefers_embedded_chat_template(self):
        assert _detect_chat_format("/tmp/gpt-oss-20b-F16.gguf") is None

    def test_known_unsupported_architecture_raises_before_llama_load(self):
        with patch(
            "airunner.components.llm.adapters.chat_gguf.detect_known_unsupported_architecture",
            return_value="qwen35",
        ), patch(
            "airunner.components.llm.adapters.chat_gguf._current_llama_cpp_version",
            return_value="0.3.16",
        ):
            with pytest.raises(UnsupportedGGUFArchitectureError) as exc_info:
                ChatGGUF(model_path="/tmp/Qwen3.5-9B-Q8_0.gguf")

        assert exc_info.value.architecture == "qwen35"

    def test_qwen35_not_flagged_on_newer_runtime(self):
        with patch(
            "airunner.components.llm.adapters.chat_gguf.read_gguf_architecture",
            return_value="qwen35",
        ), patch(
            "airunner.components.llm.adapters.chat_gguf._current_llama_cpp_version",
            return_value=Version("0.3.21"),
        ):
            assert detect_known_unsupported_architecture(
                "/tmp/Qwen3.5-9B-Q8_0.gguf"
            ) is None

    def test_generate_does_not_pass_enable_thinking_kwarg(self):
        fake_llama = FakeLlama(
            response={
                "choices": [
                    {
                        "message": {
                            "content": "Hello",
                        }
                    }
                ]
            }
        )
        chat_model = _build_chat_gguf(fake_llama)
        chat_model.enable_thinking = False

        chat_model._generate([HumanMessage(content="hello")])

        assert "enable_thinking" not in fake_llama.calls[0]

    def test_generate_prefixes_qwen3_no_think_directive(self):
        fake_llama = FakeLlama(
            response={
                "choices": [
                    {
                        "message": {
                            "content": "Hello",
                        }
                    }
                ]
            }
        )
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/Qwen3-8B-Q4_K_M.gguf",
        )
        chat_model.enable_thinking = False

        chat_model._generate([HumanMessage(content="hello")])

        assert (
            fake_llama.calls[0]["messages"][-1]["content"]
            == "/no_think\nhello"
        )

    def test_generate_passes_native_tools_and_tool_choice(self):
        fake_llama = FakeLlama(
            response={
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "get_current_datetime",
                                        "arguments": "{}",
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        )
        chat_model = _build_chat_gguf(fake_llama)
        tool_choice = {"type": "function", "function": {"name": "get_current_datetime"}}
        chat_model.bind_tools([get_current_datetime], tool_choice=tool_choice)

        result = chat_model._generate([HumanMessage(content="what time is it?")])

        call_kwargs = fake_llama.calls[0]
        assert call_kwargs["tools"]
        assert call_kwargs["tool_choice"] == tool_choice
        message = result.generations[0].message
        assert message.tool_calls[0]["name"] == "get_current_datetime"
        assert message.tool_calls[0]["args"] == {}

    def test_convert_messages_skips_xml_tool_prompt_for_native_tools(self):
        fake_llama = FakeLlama()
        chat_model = _build_chat_gguf(fake_llama)
        chat_model.bind_tools([get_current_datetime], tool_choice="auto")

        messages = chat_model._convert_messages(
            [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="what time is it?"),
            ]
        )

        assert len(messages) == 2
        assert "<tools>" not in messages[0]["content"]

    def test_stream_parses_native_tool_call_deltas(self):
        fake_llama = FakeLlama(
            stream_chunks=[
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "get_current_datetime",
                                            "arguments": "{",
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                },
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "function": {
                                            "arguments": "}",
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                },
            ]
        )
        chat_model = _build_chat_gguf(fake_llama)
        chat_model.bind_tools(
            [get_current_datetime],
            tool_choice={"type": "function", "function": {"name": "get_current_datetime"}},
        )

        chunks = list(chat_model._stream([HumanMessage(content="what time is it?")]))

        call_kwargs = fake_llama.calls[0]
        assert call_kwargs["tools"]
        assert chunks[-1].message.tool_calls[0]["name"] == "get_current_datetime"
        assert chunks[-1].message.tool_calls[0]["args"] == {}

    def test_stream_yields_reasoning_deltas(self):
        fake_llama = FakeLlama(
            stream_chunks=[
                {
                    "choices": [
                        {
                            "delta": {
                                "reasoning_content": "Thinking...",
                            }
                        }
                    ]
                },
                {
                    "choices": [
                        {
                            "delta": {
                                "content": "Hello",
                            }
                        }
                    ]
                },
            ]
        )
        chat_model = _build_chat_gguf(fake_llama)

        chunks = list(chat_model._stream([HumanMessage(content="hello")]))

        assert "enable_thinking" not in fake_llama.calls[0]
        assert (
            chunks[0].message.additional_kwargs["reasoning_content"]
            == "Thinking..."
        )
        assert chunks[1].message.content == "Hello"