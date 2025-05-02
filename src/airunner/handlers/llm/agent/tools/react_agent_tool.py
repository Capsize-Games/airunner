from typing import Any
from llama_index.core.tools.types import ToolOutput
from llama_index.core.base.llms.types import ChatMessage, MessageRole

from airunner.handlers.llm.agent.chat_engine import ReactAgentEngine
from airunner.handlers.llm.agent.tools.chat_engine_tool import ChatEngineTool


class ReActAgentTool(ChatEngineTool):
    """ReActAgentTool.

    A tool for determining which actions to take.
    """

    @classmethod
    def from_tools(cls, *args, **kwargs) -> "ReActAgentTool":
        agent = kwargs.pop("agent", None)
        return_direct = kwargs.pop("return_direct", False)
        chat_engine = ReactAgentEngine.from_tools(*args, **kwargs)
        name = "react_agent_tool"
        description = """Useful for determining which tool to use."""
        return cls.from_defaults(
            chat_engine=chat_engine,
            name=name,
            description=description,
            return_direct=return_direct,
            agent=agent,
        )

    def call(self, *args: Any, **kwargs: Any) -> ToolOutput:
        query_str = self._get_query_str(*args, **kwargs)
        chat_history = kwargs.get("chat_history", None)
        tool_choice = kwargs.get("tool_choice", None)
        streaming_response = self.chat_engine.stream_chat(
            query_str,
            chat_history=chat_history if chat_history else [],
            tool_choice=tool_choice,
        )
        self.chat_engine.chat_history.append(
            ChatMessage(content=query_str, role=MessageRole.USER)
        )

        response = ""
        is_first_message = True
        for token in streaming_response.response_gen:
            response += token
            self.agent.handle_response(
                token,
                is_first_message,
            )
            is_first_message = False

        self.chat_engine.chat_history.append(
            ChatMessage(content=response, role=MessageRole.ASSISTANT)
        )

        return ToolOutput(
            content=str(response),
            tool_name=self.metadata.name,
            raw_input={"input": query_str},
            raw_output=response,
        )
