"""Persistent planner, coder, and reviewer orchestration helpers."""

from airunner.components.agents.runtime.agent_handoff_record import (
    AgentHandoffRecord,
)
from airunner.components.agents.runtime.agent_role import AgentRole
from airunner.components.agents.runtime.agent_run_status import (
    AgentRunStatus,
)
from airunner.components.agents.runtime.agent_runtime_support import (
    copy_list,
    utc_now_iso,
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
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)


class AgentOrchestrationService:
    """Create tasks and handoffs while enforcing shared-context rules."""

    _terminal_statuses = {
        AgentTaskStatus.COMPLETED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
    }
    _shared_context_rules = [
        "Only one non-terminal task may own a given artifact path.",
        (
            "Handoffs transfer artifact ownership from the source task "
            "to the target task."
        ),
        "Every handoff must persist a summary and explicit artifact paths.",
    ]

    def __init__(self, state_service: AirunnerProjectStateService):
        self.state_service = state_service

    def shared_context_rules(self) -> list[str]:
        """Return the explicit artifact-ownership rules for collaborators."""
        return list(self._shared_context_rules)

    def create_session(
        self,
        title: str,
        *,
        metadata: dict | None = None,
    ) -> AgentSessionRecord:
        """Create and persist one multi-agent session."""
        session = AgentSessionRecord(
            project_path=str(self.state_service.project_service.project_path),
            title=title,
            status=AgentRunStatus.PENDING,
            metadata=metadata or {},
        )
        self.state_service.save_session(session)
        return session

    def create_task(
        self,
        session_id: str,
        title: str,
        role: AgentRole,
        *,
        description: str = "",
        artifact_paths: list[str] | None = None,
        status: AgentTaskStatus = AgentTaskStatus.PENDING,
        metadata: dict | None = None,
        owner_task_id: str | None = None,
    ) -> AgentTaskRecord:
        """Create a task after validating artifact ownership."""
        artifacts = copy_list(artifact_paths)
        self._assert_artifact_availability(
            session_id,
            artifacts,
            owner_task_id=owner_task_id,
        )
        task = AgentTaskRecord(
            title=title,
            role=role,
            session_id=session_id,
            description=description,
            status=status,
            artifact_paths=artifacts,
            metadata=metadata or {},
        )
        self.state_service.save_task(task)
        self._attach_task_to_session(session_id, task.record_id)
        return task

    def handoff_task(
        self,
        source_task_id: str,
        to_role: AgentRole,
        *,
        title: str,
        summary: str,
        artifact_paths: list[str] | None = None,
        metadata: dict | None = None,
    ) -> tuple[AgentHandoffRecord, AgentTaskRecord]:
        """Persist a role handoff and create the receiving task."""
        source_task = self.state_service.load_task(source_task_id)
        artifacts = self._handoff_artifacts(source_task, artifact_paths)
        target_task = self.create_task(
            source_task.session_id,
            title,
            to_role,
            description=summary,
            artifact_paths=artifacts,
            metadata={
                "source_task_id": source_task.record_id,
                "source_role": source_task.role.value,
                "handoff_summary": summary,
            },
            owner_task_id=source_task.record_id,
        )
        handoff = AgentHandoffRecord(
            session_id=source_task.session_id,
            source_task_id=source_task.record_id,
            target_task_id=target_task.record_id,
            from_role=source_task.role,
            to_role=to_role,
            summary=summary,
            artifact_paths=artifacts,
            metadata={
                "shared_context_rules": self.shared_context_rules(),
                **(metadata or {}),
            },
        )
        self.state_service.save_handoff(handoff)
        self._complete_source_task(source_task, handoff.record_id)
        return handoff, target_task

    def _handoff_artifacts(
        self,
        source_task: AgentTaskRecord,
        artifact_paths: list[str] | None,
    ) -> list[str]:
        artifacts = copy_list(artifact_paths)
        if artifacts:
            return artifacts
        return copy_list(source_task.artifact_paths)

    def _complete_source_task(
        self,
        source_task: AgentTaskRecord,
        handoff_id: str,
    ) -> None:
        handoff_ids = copy_list(source_task.metadata.get("handoff_ids"))
        handoff_ids.append(handoff_id)
        source_task.metadata["handoff_ids"] = handoff_ids
        source_task.status = AgentTaskStatus.COMPLETED
        source_task.updated_at = utc_now_iso()
        self.state_service.save_task(source_task)

    def _attach_task_to_session(self, session_id: str, task_id: str) -> None:
        session = self.state_service.load_session(session_id)
        if task_id not in session.task_ids:
            session.task_ids.append(task_id)
            session.updated_at = utc_now_iso()
            self.state_service.save_session(session)

    def _assert_artifact_availability(
        self,
        session_id: str,
        artifact_paths: list[str],
        *,
        owner_task_id: str | None = None,
    ) -> None:
        if not artifact_paths:
            return
        session = self.state_service.load_session(session_id)
        requested = {self._normalized_artifact(item) for item in artifact_paths}
        for task_id in session.task_ids:
            if task_id == owner_task_id:
                continue
            task = self.state_service.load_task(task_id)
            if task.status in self._terminal_statuses:
                continue
            current = {
                self._normalized_artifact(item)
                for item in task.artifact_paths
            }
            overlap = requested & current
            if overlap:
                paths = ", ".join(sorted(overlap))
                raise ValueError(
                    f"Artifacts already owned by active task {task_id}: {paths}"
                )

    def _normalized_artifact(self, artifact_path: str) -> str:
        return artifact_path.replace("\\", "/").strip()