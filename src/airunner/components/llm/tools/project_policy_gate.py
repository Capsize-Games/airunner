"""Wrapper-level policy gate with audited blocked tool results."""

from airunner.components.agents.runtime.agent_runtime_support import (
    utc_now_iso,
)
from airunner.components.agents.runtime.agent_tool_call_record import (
    AgentToolCallRecord,
)
from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.document_editor.project import (
    AirunnerProjectPolicyEnforcer,
)
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)


class ProjectPolicyGate:
    """Apply project autonomy policy before running agent-facing tools."""

    def __init__(self, project_path: str, run_id: str | None = None):
        self.project_service = AirunnerProjectService(project_path)
        if not self.project_service.exists():
            raise ValueError(
                "The target path is not an initialized .airunner project."
            )
        self.state_service = AirunnerProjectStateService(self.project_service)
        self.enforcer = AirunnerProjectPolicyEnforcer(self.project_service)
        self.run_id = run_id

    def require_file_review(
        self,
        operation: str,
        *,
        reviewed: bool,
    ) -> dict[str, object] | None:
        """Return an audited error when file review is still required."""
        decision = self.enforcer.file_write_decision(reviewed=reviewed)
        if decision.allowed:
            return None
        return self._audited_error(
            operation,
            decision.message or "File review required.",
            details={"policy": decision.context, "reviewed": reviewed},
        )

    def require_command_approval(
        self,
        operation: str,
        *,
        approved: bool,
    ) -> dict[str, object] | None:
        """Return an audited error when command approval is still required."""
        decision = self.enforcer.command_decision(approved=approved)
        if decision.allowed:
            return None
        return self._audited_error(
            operation,
            decision.message or "Command approval required.",
            details={"policy": decision.context, "approved": approved},
        )

    def policy_context(self) -> dict[str, object]:
        """Return the current policy context for read-only tool results."""
        return self.enforcer.context()

    def _audited_error(
        self,
        operation: str,
        message: str,
        *,
        details: dict[str, object],
    ) -> dict[str, object]:
        result = {
            "operation": operation,
            "success": False,
            "message": message,
            "error": message,
            "details": details,
        }
        tool_call = AgentToolCallRecord(
            tool_name=operation,
            arguments=details,
            output=result,
            error=message,
            finished_at=utc_now_iso(),
        )
        result["audit_record_id"] = self.state_service.record_tool_call(
            tool_call,
            run_id=self.run_id,
        )
        return result