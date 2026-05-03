"""Project-aware runtime, diagnostics, and workspace query tools."""

from airunner.components.llm.core.tool_registry import ToolCategory, tool
from airunner.components.llm.tools.project_runtime_tools_handler import (
    ProjectRuntimeToolsHandler,
)


def _handler(
    project_path: str,
    run_id: str | None = None,
) -> ProjectRuntimeToolsHandler:
    """Create a project-aware runtime tools handler."""
    return ProjectRuntimeToolsHandler(project_path, run_id=run_id)


@tool(
    name="project_run_command",
    category=ToolCategory.PROJECT,
    description=(
        "Run a shell command inside an initialized .airunner coding "
        "project and keep the terminal session available for later queries."
    ),
    keywords=["project", "terminal", "command", "run", "shell"],
)
def project_run_command(
    project_path: str,
    command: str,
    root_name: str | None = None,
    rel_working_directory: str = "",
    environment: dict[str, str] | None = None,
    run_id: str | None = None,
) -> dict:
    """Start a project-scoped terminal command."""
    return _handler(project_path, run_id).run_command(
        command,
        root_name=root_name,
        rel_working_directory=rel_working_directory,
        environment=environment,
    )


@tool(
    name="project_read_terminal_output",
    category=ToolCategory.PROJECT,
    description=(
        "Read live or completed output from a previously started "
        "project terminal session."
    ),
    keywords=["project", "terminal", "output", "logs", "session"],
)
def project_read_terminal_output(
    project_path: str,
    session_id: str,
    offset: int = 0,
    limit: int = 4000,
    run_id: str | None = None,
) -> dict:
    """Read output from a project terminal session."""
    return _handler(project_path, run_id).read_terminal_output(
        session_id,
        offset=offset,
        limit=limit,
    )


@tool(
    name="project_send_terminal_input",
    category=ToolCategory.PROJECT,
    description=(
        "Send interactive input to a running project terminal session."
    ),
    keywords=["project", "terminal", "input", "interactive"],
)
def project_send_terminal_input(
    project_path: str,
    session_id: str,
    text: str,
    append_newline: bool = True,
    run_id: str | None = None,
) -> dict:
    """Send input to a project terminal session."""
    return _handler(project_path, run_id).send_terminal_input(
        session_id,
        text,
        append_newline=append_newline,
    )


@tool(
    name="project_stop_command",
    category=ToolCategory.PROJECT,
    description=(
        "Stop a running terminal session that was started inside an "
        "initialized .airunner project."
    ),
    keywords=["project", "terminal", "stop", "cancel", "session"],
)
def project_stop_command(
    project_path: str,
    session_id: str,
    timeout: float = 1.0,
    run_id: str | None = None,
) -> dict:
    """Stop a running project terminal command."""
    return _handler(project_path, run_id).stop_command(
        session_id,
        timeout=timeout,
    )


@tool(
    name="project_list_terminal_sessions",
    category=ToolCategory.PROJECT,
    description=(
        "List terminal sessions that belong to an initialized .airunner "
        "project."
    ),
    keywords=["project", "terminal", "sessions", "list"],
)
def project_list_terminal_sessions(
    project_path: str,
    run_id: str | None = None,
) -> dict:
    """List project terminal sessions."""
    return _handler(project_path, run_id).list_terminal_sessions()


@tool(
    name="project_get_diagnostics",
    category=ToolCategory.PROJECT,
    description=(
        "Collect project-scoped Python diagnostics, including parser "
        "syntax errors and available flake8 or mypy findings."
    ),
    keywords=["project", "diagnostics", "problems", "lint", "mypy"],
)
def project_get_diagnostics(
    project_path: str,
    rel_paths: list[str] | None = None,
    root_name: str | None = None,
    rel_dir: str = "",
    pattern: str = "*.py",
    max_files: int = 50,
    run_id: str | None = None,
) -> dict:
    """Collect diagnostics for project files."""
    return _handler(project_path, run_id).diagnostics(
        rel_paths=rel_paths,
        root_name=root_name,
        rel_dir=rel_dir,
        pattern=pattern,
        max_files=max_files,
    )


@tool(
    name="project_get_workspace_summary",
    category=ToolCategory.PROJECT,
    description=(
        "Summarize project roots, validation state, recent audit counts, "
        "and active terminal sessions for an initialized .airunner project."
    ),
    keywords=["project", "workspace", "summary", "roots", "context"],
)
def project_get_workspace_summary(
    project_path: str,
    run_id: str | None = None,
) -> dict:
    """Return project workspace context for agent planning."""
    return _handler(project_path, run_id).workspace_summary()