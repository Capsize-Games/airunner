"""Thin facade for the long-running Session Agent."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.llm.long_running.project_manager import ProjectManager
from airunner_services.llm.long_running.session_agent_cleanup import (
    cleanup_node,
)
from airunner_services.llm.long_running.session_agent_delegate import (
    delegate_to_sub_agent,
)
from airunner_services.llm.long_running.session_agent_graph import build_graph
from airunner_services.llm.long_running.session_agent_implementation import (
    implementation_node,
)
from airunner_services.llm.long_running.session_agent_orientation import (
    orientation_node,
)
from airunner_services.llm.long_running.session_agent_planning import (
    planning_node,
)
from airunner_services.llm.long_running.session_agent_routes import (
    format_feature_list,
    route_after_implementation,
    route_after_planning,
    route_after_verification,
)
from airunner_services.llm.long_running.session_agent_run import run_session
from airunner_services.llm.long_running.session_agent_verification import (
    verification_node,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class SessionAgent:
    """Agent that handles one focused working session on a project."""

    def __init__(
        self,
        chat_model: Any,
        tools: Optional[list[Any]] = None,
        project_manager: Optional[ProjectManager] = None,
        sub_agents: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the Session Agent."""
        self._chat_model = chat_model
        self._tools = tools or []
        self._project_manager = project_manager or ProjectManager()
        self._sub_agents = sub_agents or {}
        if self._tools and hasattr(self._chat_model, "bind_tools"):
            self._chat_model = self._chat_model.bind_tools(self._tools)
            logger.info("Session agent bound %s tools", len(self._tools))
        self._graph = self._build_graph()
        logger.info("SessionAgent initialized")

    _build_graph = build_graph
    _orientation_node = orientation_node
    _planning_node = planning_node
    _implementation_node = implementation_node
    _verification_node = verification_node
    _cleanup_node = cleanup_node
    _delegate_to_sub_agent = delegate_to_sub_agent
    _route_after_planning = route_after_planning
    _route_after_implementation = route_after_implementation
    _route_after_verification = route_after_verification
    _format_feature_list = format_feature_list
    run_session = run_session


# Session-agent responsibilities are intentionally split across modules.
# The facade preserves the public API, graph wiring, and runtime dependencies.
# Phase-specific behavior lives in the neighboring planning, implementation,
# verification, cleanup, and routing helpers.
