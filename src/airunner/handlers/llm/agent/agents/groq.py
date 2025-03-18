from typing import Type
from llama_index.core.llms.llm import LLM
from airunner.handlers.llm.agent.agents.base import BaseAgent


class GroqAgent(BaseAgent):
    def llm(self) -> Type[LLM]:
        pass

