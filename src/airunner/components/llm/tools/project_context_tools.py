"""Project context indexing and compaction tools for coding agents."""

from airunner.components.llm.core.tool_registry import ToolCategory, tool
from airunner.components.llm.tools.project_context_index_handler import (
    ProjectContextIndexHandler,
)
from airunner.components.llm.tools.project_policy_gate import (
    ProjectPolicyGate,
)


def _handler(
    project_path: str,
    run_id: str | None = None,
) -> ProjectContextIndexHandler:
    """Create a project context handler."""
    return ProjectContextIndexHandler(project_path, run_id=run_id)


def _policy_gate(
    project_path: str,
    run_id: str | None = None,
) -> ProjectPolicyGate:
    """Create a project policy gate for context tools."""
    return ProjectPolicyGate(project_path, run_id=run_id)


@tool(
    name="project_build_context_index",
    category=ToolCategory.PROJECT,
    description=(
        "Build and persist a keyword-searchable index over project files "
        "and .airunner artifacts for coding agents."
    ),
    keywords=["project", "index", "context", "retrieve", "airunner"],
)
def project_build_context_index(
    project_path: str,
    max_entries: int = 500,
    reviewed: bool = False,
    run_id: str | None = None,
) -> dict:
    """Build and persist the project context index."""
    blocked = _policy_gate(project_path, run_id).require_file_review(
        "project_build_context_index",
        reviewed=reviewed,
    )
    if blocked:
        return blocked
    return _handler(project_path, run_id).build_index(max_entries=max_entries)


@tool(
    name="project_query_context_index",
    category=ToolCategory.PROJECT,
    description=(
        "Query indexed project files, plans, memory, and compacted run "
        "summaries for coding-run context."
    ),
    keywords=["project", "context", "query", "retrieve", "search"],
)
def project_query_context_index(
    project_path: str,
    query: str,
    limit: int = 5,
    rebuild_if_missing: bool = True,
    run_id: str | None = None,
) -> dict:
    """Query the indexed project context for agent retrieval."""
    return _handler(project_path, run_id).query_index(
        query,
        limit=limit,
        rebuild_if_missing=rebuild_if_missing,
    )


@tool(
    name="project_compact_run",
    category=ToolCategory.PROJECT,
    description=(
        "Compact one persisted coding-agent run by summarizing older "
        "messages and tool calls while keeping recent state available."
    ),
    keywords=["project", "run", "compact", "summary", "agent"],
)
def project_compact_run(
    project_path: str,
    target_run_id: str,
    max_messages: int = 12,
    max_tool_calls: int = 20,
    reviewed: bool = False,
    run_id: str | None = None,
) -> dict:
    """Compact one persisted run transcript."""
    blocked = _policy_gate(project_path, run_id).require_file_review(
        "project_compact_run",
        reviewed=reviewed,
    )
    if blocked:
        return blocked
    return _handler(project_path, run_id).compact_run(
        target_run_id,
        max_messages=max_messages,
        max_tool_calls=max_tool_calls,
    )