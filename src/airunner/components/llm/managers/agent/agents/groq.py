from typing import Type
from llama_index.core.llms.llm import LLM
from airunner.components.llm.managers.agent.agents.base import BaseAgent


class GroqAgent(BaseAgent):
    def llm(self) -> Type[LLM]:
        pass
