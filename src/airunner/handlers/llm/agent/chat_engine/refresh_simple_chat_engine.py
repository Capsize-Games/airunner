from typing import Type

from llama_index.core.chat_engine.simple import SimpleChatEngine
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.memory import BaseMemory
from llama_index.core.llms.llm import LLM


class RefreshSimpleChatEngine(SimpleChatEngine):
    @property
    def llm(self) -> Type[LLM]:
        return self._llm

    @property
    def memory(self) -> BaseMemory:
        return self._memory

    @memory.setter
    def memory(self, memory: BaseMemory):
        self._memory = memory

    def update_system_prompt(self, system_prompt: str):
        print("self._prefix_messages", self._prefix_messages)
        self._prefix_messages.insert(0, ChatMessage(
            content=system_prompt, 
            role=self.llm.metadata.system_role
        ))

    async def achat(self, *args, **kwargs):
        pass

    async def astream_chat(self, *args, **kwargs):
        pass
