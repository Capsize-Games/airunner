from unittest.mock import patch

from langchain_core.messages import HumanMessage, SystemMessage

from airunner.components.llm.adapters.chat_gguf import ChatGGUF
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


def _build_chat_gguf(fake_llama):
    def fake_load_model(self):
        self._llama = fake_llama

    with patch.object(ChatGGUF, "_load_model", fake_load_model):
        return ChatGGUF(model_path="/tmp/fake.gguf")


class TestChatGGUFNativeTools:
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