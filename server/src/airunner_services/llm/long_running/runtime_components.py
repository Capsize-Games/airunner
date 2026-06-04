"""Shared construction helpers for long-running harness components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from airunner_services.llm.long_running.initializer_agent import (
    InitializerAgent,
)
from airunner_services.llm.long_running.project_manager import ProjectManager
from airunner_services.llm.long_running.session_agent import SessionAgent


@dataclass(frozen=True)
class LongRunningRuntimeComponents:
    """Shared manager and agent instances for the long-running stack."""

    project_manager: ProjectManager
    sub_agents: dict[str, Any]
    initializer: InitializerAgent
    session_agent: SessionAgent


def resolve_project_manager(
    project_manager: Optional[ProjectManager] = None,
) -> ProjectManager:
    """Return the project manager used by the long-running stack."""
    return project_manager or ProjectManager()


def resolve_sub_agents(
    sub_agents: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return a copy of the configured long-running sub-agent map."""
    return dict(sub_agents or {})


def build_session_agent(
    chat_model: Any,
    *,
    tools: Optional[list[Any]] = None,
    project_manager: Optional[ProjectManager] = None,
    sub_agents: Optional[dict[str, Any]] = None,
) -> SessionAgent:
    """Create one session agent with shared long-running dependencies."""
    manager = resolve_project_manager(project_manager)
    return SessionAgent(
        chat_model=chat_model,
        tools=tools,
        project_manager=manager,
        sub_agents=resolve_sub_agents(sub_agents),
    )


def build_runtime_components(
    chat_model: Any,
    *,
    tools: Optional[list[Any]] = None,
    project_manager: Optional[ProjectManager] = None,
    sub_agents: Optional[dict[str, Any]] = None,
) -> LongRunningRuntimeComponents:
    """Create the shared runtime components for a harness instance."""
    manager = resolve_project_manager(project_manager)
    agents = resolve_sub_agents(sub_agents)
    initializer = InitializerAgent(chat_model=chat_model, project_manager=manager)
    return LongRunningRuntimeComponents(
        project_manager=manager,
        sub_agents=agents,
        initializer=initializer,
        session_agent=build_session_agent(
            chat_model, tools=tools, project_manager=manager,
            sub_agents=agents,
        ),
    )
# MI note: this helper stays intentionally narrow and delegated.
# MI note: related orchestration lives in neighboring long_running modules.
