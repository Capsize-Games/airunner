"""Review, diff, and rollback tools for generated writes."""

from airunner.components.agents.runtime.agent_tool_call_record import (
    AgentToolCallRecord,
)
from airunner.components.agents.runtime.agent_runtime_support import (
    utc_now_iso,
)
from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)
from airunner.components.llm.tools.project_generated_write_support import (
    ProjectGeneratedWriteSupport,
)
from airunner.components.llm.tools.project_tool_result import (
    ProjectToolResult,
)


class ProjectGeneratedWriteReviewHandler:
    """Inspect and revert generated writes for coding-agent review."""

    def __init__(self, project_path: str, run_id: str | None = None):
        self.project_service = AirunnerProjectService(project_path)
        if not self.project_service.exists():
            raise ValueError(
                "The target path is not an initialized .airunner project."
            )
        self.state_service = AirunnerProjectStateService(self.project_service)
        self.generated_writes = ProjectGeneratedWriteSupport(
            self.project_service,
            self.state_service,
        )
        self.run_id = run_id

    def list_generated_writes(
        self,
        *,
        limit: int = 20,
        run_id: str | None = None,
    ) -> ProjectToolResult:
        records = self.generated_writes.list_records(limit=limit, run_id=run_id)
        summary = self.generated_writes.review_summary(records)
        return self._audited_result(
            "project_list_generated_writes",
            {"limit": limit, "run_id": run_id},
            message=summary,
            details={
                "generated_writes": self.generated_writes.review_items(records)
            },
        )

    def get_generated_write_diff(
        self,
        generated_write_id: str,
    ) -> ProjectToolResult:
        try:
            record = self.state_service.load_generated_write(generated_write_id)
        except FileNotFoundError:
            return self._error(
                "project_get_generated_write_diff",
                generated_write_id,
                "Generated write record does not exist.",
            )
        return self._audited_result(
            "project_get_generated_write_diff",
            {"generated_write_id": generated_write_id},
            message=record.summary,
            content=record.diff,
            details={
                "generated_write": self.generated_writes.review_item(record)
            },
        )

    def revert_generated_write(
        self,
        generated_write_id: str,
    ) -> ProjectToolResult:
        try:
            record = self.state_service.load_generated_write(generated_write_id)
        except FileNotFoundError:
            return self._error(
                "project_revert_generated_write",
                generated_write_id,
                "Generated write record does not exist.",
            )
        try:
            self.generated_writes.revert(record)
        except ValueError as exc:
            return self._error(
                "project_revert_generated_write",
                generated_write_id,
                str(exc),
            )
        result = self._result(
            "project_revert_generated_write",
            True,
            message=f"Reverted {record.summary}",
        )
        result.details = {
            "generated_write": self.generated_writes.review_item(record)
        }
        result.audit_record_id = self._record_tool_call(
            "project_revert_generated_write",
            {"generated_write_id": generated_write_id},
            result.to_dict(),
        )
        reverted = self.generated_writes.mark_reverted(
            record,
            result.audit_record_id,
        )
        result.details = {
            "generated_write": self.generated_writes.review_item(reverted)
        }
        return result

    def _audited_result(
        self,
        tool_name: str,
        arguments: dict[str, object],
        **kwargs,
    ) -> ProjectToolResult:
        result = self._result(tool_name, True, **kwargs)
        result.audit_record_id = self._record_tool_call(
            tool_name,
            arguments,
            result.to_dict(),
        )
        return result

    def _record_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, object],
        output: dict[str, object],
        error: str | None = None,
    ) -> str:
        tool_call = AgentToolCallRecord(
            tool_name=tool_name,
            arguments=arguments,
            output=output,
            error=error,
            finished_at=utc_now_iso(),
        )
        return self.state_service.record_tool_call(
            tool_call,
            run_id=self.run_id,
        )

    def _result(
        self,
        operation: str,
        success: bool,
        **kwargs,
    ) -> ProjectToolResult:
        message = kwargs.pop("message", f"{operation} succeeded.")
        return ProjectToolResult(
            operation=operation,
            success=success,
            message=message,
            **kwargs,
        )

    def _error(
        self,
        operation: str,
        generated_write_id: str,
        error: str,
    ) -> ProjectToolResult:
        result = self._result(
            operation,
            False,
            message=error,
            error=error,
            details={"generated_write_id": generated_write_id},
        )
        result.audit_record_id = self._record_tool_call(
            operation,
            {"generated_write_id": generated_write_id},
            result.to_dict(),
            error=error,
        )
        return result