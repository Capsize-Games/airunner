"""Lifecycle states for coding-agent runs and sessions."""

from enum import Enum


class AgentRunStatus(str, Enum):
    """Supported states for agent runs and resumable sessions."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
