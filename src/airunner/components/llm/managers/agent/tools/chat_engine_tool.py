from typing import (
    Any,
    Optional,
    Union,
)
import jinja2

from llama_index.core.tools.types import (
    AsyncBaseTool,
    ToolMetadata,
    ToolOutput,
)
from llama_index.core.langchain_helpers.agents.tools import (
    IndexToolConfig,
    LlamaIndexTool,
)

from airunner.components.llm.managers.agent.chat_engine import ReactAgentEngine
from airunner.components.llm.managers.agent.chat_engine import (
    RefreshContextChatEngine,
    RefreshSimpleChatEngine,
)
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.application.gui.windows.main.settings_mixin import SettingsMixin
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.llm.managers.agent.engines.base_conversation_engine import (
    BaseConversationEngine,
)


class ChatEngineTool(
    BaseConversationEngine, AsyncBaseTool, SettingsMixin, MediatorMixin
):
    """Conversational agent tool using the chat engine.

    Provides context-aware Q&A and conversation capabilities for LLM agents, leveraging chat history and memory.
    """

    def __init__(
        self,
        chat_engine: Union[
            RefreshSimpleChatEngine, RefreshContextChatEngine, ReactAgentEngine
        ],
        metadata: ToolMetadata,
        resolve_input_errors: bool = True,
        agent=None,
        do_handle_response: bool = True,
        *args: Any,
        **kwargs: Any,
    ):
        self.chat_engine = chat_engine
        self._metadata = metadata
        self._resolve_input_errors = resolve_input_errors
        self.agent = agent
        self.do_handle_response: bool = do_handle_response
        self._do_interrupt: bool = False
        self._logger = kwargs.pop("logger", None)
        if self._logger is None:
            from airunner.utils.application.get_logger import get_logger
            from airunner.settings import AIRUNNER_LOG_LEVEL

            self._logger = get_logger(
                self.__class__.__name__, AIRUNNER_LOG_LEVEL
            )
        super().__init__(agent)

    @property
    def logger(self):
        """
        Get the logger instance for this tool.
        Returns:
            Logger: The logger instance.
        """
        return self._logger

    @classmethod
    def from_defaults(
        cls,
        chat_engine: Union[
            RefreshSimpleChatEngine, RefreshContextChatEngine, ReactAgentEngine
        ],
        name: Optional[str] = None,
        description: Optional[str] = None,
        return_direct: bool = False,
        resolve_input_errors: bool = True,
        agent=None,
        do_handle_response: bool = True,
    ) -> "ChatEngineTool":
        name = name or "chat_engine_tool"
        description = description or """Useful for chatting with the LLM."""

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

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    def call(
        self, *args: Any, tool_call: bool = False, **kwargs: Any
    ) -> ToolOutput:
        system_prompt = kwargs.get("system_prompt", None)
        if system_prompt is not None:
            self.chat_engine.update_system_prompt(system_prompt)
        query_str = self._get_query_str(*args, **kwargs)
        llm_request = kwargs.get("llm_request", LLMRequest.from_default())
        if hasattr(self.chat_engine.llm, "llm_request"):
            self.chat_engine.llm.llm_request = llm_request

        response = ""

        if not self._do_interrupt:
            do_not_display = kwargs.get("do_not_display", False)
            chat_history = kwargs.get("chat_history", [])
            try:
                streaming_response = self.chat_engine.stream_chat(
                    query_str, **kwargs
                )
            except jinja2.exceptions.TemplateError as e:
                self.logger.error(
                    f"Error in template rendering. Please check your template. {e}"
                )
                response = (
                    "Error in template rendering. Please check your template."
                )
                self._do_interrupt = False
                return ToolOutput(
                    content=str(response),
                    tool_name=self.metadata.name,
                    raw_input={"input": query_str},
                    raw_output=response,
                )

            is_first_message = True
            for token in streaming_response:
                if self._do_interrupt:
                    break
                if not token:
                    continue
                response += token
                if response != "Empty Response" and self.do_handle_response:
                    self.agent.handle_response(
                        token,
                        is_first_message,
                        do_not_display=do_not_display,
                        do_tts_reply=llm_request.do_tts_reply,
                    )
                is_first_message = False

        self._do_interrupt = False

        return ToolOutput(
            content=str(response),
            tool_name=self.metadata.name,
            raw_input={"input": query_str},
            raw_output=response,
        )

    async def acall(self, *args, **kwargs):
        pass

    def as_langchain_tool(self) -> "LlamaIndexTool":
        tool_config = IndexToolConfig(
            chat_engine=self.chat_engine,
            name=self.metadata.name,
            description=self.metadata.description,
        )
        return LlamaIndexTool.from_tool_config(tool_config=tool_config)

    def _get_query_str(self, *args: Any, **kwargs: Any) -> str:
        if args is not None and len(args) > 0:
            query_str = str(args[0])
        elif kwargs is not None and "input" in kwargs:
            # NOTE: this assumes our default function schema of `input`
            query_str = kwargs["input"]
        elif kwargs is not None and self._resolve_input_errors:
            query_str = str(kwargs)
        else:
            raise ValueError(
                "Cannot call query engine without specifying `input` parameter."
            )
        return query_str

    def update_system_prompt(self, system_prompt: str):
        self.chat_engine.update_system_prompt(system_prompt)
