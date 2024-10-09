from typing import Any
from llama_index.core.base.embeddings.base import BaseEmbedding
from pydantic import PrivateAttr


class CustomEmbedding(BaseEmbedding):
    _llm: Any = PrivateAttr()

    def __init__(self, llm, **data: Any):
        super().__init__(**data)
        self._llm = llm  # Initialize the LLM as a private attribute

    def _get_text_embedding(self, text):
        # Generate embedding using the preloaded LLM
        response = self._llm.generate(text)
        return response['embedding']

    def _get_query_embedding(self, query):
        # Generate query embedding using the preloaded LLM
        response = self._llm.generate(query)
        return response['embedding']

    async def _aget_query_embedding(self, query):
        # Asynchronously generate query embedding
        response = await self._llm.agenerate(query)
        return response['embedding']

