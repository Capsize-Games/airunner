from abc import ABC

from llama_index.core.agent import ReActAgent
from llama_index.core.memory import BaseMemory


class ReactAgentEngine(ReActAgent, ABC):
    @property
    def memory(self) -> BaseMemory:
        return self._memory

    @memory.setter
    def memory(self, memory: BaseMemory):
        self._memory = memory
