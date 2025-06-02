from typing import Any
from llama_index.core.tools.types import ToolOutput, ToolMetadata
from llama_index.core.base.llms.types import ChatMessage, MessageRole

from airunner.handlers.llm.agent.chat_engine import ReactAgentEngine
from airunner.handlers.llm.agent.engines.base_conversation_engine import (
    BaseConversationEngine,
)

import logging


class ReActAgentTool(BaseConversationEngine):
    """ReActAgentTool.

    A tool for determining which actions to take.
    """

    def __init__(
        self,
        chat_engine,
        metadata: ToolMetadata = None,
        resolve_input_errors: bool = True,
        agent=None,
        do_handle_response: bool = True,
        *args,
        **kwargs,
    ):
        super().__init__(agent)
        self.chat_engine = chat_engine
        self._metadata = metadata
        self._resolve_input_errors = resolve_input_errors
        self.agent = agent
        self.do_handle_response = do_handle_response
        self._logger = kwargs.pop("logger", None)
        if self._logger is None:
            from airunner.utils.application.get_logger import get_logger
            from airunner.settings import AIRUNNER_LOG_LEVEL

            self._logger = get_logger(
                self.__class__.__name__, AIRUNNER_LOG_LEVEL
            )

    @property
    def logger(self):
        return self._logger

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    @classmethod
    def from_defaults(
        cls,
        chat_engine,
        name: str = None,
        description: str = None,
        return_direct: bool = False,
        resolve_input_errors: bool = True,
        agent=None,
        do_handle_response: bool = True,
    ):
        name = name or "react_agent_tool"
        description = (
            description or """Useful for determining which tool to use."""
        )
        metadata = ToolMetadata(
            name=name, description=description, return_direct=return_direct
        )
        return cls(
            chat_engine=chat_engine,
            metadata=metadata,
            resolve_input_errors=resolve_input_errors,
            agent=agent,
            do_handle_response=do_handle_response,
        )

    @classmethod
    def from_tools(cls, *args, **kwargs) -> "ReActAgentTool":
        agent = kwargs.pop("agent", None)
        return_direct = kwargs.pop("return_direct", False)
        do_handle_response = kwargs.pop(
            "do_handle_response", False
        )  # Default to False for orchestrator
        chat_engine = ReactAgentEngine.from_tools(*args, **kwargs)
        name = "react_agent_tool"
        description = """Useful for determining which tool to use."""
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
        return cls.from_defaults(
            chat_engine=chat_engine,
            name=name,
            description=description,
            return_direct=return_direct,
            agent=agent,
            do_handle_response=do_handle_response,
        )

    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)

    def call(self, *args: Any, **kwargs: Any) -> ToolOutput:
        query_str = self._get_query_str(*args, **kwargs)
        chat_history = kwargs.get("chat_history", None)
        if (
            chat_history is None
            and self.agent is not None
            and hasattr(self.agent, "chat_memory")
        ):
            chat_history = (
                self.agent.chat_memory.get() if self.agent.chat_memory else []
            )
        if chat_history is None:
            chat_history = []
        tool_choice = kwargs.get("tool_choice", None)
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
        try:
            streaming_response = self.chat_engine.stream_chat(
                query_str,
                chat_history=chat_history if chat_history else [],
                tool_choice=tool_choice,
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"[ReActAgentTool.call] Exception: {e}"
            )
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
                continue
            response += token
            if self.agent is not None and self.do_handle_response:
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

    def _get_query_str(self, *args: Any, **kwargs: Any) -> str:
        """Extract query string from arguments - same pattern as ChatEngineTool."""
        if args is not None and len(args) > 0:
            query_str = str(args[0])
        elif kwargs is not None and "input" in kwargs:
            # NOTE: this assumes our default function schema of `input`
            query_str = kwargs["input"]
        elif kwargs is not None and self._resolve_input_errors:
            query_str = str(kwargs)
        else:
            raise ValueError(
                "Cannot call ReActAgentTool without specifying `input` parameter."
            )
        return query_str
