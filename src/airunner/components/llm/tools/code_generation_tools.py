"""
Code generation tools for LLM-assisted programming.

Provides high-level tools that use the code generation infrastructure
(WorkspaceManager, CodeSession, CodeOperationsHandler, etc.) to enable
AI-assisted code creation, editing, and validation.
"""

from typing import Optional
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
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

# Singleton instances for tools
_workspace_manager: Optional[WorkspaceManager] = None
_code_handler: Optional[CodeOperationsHandler] = None
_code_validator: Optional[CodeValidator] = None
_quality_manager: Optional[CodeQualityManager] = None
_test_runner: Optional[TestRunner] = None


def _get_default_code_directory() -> str:
    """Get the default code directory from PathSettings database or fallback."""
    try:
        from airunner.components.settings.data.path_settings import PathSettings
        path_settings = PathSettings.objects.first()
        if path_settings and path_settings.base_path:
            return str(Path(path_settings.base_path) / "code")
    except Exception:
        pass
    
    # Fallback to settings constant
    try:
        from airunner.settings import AIRUNNER_BASE_PATH
        return str(Path(AIRUNNER_BASE_PATH) / "code")
    except ImportError:
        pass
    
    # Ultimate fallback
    return str(Path.home() / ".local" / "share" / "airunner" / "code")


def _get_workspace_manager(
    workspace_path: Optional[str] = None,
) -> WorkspaceManager:
    """Get or create workspace manager singleton."""
    global _workspace_manager
    if _workspace_manager is None or (
        workspace_path and _workspace_manager.base_path != workspace_path
    ):
        # Default to ~/.local/share/airunner/code/ if not specified
        path = workspace_path or _get_default_code_directory()
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
    _get_workspace_manager(workspace_path)
    if _quality_manager is None:
        handler = _get_code_handler(workspace_path)
        validator = _get_validator(workspace_path)
        _quality_manager = CodeQualityManager(handler, validator)
    return _quality_manager


def _get_test_runner(workspace_path: Optional[str] = None) -> TestRunner:
    """Get or create test runner singleton."""
    global _test_runner
    workspace = _get_workspace_manager(workspace_path)
    workspace_root = str(workspace.base_path) if hasattr(workspace, 'base_path') else workspace_path or _get_default_code_directory()
    if _test_runner is None or _test_runner.workspace_root != Path(workspace_root):
        _test_runner = TestRunner(workspace_root=workspace_root, test_dir=".")
    return _test_runner


def _normalize_content(content: str) -> str:
    """Normalize code content to fix common LLM output issues.
    
    Fixes:
    - Double-escaped newlines (\\n -> \n)
    - Double-escaped tabs (\\t -> \t)
    - Windows line endings (\r\n -> \n)
    
    Args:
        content: Raw content from LLM
        
    """
    if not content:
        return content
    
    # Fix double-escaped sequences (happens with JSON serialization)
    # Only fix if there are escaped newlines but no actual newlines
    if "\\n" in content and "\n" not in content.replace("\\n", ""):
        content = content.replace("\\n", "\n")
        content = content.replace("\\t", "\t")
        content = content.replace("\\r", "\r")
        content = content.replace('\\"', '"')
        content = content.replace("\\'", "'")
    
    # Normalize Windows line endings
    content = content.replace("\r\n", "\n")
    content = content.replace("\r", "\n")
    
    return content


@tool(
    name="create_code_file",
    category=ToolCategory.CODE,
    description=(
        "Create a new code file with the specified content. "
        "REQUIRES an active coding workflow - call start_workflow first! "
        "Automatically creates parent directories if needed. "
        "Use for generating new Python modules, scripts, or configuration files."
    ),
    allowed_callers=["code_execution"],  # Can be called from code sandbox
    input_examples=[
        {"file_path": "src/hello.py", "content": "def hello():\n    print('Hello World')"},
        {"file_path": "tests/test_hello.py", "content": "import pytest\nfrom src.hello import hello"},
    ],
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

    """
    # Check if workflow is in EXECUTION phase with active TODO
    from airunner.components.llm.agents.workflow_tools import require_execution_phase
    workflow_error = require_execution_phase("create_code_file")
    if workflow_error:
        return workflow_error
    
    # Normalize content to fix LLM output issues (e.g., escaped newlines)
    content = _normalize_content(content)
    
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
        "REQUIRES an active coding workflow - call start_workflow first! "
        "Creates a backup before editing. "
        "Use for major refactoring or complete file rewrites."
    ),
    allowed_callers=["code_execution"],  # Can be called from code sandbox
    input_examples=[
        {"file_path": "src/hello.py", "content": "def hello(name: str):\n    print(f'Hello {name}')"},
    ],
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

    """
    # Check if workflow is in EXECUTION phase with active TODO
    from airunner.components.llm.agents.workflow_tools import require_execution_phase
    workflow_error = require_execution_phase("edit_code_file")
    if workflow_error:
        return workflow_error
    
    # Normalize content to fix LLM output issues (e.g., escaped newlines)
    content = _normalize_content(content)
        
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
        "Read the contents of a code file from the workspace. "
        "Returns the full file content with optional line numbers. "
        "Use this to understand existing code before making changes."
    ),
    allowed_callers=["code_execution"],  # Can be called from code sandbox
    input_examples=[
        {"file_path": "src/hello.py"},
        {"file_path": "src/hello.py", "include_line_numbers": True},
    ],
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
    defer_loading=True,  # Optional, discoverable via search_tools
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
    defer_loading=True,  # Optional, discoverable via search_tools
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
        "Run pytest tests on a specific test file or discover tests for a source file. "
        "For TDD: pass your test file directly (e.g., 'test_hello.py'). "
        "Returns pass/fail counts and detailed output."
    ),
    allowed_callers=["code_execution"],  # Can be called from code sandbox
    input_examples=[
        {"file_path": "tests/test_hello.py"},
        {"file_path": "src/hello.py"},  # Will find associated tests
    ],
)
def run_tests(
    file_path: str,
    workspace_path: Optional[str] = None,
) -> str:
    """
    Run tests for a code file.

    Args:
        file_path: Relative path to test file (test_*.py) or source file
        workspace_path: Optional workspace root path

    """
    try:
        test_runner = _get_test_runner(workspace_path)
        
        # If it's a test file, run it directly
        if file_path.startswith("test_") or "/test_" in file_path or file_path.endswith("_test.py"):
            result = test_runner.run_tests(test_files=[file_path], verbose=True)
        else:
            # Otherwise, discover and run related tests
            result = test_runner.run_tests_for_file(file_path)

        summary = [
            f"Tests for {file_path}:",
            f"  Total: {result.total}",
            f"  Passed: {result.passed}",
            f"  Failed: {result.failed}",
        ]

        if result.skipped > 0:
            summary.append(f"  Skipped: {result.skipped}")
        
        if result.errors > 0:
            summary.append(f"  Errors: {result.errors}")

        summary.append(f"  Duration: {result.duration:.2f}s")
        
        # Include relevant output for failures/errors
        if not result.success and result.output:
            summary.append("\n--- Test Output ---")
            # Get last 50 lines of output to show failures
            output_lines = result.output.strip().split('\n')
            if len(output_lines) > 50:
                summary.append("(truncated to last 50 lines)")
                output_lines = output_lines[-50:]
            summary.append('\n'.join(output_lines))

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
    defer_loading=True,  # Discoverable via search_tools
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
    defer_loading=True,  # Rare operation, discoverable via search_tools
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
