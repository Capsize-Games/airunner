"""Persist plans, memory, sessions, tasks, and audit data under .airunner."""

import json
import os

from airunner.components.agents.runtime.agent_message_record import (
    AgentMessageRecord,
)
from airunner.components.agents.runtime.agent_handoff_record import (
    AgentHandoffRecord,
)
from airunner.components.agents.runtime.agent_generated_write_record import (
    AgentGeneratedWriteRecord,
)
from airunner.components.agents.runtime.agent_run_record import AgentRunRecord
from airunner.components.agents.runtime.agent_run_status import (
    AgentRunStatus,
)
from airunner.components.agents.runtime.research_evidence_record import (
    ResearchEvidenceRecord,
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
from airunner.components.agents.runtime.agent_tool_call_record import (
    AgentToolCallRecord,
)
from airunner.components.document_editor.project.airunner_project_paths import (
    PROJECT_DIR_NAME,
)
from airunner.components.document_editor.project.airunner_project_service import (
    AirunnerProjectService,
)


class AirunnerProjectStateService:
    """Manage persisted coding-agent state within a .airunner project."""

    def __init__(self, project_service: AirunnerProjectService):
        """Initialize project-state persistence for one coding workspace."""
        self.project_service = project_service
        self._workspace_manager = project_service.workspace_manager

    def write_plan(self, name: str, content: str) -> str:
        """Write a markdown plan under .airunner/plans/."""
        return self._write_markdown("plans", name, content)

    def read_plan(self, name: str) -> str:
        """Read a markdown plan from .airunner/plans/."""
        return self._read_markdown("plans", name)

    def write_memory(self, name: str, content: str) -> str:
        """Write a markdown memory file under .airunner/memory/."""
        return self._write_markdown("memory", name, content)

    def read_memory(self, name: str) -> str:
        """Read a markdown memory file from .airunner/memory/."""
        return self._read_markdown("memory", name)

    def save_session(self, session: AgentSessionRecord) -> str:
        """Persist a coding-agent session ledger file."""
        return self._write_json(
            self._session_path(session.record_id),
            session.to_dict(),
        )

    def load_session(self, session_id: str) -> AgentSessionRecord:
        """Load one coding-agent session ledger file."""
        return AgentSessionRecord.from_dict(
            self._read_json(self._session_path(session_id))
        )

    def save_task(self, task: AgentTaskRecord) -> str:
        """Persist a coding-agent task ledger file."""
        return self._write_json(self._task_path(task.record_id), task.to_dict())

    def load_task(self, task_id: str) -> AgentTaskRecord:
        """Load one coding-agent task ledger file."""
        return AgentTaskRecord.from_dict(
            self._read_json(self._task_path(task_id))
        )

    def save_handoff(self, handoff: AgentHandoffRecord) -> str:
        """Persist one coding-agent handoff artifact."""
        return self._write_json(
            self._handoff_path(handoff.record_id),
            handoff.to_dict(),
        )

    def load_handoff(self, handoff_id: str) -> AgentHandoffRecord:
        """Load one coding-agent handoff artifact."""
        return AgentHandoffRecord.from_dict(
            self._read_json(self._handoff_path(handoff_id))
        )

    def list_handoffs(self, session_id: str | None = None) -> list[AgentHandoffRecord]:
        """Return persisted handoffs, optionally filtered to one session."""
        records: list[AgentHandoffRecord] = []
        for rel_path in self._workspace_manager.list_files(
            self._project_dir(os.path.join("agents", "handoffs")),
            pattern="*.json",
            recursive=False,
        ):
            handoff = AgentHandoffRecord.from_dict(self._read_json(rel_path))
            if session_id and handoff.session_id != session_id:
                continue
            records.append(handoff)
        return records

    def save_generated_write(
        self,
        generated_write: AgentGeneratedWriteRecord,
    ) -> str:
        """Persist one generated-write audit record."""
        return self._write_json(
            self._generated_write_path(generated_write.record_id),
            generated_write.to_dict(),
        )

    def load_generated_write(
        self,
        generated_write_id: str,
    ) -> AgentGeneratedWriteRecord:
        """Load one generated-write audit record."""
        return AgentGeneratedWriteRecord.from_dict(
            self._read_json(self._generated_write_path(generated_write_id))
        )

    def list_generated_writes(
        self,
        run_id: str | None = None,
    ) -> list[AgentGeneratedWriteRecord]:
        """Return generated-write audit records, optionally for one run."""
        records: list[AgentGeneratedWriteRecord] = []
        for rel_path in self._workspace_manager.list_files(
            self._project_dir(os.path.join("audit", "generated_writes")),
            pattern="*.json",
            recursive=False,
        ):
            generated_write = AgentGeneratedWriteRecord.from_dict(
                self._read_json(rel_path)
            )
            if run_id and generated_write.run_id != run_id:
                continue
            records.append(generated_write)
        return records

    def save_run(self, run: AgentRunRecord) -> str:
        """Persist one coding-agent run audit record."""
        return self._write_json(self._run_path(run.record_id), run.to_dict())

    def load_run(self, run_id: str) -> AgentRunRecord:
        """Load one coding-agent run audit record."""
        return AgentRunRecord.from_dict(self._read_json(self._run_path(run_id)))

    def save_research_run(self, research_run: ResearchRunRecord) -> str:
        """Persist one research-run ledger file."""
        return self._write_json(
            self._research_run_path(research_run.record_id),
            research_run.to_dict(),
        )

    def load_research_run(self, run_id: str) -> ResearchRunRecord:
        """Load one research-run ledger file."""
        return ResearchRunRecord.from_dict(
            self._read_json(self._research_run_path(run_id))
        )

    def list_research_runs(
        self,
        status: AgentRunStatus | None = None,
    ) -> list[ResearchRunRecord]:
        """Return persisted research runs, optionally by status."""
        records: list[ResearchRunRecord] = []
        for rel_path in self._workspace_manager.list_files(
            self._project_dir(os.path.join("research", "runs")),
            pattern="*.json",
            recursive=False,
        ):
            research_run = ResearchRunRecord.from_dict(
                self._read_json(rel_path)
            )
            if status and research_run.status != status:
                continue
            records.append(research_run)
        return records

    def save_research_source(self, source: ResearchSourceRecord) -> str:
        """Persist one research source and attach it to its run."""
        self._write_json(
            self._research_source_path(source.record_id),
            source.to_dict(),
        )
        if source.run_id:
            self._append_research_source(source.run_id, source.record_id)
        return source.record_id

    def load_research_source(self, source_id: str) -> ResearchSourceRecord:
        """Load one research source ledger file."""
        return ResearchSourceRecord.from_dict(
            self._read_json(self._research_source_path(source_id))
        )

    def list_research_sources(
        self,
        run_id: str | None = None,
        status: ResearchReviewStatus | None = None,
    ) -> list[ResearchSourceRecord]:
        """Return research sources, optionally filtered by run and status."""
        records: list[ResearchSourceRecord] = []
        for rel_path in self._workspace_manager.list_files(
            self._project_dir(os.path.join("research", "sources")),
            pattern="*.json",
            recursive=False,
        ):
            source = ResearchSourceRecord.from_dict(self._read_json(rel_path))
            if run_id and source.run_id != run_id:
                continue
            if status and source.status != status:
                continue
            records.append(source)
        return records

    def save_research_evidence(
        self,
        evidence: ResearchEvidenceRecord,
    ) -> str:
        """Persist one research evidence record and attach it to its run."""
        self._write_json(
            self._research_evidence_path(evidence.record_id),
            evidence.to_dict(),
        )
        if evidence.run_id:
            self._append_research_evidence(
                evidence.run_id,
                evidence.record_id,
            )
        return evidence.record_id

    def load_research_evidence(
        self,
        evidence_id: str,
    ) -> ResearchEvidenceRecord:
        """Load one research evidence ledger file."""
        return ResearchEvidenceRecord.from_dict(
            self._read_json(self._research_evidence_path(evidence_id))
        )

    def list_research_evidence(
        self,
        run_id: str | None = None,
        status: ResearchReviewStatus | None = None,
        source_id: str | None = None,
    ) -> list[ResearchEvidenceRecord]:
        """Return research evidence filtered by run, status, or source."""
        records: list[ResearchEvidenceRecord] = []
        for rel_path in self._workspace_manager.list_files(
            self._project_dir(os.path.join("research", "evidence")),
            pattern="*.json",
            recursive=False,
        ):
            evidence = ResearchEvidenceRecord.from_dict(
                self._read_json(rel_path)
            )
            if run_id and evidence.run_id != run_id:
                continue
            if status and evidence.status != status:
                continue
            if source_id and source_id not in evidence.source_ids:
                continue
            records.append(evidence)
        return records

    def append_message(
        self,
        run_id: str,
        message: AgentMessageRecord,
    ) -> AgentRunRecord:
        """Append a persisted message to one run transcript."""
        run = self.load_run(run_id)
        run.add_message(message)
        self.save_run(run)
        return run

    def append_tool_call(
        self,
        run_id: str,
        tool_call: AgentToolCallRecord,
    ) -> AgentRunRecord:
        """Append a persisted tool call to one run audit trail."""
        run = self.load_run(run_id)
        run.add_tool_call(tool_call)
        self.save_run(run)
        return run

    def record_tool_call(
        self,
        tool_call: AgentToolCallRecord,
        run_id: str | None = None,
    ) -> str:
        """Persist one tool-call audit record and optionally append it."""
        self._write_json(
            self._tool_call_path(tool_call.record_id),
            tool_call.to_dict(),
        )
        if run_id:
            self.append_tool_call(run_id, tool_call)
        return tool_call.record_id

    def load_tool_call(self, tool_call_id: str) -> AgentToolCallRecord:
        """Load one persisted tool-call audit record."""
        return AgentToolCallRecord.from_dict(
            self._read_json(self._tool_call_path(tool_call_id))
        )

    def list_tool_calls(self) -> list[AgentToolCallRecord]:
        """Return all persisted tool-call audit records."""
        records: list[AgentToolCallRecord] = []
        for rel_path in self._workspace_manager.list_files(
            self._project_dir(os.path.join("audit", "tool_calls")),
            pattern="*.json",
            recursive=False,
        ):
            records.append(
                AgentToolCallRecord.from_dict(self._read_json(rel_path))
            )
        return records

    def list_resumable_sessions(self) -> list[AgentSessionRecord]:
        """Return sessions that still need recovery after restart."""
        candidates: list[AgentSessionRecord] = []
        for rel_path in self._workspace_manager.list_files(
            self._project_dir("sessions"),
            pattern="*.json",
            recursive=False,
        ):
            session = AgentSessionRecord.from_dict(self._read_json(rel_path))
            if session.status not in self._resumable_statuses():
                continue
            candidates.append(session)
        return candidates

    def _session_path(self, session_id: str) -> str:
        """Return the relative ledger path for a session record."""
        return os.path.join(self._project_dir("sessions"), f"{session_id}.json")

    def _task_path(self, task_id: str) -> str:
        """Return the relative ledger path for a task record."""
        return os.path.join(self._project_dir("tasks"), f"{task_id}.json")

    def _run_path(self, run_id: str) -> str:
        """Return the relative audit path for a run record."""
        directory = os.path.join(self._project_dir("audit"), "runs")
        return os.path.join(directory, f"{run_id}.json")

    def _research_run_path(self, run_id: str) -> str:
        """Return the relative ledger path for a research run record."""
        directory = os.path.join(self._project_dir("research"), "runs")
        return os.path.join(directory, f"{run_id}.json")

    def _research_source_path(self, source_id: str) -> str:
        """Return the relative ledger path for a research source record."""
        directory = os.path.join(self._project_dir("research"), "sources")
        return os.path.join(directory, f"{source_id}.json")

    def _research_evidence_path(self, evidence_id: str) -> str:
        """Return the relative ledger path for a research evidence file."""
        directory = os.path.join(self._project_dir("research"), "evidence")
        return os.path.join(directory, f"{evidence_id}.json")

    def _handoff_path(self, handoff_id: str) -> str:
        """Return the relative artifact path for a handoff record."""
        directory = os.path.join(self._project_dir("agents"), "handoffs")
        return os.path.join(directory, f"{handoff_id}.json")

    def _tool_call_path(self, tool_call_id: str) -> str:
        """Return the relative audit path for a tool-call record."""
        directory = os.path.join(self._project_dir("audit"), "tool_calls")
        return os.path.join(directory, f"{tool_call_id}.json")

    def _generated_write_path(self, generated_write_id: str) -> str:
        """Return the relative audit path for a generated-write record."""
        directory = os.path.join(
            self._project_dir("audit"),
            "generated_writes",
        )
        return os.path.join(directory, f"{generated_write_id}.json")

    def _write_markdown(
        self,
        directory: str,
        name: str,
        content: str,
    ) -> str:
        """Write one markdown artifact under the .airunner root."""
        rel_path = os.path.join(
            self._project_dir(directory),
            self._markdown_name(name),
        )
        return self._workspace_manager.write_file(
            rel_path,
            self._markdown_content(content),
            backup=True,
            create_dirs=True,
        )

    def _read_markdown(self, directory: str, name: str) -> str:
        """Read one markdown artifact from the .airunner root."""
        rel_path = os.path.join(
            self._project_dir(directory),
            self._markdown_name(name),
        )
        return self._workspace_manager.read_file(rel_path)

    def _read_json(self, rel_path: str) -> dict:
        """Read one JSON artifact relative to the project root."""
        return json.loads(self._workspace_manager.read_file(rel_path))

    def _write_json(self, rel_path: str, payload: dict) -> str:
        """Write one JSON artifact relative to the project root."""
        return self._workspace_manager.write_file(
            rel_path,
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            backup=True,
            create_dirs=True,
        )

    def _project_dir(self, name: str) -> str:
        """Return the .airunner-relative path for a state directory."""
        return os.path.join(PROJECT_DIR_NAME, name)

    def _markdown_name(self, name: str) -> str:
        """Normalize one markdown artifact file name."""
        return name if name.endswith(".md") else f"{name}.md"

    def _markdown_content(self, content: str) -> str:
        """Normalize markdown content with a trailing newline."""
        return content if content.endswith("\n") else content + "\n"

    def _resumable_statuses(self) -> set[AgentRunStatus]:
        """Return the session states that should be recovered."""
        return {
            AgentRunStatus.RUNNING,
            AgentRunStatus.PAUSED,
            AgentRunStatus.PENDING,
        }

    def _append_research_source(self, run_id: str, source_id: str) -> None:
        """Attach one source identifier to its research run."""
        research_run = self.load_research_run(run_id)
        research_run.add_source(source_id)
        self.save_research_run(research_run)

    def _append_research_evidence(
        self,
        run_id: str,
        evidence_id: str,
    ) -> None:
        """Attach one evidence identifier to its research run."""
        research_run = self.load_research_run(run_id)
        research_run.add_evidence(evidence_id)
        self.save_research_run(research_run)