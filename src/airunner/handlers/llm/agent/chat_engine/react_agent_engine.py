from abc import ABC

from llama_index.core.agent import ReActAgent
from llama_index.core.memory import BaseMemory

ReActAgentMeta = type(ReActAgent)


class ReactAgentEngine(
    ReActAgent, 
    ABC, 
    metaclass=ReActAgentMeta
):
    @property
    def memory(self) -> BaseMemory:
        return self._memory

    @memory.setter
    def memory(self, memory: BaseMemory):
        self._memory = memory