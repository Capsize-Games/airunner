"""Project-aware runtime, diagnostics, and workspace query tools."""

from airunner.components.llm.core.tool_registry import ToolCategory, tool
from airunner.components.llm.tools.project_policy_gate import (
    ProjectPolicyGate,
)
from airunner.components.llm.tools.project_runtime_tools_handler import (
    ProjectRuntimeToolsHandler,
)


def _handler(
    project_path: str,
    run_id: str | None = None,
) -> ProjectRuntimeToolsHandler:
    """Create a project-aware runtime tools handler."""
    return ProjectRuntimeToolsHandler(project_path, run_id=run_id)


def _policy_gate(
    project_path: str,
    run_id: str | None = None,
) -> ProjectPolicyGate:
    """Create a wrapper-level policy gate for runtime tools."""
    return ProjectPolicyGate(project_path, run_id=run_id)


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
    approved: bool = False,
    run_id: str | None = None,
) -> dict:
    """Start a project-scoped terminal command."""
    blocked = _policy_gate(project_path, run_id).require_command_approval(
        "project_run_command",
        approved=approved,
    )
    if blocked:
        return blocked
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
    name="project_run_python_tests",
    category=ToolCategory.PROJECT,
    description=(
        "Run pytest inside an initialized .airunner project using the "
        "project's selected Python environment metadata."
    ),
    keywords=["project", "python", "tests", "pytest", "validate"],
)
def project_run_python_tests(
    project_path: str,
    root_name: str | None = None,
    rel_working_directory: str = "",
    extra_args: list[str] | None = None,
    approved: bool = False,
    run_id: str | None = None,
) -> dict:
    """Run Python tests inside a project workspace."""
    blocked = _policy_gate(project_path, run_id).require_command_approval(
        "project_run_python_tests",
        approved=approved,
    )
    if blocked:
        return blocked
    return _handler(project_path, run_id).run_python_tests(
        root_name=root_name,
        rel_working_directory=rel_working_directory,
        extra_args=extra_args,
    )


@tool(
    name="project_run_python_lint",
    category=ToolCategory.PROJECT,
    description=(
        "Run AIRunner's Python code-quality lint workflow inside an "
        "initialized .airunner project using the selected environment."
    ),
    keywords=["project", "python", "lint", "quality", "diagnostics"],
)
def project_run_python_lint(
    project_path: str,
    root_name: str | None = None,
    rel_working_directory: str = "",
    approved: bool = False,
    run_id: str | None = None,
) -> dict:
    """Run Python linting inside a project workspace."""
    blocked = _policy_gate(project_path, run_id).require_command_approval(
        "project_run_python_lint",
        approved=approved,
    )
    if blocked:
        return blocked
    return _handler(project_path, run_id).run_python_lint(
        root_name=root_name,
        rel_working_directory=rel_working_directory,
    )


@tool(
    name="project_run_python_format",
    category=ToolCategory.PROJECT,
    description=(
        "Run Python formatting inside an initialized .airunner project "
        "using the selected environment metadata."
    ),
    keywords=["project", "python", "format", "ruff", "style"],
)
def project_run_python_format(
    project_path: str,
    root_name: str | None = None,
    rel_working_directory: str = "",
    paths: list[str] | None = None,
    check_only: bool = False,
    approved: bool = False,
    run_id: str | None = None,
) -> dict:
    """Run Python formatting inside a project workspace."""
    blocked = _policy_gate(project_path, run_id).require_command_approval(
        "project_run_python_format",
        approved=approved,
    )
    if blocked:
        return blocked
    return _handler(project_path, run_id).run_python_format(
        root_name=root_name,
        rel_working_directory=rel_working_directory,
        paths=paths,
        check_only=check_only,
    )


@tool(
    name="project_get_python_workflow_summary",
    category=ToolCategory.PROJECT,
    description=(
        "Return the resolved Python test, lint, format, bootstrap, and "
        "diagnostics commands for an initialized .airunner project."
    ),
    keywords=["project", "python", "workflow", "summary", "quality"],
)
def project_get_python_workflow_summary(
    project_path: str,
    root_name: str | None = None,
    rel_working_directory: str = "",
    run_id: str | None = None,
) -> dict:
    """Return Python workflow command metadata for a project."""
    return _handler(project_path, run_id).python_workflow_summary(
        root_name=root_name,
        rel_working_directory=rel_working_directory,
    )


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
    summary = _handler(project_path, run_id).workspace_summary()
    summary["policy"] = _policy_gate(project_path, run_id).policy_context()
    return summary