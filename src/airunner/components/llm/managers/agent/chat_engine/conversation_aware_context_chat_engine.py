"""
Conversation-Aware Context Chat Engine for RAG

This engine extends ContextChatEngine to make RAG retrieval aware of
conversation history by augmenting queries before retrieval.
"""

import logging
from typing import Optional, Sequence, List
from llama_index.core.chat_engine import ContextChatEngine
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.memory import BaseMemory
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.llms import LLM
from llama_index.core.indices.query.schema import QueryBundle
from llama_index.core.schema import NodeWithScore

logger = logging.getLogger(__name__)


class ConversationAwareContextChatEngine(ContextChatEngine):
    """
    A context-aware RAG chat engine that augments queries with conversation
    history before document retrieval.
    """

    def __init__(
        self,
        retriever: BaseRetriever,
        llm: LLM,
        memory: Optional[BaseMemory] = None,
        prefix_messages: Optional[Sequence[ChatMessage]] = None,
        context_window_turns: int = 3,
        **kwargs,
    ):
        """
        Initialize the conversation-aware context chat engine.

        Args:
            retriever: The vector index retriever
            llm: The language model
            memory: Optional memory buffer for chat history
            prefix_messages: Optional prefix messages (system prompt, etc.)
            context_window_turns: Number of recent conversation turns to include
        """
        super().__init__(
            retriever=retriever,
            llm=llm,
            memory=memory,
            prefix_messages=prefix_messages,
            **kwargs,
        )
        self._context_window_turns = context_window_turns
        logger.info(
            f"ConversationAwareContextChatEngine initialized "
            f"(context_window_turns={context_window_turns})"
        )

    @property
    def llm(self):
        return self._llm

    @property
    def memory(self) -> BaseMemory:
        return self._memory

    @memory.setter
    def memory(self, memory: BaseMemory):
        self._memory = memory

    def update_system_prompt(self, system_prompt: str):
        """Update the system prompt."""
        message = ChatMessage(content=system_prompt, role=MessageRole.SYSTEM)
        if len(self._prefix_messages) == 0:
            self._prefix_messages = [message]
        else:
            self._prefix_messages[0] = message

    def _get_conversation_context(self, current_message: str) -> str:
        """
        Extract conversation context intelligently for query augmentation.

        Only augments queries that are ambiguous (contain pronouns/references
        without clear subjects). For explicit queries, returns empty string
        to avoid biasing retrieval toward previous topics.
        """
        if not self._memory:
            return ""

        # Check if query needs augmentation (contains ambiguous references)
        needs_augmentation = self._is_ambiguous_query(current_message)
        if not needs_augmentation:
            logger.debug(
                f"Query is explicit, no augmentation needed: {current_message}"
            )
            return ""

        try:
            all_messages = self._memory.get_all()
            if not all_messages:
                return ""

            # Take last N turns
            num_messages = self._context_window_turns * 2
            recent_messages = (
                all_messages[-num_messages:]
                if len(all_messages) > num_messages
                else all_messages
            )

            # Extract key topics/entities from recent conversation
            topics = self._extract_topics(recent_messages)

            if topics:
                # Return a minimal context with just the key topics
                context = f"Related to: {', '.join(topics)}. "
                logger.debug(
                    f"Augmenting ambiguous query with topics: {topics}"
                )
                return context
            return ""

        except Exception as e:
            logger.warning(f"Failed to extract conversation context: {e}")
            return ""

    def _is_ambiguous_query(self, message: str) -> bool:
        """
        Check if a query contains ambiguous references that need context.

        Returns True for queries with pronouns or references like:
        - "it", "that", "this", "those"
        - "who wrote it?"
        - "the other one"
        - "summarize it"
        """
        import re

        message_lower = message.lower()

        # Ambiguous pronouns and references
        ambiguous_patterns = [
            r"\bit\b",  # "it"
            r"\bthat\b",  # "that"
            r"\bthis\b",  # "this"
            r"\bthose\b",  # "those"
            r"\bthese\b",  # "these"
            r"\bone\b",  # "one" (as in "the other one")
            r"\bother\b",  # "other"
            r"\bprevious\b",  # "previous"
            r"\bearlier\b",  # "earlier"
            r"\babove\b",  # "above"
        ]

        for pattern in ambiguous_patterns:
            if re.search(pattern, message_lower):
                return True

        return False

    def _extract_topics(self, messages: List[ChatMessage]) -> List[str]:
        """
        Extract key topics/entities from recent messages.

        Returns a list of important terms (proper nouns, titles, etc.)
        mentioned in the conversation.
        """
        import re

        topics = set()

        for msg in messages:
            role = getattr(msg, "role", "unknown")
            content = ""

            if hasattr(msg, "content"):
                content = msg.content
            elif hasattr(msg, "blocks") and msg.blocks:
                content = " ".join(
                    (
                        block.get("text", "")
                        if isinstance(block, dict)
                        else getattr(block, "text", "")
                    )
                    for block in msg.blocks
                )

            if content and role in (MessageRole.USER, MessageRole.ASSISTANT):
                # Extract potential titles (quoted text)
                quoted = re.findall(r'"([^"]+)"', content)
                for title in quoted:
                    # Only add if longer than 3 chars
                    if len(title) > 3:
                        topics.add(title)

                # Extract capitalized multi-word phrases (e.g., "MindWar", "Color of Magic")
                capitalized_phrases = re.findall(
                    r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", content
                )
                for phrase in capitalized_phrases:
                    if len(phrase) > 3 and phrase.lower() not in [
                        "user",
                        "assistant",
                        "the",
                        "this",
                        "that",
                    ]:
                        topics.add(phrase)

        # Return most recent topics (max 2 to keep query focused)
        return list(topics)[-2:]

    def _get_nodes(self, message: str) -> List[NodeWithScore]:
        """
        Override ContextChatEngine's _get_nodes to use conversation-aware retrieval.
        """
        # Get conversation context (only if query is ambiguous)
        conversation_context = self._get_conversation_context(message)

        # Augment query only if context was provided
        augmented_query = (
            f"{conversation_context}{message}"
            if conversation_context
            else message
        )

        if conversation_context:
            logger.debug(f"Original query: {message}")
            logger.debug(f"Augmented with: {conversation_context}")
        else:
            logger.debug(f"Query used as-is (no augmentation): {message}")

        # Retrieve with query (augmented or original)
        nodes = self._retriever.retrieve(augmented_query)

        # Apply postprocessors
        for postprocessor in self._node_postprocessors:
            nodes = postprocessor.postprocess_nodes(
                nodes, query_bundle=QueryBundle(message)
            )

        logger.info(f"Retrieved {len(nodes)} nodes for query: {message}")

        return nodes

    async def _aget_nodes(self, message: str) -> List[NodeWithScore]:
        """
        Override ContextChatEngine's _aget_nodes for async conversation-aware retrieval.
        """
        # Get conversation context (only if query is ambiguous)
        conversation_context = self._get_conversation_context(message)

        # Augment query only if context was provided
        augmented_query = (
            f"{conversation_context}{message}"
            if conversation_context
            else message
        )

        if conversation_context:
            logger.debug(f"Original query: {message}")
            logger.debug(f"Augmented with: {conversation_context}")
        else:
            logger.debug(f"Query used as-is (no augmentation): {message}")

        # Retrieve with query (augmented or original)
        nodes = await self._retriever.aretrieve(augmented_query)

        # Apply postprocessors
        for postprocessor in self._node_postprocessors:
            nodes = postprocessor.postprocess_nodes(
                nodes, query_bundle=QueryBundle(message)
            )

        logger.info(f"Retrieved {len(nodes)} nodes for query: {message}")

        return nodes
