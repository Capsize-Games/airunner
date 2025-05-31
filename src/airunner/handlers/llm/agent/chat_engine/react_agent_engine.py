from abc import ABC

from llama_index.core.agent import ReActAgent
from llama_index.core.memory import BaseMemory
from llama_index.core.agent.react.formatter import ReActChatFormatter

ReActAgentMeta = type(ReActAgent)


class ReactAgentEngine(ReActAgent, ABC, metaclass=ReActAgentMeta):
    @classmethod
    def from_tools(cls, *args, formatter=None, **kwargs):
        """Create a ReactAgentEngine with the correct formatter (from_defaults)."""
        if formatter is None:
            formatter = ReActChatFormatter.from_defaults()
        return super().from_tools(*args, formatter=formatter, **kwargs)

    @property
    def memory(self) -> BaseMemory:
        return self._memory

    @memory.setter
    def memory(self, memory: BaseMemory):
        self._memory = memory
