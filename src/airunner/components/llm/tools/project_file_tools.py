"""Project-aware file and search tools for coding agents."""

from airunner.components.llm.core.tool_registry import ToolCategory, tool
from airunner.components.llm.tools.project_operations_handler import (
    ProjectOperationsHandler,
)


def _handler(
    project_path: str,
    run_id: str | None = None,
) -> ProjectOperationsHandler:
    """Create a project-aware operations handler."""
    return ProjectOperationsHandler(project_path, run_id=run_id)


@tool(
    name="project_list_files",
    category=ToolCategory.PROJECT,
    description=(
        "List files from an initialized .airunner coding project. "
        "Can scan one root or all configured workspace roots."
    ),
    keywords=["project", "workspace", "files", "roots", "list"],
    input_examples=[
        {"project_path": "/workspace/demo", "pattern": "*.py"}
    ],
)
def project_list_files(
    project_path: str,
    rel_dir: str = "",
    root_name: str | None = None,
    pattern: str = "*",
    recursive: bool = True,
    run_id: str | None = None,
) -> dict:
    """List files from a coding project."""
    return _handler(project_path, run_id).list_files(
        rel_dir,
        root_name=root_name,
        pattern=pattern,
        recursive=recursive,
    ).to_dict()


@tool(
    name="project_read_file",
    category=ToolCategory.PROJECT,
    description=(
        "Read one file from an initialized .airunner coding project."
    ),
    keywords=["project", "read", "file", "workspace"],
    input_examples=[
        {"project_path": "/workspace/demo", "rel_path": "src/app.py"}
    ],
)
def project_read_file(
    project_path: str,
    rel_path: str,
    root_name: str | None = None,
    run_id: str | None = None,
) -> dict:
    """Read one project-scoped file."""
    return _handler(project_path, run_id).read_file(
        rel_path,
        root_name=root_name,
    ).to_dict()


@tool(
    name="project_search_files",
    category=ToolCategory.PROJECT,
    description=(
        "Search text across one or more roots of an initialized "
        ".airunner coding project."
    ),
    keywords=["project", "search", "grep", "workspace", "files"],
    input_examples=[
        {"project_path": "/workspace/demo", "query": "run_script"}
    ],
)
def project_search_files(
    project_path: str,
    query: str,
    root_name: str | None = None,
    rel_dir: str = "",
    include_pattern: str = "*",
    is_regex: bool = False,
    case_sensitive: bool = False,
    max_results: int = 20,
    recursive: bool = True,
    run_id: str | None = None,
) -> dict:
    """Search project files for matching text."""
    return _handler(project_path, run_id).search_files(
        query,
        root_name=root_name,
        rel_dir=rel_dir,
        include_pattern=include_pattern,
        is_regex=is_regex,
        case_sensitive=case_sensitive,
        max_results=max_results,
        recursive=recursive,
    ).to_dict()


@tool(
    name="project_create_file",
    category=ToolCategory.PROJECT,
    description=(
        "Create a file inside an initialized .airunner coding project "
        "and audit the write."
    ),
    keywords=["project", "create", "file", "write", "audit"],
    input_examples=[
        {
            "project_path": "/workspace/demo",
            "rel_path": "src/app.py",
            "content": "print('hi')\n",
        }
    ],
)
def project_create_file(
    project_path: str,
    rel_path: str,
    content: str,
    root_name: str | None = None,
    overwrite: bool = False,
    run_id: str | None = None,
) -> dict:
    """Create one project-scoped file and audit the operation."""
    return _handler(project_path, run_id).create_file(
        rel_path,
        content,
        root_name=root_name,
        overwrite=overwrite,
    ).to_dict()


@tool(
    name="project_edit_file",
    category=ToolCategory.PROJECT,
    description=(
        "Replace a file's contents inside an initialized .airunner "
        "coding project and audit the write."
    ),
    keywords=["project", "edit", "replace", "file", "audit"],
)
def project_edit_file(
    project_path: str,
    rel_path: str,
    content: str,
    root_name: str | None = None,
    backup: bool = True,
    run_id: str | None = None,
) -> dict:
    """Replace one project-scoped file and audit the operation."""
    return _handler(project_path, run_id).edit_file(
        rel_path,
        content,
        root_name=root_name,
        backup=backup,
    ).to_dict()


@tool(
    name="project_patch_file",
    category=ToolCategory.PROJECT,
    description=(
        "Apply a deterministic text patch to a project file by "
        "replacing exact text and auditing the write."
    ),
    keywords=["project", "patch", "replace", "edit", "audit"],
)
def project_patch_file(
    project_path: str,
    rel_path: str,
    old_text: str,
    new_text: str,
    root_name: str | None = None,
    expected_occurrences: int = 1,
    backup: bool = True,
    run_id: str | None = None,
) -> dict:
    """Patch one project file by replacing exact text."""
    return _handler(project_path, run_id).patch_file(
        rel_path,
        old_text,
        new_text,
        root_name=root_name,
        expected_occurrences=expected_occurrences,
        backup=backup,
    ).to_dict()


@tool(
    name="project_rename_file",
    category=ToolCategory.PROJECT,
    description=(
        "Rename or move a file within an initialized .airunner "
        "coding project and audit the write."
    ),
    keywords=["project", "rename", "move", "file", "audit"],
)
def project_rename_file(
    project_path: str,
    rel_path: str,
    new_rel_path: str,
    root_name: str | None = None,
    new_root_name: str | None = None,
    run_id: str | None = None,
) -> dict:
    """Rename or move one project file."""
    return _handler(project_path, run_id).rename_file(
        rel_path,
        new_rel_path,
        root_name=root_name,
        new_root_name=new_root_name,
    ).to_dict()


@tool(
    name="project_delete_file",
    category=ToolCategory.PROJECT,
    description=(
        "Delete a file inside an initialized .airunner coding project "
        "and audit the write."
    ),
    keywords=["project", "delete", "remove", "file", "audit"],
)
def project_delete_file(
    project_path: str,
    rel_path: str,
    root_name: str | None = None,
    backup: bool = True,
    run_id: str | None = None,
) -> dict:
    """Delete one project-scoped file."""
    return _handler(project_path, run_id).delete_file(
        rel_path,
        root_name=root_name,
        backup=backup,
    ).to_dict()