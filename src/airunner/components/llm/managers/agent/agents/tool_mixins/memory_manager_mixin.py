from airunner.settings import AIRUNNER_LLM_CHAT_STORE
from airunner.components.llm.managers.storage.chat_store import DatabaseChatStore
from llama_index.core.storage.chat_store import SimpleChatStore
from airunner.components.llm.managers.agent.memory import ChatMemoryBuffer


class MemoryManagerMixin:
    """
    Mixin for managing chat memory and chat store logic.
    """

    def __init__(self):
        self._chat_memory = None
        self._chat_store = None

    @property
    def chat_store(self):
        if not hasattr(self, "_chat_store") or self._chat_store is None:
            if AIRUNNER_LLM_CHAT_STORE == "db" and self.use_memory:
                self._chat_store = DatabaseChatStore()
            else:
                self._chat_store = SimpleChatStore()
        return self._chat_store

    @chat_store.setter
    def chat_store(self, value):
        self._chat_store = value

    @property
    def chat_memory(self):
        if not hasattr(self, "_chat_memory") or self._chat_memory is None:
            self.logger.info("Loading ChatMemoryBuffer")
            self._chat_memory = ChatMemoryBuffer.from_defaults(
                token_limit=3000,
                chat_store=self.chat_store,
                chat_store_key=str(self.conversation_id),
            )
        return self._chat_memory

    @chat_memory.setter
    def chat_memory(self, value):
        self._chat_memory = value

    def reset_memory(self):
        self.chat_memory = None
        self.chat_store = None
        # Defensive: check for None before using
        if self.chat_store is not None:
            messages = self.chat_store.get_messages(
                key=str(self.conversation_id)
            )
        else:
            messages = []
        if self.chat_memory is not None:
            self.chat_memory.set(messages)
        # Only set memory if chat_engine is initialized
        if self.chat_engine is not None:
            self.chat_engine.memory = self.chat_memory
        else:
            self.logger.warning(
                "reset_memory: chat_engine is None, cannot set memory."
            )
        if (
            hasattr(self, "react_tool_agent")
            and self.react_tool_agent is not None
        ):
            self.react_tool_agent.memory = self.chat_memory
        self.reload_rag_engine()

    def _update_memory(self, action: str) -> None:
        """
        Update the memory for the given action and ensure all chat engines share the same memory instance.
        Args:
            action (str): The action type to update memory for.
        """
        # Use a custom memory strategy if provided
        if hasattr(self, "_memory_strategy") and self._memory_strategy:
            self._memory = self._memory_strategy(action, self)
        elif action in ("CHAT", "APPLICATION_COMMAND"):
            self.chat_memory.chat_store_key = str(self.conversation_id)
            self._memory = self.chat_memory
        elif action == "PERFORM_RAG_SEARCH":
            if hasattr(self, "rag_engine") and self.rag_engine is not None:
                self._memory = self.rag_engine.memory
            else:
                self._memory = None
        else:
            self._memory = None

        # Ensure all chat engines share the same memory instance for consistency
        for engine_attr in [
            "_chat_engine",
            "_mood_engine",
            "_summary_engine",
            "_information_scraper_engine",
        ]:
            engine = getattr(self, engine_attr, None)
            if engine is not None:
                engine.memory = self._memory
