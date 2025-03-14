from llama_index.core.agent import ReActAgent
from llama_index.core.memory import BaseMemory


class ReactAgentEngine(ReActAgent):
    @property
    def memory(self) -> BaseMemory:
        return self._memory

    @memory.setter
    def memory(self, memory: BaseMemory):
        self._memory = memory
