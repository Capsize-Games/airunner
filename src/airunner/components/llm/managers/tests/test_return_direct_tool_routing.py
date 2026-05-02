from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from airunner.components.llm.managers.mixins.node_functions_mixin import (
    NodeFunctionsMixin,
)
from airunner.enums import SignalCode


class DummyNodeFunctionsMixin(NodeFunctionsMixin):
    def __init__(self):
        self.logger = Mock()
        self._tools = []
        self._token_callback = None
        self._interrupted = False


def _make_tool(name: str, return_direct: bool):
    tool = Mock()
    tool.name = name
    tool.return_direct = return_direct
    return tool


class TestReturnDirectToolRouting:
    def test_route_after_tools_uses_force_response_for_return_direct_tool(self):
        mixin = DummyNodeFunctionsMixin()
        mixin._tools = [_make_tool("get_current_datetime", True)]
        state = {
            "messages": [
                HumanMessage(content="what time is it?"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "tool-call-1",
                            "name": "get_current_datetime",
                            "args": {},
                        }
                    ],
                ),
                ToolMessage(
                    content="Current local date and time: 2026-03-21 22:14:54.",
                    tool_call_id="tool-call-1",
                    name="get_current_datetime",
                ),
            ]
        }

        route = mixin._route_after_tools(state)

        assert route == "force_response"

    def test_force_response_node_returns_tool_content_directly(self):
        mixin = DummyNodeFunctionsMixin()
        mixin._tools = [_make_tool("get_current_datetime", True)]
        state = {
            "messages": [
                HumanMessage(content="what time is it?"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "tool-call-1",
                            "name": "get_current_datetime",
                            "args": {},
                        }
                    ],
                ),
                ToolMessage(
                    content="Current local date and time: 2026-03-21 22:14:54.",
                    tool_call_id="tool-call-1",
                    name="get_current_datetime",
                ),
            ]
        }

        result = mixin._force_response_node(state)

        assert result["workflow_continuation"] is False
        message = result["messages"][0]
        assert isinstance(message, AIMessage)
        assert message.content == "Current local date and time: 2026-03-21 22:14:54."
        assert message.tool_calls == []

    def test_streaming_reasoning_completion_keeps_request_id(
        self,
        monkeypatch,
    ):
        monkeypatch.delenv("AIRUNNER_HEADLESS", raising=False)
        emitted = []
        mixin = DummyNodeFunctionsMixin()
        mixin._current_request_id = "req-2"
        mixin._signal_emitter = SimpleNamespace(
            emit_signal=lambda code, data: emitted.append((code, data))
        )
        mixin._create_streamed_message = Mock(
            return_value=AIMessage(content="")
        )
        mixin._chat_model = SimpleNamespace(
            stream=lambda *_args, **_kwargs: iter(
                [
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="",
                            additional_kwargs={
                                "reasoning_content": "plan"
                            },
                            tool_calls=[],
                        )
                    )
                ]
            )
        )

        mixin._generate_streaming_response("prompt", {})

        thinking_updates = [
            data
            for code, data in emitted
            if code == SignalCode.LLM_THINKING_SIGNAL
        ]
        assert thinking_updates == [
            {
                "status": "started",
                "content": "",
                "request_id": "req-2",
            },
            {
                "status": "streaming",
                "content": "plan",
                "request_id": "req-2",
            },
            {
                "status": "completed",
                "content": "plan",
                "request_id": "req-2",
            },
        ]