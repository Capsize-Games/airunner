"""Autonomous application control tools."""

from typing import Callable

from airunner_services.llm.managers.tools.autonomous_control_analysis_tools import (
    build_analyze_user_behavior_tool,
)
from airunner_services.llm.managers.tools.autonomous_control_insight_tools import (
    build_log_agent_decision_tool,
    build_monitor_system_health_tool,
    build_propose_action_tool,
)
from airunner_services.llm.managers.tools.autonomous_control_request_tools import (
    build_request_user_input_tool,
)
from airunner_services.llm.managers.tools.autonomous_control_state_tools import (
    build_get_application_state_tool,
    build_schedule_task_tool,
    build_set_application_mode_tool,
)
from airunner_services.tools.base_tool import BaseTool


class AutonomousControlTools(BaseTool):
    """Provide the autonomous-control tool builders."""

    def get_application_state_tool(self) -> Callable:
        """Return the application-state inspection tool."""
        return build_get_application_state_tool(self)

    def schedule_task_tool(self) -> Callable:
        """Return the task-scheduling tool."""
        return build_schedule_task_tool(self)

    def set_application_mode_tool(self) -> Callable:
        """Return the application-mode control tool."""
        return build_set_application_mode_tool(self)

    def request_user_input_tool(self) -> Callable:
        """Return the user-input request tool."""
        return build_request_user_input_tool(self)

    def analyze_user_behavior_tool(self) -> Callable:
        """Return the user-behavior analysis tool."""
        return build_analyze_user_behavior_tool(self)

    def propose_action_tool(self) -> Callable:
        """Return the action-proposal tool."""
        return build_propose_action_tool(self)

    def monitor_system_health_tool(self) -> Callable:
        """Return the health-monitoring tool."""
        return build_monitor_system_health_tool(self)

    def log_agent_decision_tool(self) -> Callable:
        """Return the decision logging tool."""
        return build_log_agent_decision_tool(self)
