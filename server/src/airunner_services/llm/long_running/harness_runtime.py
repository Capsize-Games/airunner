"""Runtime wiring helpers for the long-running harness facade."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.llm.long_running.project_manager import ProjectManager
from airunner_services.llm.long_running.runtime_components import (
    build_runtime_components,
    build_session_agent,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def initialize_runtime(
    agent: Any,
    project_manager: Optional[ProjectManager],
    sub_agents: Optional[dict[str, Any]],
) -> None:
    """Initialize the harness runtime components."""
    runtime = build_runtime_components(
        agent._chat_model,
        tools=agent._tools,
        project_manager=project_manager,
        sub_agents=sub_agents,
    )
    agent._project_manager, agent._sub_agents = (
        runtime.project_manager,
        runtime.sub_agents,
    )
    agent._initializer, agent._session_agent = (
        runtime.initializer,
        runtime.session_agent,
    )


def register_sub_agent(agent: Any, category: str, sub_agent: Any) -> None:
    """Register one specialized sub-agent and rebuild the session agent."""
    agent._sub_agents[category] = sub_agent
    agent._session_agent = build_session_agent(
        agent._chat_model,
        tools=agent._tools,
        project_manager=agent._project_manager,
        sub_agents=agent._sub_agents,
    )
    logger.info("Registered sub-agent for category: %s", category)
