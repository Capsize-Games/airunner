"""Runtime records for AIRunner coding agents."""

from airunner.components.agents.runtime.agent_message_channel import (
    AgentMessageChannel,
)
from airunner.components.agents.runtime.meeting_deliverable_record import (
    MeetingDeliverableRecord,
)
from airunner.components.agents.runtime.meeting_item_record import (
    MeetingItemRecord,
)
from airunner.components.agents.runtime.meeting_review_record import (
    MeetingReviewRecord,
)
from airunner.components.agents.runtime.meeting_review_status import (
    MeetingReviewStatus,
)
from airunner.components.agents.runtime.meeting_item_status import (
    MeetingItemStatus,
)
from airunner.components.agents.runtime.meeting_run_record import (
    MeetingRunRecord,
)
from airunner.components.agents.runtime.agent_message_record import (
    AgentMessageRecord,
)
from airunner.components.agents.runtime.agent_generated_write_record import (
    AgentGeneratedWriteRecord,
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
from airunner.components.agents.runtime.research_evidence_record import (
    ResearchEvidenceRecord,
)
from airunner.components.agents.runtime.research_brief_record import (
    ResearchBriefRecord,
)
from airunner.components.agents.runtime.research_review_status import (
    ResearchReviewStatus,
)
from airunner.components.agents.runtime.research_run_record import (
    ResearchRunRecord,
)
from airunner.components.agents.runtime.research_source_record import (
    ResearchSourceRecord,
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
    "AgentGeneratedWriteRecord",
    "AgentHandoffRecord",
    "MeetingDeliverableRecord",
    "MeetingItemRecord",
    "MeetingReviewRecord",
    "MeetingReviewStatus",
    "MeetingItemStatus",
    "MeetingRunRecord",
    "AgentOrchestrationService",
    "AgentRole",
    "AgentRunRecord",
    "AgentRunStatus",
    "ResearchBriefRecord",
    "ResearchEvidenceRecord",
    "ResearchReviewStatus",
    "ResearchRunRecord",
    "ResearchSourceRecord",
    "AgentSessionRecord",
    "AgentTaskRecord",
    "AgentTaskStatus",
    "AgentToolCallRecord",
]