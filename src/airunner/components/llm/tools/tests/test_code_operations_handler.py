"""
Tests for code_operations_handler.py

Test all code operation types (CREATE, READ, EDIT, PATCH, APPEND, RENAME, DELETE, LIST, FORMAT)
"""

import pytest

from airunner.components.document_editor.workspace_manager import (
    WorkspaceManager,
)
from airunner.components.llm.tools.code_operations_handler import (
    CodeOperationsHandler,
    CodeOperationResult,
)
from airunner.enums import CodeOperationType


@pytest.fixture
def workspace_dir(tmp_path):
    """Create temporary workspace directory."""
    return tmp_path / "workspace"


@pytest.fixture
def workspace(workspace_dir):
    """Create WorkspaceManager instance."""
    workspace_dir.mkdir(exist_ok=True)
    return WorkspaceManager(str(workspace_dir))


@pytest.fixture
def handler(workspace):
    """Create CodeOperationsHandler instance."""
    return CodeOperationsHandler(workspace)


def test_create_new_file(handler):
    """Test creating a new file."""
    result = handler.create("test.py", "print('hello')")

    assert result.success is True
    assert result.operation == CodeOperationType.CREATE
    assert result.content == "print('hello')"
    assert "Created file" in result.message


def test_read_existing_file(handler):
    """Test reading an existing file."""
    handler.create("test.py", "content")

    result = handler.read("test.py")

    assert result.success is True
    assert result.operation == CodeOperationType.READ
    assert result.content == "content"
    assert "Read file" in result.message


def test_read_nonexistent_file(handler):
    """Test reading a file that doesn't exist."""
    result = handler.read("missing.py")

    assert result.success is False
    assert result.operation == CodeOperationType.READ
    assert "does not exist" in result.error


def test_edit_existing_file(handler):
    """Test editing an existing file."""
    handler.create("test.py", "old content")

    result = handler.edit("test.py", "new content", backup=False)

    assert result.success is True
    assert result.operation == CodeOperationType.EDIT
    assert result.content == "new content"
    assert "Edited file" in result.message


def test_edit_nonexistent_file(handler):
    """Test editing a file that doesn't exist."""
    result = handler.edit("missing.py", "content")

    assert result.success is False
    assert result.operation == CodeOperationType.EDIT
    assert "does not exist" in result.error


def test_append_to_file(handler):
    """Test appending content to a file."""
    handler.create("test.py", "line 1\n")

    result = handler.append("test.py", "line 2\n")

    assert result.success is True
    assert result.operation == CodeOperationType.APPEND
    assert result.content == "line 1\nline 2\n"
    assert "Appended" in result.message


def test_append_creates_file_if_missing(handler):
    """Test appending creates file if it doesn't exist."""
    result = handler.append("new.py", "content\n")

    assert result.success is True
    assert result.operation == CodeOperationType.APPEND
    assert result.content == "content\n"


def test_rename_file(handler):
    """Test renaming a file."""
    handler.create("old.py", "content")

    result = handler.rename("old.py", "new.py")

    assert result.success is True
    assert result.operation == CodeOperationType.RENAME
    assert "Renamed" in result.message

    # Verify old file doesn't exist, new file does
    assert not handler.workspace.exists("old.py")
    assert handler.workspace.exists("new.py")


def test_rename_nonexistent_file(handler):
    """Test renaming a file that doesn't exist."""
    result = handler.rename("missing.py", "new.py")

    assert result.success is False
    assert result.operation == CodeOperationType.RENAME
    assert "does not exist" in result.error


def test_rename_without_new_path(handler):
    """Test renaming without providing new_path."""
    handler.create("test.py", "content")

    result = handler.rename("test.py", None)

    assert result.success is False
    assert result.operation == CodeOperationType.RENAME
    assert "new_path is required" in result.error


def test_delete_file(handler):
    """Test deleting a file."""
    handler.create("test.py", "content")

    result = handler.delete("test.py", backup=False)

    assert result.success is True
    assert result.operation == CodeOperationType.DELETE
    assert "Deleted file" in result.message

    # Verify file is gone
    assert not handler.workspace.exists("test.py")


def test_delete_nonexistent_file(handler):
    """Test deleting a file that doesn't exist."""
    result = handler.delete("missing.py")

    assert result.success is False
    assert result.operation == CodeOperationType.DELETE
    assert "does not exist" in result.error


