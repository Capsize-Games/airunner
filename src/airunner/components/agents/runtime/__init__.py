"""Runtime records for AIRunner coding agents."""

from airunner.components.agents.runtime.agent_message_channel import (
    AgentMessageChannel,
)
from airunner.components.agents.runtime.agent_message_record import (
    AgentMessageRecord,
)
from airunner.components.agents.runtime.agent_handoff_record import (
    AgentHandoffRecord,
)
from airunner.components.agents.runtime.agent_role import AgentRole
from airunner.components.agents.runtime.agent_run_record import (
    AgentRunRecord,
)
from airunner.components.agents.runtime.agent_run_status import (
    AgentRunStatus,
)
from airunner.components.agents.runtime.agent_session_record import (
    AgentSessionRecord,
)
from airunner.components.agents.runtime.agent_task_record import (
    AgentTaskRecord,
)
from airunner.components.agents.runtime.agent_task_status import (
    AgentTaskStatus,
)
from airunner.components.agents.runtime.agent_tool_call_record import (
    AgentToolCallRecord,
)


def __getattr__(name: str):
    """Lazily expose runtime helpers that depend on project services."""
    if name == "AgentBackgroundRunManager":
        from airunner.components.agents.runtime.agent_background_run_manager import (
            AgentBackgroundRunManager,
        )

        return AgentBackgroundRunManager
    if name == "AgentOrchestrationService":
        from airunner.components.agents.runtime.agent_orchestration_service import (
            AgentOrchestrationService,
        )

        return AgentOrchestrationService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "AgentMessageChannel",
    "AgentMessageRecord",
    "AgentBackgroundRunManager",
    "AgentHandoffRecord",
    "AgentOrchestrationService",
    "AgentRole",
    "AgentRunRecord",
    "AgentRunStatus",
    "AgentSessionRecord",
    "AgentTaskRecord",
    "AgentTaskStatus",
    "AgentToolCallRecord",
]