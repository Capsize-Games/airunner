from typing import Any
from llama_index.core.tools.types import ToolOutput, ToolMetadata
from llama_index.core.base.llms.types import ChatMessage, MessageRole

from airunner.enums import LLMActionType
from airunner.components.llm.managers.agent.chat_engine import ReactAgentEngine
from airunner.components.llm.managers.agent.engines.base_conversation_engine import (
    BaseConversationEngine,
)
from airunner.components.llm.managers.llm_request import LLMRequest


class ReActAgentTool(BaseConversationEngine):
    """ReAct agent tool for reasoning and acting.

    Implements the ReAct pattern, enabling multi-step reasoning and tool use for complex agent workflows.
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

        if len(args) > 0:
            tools_list = args[0] if len(args) == 1 else args

        chat_engine = ReactAgentEngine.from_tools(*args, **kwargs)
        # Patch: ensure the LLM's agent is set to the correct agent
        if (
            hasattr(chat_engine._llm, "set_agent")
            and getattr(chat_engine._llm, "_agent", None) is None
            and agent is not None
        ):
            chat_engine._llm.set_agent(agent)
            # Update the system prompt with the agent information
            if hasattr(chat_engine, "update_system_prompt"):
                chat_engine.update_system_prompt(
                    chat_engine._llm.agent.system_prompt
                )

        name = "react_agent_tool"
        description = """Useful for determining which tool to use."""
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
        print("REACT AGENT TOOL", kwargs)
        tool_choice = kwargs.get("tool_choice", None)
        llm_request = kwargs.get("llm_request", LLMRequest.from_default())
        self.agent.llm.llm_request = llm_request
        query_str = self._get_query_str(*args, **kwargs)
        chat_history = kwargs.get("chat_history", None)

        action = self.agent.action

        chat_history = (
            (self.agent.chat_memory.get() if self.agent.chat_memory else [])
            if (
                chat_history is None
                and self.agent is not None
                and hasattr(self.agent, "chat_memory")
            )
            else (chat_history or [])
        )

        # Keep a copy of kwargs so we can retry with safe defaults if formatting fails
        original_kwargs = {} if kwargs is None else dict(kwargs)
        try:
            # Forward any kwargs (e.g., username, botname) into the chat engine.
            # Remove tool_choice and messages from kwargs to avoid multiple values error
            filtered_kwargs = {
                k: v
                for k, v in (original_kwargs or {}).items()
                if k not in ["tool_choice", "messages"]
            }
            streaming_response = self.chat_engine.stream_chat(
                query_str=query_str,
                messages=chat_history,
                tool_choice=tool_choice,
                **filtered_kwargs,
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
        if not action is LLMActionType.DECISION:
            self.chat_engine.chat_history.append(
                ChatMessage(content=query_str, role=MessageRole.USER)
            )
        response = ""
        is_first_message = True
        # Stream tokens; if a KeyError occurs during formatting (e.g., missing
        # 'username'), retry once with safe defaults inserted.
        try:
            for token in streaming_response:
                # Accumulate all tokens (including empty ones)
                response += token
                # Only send non-empty tokens to GUI to avoid flickering
                if token and self.agent is not None:
                    self.agent.handle_response(token, is_first_message)
                    is_first_message = False

            # Signal that streaming is complete
            if self.agent is not None:
                self.agent.handle_response("", is_last_message=True)
        except KeyError as e:
            # Only attempt a retry for missing username/botname formatting keys.
            msg = str(e)
            if "username" in msg or "botname" in msg:
                self.logger.error(
                    f"ReAct streaming failed due to missing format key: {e}; retrying with safe defaults."
                )
                safe_kwargs = dict(original_kwargs or {})
                try:
                    safe_kwargs.setdefault(
                        "username", getattr(self.agent, "username", "") or ""
                    )
                except Exception:
                    safe_kwargs.setdefault("username", "")
                try:
                    safe_kwargs.setdefault(
                        "botname", getattr(self.agent, "botname", "") or ""
                    )
                except Exception:
                    safe_kwargs.setdefault("botname", "")

                try:
                    streaming_response = self.chat_engine.stream_chat(
                        query_str=query_str,
                        messages=chat_history,
                        tool_choice=tool_choice,
                        **{
                            k: v
                            for k, v in safe_kwargs.items()
                            if k not in ["tool_choice", "messages"]
                        },
                    )
                except Exception as e2:
                    self.logger.error(f"Retry stream_chat failed: {e2}")
                    return ToolOutput(
                        content="",
                        tool_name=self.metadata.name,
                        raw_input={"input": query_str},
                        raw_output="",
                    )

                # replay tokens from the retried generator
                response = ""
                is_first_message = True
                for token in streaming_response:
                    if not token:
                        continue
                    response += token
                    if self.agent is not None:
                        self.agent.handle_response(token, is_first_message)
                    is_first_message = False

                # Signal that streaming is complete
                if self.agent is not None:
                    self.agent.handle_response("", is_last_message=True)
            else:
                # re-raise other KeyErrors
                raise

        if not action is LLMActionType.DECISION:
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
