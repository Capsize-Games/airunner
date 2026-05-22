from unittest.mock import patch

import pytest

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

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
    def __init__(
        self,
        response=None,
        stream_chunks=None,
        completion_response=None,
        completion_responses=None,
        completion_chunks=None,
    ):
        self.response = response or {"choices": [{"message": {"content": ""}}]}
        self.stream_chunks = stream_chunks or []
        self.calls = []
        self.completion_response = completion_response or {
            "choices": [{"text": ""}]
        }
        self.completion_responses = list(completion_responses or [])
        self.completion_chunks = completion_chunks or []
        self.completion_calls = []

    def create_chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return iter(self.stream_chunks)
        return self.response

    def create_completion(self, **kwargs):
        self.completion_calls.append(kwargs)
        if kwargs.get("stream"):
            return iter(self.completion_chunks)
        if self.completion_responses:
            index = len(self.completion_calls) - 1
            if index < len(self.completion_responses):
                return self.completion_responses[index]
            return self.completion_responses[-1]
        return self.completion_response


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

    def test_generate_uses_visible_gpt_oss_commentary_without_final(self):
        fake_llama = FakeLlama(
            response={
                "choices": [
                    {
                        "message": {
                            "content": (
                                "<|channel|>analysis<|message|>Need to "
                                "inspect the workspace.<|end|>"
                                "<|start|>assistant<|channel|>commentary"
                                "<|message|>I will inspect the workspace "
                                "first.<|return|>"
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
        assert message.content == "I will inspect the workspace first."
        assert (
            message.additional_kwargs["thinking_content"]
            == "Need to inspect the workspace."
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

    def test_generate_respects_per_call_qwen_overrides(self):
        fake_llama = FakeLlama(
            response={
                "choices": [{"message": {"content": "Hello"}}]
            }
        )
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/Qwen3-8B-Q4_K_M.gguf",
        )
        chat_model.max_tokens = 8192
        chat_model.temperature = 0.6
        chat_model.enable_thinking = True

        chat_model._generate(
            [HumanMessage(content="hello")],
            max_new_tokens=256,
            temperature=0.1,
            enable_thinking=False,
        )

        call_kwargs = fake_llama.calls[0]
        assert call_kwargs["max_tokens"] == 256
        assert call_kwargs["temperature"] == 0.1
        assert call_kwargs["messages"][-1]["content"] == "/no_think\nhello"
        assert chat_model.max_tokens == 8192
        assert chat_model.temperature == 0.6
        assert chat_model.enable_thinking is True

    def test_stream_respects_per_call_gpt_oss_overrides(self):
        fake_llama = FakeLlama(
            stream_chunks=[
                {"choices": [{"delta": {"content": "Hello"}}]}
            ]
        )
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )
        chat_model.max_tokens = 4096
        chat_model.temperature = 0.6
        chat_model.reasoning_effort = "high"

        list(
            chat_model._stream(
                [
                    SystemMessage(content="You are a helpful assistant."),
                    HumanMessage(content="hello"),
                ],
                max_new_tokens=384,
                temperature=0.1,
                reasoning_effort="low",
            )
        )

        call_kwargs = fake_llama.calls[0]
        assert call_kwargs["max_tokens"] == 384
        assert call_kwargs["temperature"] == 0.1
        assert "reasoning effort low" in call_kwargs["messages"][0][
            "content"
        ].lower()
        assert chat_model.max_tokens == 4096
        assert chat_model.temperature == 0.6
        assert chat_model.reasoning_effort == "high"

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
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice=tool_choice,
        )

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
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice="auto",
        )

        messages = chat_model._convert_messages(
            [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="what time is it?"),
            ]
        )

        assert len(messages) == 2
        assert "<tools>" not in messages[0]["content"]

    def test_convert_messages_injects_xml_tool_prompt_for_json_mode(self):
        fake_llama = FakeLlama()
        chat_model = _build_chat_gguf(fake_llama)
        chat_model.tool_calling_mode = "json"
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice="any",
        )
        chat_model.tool_calling_mode = "json"

        messages = chat_model._convert_messages(
            [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="what time is it?"),
            ]
        )

        assert len(messages) == 2
        assert "<tools>" in messages[0]["content"]
        assert "You MUST call at least one tool now." in messages[0][
            "content"
        ]

    def test_generate_parses_xml_tools_without_native_binding_in_json_mode(
        self,
    ):
        fake_llama = FakeLlama(
            response={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '<tool_call>{"name": '
                                '"get_current_datetime", '
                                '"arguments": {}}</tool_call>'
                            ),
                        }
                    }
                ]
            }
        )
        chat_model = _build_chat_gguf(fake_llama)
        chat_model.tool_calling_mode = "json"
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice="any",
        )
        chat_model.tool_calling_mode = "json"

        result = chat_model._generate([HumanMessage(content="what time is it?")])

        call_kwargs = fake_llama.calls[0]
        assert "tools" not in call_kwargs
        assert "tool_choice" not in call_kwargs
        message = result.generations[0].message
        assert message.content == ""
        assert message.tool_calls[0]["name"] == "get_current_datetime"
        assert message.tool_calls[0]["args"] == {}

    def test_bind_tools_returns_isolated_model_copy(self):
        fake_llama = FakeLlama()
        chat_model = _build_chat_gguf(fake_llama)

        def echo_tool(text: str) -> str:
            """Return the provided text."""
            return text

        bound_time = chat_model.bind_tools([get_current_datetime])
        bound_echo = chat_model.bind_tools([echo_tool])

        assert bound_time is not chat_model
        assert bound_echo is not chat_model
        assert bound_time is not bound_echo
        assert chat_model.tools is None
        assert bound_time._llama is chat_model._llama
        assert bound_echo._llama is chat_model._llama
        assert (
            bound_time.tools[0]["function"]["name"]
            == "get_current_datetime"
        )
        assert bound_echo.tools[0]["function"]["name"] == "echo_tool"

    def test_generate_uses_raw_harmony_completion_for_gpt_oss_mode(self):
        fake_llama = FakeLlama(
            completion_response={
                "choices": [
                    {
                        "text": (
                            "<|channel|>analysis<|message|>Need to use "
                            "function get_current_datetime.<|end|>"
                            "<|start|>assistant<|channel|>commentary "
                            "to=functions.get_current_datetime "
                            "<|constrain|>json<|message|>{}"
                        )
                    }
                ]
            }
        )
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )
        chat_model.tool_calling_mode = "react"
        chat_model = chat_model.bind_tools([get_current_datetime])

        result = chat_model._generate(
            [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="what time is it?"),
            ]
        )

        call_kwargs = fake_llama.completion_calls[0]
        assert not fake_llama.calls
        assert "<|start|>developer<|message|>" in call_kwargs["prompt"]
        assert "namespace functions" in call_kwargs["prompt"]
        assert "Valid channels: analysis, commentary, final" in (
            call_kwargs["prompt"]
        )
        message = result.generations[0].message
        assert message.tool_calls[0]["name"] == "get_current_datetime"
        assert message.tool_calls[0]["args"] == {}
        assert message.content == ""
        assert "Need to use function get_current_datetime." in (
            message.additional_kwargs["thinking_content"]
        )

    def test_stream_uses_raw_harmony_completion_for_gpt_oss_mode(self):
        fake_llama = FakeLlama(
            completion_chunks=[
                {
                    "choices": [
                        {
                            "text": (
                                "<|channel|>analysis<|message|>Need to use "
                                "function get_current_datetime.<|end|>"
                                "<|start|>assistant<|channel|>commentary "
                            )
                        }
                    ]
                },
                {
                    "choices": [
                        {
                            "text": (
                                "to=functions.get_current_datetime "
                                "<|constrain|>json<|message|>{}"
                            )
                        }
                    ]
                },
            ]
        )
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )
        chat_model.tool_calling_mode = "react"
        chat_model = chat_model.bind_tools([get_current_datetime])

        chunks = list(chat_model._stream([HumanMessage(content="what time is it?")]))

        assert fake_llama.completion_calls[0]["stream"] is True
        assert chunks[-1].message.tool_calls[0]["name"] == "get_current_datetime"
        assert chunks[-1].message.tool_calls[0]["args"] == {}

    def test_convert_messages_preserves_gpt_oss_tool_history(self):
        fake_llama = FakeLlama()
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )
        chat_model.tool_calling_mode = "react"
        chat_model = chat_model.bind_tools([get_current_datetime])

        assistant = AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "get_current_datetime",
                    "args": {},
                    "type": "tool_call",
                }
            ],
            additional_kwargs={
                "thinking_content": "Need to call the clock tool.",
            },
        )
        tool_message = ToolMessage(
            content='{"timestamp": "2026-05-04T10:40:00"}',
            tool_call_id="call_1",
            name="get_current_datetime",
        )

        converted = chat_model._convert_messages(
            [HumanMessage(content="what time is it?"), assistant, tool_message]
        )

        assert converted[0]["role"] == "system"
        assert "namespace functions" in converted[0]["content"]
        assert converted[1]["role"] == "user"
        assert converted[2]["role"] == "assistant"
        assert converted[2]["content"] == "Need to call the clock tool."
        assert converted[2]["tool_calls"][0]["function"]["name"] == (
            "get_current_datetime"
        )
        assert converted[2]["tool_calls"][0]["function"]["arguments"] == (
            "{}"
        )
        assert converted[3]["role"] == "tool"
        assert converted[3]["tool_call_id"] == "call_1"

    def test_raw_harmony_prompt_preserves_gpt_oss_tool_history(self):
        fake_llama = FakeLlama()
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )
        chat_model.tool_calling_mode = "react"
        chat_model = chat_model.bind_tools([get_current_datetime])

        assistant = AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "get_current_datetime",
                    "args": {},
                    "type": "tool_call",
                }
            ],
            additional_kwargs={
                "thinking_content": "Need to call the clock tool.",
            },
        )
        tool_message = ToolMessage(
            content='{"timestamp": "2026-05-04T10:40:00"}',
            tool_call_id="call_1",
            name="get_current_datetime",
        )

        prompt = chat_model._render_gpt_oss_harmony_prompt(
            [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="what time is it?"),
                assistant,
                tool_message,
            ]
        )

        assert "<|start|>assistant<|channel|>analysis<|message|>" in prompt
        assert "Need to call the clock tool." in prompt
        assert "to=functions.get_current_datetime" in prompt
        assert "<|start|>tool to=functions.get_current_datetime" in prompt
        assert '{"timestamp": "2026-05-04T10:40:00"}' in prompt

    def test_raw_harmony_prompt_prefills_forced_gpt_oss_tool_call(self):
        fake_llama = FakeLlama()
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )
        chat_model.tool_calling_mode = "react"
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice="get_current_datetime",
        )

        prompt = chat_model._render_gpt_oss_harmony_prompt(
            [HumanMessage(content="what time is it?")]
        )

        assert prompt.endswith(
            "<|start|>assistant to=functions.get_current_datetime"
            "<|channel|>commentary<|constrain|>json<|message|>"
        )

    def test_generate_parses_gpt_oss_commentary_tool_call(self):
        fake_llama = FakeLlama(
            response={
                "choices": [
                    {
                        "message": {
                            "content": (
                                "<|channel|>analysis<|message|>Need to use "
                                "function get_current_datetime.<|end|>"
                                "<|start|>assistant<|channel|>commentary "
                                "to=functions.get_current_datetime"
                                "<|constrain|>json<|message|>{}"
                                "<|call|>"
                            ),
                        }
                    }
                ]
            }
        )
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )

        result = chat_model._generate([HumanMessage(content="what time is it?")])

        message = result.generations[0].message
        assert message.content == ""
        assert message.tool_calls[0]["name"] == "get_current_datetime"
        assert message.tool_calls[0]["args"] == {}
        assert (
            "Need to use function get_current_datetime."
            in message.additional_kwargs["thinking_content"]
        )

    def test_generate_parses_prefilled_gpt_oss_tool_call_body(self):
        fake_llama = FakeLlama(completion_response={"choices": [{"text": "{}"}]})
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )
        chat_model.tool_calling_mode = "react"
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice="get_current_datetime",
        )

        result = chat_model._generate([HumanMessage(content="what time is it?")])

        message = result.generations[0].message
        assert message.content == ""
        assert message.tool_calls[0]["name"] == "get_current_datetime"
        assert message.tool_calls[0]["args"] == {}
        assert fake_llama.completion_calls[0]["prompt"].endswith(
            "<|start|>assistant to=functions.get_current_datetime"
            "<|channel|>commentary<|constrain|>json<|message|>"
        )

    def test_generate_continues_incomplete_prefilled_gpt_oss_tool_call(self):
        def echo_tool(text: str) -> str:
            """Return the provided text."""
            return text

        fake_llama = FakeLlama(
            completion_responses=[
                {"choices": [{"text": '{"text":"hello'}]},
                {"choices": [{"text": ' world"}'}]},
            ]
        )
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )
        chat_model.tool_calling_mode = "react"
        chat_model = chat_model.bind_tools(
            [echo_tool],
            tool_choice="echo_tool",
        )

        result = chat_model._generate([HumanMessage(content="echo hello")])

        message = result.generations[0].message
        assert len(fake_llama.completion_calls) == 2
        assert message.content == ""
        assert message.tool_calls[0]["name"] == "echo_tool"
        assert message.tool_calls[0]["args"] == {"text": "hello world"}
        assert fake_llama.completion_calls[1]["prompt"].endswith(
            '{"text":"hello'
        )

    def test_generate_suppresses_malformed_prefilled_gpt_oss_tool_payload(
        self,
    ):
        fake_llama = FakeLlama(
            completion_responses=[
                {
                    "choices": [
                        {
                            "text": (
                                '{"file_path":"src/mazes/__main__.py",'
                                '"content":"print'
                            )
                        }
                    ]
                },
                {"choices": [{"text": ""}]},
            ]
        )
        chat_model = _build_chat_gguf(
            fake_llama,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )
        chat_model.tool_calling_mode = "react"
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice="get_current_datetime",
        )

        result = chat_model._generate([HumanMessage(content="write the file")])

        message = result.generations[0].message
        assert len(fake_llama.completion_calls) == 2
        assert message.content == ""
        assert message.tool_calls == []

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
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice={"type": "function", "function": {"name": "get_current_datetime"}},
        )

        chunks = list(chat_model._stream([HumanMessage(content="what time is it?")]))

        call_kwargs = fake_llama.calls[0]
        assert call_kwargs["tools"]
        assert chunks[-1].message.tool_calls[0]["name"] == "get_current_datetime"
        assert chunks[-1].message.tool_calls[0]["args"] == {}

    def test_stream_normalizes_any_tool_choice_to_required(self):
        fake_llama = FakeLlama(stream_chunks=[])
        chat_model = _build_chat_gguf(fake_llama)
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice="any",
        )

        list(chat_model._stream([HumanMessage(content="what time is it?")]))

        call_kwargs = fake_llama.calls[0]
        assert chat_model.tool_choice == "any"
        assert call_kwargs["tool_choice"] == "required"

    def test_stream_parses_xml_tools_without_native_binding_in_json_mode(
        self,
    ):
        fake_llama = FakeLlama(
            stream_chunks=[
                {
                    "choices": [
                        {
                            "delta": {
                                "content": (
                                    '<tool_call>{"name": '
                                    '"get_current_datetime", '
                                    '"arguments": {}}</tool_call>'
                                )
                            }
                        }
                    ]
                }
            ]
        )
        chat_model = _build_chat_gguf(fake_llama)
        chat_model.tool_calling_mode = "json"
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice="any",
        )
        chat_model.tool_calling_mode = "json"

        chunks = list(chat_model._stream([HumanMessage(content="what time is it?")]))

        call_kwargs = fake_llama.calls[0]
        assert "tools" not in call_kwargs
        assert "tool_choice" not in call_kwargs
        assert chunks[-1].message.tool_calls[0]["name"] == (
            "get_current_datetime"
        )
        assert chunks[-1].message.tool_calls[0]["args"] == {}

    def test_stream_deduplicates_repeated_native_tool_name_deltas(self):
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
                                            "name": "get_current_datetime",
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
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice={
                "type": "function",
                "function": {"name": "get_current_datetime"},
            },
        )

        chunks = list(chat_model._stream([HumanMessage(content="what time is it?")]))

        assert chunks[-1].message.tool_calls[0]["name"] == (
            "get_current_datetime"
        )
        assert chunks[-1].message.tool_calls[0]["args"] == {}

    def test_convert_messages_keeps_empty_content_for_tool_history(self):
        fake_llama = FakeLlama()
        chat_model = _build_chat_gguf(fake_llama)
        chat_model = chat_model.bind_tools(
            [get_current_datetime],
            tool_choice={
                "type": "function",
                "function": {"name": "get_current_datetime"},
            },
        )

        assistant = AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "get_current_datetime",
                    "args": {},
                    "type": "tool_call",
                }
            ],
        )

        converted = chat_model._convert_messages(
            [HumanMessage(content="what time is it?"), assistant]
        )

        assert converted[1]["role"] == "assistant"
        assert converted[1]["content"] == ""
        assert converted[1]["tool_calls"][0]["function"]["name"] == (
            "get_current_datetime"
        )

    def test_stream_parses_gpt_oss_commentary_tool_call(self):
        fake_llama = FakeLlama(
            stream_chunks=[
                {
                    "choices": [
                        {
                            "delta": {
                                "content": (
                                    "<|channel|>analysis<|message|>Need to use "
                                    "function get_current_datetime.<|end|>"
                                    "<|start|>assistant<|channel|>commentary "
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
                                    "to=functions.get_current_datetime"
                                    "<|constrain|>json<|message|>{}"
                                    "<|call|>"
                                )
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

        chunks = list(chat_model._stream([HumanMessage(content="what time is it?")]))

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