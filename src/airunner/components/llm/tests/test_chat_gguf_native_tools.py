from unittest.mock import patch

import pytest

from langchain_core.messages import HumanMessage, SystemMessage

from airunner.components.llm.adapters.chat_gguf import (
    ChatGGUF,
    UnsupportedGGUFArchitectureError,
    _detect_chat_format,
    _llama_chat_format_supported,
    detect_known_unsupported_architecture,
    estimate_gguf_kv_cache_gb,
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
    def test_estimate_gguf_kv_cache_gb_uses_metadata(self):
        estimated = estimate_gguf_kv_cache_gb(
            "/tmp/Qwen3-8B-Q4_K_M.gguf",
            32768,
            metadata={
                "general.architecture": "qwen3",
                "qwen3.block_count": "36",
                "qwen3.attention.head_count_kv": "8",
                "qwen3.attention.key_length": "128",
                "qwen3.attention.value_length": "128",
            },
        )

        assert estimated == pytest.approx(2.25, rel=1e-3)

    def test_estimate_gguf_kv_cache_gb_uses_known_filename_fast_path(self):
        with patch(
            "airunner.components.llm.adapters.chat_gguf.read_gguf_architecture",
            side_effect=AssertionError("GGUF metadata probe should not run"),
        ):
            estimated = estimate_gguf_kv_cache_gb(
                "/tmp/Qwen3-8B-Q4_K_M.gguf",
                32768,
            )

        assert estimated == pytest.approx(2.25, rel=1e-3)

    def test_gpt_oss_uses_explicit_chat_format_when_supported(self):
        _llama_chat_format_supported.cache_clear()
        with patch(
            "airunner.components.llm.adapters.chat_gguf."
            "_llama_chat_format_supported",
            return_value=True,
        ):
            assert _detect_chat_format("/tmp/gpt-oss-20b-F16.gguf") == "gpt-oss"

    def test_gpt_oss_falls_back_to_embedded_template_when_needed(self):
        _llama_chat_format_supported.cache_clear()
        with patch(
            "airunner.components.llm.adapters.chat_gguf."
            "_llama_chat_format_supported",
            return_value=False,
        ):
            assert _detect_chat_format("/tmp/gpt-oss-20b-F16.gguf") is None

    def test_generate_normalizes_gpt_oss_channel_response(self):
        fake_llama = FakeLlama(
            response={
                "choices": [
                    {
                        "message": {
                            "content": (
                                "<|channel|>analysis<|message|>"
                                'User says "hello".'
                                "<|end|><|start|>assistant"
                                "<|channel|>final<|message|>"
                                "Hi there!<|return|>"
                            )
                        }
                    }
                ]
            }
        )
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )

        result = chat_model._generate([HumanMessage(content="hello")])

        message = result.generations[0].message
        assert message.content == "Hi there!"
        assert (
            message.additional_kwargs["thinking_content"]
            == 'User says "hello".'
        )

    def test_stream_normalizes_gpt_oss_channel_response(self):
        fake_llama = FakeLlama(
            stream_chunks=[
                {
                    "choices": [
                        {
                            "delta": {
                                "content": (
                                    "<|channel|>analysis<|message|>"
                                    "User says"
                                )
                            }
                        }
                    ]
                },
                {
                    "choices": [
                        {
                            "delta": {
                                "content": (
                                    ' "hello".<|end|><|start|>assistant'
                                    "<|channel|>final<|message|>Hi"
                                )
                            }
                        }
                    ]
                },
                {
                    "choices": [
                        {
                            "delta": {
                                "content": " there!<|return|>"
                            }
                        }
                    ]
                },
            ]
        )
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )

        chunks = list(chat_model._stream([HumanMessage(content="hello")]))

        content = "".join(chunk.message.content for chunk in chunks)
        thinking = "".join(
            chunk.message.additional_kwargs.get("reasoning_content", "")
            for chunk in chunks
        )
        assert content == "Hi there!"
        assert thinking == 'User says "hello".'

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
            "airunner.components.llm.adapters.chat_gguf._current_llama_cpp_version",
            return_value=Version("0.3.21"),
        ):
            assert detect_known_unsupported_architecture(
                "/tmp/Qwen3.5-9B-Q8_0.gguf"
            ) is None

    def test_known_supported_qwen3_filename_skips_metadata_probe(self):
        with patch(
            "airunner.components.llm.adapters.chat_gguf.read_gguf_architecture",
            side_effect=AssertionError("GGUF metadata probe should not run"),
        ):
            assert (
                detect_known_unsupported_architecture(
                    "/tmp/Qwen3-8B-Q4_K_M.gguf"
                )
                is None
            )

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

    def test_generate_injects_gpt_oss_reasoning_effort_directive(self):
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
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )
        chat_model.reasoning_effort = "high"

        chat_model._generate(
            [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="hello"),
            ]
        )

        assert "reasoning effort high" in fake_llama.calls[0]["messages"][0][
            "content"
        ].lower()

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