def test_list_files(handler):
    """Test listing files."""
    handler.create("test1.py", "")
    handler.create("test2.py", "")
    handler.create("subdir/test3.py", "")

    result = handler.list_files("**/*.py")

    assert result.success is True
    assert result.operation == CodeOperationType.LIST
    assert "Found 3 files" in result.message
    assert "test1.py" in result.content
    assert "test2.py" in result.content
    assert "subdir/test3.py" in result.content


def test_list_files_with_pattern(handler):
    """Test listing files with specific pattern."""
    handler.create("test.py", "")
    handler.create("example.py", "")
    handler.create("data.json", "")

    result = handler.list_files("test*.py")

    assert result.success is True
    assert result.operation == CodeOperationType.LIST
    assert "Found 1 files" in result.message
    assert "test.py" in result.content
    assert "example.py" not in result.content


def test_patch_file(handler):
    """Test patching a file (simplified implementation)."""
    handler.create("test.py", "line 1\nline 2\n")

    patch = "--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,3 @@\n line 1\n+line 1.5\n line 2\n"

    result = handler.patch("test.py", patch, backup=False)

    assert result.success is True
    assert result.operation == CodeOperationType.PATCH
    assert "Applied patch" in result.message
    # Note: Current implementation just appends patch as comment
    assert "PATCH APPLIED" in result.content


def test_patch_nonexistent_file(handler):
    """Test patching a file that doesn't exist."""
    result = handler.patch("missing.py", "patch content")

    assert result.success is False
    assert result.operation == CodeOperationType.PATCH
    assert "does not exist" in result.error


def test_format_file_no_formatters(handler):
    """Test formatting when black/isort are not available."""
    handler.create("test.py", "x=1\n")

    # File should exist and be readable, even if formatters aren't installed
    # The format_file method gracefully handles missing formatters
    result = handler.format_file("test.py", backup=False)

    # Should succeed (formatters are optional)
    assert result.success is True
    assert result.operation == CodeOperationType.FORMAT


def test_format_nonexistent_file(handler):
    """Test formatting a file that doesn't exist."""
    result = handler.format_file("missing.py")

    assert result.success is False
    assert result.operation == CodeOperationType.FORMAT
    assert "does not exist" in result.error


def test_execute_dispatch_create(handler):
    """Test execute() dispatches CREATE correctly."""
    result = handler.execute(CodeOperationType.CREATE, "test.py", "content")

    assert result.success is True
    assert result.operation == CodeOperationType.CREATE


def test_execute_dispatch_read(handler):
    """Test execute() dispatches READ correctly."""
    handler.create("test.py", "content")

    result = handler.execute(CodeOperationType.READ, "test.py")

    assert result.success is True
    assert result.operation == CodeOperationType.READ
    assert result.content == "content"


def test_execute_dispatch_append(handler):
    """Test execute() dispatches APPEND correctly."""
    result = handler.execute(CodeOperationType.APPEND, "test.py", "content")

    assert result.success is True
    assert result.operation == CodeOperationType.APPEND


def test_execute_dispatch_rename(handler):
    """Test execute() dispatches RENAME correctly."""
    handler.create("old.py", "content")

    result = handler.execute(
        CodeOperationType.RENAME, "old.py", new_path="new.py"
    )

    assert result.success is True
    assert result.operation == CodeOperationType.RENAME


def test_execute_dispatch_delete(handler):
    """Test execute() dispatches DELETE correctly."""
    handler.create("test.py", "content")

    result = handler.execute(CodeOperationType.DELETE, "test.py", backup=False)

    assert result.success is True
    assert result.operation == CodeOperationType.DELETE


def test_execute_unknown_operation(handler):
    """Test execute() handles unknown operation."""

    # Create a mock invalid operation
    class FakeOperation:
        value = "INVALID"

    result = handler.execute(FakeOperation(), "test.py", "content")

    assert result.success is False
    assert "Unknown operation" in result.error


def test_code_operation_result_str(handler):
    """Test CodeOperationResult string representation."""
    result = CodeOperationResult(
        success=True,
        operation=CodeOperationType.CREATE,
        file_path="test.py",
        message="Created successfully",
    )

    result_str = str(result)
    assert "✓" in result_str
    assert "create" in result_str.lower()
    assert "test.py" in result_str
    assert "Created successfully" in result_str


def test_code_operation_result_str_failure(handler):
    """Test CodeOperationResult string representation for failure."""
    result = CodeOperationResult(
        success=False,
        operation=CodeOperationType.READ,
        file_path="missing.py",
        error="File not found",
    )

    result_str = str(result)
    assert "✗" in result_str
    assert "read" in result_str.lower()
    assert "missing.py" in result_str
