from typing import (
    Optional,
)
from llama_index.core.tools.types import ToolMetadata

from airunner.handlers.llm.agent.chat_engine import RefreshContextChatEngine
from airunner.handlers.llm.agent.tools.chat_engine_tool import ChatEngineTool


class RAGEngineTool(ChatEngineTool):
    """RAG tool.
    
    A tool for querying data with RAG.
    """
    @classmethod
    def from_defaults(
        cls,
        chat_engine: RefreshContextChatEngine,
        name: Optional[str] = None,
        description: Optional[str] = None,
        return_direct: bool = False,
        resolve_input_errors: bool = True,
        agent=None
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
            agent=agent
        )
