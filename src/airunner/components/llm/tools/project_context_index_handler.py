"""Project context indexing, retrieval, and run-compaction helpers."""

from airunner.components.agents.runtime.agent_runtime_support import (
    utc_now_iso,
)
from airunner.components.agents.runtime.agent_tool_call_record import (
    AgentToolCallRecord,
)
from airunner.components.document_editor.project import (
    AirunnerProjectContextIndexService,
    AirunnerProjectService,
    AirunnerProjectStateService,
)


class ProjectContextIndexHandler:
    """Manage persisted project context indexes and run compaction."""

    def __init__(self, project_path: str, run_id: str | None = None):
        self.project_service = AirunnerProjectService(project_path)
        if not self.project_service.exists():
            raise ValueError(
                "The target path is not an initialized .airunner project."
            )
        self.state_service = AirunnerProjectStateService(self.project_service)
        self.index_service = AirunnerProjectContextIndexService(
            self.project_service
        )
        self.run_id = run_id

    def build_index(self, *, max_entries: int = 500) -> dict[str, object]:
        """Build and persist one project context index."""
        index = self.index_service.build_index(max_entries=max_entries)
        return self._audited_result(
            "project_build_context_index",
            {"max_entries": max_entries},
            generated_at=index.generated_at,
            entry_count=len(index.entries),
            message=f"Built project context index with {len(index.entries)} entries.",
        )

    def query_index(
        self,
        query: str,
        *,
        limit: int = 5,
        rebuild_if_missing: bool = True,
    ) -> dict[str, object]:
        """Query indexed project context for agent retrieval."""
        result = self.index_service.query_index(
            query,
            limit=limit,
            rebuild_if_missing=rebuild_if_missing,
        )
        return self._audited_result(
            "project_query_context_index",
            {
                "query": query,
                "limit": limit,
                "rebuild_if_missing": rebuild_if_missing,
            },
            query=query,
            generated_at=result["generated_at"],
            match_count=result["match_count"],
            results=result["results"],
            context=result["context"],
            message=f"Found {result['match_count']} indexed context match(es).",
        )

    def compact_run(
        self,
        target_run_id: str,
        *,
        max_messages: int = 12,
        max_tool_calls: int = 20,
    ) -> dict[str, object]:
        """Compact one persisted run transcript and save it back."""
        run = self.state_service.load_run(target_run_id)
        before_messages = len(run.messages)
        before_tool_calls = len(run.tool_calls)
        run.compact(
            max_messages=max_messages,
            max_tool_calls=max_tool_calls,
        )
        self.state_service.save_run(run)
        return self._audited_result(
            "project_compact_run",
            {
                "target_run_id": target_run_id,
                "max_messages": max_messages,
                "max_tool_calls": max_tool_calls,
            },
            run_id=target_run_id,
            summary=run.summary,
            message_count=len(run.messages),
            tool_call_count=len(run.tool_calls),
            omitted_messages=before_messages - len(run.messages),
            omitted_tool_calls=before_tool_calls - len(run.tool_calls),
            metadata=run.metadata,
            message=f"Compacted persisted run {target_run_id}.",
        )

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

    def _audited_result(
        self,
        operation: str,
        arguments: dict[str, object],
        **kwargs,
    ) -> dict[str, object]:
        result = {
            "operation": operation,
            "success": True,
            **kwargs,
        }
        result["audit_record_id"] = self._record_tool_call(
            operation,
            arguments,
            result,
        )
        return result