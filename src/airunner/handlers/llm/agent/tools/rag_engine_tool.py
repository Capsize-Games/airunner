from typing import (
    Optional,
)
from llama_index.core.tools.types import ToolMetadata

from airunner.handlers.llm.agent.chat_engine import RefreshContextChatEngine
from airunner.handlers.llm.agent.tools.chat_engine_tool import ChatEngineTool
from airunner.handlers.llm.agent.engines.base_conversation_engine import (
    BaseConversationEngine,
)


class RAGEngineTool(BaseConversationEngine):
    """RAG tool.

    A tool for querying data with RAG.
    """

    def __init__(
        self,
        chat_engine,
        metadata: ToolMetadata,
        resolve_input_errors: bool = True,
        agent=None,
        *args,
        **kwargs
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
