"""Task states for coding-agent task ledgers."""

from enum import Enum


class AgentTaskStatus(str, Enum):
    """Supported states for persisted coding-agent tasks."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"