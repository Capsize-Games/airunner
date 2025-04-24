from typing import List, Type
from airunner.handlers.llm.agent.actions.agent_action import AgentAction
from airunner.handlers.llm.agent.actions.agent_action_message import (
    AgentActionMessage,
)
from airunner.utils.application.get_logger import get_logger


class WorkFlow:
    @staticmethod
    def run(
        name: str,
        description: str,
        message: AgentActionMessage,
        steps: List[Type[AgentAction]],
    ):
        logger = get_logger(__name__)
        logger.info(f"Running workflow: {name}")
        logger.info(f"Description: {description}")
        current_message = message
        for current_step in steps:
            logger.info(f"Running step: {current_step.__name__}")
            current_message = current_step.run(current_message)
