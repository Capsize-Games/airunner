from typing import (
    Optional,
)
from llama_index.core.tools.types import ToolMetadata

from airunner.components.llm.managers.agent.chat_engine import (
    RefreshContextChatEngine,
)
from airunner.components.llm.managers.agent.engines.base_conversation_engine import (
    BaseConversationEngine,
)
from llama_index.core.tools.types import (
    AsyncBaseTool,
    ToolMetadata,
    ToolOutput,
)
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.utils.application.mediator_mixin import MediatorMixin


class RAGEngineTool(
    BaseConversationEngine, AsyncBaseTool, SettingsMixin, MediatorMixin
):
    """Retrieval-Augmented Generation (RAG) tool.

    Fetches relevant documents from a vector database or corpus and synthesizes an answer using the LLM.
    """

    def __init__(
        self,
        chat_engine,
        metadata: ToolMetadata,
        resolve_input_errors: bool = True,
        agent=None,
        *args,
        **kwargs,
    ):
        super().__init__(agent)
        self.chat_engine = chat_engine
        self._metadata = metadata
        self._resolve_input_errors = resolve_input_errors
        self.agent = agent
        self._logger = kwargs.pop("logger", None)
        if self._logger is None:
            from airunner.utils.application.get_logger import get_logger
            from airunner.settings import AIRUNNER_LOG_LEVEL

            self._logger = get_logger(
                self.__class__.__name__, AIRUNNER_LOG_LEVEL
            )

    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)

    def update_system_prompt(self, system_prompt: str):
        if system_prompt is not None and hasattr(
            self.chat_engine, "update_system_prompt"
        ):
            self.chat_engine.update_system_prompt(system_prompt)

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    def call(self, *args, **kwargs):
        """Main entry point for RAGEngineTool. Streams a RAG answer using the chat engine."""
        # Accept both 'input' (ReAct standard) and 'query' (legacy)
        query_str = (
            kwargs.get("input")
            or kwargs.get("query")
            or (args[0] if args else None)
        )

        if not query_str:
            raise ValueError("No query provided for RAGEngineTool.call().")

        llm_request = kwargs.get("llm_request", None)
        system_prompt = kwargs.get("system_prompt", None)
        self.update_system_prompt(system_prompt)
        if llm_request is not None and hasattr(
            self.chat_engine.llm, "llm_request"
        ):
            self.chat_engine.llm.llm_request = llm_request

        # Don't pass tool-specific kwargs to chat engine
        clean_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k
            not in [
                "input",
                "query",
                "llm_request",
                "system_prompt",
                "tool_choice",
                "messages",
            ]
        }

        # Provide a generator that streams tokens progressively
        def _stream():
            # Try streaming first
            try:
                streaming = self.chat_engine.stream_chat(
                    query_str, **clean_kwargs
                )
                # LlamaIndex streaming responses often expose response_gen
                if hasattr(streaming, "response_gen"):
                    for token in streaming.response_gen:
                        if token is None:
                            continue
                        yield token
                    return
                # If streaming is directly iterable
                try:
                    for token in streaming:
                        if token is None:
                            continue
                        yield token
                    return
                except TypeError:
                    pass
            except Exception:
                pass

            # Fallback: non-streaming
            response = self.chat_engine.chat(query_str, **clean_kwargs)
            content = str(getattr(response, "response", response))
            yield content

        return _stream()

    async def acall(self, *args, **kwargs):
        pass

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
        chat_engine: RefreshContextChatEngine,
        name: Optional[str] = None,
        description: Optional[str] = None,
        return_direct: bool = False,
        resolve_input_errors: bool = True,
        agent=None,
    ) -> "RAGEngineTool":
        name = name or "rag_engine_tool"
        description = description or """Useful for querying data with RAG."""
        metadata = ToolMetadata(
            name=name, description=description, return_direct=return_direct
        )
        return cls(
            chat_engine=chat_engine,
            metadata=metadata,
            resolve_input_errors=resolve_input_errors,
            agent=agent,
        )
