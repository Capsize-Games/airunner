from typing import (
    Any,
    Optional,
    Union,
)
from airunner.handlers.llm.agent.chat_engine.refresh_context_chat_engine import (
    RefreshContextChatEngine
)
from airunner.handlers.llm.agent.chat_engine.refresh_simple_chat_engine import (
    RefreshSimpleChatEngine
)
from llama_index.core.tools.types import AsyncBaseTool, ToolMetadata, ToolOutput
from llama_index.core.langchain_helpers.agents.tools import IndexToolConfig, LlamaIndexTool
from llama_index.core.base.llms.types import ChatMessage, MessageRole


class ChatEngineTool(AsyncBaseTool):
    """Chat tool.
    
    A tool for chatting with the LLM.
    """
    
    def __init__(
        self,
        chat_engine: Union[RefreshSimpleChatEngine, RefreshContextChatEngine],
        metadata: ToolMetadata,
        resolve_input_errors: bool = True,
        agent=None
    ):
        self.chat_engine: Union[
            RefreshSimpleChatEngine, 
            RefreshContextChatEngine
        ] = chat_engine
        if not chat_engine:
            raise ValueError("Chat engine must be provided.")
        self._metadata = metadata
        self._resolve_input_errors = resolve_input_errors
        self.agent = agent

    @classmethod
    def from_defaults(
        cls,
        chat_engine: Union[RefreshSimpleChatEngine, RefreshContextChatEngine],
        name: Optional[str] = None,
        description: Optional[str] = None,
        return_direct: bool = False,
        resolve_input_errors: bool = True,
        agent = None
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
            agent=agent
        )
    
    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata
    
    def call(self, *args: Any, **kwargs: Any) -> ToolOutput:
        query_str = self._get_query_str(*args, **kwargs)
        do_not_display = kwargs.get("do_not_display", False)
        chat_history = kwargs.get("chat_history", [])
        streaming_response = self.chat_engine.stream_chat(
            query_str, 
            chat_history=chat_history
        )

        response = ""
        is_first_message = True
        for token in streaming_response.response_gen:
            response += token
            if response != "Empty Response":
                self.agent.handle_response(
                    token, 
                    is_first_message, 
                    do_not_display=do_not_display
                )
            is_first_message = False

        return ToolOutput(
            content=str(response),
            tool_name=self.metadata.name,
            raw_input={"input": query_str},
            raw_output=response,
        )

    async def acall(self, *args: Any, **kwargs: Any) -> ToolOutput:
        query_str = self._get_query_str(*args, **kwargs)
        chat_history = kwargs.get("chat_history", None)
        streaming_response = await self.chat_engine.astream_chat(
            query_str,
            chat_history=chat_history
        )

        response = ""
        is_first_message = True
        for token in streaming_response.response_gen:
            response += token
            self.agent.handle_response(token, is_first_message)
            is_first_message = False

        return ToolOutput(
            content=str(response),
            tool_name=self.metadata.name,
            raw_input={"input": query_str},
            raw_output=response,
        )

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

    def update_system_prompt(self, system_prompt:str):
        self.chat_engine.update_system_prompt(system_prompt)