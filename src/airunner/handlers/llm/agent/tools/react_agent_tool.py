from typing import Any
from llama_index.core.tools.types import ToolOutput
from llama_index.core.base.llms.types import ChatMessage, MessageRole

from airunner.handlers.llm.agent.chat_engine import ReactAgentEngine
from airunner.handlers.llm.agent.tools.chat_engine_tool import ChatEngineTool

import logging


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
        logging.getLogger(__name__).info(
            f"[ReActAgentTool.from_tools] args: {args}, kwargs keys: {list(kwargs.keys())}"
        )
        if hasattr(chat_engine, "tools"):
            tool_names = [
                getattr(
                    t,
                    "name",
                    getattr(
                        getattr(t, "metadata", None),
                        "name",
                        t.__class__.__name__,
                    ),
                )
                for t in getattr(chat_engine, "tools", [])
            ]
            logging.getLogger(__name__).info(
                f"[ReActAgentTool.from_tools] Registered tool names: {tool_names}"
            )
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
        logging.getLogger(__name__).info(
            f"[ReActAgentTool.call] tool_choice: {tool_choice}, query_str: {query_str}"
        )
        if hasattr(self.chat_engine, "tools"):
            tool_names = [
                getattr(
                    t,
                    "name",
                    getattr(
                        getattr(t, "metadata", None),
                        "name",
                        t.__class__.__name__,
                    ),
                )
                for t in getattr(self.chat_engine, "tools", [])
            ]
            logging.getLogger(__name__).info(
                f"[ReActAgentTool.call] Available tool names: {tool_names}"
            )
        try:
            streaming_response = self.chat_engine.stream_chat(
                query_str,
                chat_history=chat_history if chat_history else [],
                tool_choice=tool_choice,
            )
        except Exception as e:
            logging.getLogger(__name__).error(
                f"[ReActAgentTool.call] Exception: {e}"
            )
            # Return empty ToolOutput on error
            return ToolOutput(
                content="",
                tool_name=self.metadata.name,
                raw_input={"input": query_str},
                raw_output="",
            )
        self.chat_engine.chat_history.append(
            ChatMessage(content=query_str, role=MessageRole.USER)
        )

        response = ""
        is_first_message = True
        for token in streaming_response.response_gen:
            if not token:
                continue  # Skip empty tokens
            response += token
            if self.agent is not None:
                # Pass the individual token, not the accumulated response
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
