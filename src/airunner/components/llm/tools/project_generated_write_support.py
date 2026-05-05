"""Generated-write diff, summary, and rollback helpers."""

from dataclasses import dataclass
import difflib

from airunner.components.agents.runtime.agent_generated_write_record import (
    AgentGeneratedWriteRecord,
)
from airunner.components.agents.runtime.agent_runtime_support import (
    utc_now_iso,
)
from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)


@dataclass(slots=True)
class ProjectFileSnapshot:
    """Represent one project file before or after a generated write."""

    root_name: str | None
    rel_path: str | None
    abs_path: str | None
    exists: bool
    content: str | None


class ProjectGeneratedWriteSupport:
    """Persist and revert generated writes for review workflows."""

    def __init__(
        self,
        project_service: AirunnerProjectService,
        state_service: AirunnerProjectStateService,
    ):
        self.project_service = project_service
        self.state_service = state_service

    def snapshot(
        self,
        rel_path: str | None,
        root_name: str | None,
    ) -> ProjectFileSnapshot:
        """Capture a best-effort snapshot of one project file."""
        if not rel_path or not root_name:
            return ProjectFileSnapshot(root_name, rel_path, None, False, None)
        manager = self.project_service.get_workspace_manager(root_name)
        abs_path = self.project_service.resolve_path(rel_path, root_name)
        if not manager.exists(rel_path):
            return ProjectFileSnapshot(root_name, rel_path, abs_path, False, None)
        content = self._read_content(rel_path, root_name)
        return ProjectFileSnapshot(root_name, rel_path, abs_path, True, content)

    def record_write(
        self,
        operation: str,
        before: ProjectFileSnapshot,
        after: ProjectFileSnapshot,
        *,
        tool_call_id: str,
        run_id: str | None = None,
        metadata: dict | None = None,
    ) -> AgentGeneratedWriteRecord:
        """Persist one generated-write record tied to a tool call."""
        diff_text, lines_added, lines_removed = self._diff_info(before, after)
        record = AgentGeneratedWriteRecord(
            operation=operation,
            summary=self._summary(
                operation,
                before,
                after,
                lines_added,
                lines_removed,
            ),
            tool_call_id=tool_call_id,
            run_id=run_id,
            root_name=before.root_name or after.root_name,
            rel_path=before.rel_path or after.rel_path,
            target_root_name=after.root_name,
            target_rel_path=after.rel_path,
            before_exists=before.exists,
            after_exists=after.exists,
            before_content=before.content,
            after_content=after.content,
            diff=diff_text,
            metadata=metadata or {},
        )
        self.state_service.save_generated_write(record)
        return record

    def record_result_write(
        self,
        operation: str,
        tool_call_id: str,
        generated_write: dict[str, object],
        result,
        *,
        run_id: str | None = None,
    ) -> dict[str, str]:
        """Persist generated-write metadata for one tool result."""
        before = generated_write["before"]
        after_root = generated_write.get("after_root_name") or result.root_name
        after_rel = generated_write.get("after_rel_path") or result.rel_path
        after = self.snapshot(after_rel, after_root)
        record = self.record_write(
            operation,
            before,
            after,
            tool_call_id=tool_call_id,
            run_id=run_id,
        )
        return {
            "generated_write_id": record.record_id,
            "generated_write_summary": record.summary,
        }

    def list_records(
        self,
        *,
        limit: int = 20,
        run_id: str | None = None,
    ) -> list[AgentGeneratedWriteRecord]:
        """Return recent generated-write records, newest first."""
        records = self.state_service.list_generated_writes(run_id=run_id)
        records.sort(key=lambda item: item.created_at, reverse=True)
        return records[:limit]

    def review_item(
        self,
        record: AgentGeneratedWriteRecord,
    ) -> dict[str, object]:
        """Return one generated-write record as review-friendly data."""
        return {
            "record_id": record.record_id,
            "operation": record.operation,
            "summary": record.summary,
            "tool_call_id": record.tool_call_id,
            "run_id": record.run_id,
            "root_name": record.root_name,
            "rel_path": record.rel_path,
            "target_root_name": record.target_root_name,
            "target_rel_path": record.target_rel_path,
            "created_at": record.created_at,
            "reverted_at": record.metadata.get("reverted_at"),
            "can_revert": not bool(record.metadata.get("reverted_at")),
        }

    def review_items(
        self,
        records: list[AgentGeneratedWriteRecord],
    ) -> list[dict[str, object]]:
        """Return review-friendly data for many generated writes."""
        return [self.review_item(record) for record in records]

    def review_summary(
        self,
        records: list[AgentGeneratedWriteRecord],
    ) -> str:
        """Return a human-readable summary of recent generated writes."""
        if not records:
            return "No agent-generated writes recorded yet."
        lines = ["Generated writes:"]
        for record in records:
            lines.append(f"- {record.summary} [id: {record.record_id}]")
        return "\n".join(lines)

    def revert(
        self,
        record: AgentGeneratedWriteRecord,
    ) -> AgentGeneratedWriteRecord:
        """Restore the workspace state from before one generated write."""
        if record.metadata.get("reverted_at"):
            raise ValueError("This generated write has already been reverted.")
        target_root = record.target_root_name or record.root_name
        target_rel_path = record.target_rel_path or record.rel_path
        if record.before_exists:
            if not record.rel_path or not record.root_name:
                raise ValueError(
                    "This generated write is missing its original location."
                )
            if record.before_content is None:
                raise ValueError(
                    "The previous file contents were not captured for this write."
                )
            if self._path_changed(record):
                self._delete_path(target_rel_path, target_root)
            self.project_service.write_file(
                record.rel_path,
                record.before_content,
                record.root_name,
                backup=False,
            )
            return record
        self._delete_path(target_rel_path, target_root)
        return record

    def mark_reverted(
        self,
        record: AgentGeneratedWriteRecord,
        tool_call_id: str,
    ) -> AgentGeneratedWriteRecord:
        """Persist revert metadata on a generated-write record."""
        record.metadata["reverted_at"] = utc_now_iso()
        record.metadata["reverted_by_tool_call_id"] = tool_call_id
        record.updated_at = utc_now_iso()
        self.state_service.save_generated_write(record)
        return record

    def _read_content(
        self,
        rel_path: str,
        root_name: str,
    ) -> str | None:
        try:
            return self.project_service.read_file(rel_path, root_name)
        except (OSError, UnicodeDecodeError):
            return None

    def _diff_info(
        self,
        before: ProjectFileSnapshot,
        after: ProjectFileSnapshot,
    ) -> tuple[str, int, int]:
        if before.content is None or after.content is None:
            return self._non_text_diff(before, after), 0, 0
        diff_lines = list(
            difflib.unified_diff(
                before.content.splitlines(),
                after.content.splitlines(),
                fromfile=self._label(before),
                tofile=self._label(after),
                lineterm="",
            )
        )
        lines_added = sum(
            1
            for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        )
        lines_removed = sum(
            1
            for line in diff_lines
            if line.startswith("-") and not line.startswith("---")
        )
        if diff_lines:
            return "\n".join(diff_lines), lines_added, lines_removed
        return self._non_text_diff(before, after), 0, 0

    def _non_text_diff(
        self,
        before: ProjectFileSnapshot,
        after: ProjectFileSnapshot,
    ) -> str:
        if self._snapshot_path(before) != self._snapshot_path(after):
            return (
                f"--- {self._label(before)}\n"
                f"+++ {self._label(after)}\n"
                "(file moved without textual changes)"
            )
        return "Text diff unavailable for this write."

    def _summary(
        self,
        operation: str,
        before: ProjectFileSnapshot,
        after: ProjectFileSnapshot,
        lines_added: int,
        lines_removed: int,
    ) -> str:
        if operation == "project_create_file":
            return self._line_summary(
                "Created",
                self._label(after),
                lines_added,
                lines_removed,
            )
        if operation == "project_delete_file":
            return self._line_summary(
                "Deleted",
                self._label(before),
                lines_added,
                lines_removed,
            )
        if operation == "project_rename_file":
            return (
                f"Renamed {self._label(before)} to {self._label(after)}."
            )
        if operation == "project_patch_file":
            return self._line_summary(
                "Patched",
                self._label(after),
                lines_added,
                lines_removed,
            )
        return self._line_summary(
            "Edited",
            self._label(after),
            lines_added,
            lines_removed,
        )

    def _line_summary(
        self,
        verb: str,
        label: str,
        lines_added: int,
        lines_removed: int,
    ) -> str:
        return (
            f"{verb} {label} "
            f"(+{lines_added}/-{lines_removed} lines)."
        )

    def _delete_path(
        self,
        rel_path: str | None,
        root_name: str | None,
    ) -> None:
        if not rel_path or not root_name:
            return
        manager = self.project_service.get_workspace_manager(root_name)
        if not manager.exists(rel_path):
            return
        manager.delete(rel_path, backup=False)

    def _path_changed(self, record: AgentGeneratedWriteRecord) -> bool:
        return (
            record.root_name != record.target_root_name
            or record.rel_path != record.target_rel_path
        )

    def _label(self, snapshot: ProjectFileSnapshot) -> str:
        root = snapshot.root_name or "workspace"
        rel_path = snapshot.rel_path or "<missing>"
        return f"{root}:{rel_path}"

    def _snapshot_path(
        self,
        snapshot: ProjectFileSnapshot,
    ) -> tuple[str | None, str | None]:
        return snapshot.root_name, snapshot.rel_path