from typing import Type
from airunner.handlers.llm.agent.agents.base import BaseAgent
from airunner.handlers.llm.agent.actions.agent_action_message import (
    AgentActionMessage,
)


class AgentAction:
    @staticmethod
    def run(
        llm: Type[BaseAgent], message: AgentActionMessage
    ) -> AgentActionMessage:
        raise NotImplementedError("Implement the run method in subclasses")
