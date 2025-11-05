"""
Code generation tools for LLM-assisted programming.

Provides high-level tools that use the code generation infrastructure
(WorkspaceManager, CodeSession, CodeOperationsHandler, etc.) to enable
AI-assisted code creation, editing, and validation.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.llm.tools.code_operations_handler import (
    CodeOperationsHandler,
)
from airunner.components.llm.tools.code_validator import CodeValidator
from airunner.components.llm.tools.code_quality_manager import (
    CodeQualityManager,
)
from airunner.components.llm.tools.test_runner import TestRunner
from airunner.components.document_editor.workspace_manager import (
    WorkspaceManager,
)
from airunner.enums import CodeOperationType

logger = logging.getLogger(__name__)

# Singleton instances for tools
_workspace_manager: Optional[WorkspaceManager] = None
_code_handler: Optional[CodeOperationsHandler] = None
_code_validator: Optional[CodeValidator] = None
_quality_manager: Optional[CodeQualityManager] = None
_test_runner: Optional[TestRunner] = None


def _get_workspace_manager(
    workspace_path: Optional[str] = None,
) -> WorkspaceManager:
    """Get or create workspace manager singleton."""
    global _workspace_manager
    if _workspace_manager is None or (
        workspace_path and _workspace_manager.base_path != workspace_path
    ):
        # Default to ~/airunner_workspace if not specified
        path = workspace_path or str(Path.home() / "airunner_workspace")
        _workspace_manager = WorkspaceManager(path)
        logger.info(f"Initialized workspace manager at: {path}")
    return _workspace_manager


def _get_code_handler(
    workspace_path: Optional[str] = None,
) -> CodeOperationsHandler:
    """Get or create code operations handler singleton."""
    global _code_handler
    workspace = _get_workspace_manager(workspace_path)
    if _code_handler is None or _code_handler.workspace != workspace:
        _code_handler = CodeOperationsHandler(workspace)
    return _code_handler


def _get_validator(workspace_path: Optional[str] = None) -> CodeValidator:
    """Get or create code validator singleton."""
    global _code_validator
    workspace = _get_workspace_manager(workspace_path)
    if _code_validator is None or _code_validator.workspace != workspace:
        _code_validator = CodeValidator(workspace)
    return _code_validator


def _get_quality_manager(
    workspace_path: Optional[str] = None,
) -> CodeQualityManager:
    """Get or create quality manager singleton."""
    global _quality_manager
    workspace = _get_workspace_manager(workspace_path)
    if _quality_manager is None:
        handler = _get_code_handler(workspace_path)
        validator = _get_validator(workspace_path)
        _quality_manager = CodeQualityManager(handler, validator)
    return _quality_manager


def _get_test_runner(workspace_path: Optional[str] = None) -> TestRunner:
    """Get or create test runner singleton."""
    global _test_runner
    workspace = _get_workspace_manager(workspace_path)
    if _test_runner is None or _test_runner.workspace != workspace:
        _test_runner = TestRunner(workspace)
    return _test_runner


@tool(
    name="create_code_file",
    category=ToolCategory.CODE,
    description=(
        "Create a new code file with the specified content. "
        "Automatically creates parent directories if needed. "
        "Use for generating new Python modules, scripts, or configuration files."
    ),
)
def create_code_file(
    file_path: str,
    content: str,
    workspace_path: Optional[str] = None,
    create_backup: bool = True,
) -> str:
    """
    Create a new code file.

    Args:
        file_path: Relative path to the file (e.g., "src/module.py")
        content: File content
        workspace_path: Optional workspace root path
        create_backup: Whether to create backup if file exists

    Returns:
        Success message or error description
    """
    try:
        handler = _get_code_handler(workspace_path)
        result = handler.execute(
            operation=CodeOperationType.CREATE,
            rel_path=file_path,
            content=content,
            backup=create_backup,
        )

        if result.success:
            return f"✓ Created file: {file_path}\n{result.message}"
        else:
            return f"✗ Failed to create {file_path}: {result.error}"

    except Exception as e:
        logger.error(f"Error creating file {file_path}: {e}")
        return f"Error: {str(e)}"


@tool(
    name="edit_code_file",
    category=ToolCategory.CODE,
    description=(
        "Replace the entire content of an existing code file. "
        "Creates a backup before editing. "
        "Use for major refactoring or complete file rewrites."
    ),
)
def edit_code_file(
    file_path: str,
    content: str,
    workspace_path: Optional[str] = None,
    create_backup: bool = True,
) -> str:
    """
    Edit an existing code file.

    Args:
        file_path: Relative path to the file
        content: New file content
        workspace_path: Optional workspace root path
        create_backup: Whether to create backup before editing

    Returns:
        Success message or error description
    """
    try:
        handler = _get_code_handler(workspace_path)
        result = handler.execute(
            operation=CodeOperationType.EDIT,
            rel_path=file_path,
            content=content,
            backup=create_backup,
        )

        if result.success:
            return f"✓ Edited file: {file_path}\n{result.message}"
        else:
            return f"✗ Failed to edit {file_path}: {result.error}"

    except Exception as e:
        logger.error(f"Error editing file {file_path}: {e}")
        return f"Error: {str(e)}"


@tool(
    name="read_code_file",
    category=ToolCategory.CODE,
    description=(
        "Read the content of a code file. "
        "Use to examine existing code before making changes or to understand "
        "the current implementation."
    ),
)
def read_code_file(
    file_path: str,
    workspace_path: Optional[str] = None,
) -> str:
    """
    Read a code file.

    Args:
        file_path: Relative path to the file
        workspace_path: Optional workspace root path

    Returns:
        File content or error message
    """
    try:
        handler = _get_code_handler(workspace_path)
        result = handler.execute(
            operation=CodeOperationType.READ,
            rel_path=file_path,
        )

        if result.success:
            return result.content or ""
        else:
            return f"Error reading {file_path}: {result.error}"

    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return f"Error: {str(e)}"


@tool(
    name="validate_code",
    category=ToolCategory.CODE,
    description=(
        "Validate Python code for syntax errors, style issues, and type problems. "
        "Uses flake8 for style checking and mypy for type checking. "
        "Returns detailed validation results with line numbers and issue descriptions."
    ),
)
def validate_code(
    file_path: str,
    workspace_path: Optional[str] = None,
) -> str:
    """
    Validate a Python file.

    Args:
        file_path: Relative path to the file
        workspace_path: Optional workspace root path

    Returns:
        Validation results summary
    """
    try:
        validator = _get_validator(workspace_path)
        result = validator.validate_file(file_path)

        if result.success:
            msg = f"✓ {file_path} is valid"
            if result.warning_count > 0:
                msg += f" ({result.warning_count} warnings)"
            return msg
        else:
            summary = [f"✗ {file_path} has {result.error_count} errors"]
            if result.warning_count > 0:
                summary.append(f"  Warnings: {result.warning_count}")

            # Show first few errors
            error_issues = [i for i in result.issues if i.severity == "error"]
            for issue in error_issues[:5]:
                summary.append(f"  Line {issue.line}: {issue.message}")

            if len(error_issues) > 5:
                summary.append(
                    f"  ... and {len(error_issues) - 5} more errors"
                )

            return "\n".join(summary)

    except Exception as e:
        logger.error(f"Error validating file {file_path}: {e}")
        return f"Error: {str(e)}"


@tool(
    name="format_code_file",
    category=ToolCategory.CODE,
    description=(
        "Format a Python file according to PEP 8 using Black formatter. "
        "Also runs isort to organize imports. "
        "Creates a backup before formatting."
    ),
)
def format_code_file(
    file_path: str,
    workspace_path: Optional[str] = None,
    create_backup: bool = True,
) -> str:
    """
    Format a code file.

    Args:
        file_path: Relative path to the file
        workspace_path: Optional workspace root path
        create_backup: Whether to create backup before formatting

    Returns:
        Formatting result message
    """
    try:
        handler = _get_code_handler(workspace_path)
        result = handler.format_file(file_path, backup=create_backup)

        if result.success:
            return f"✓ Formatted {file_path}\n{result.message}"
        else:
            return f"✗ Failed to format {file_path}: {result.error}"

    except Exception as e:
        logger.error(f"Error formatting file {file_path}: {e}")
        return f"Error: {str(e)}"


@tool(
    name="run_tests",
    category=ToolCategory.CODE,
    description=(
        "Discover and run pytest tests for a code file. "
        "Automatically finds corresponding test files and executes them. "
        "Returns test results with pass/fail counts and failure details."
    ),
)
def run_tests(
    file_path: str,
    workspace_path: Optional[str] = None,
) -> str:
    """
    Run tests for a code file.

    Args:
        file_path: Relative path to the code file
        workspace_path: Optional workspace root path

    Returns:
        Test results summary
    """
    try:
        test_runner = _get_test_runner(workspace_path)
        result = test_runner.run_tests_for_file(file_path)

        summary = [
            f"Tests for {file_path}:",
            f"  Total: {result.total}",
            f"  Passed: {result.passed}",
            f"  Failed: {result.failed}",
        ]

        if result.skipped > 0:
            summary.append(f"  Skipped: {result.skipped}")

        if result.failures:
            summary.append("\nFailures:")
            for failure in result.failures[:3]:
                summary.append(f"  - {failure}")
            if len(result.failures) > 3:
                summary.append(f"  ... and {len(result.failures) - 3} more")

        return "\n".join(summary)

    except Exception as e:
        logger.error(f"Error running tests for {file_path}: {e}")
        return f"Error: {str(e)}"


@tool(
    name="list_workspace_files",
    category=ToolCategory.CODE,
    description=(
        "List files in the workspace directory. "
        "Supports glob patterns for filtering (e.g., '*.py' for Python files). "
        "Use to explore the workspace structure."
    ),
)
def list_workspace_files(
    pattern: str = "**/*",
    workspace_path: Optional[str] = None,
) -> str:
    """
    List files in workspace.

    Args:
        pattern: Glob pattern for filtering (default: all files)
        workspace_path: Optional workspace root path

    Returns:
        List of matching files
    """
    try:
        handler = _get_code_handler(workspace_path)
        result = handler.execute(
            operation=CodeOperationType.LIST,
            rel_path=pattern,  # pattern is passed as rel_path
        )

        if result.success and result.content:
            files = result.content.split("\n")
            return f"Found {len(files)} files:\n" + "\n".join(
                f"  {f}" for f in files[:20]
            )
        elif result.success:
            return "No files found matching pattern"
        else:
            return f"Error listing files: {result.error}"

    except Exception as e:
        logger.error(f"Error listing workspace files: {e}")
        return f"Error: {str(e)}"


@tool(
    name="delete_code_file",
    category=ToolCategory.CODE,
    description=(
        "Delete a code file from the workspace. "
        "Creates a backup before deletion. "
        "Use with caution - this operation cannot be easily undone."
    ),
)
def delete_code_file(
    file_path: str,
    workspace_path: Optional[str] = None,
    create_backup: bool = True,
) -> str:
    """
    Delete a code file.

    Args:
        file_path: Relative path to the file
        workspace_path: Optional workspace root path
        create_backup: Whether to create backup before deletion

    Returns:
        Success message or error description
    """
    try:
        handler = _get_code_handler(workspace_path)
        result = handler.execute(
            operation=CodeOperationType.DELETE,
            rel_path=file_path,
            backup=create_backup,
        )

        if result.success:
            return f"✓ Deleted file: {file_path}\n{result.message}"
        else:
            return f"✗ Failed to delete {file_path}: {result.error}"

    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return f"Error: {str(e)}"
