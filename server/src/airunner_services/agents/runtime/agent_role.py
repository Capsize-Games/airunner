"""Agent roles for AIRunner coding workflows."""

from enum import Enum


class AgentRole(str, Enum):
    """Supported first-class coding agent roles."""

    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
