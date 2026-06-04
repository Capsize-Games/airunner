"""Requirement-analysis helpers for the initializer agent."""

from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from airunner_services.llm.long_running.initializer_agent_state import (
    INITIALIZER_SYSTEM_PROMPT,
    InitializerWorkflowState,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _analysis_prompt() -> ChatPromptTemplate:
    """Return the initializer analysis prompt template."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", INITIALIZER_SYSTEM_PROMPT),
            (
                "human",
                """Analyze these project requirements and prepare a comprehensive feature list.

PROJECT NAME: {project_name}

REQUIREMENTS:
{project_description}

First, identify:
1. Core functionality needed
2. User-facing features
3. Backend/infrastructure needs
4. Testing requirements
5. Potential integrations

Then generate the full feature list in JSON format.""",
            ),
        ]
    )


def analyze_requirements(
    agent: Any,
    state: InitializerWorkflowState,
) -> dict[str, Any]:
    """Analyze one set of project requirements."""
    logger.info("Analyzing requirements for project: %s", state["project_name"])
    messages = _analysis_prompt().format_messages(
        project_name=state["project_name"],
        project_description=state["project_description"],
    )
    return {"messages": messages}