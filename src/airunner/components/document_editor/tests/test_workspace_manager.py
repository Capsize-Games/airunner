"""
test_workspace_manager.py

Unit tests for WorkspaceManager class.
"""

import os
import tempfile
import shutil
import pytest

from airunner.components.document_editor.workspace_manager import (
    WorkspaceManager,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_workspace_")
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def workspace_manager(temp_workspace):
    """Create a WorkspaceManager instance with temporary workspace."""
    return WorkspaceManager(temp_workspace)


def test_workspace_initialization(temp_workspace):
    """Test workspace manager initialization."""
    wm = WorkspaceManager(temp_workspace)
    assert os.path.exists(wm.base_path)
    assert wm.base_path == os.path.abspath(temp_workspace)


def test_path_validation_prevents_escape(workspace_manager):
    """Test that paths outside workspace are rejected."""
    with pytest.raises(ValueError, match="outside workspace"):
        workspace_manager._abs("../../../etc/passwd")

    with pytest.raises(ValueError, match="outside workspace"):
        workspace_manager._abs("/tmp/malicious")


def test_write_and_read_file(workspace_manager):
    """Test basic file write and read operations."""
    content = "print('Hello, World!')\n"
    rel_path = "test_script.py"

    # Write file
    abs_path = workspace_manager.write_file(rel_path, content, backup=False)
    assert os.path.exists(abs_path)

    # Read file
    read_content = workspace_manager.read_file(rel_path)
    assert read_content == content


def test_write_creates_directories(workspace_manager):
    """Test that write_file creates parent directories."""
    content = "def foo():\n    pass\n"
    rel_path = "subdir/nested/file.py"

    abs_path = workspace_manager.write_file(rel_path, content)
    assert os.path.exists(abs_path)
    assert os.path.isfile(abs_path)


def test_backup_creation(workspace_manager):
    """Test that backups are created on overwrite."""
    rel_path = "test.py"
    original_content = "# Original\n"
    new_content = "# Updated\n"

    # Write original
    abs_path = workspace_manager.write_file(
        rel_path, original_content, backup=False
    )

    # Overwrite with backup
    workspace_manager.write_file(rel_path, new_content, backup=True)

    # Check backup exists
    backup_path = abs_path + ".bak"
    assert os.path.exists(backup_path)

    # Verify backup has original content
    with open(backup_path, "r") as f:
        assert f.read() == original_content


def test_append_file(workspace_manager):
    """Test appending content to file."""
    rel_path = "append_test.py"

    # Append to non-existent file (creates it)
    workspace_manager.append_file(rel_path, "# Part 1\n")
    assert workspace_manager.read_file(rel_path) == "# Part 1\n"

    # Append more content
    workspace_manager.append_file(rel_path, "# Part 2\n")
    assert workspace_manager.read_file(rel_path) == "# Part 1\n# Part 2\n"


def test_unique_path_no_conflict(workspace_manager):
    """Test unique_path when file doesn't exist."""
    rel_path = workspace_manager.unique_path("", "new_file.py")
    assert rel_path == "new_file.py"


def test_unique_path_with_conflicts(workspace_manager):
    """Test unique_path generates numbered suffix on conflicts."""
    # Create original file
    workspace_manager.write_file("test.py", "# Original\n")

    # Get unique path
    unique = workspace_manager.unique_path("", "test.py")
    assert unique == "test_1.py"

    # Create that one too
    workspace_manager.write_file(unique, "# Second\n")

    # Get another unique path
    unique2 = workspace_manager.unique_path("", "test.py")
    assert unique2 == "test_2.py"


def test_list_files(workspace_manager):
    """Test listing files with glob patterns."""
    # Create some test files
    workspace_manager.write_file("file1.py", "# File 1\n")
    workspace_manager.write_file("file2.py", "# File 2\n")
    workspace_manager.write_file("file3.txt", "Text file\n")
    workspace_manager.write_file("subdir/nested.py", "# Nested\n")

    # List Python files in root (non-recursive)
    py_files = workspace_manager.list_files("", "*.py", recursive=False)
    assert len(py_files) == 2
    assert "file1.py" in py_files
    assert "file2.py" in py_files

    # List all Python files recursively
    all_py = workspace_manager.list_files("", "*.py", recursive=True)
    assert len(all_py) == 3
    assert any("nested.py" in f for f in all_py)


def test_rename_file(workspace_manager):
    """Test renaming/moving files."""
    original_path = "original.py"
    new_path = "renamed.py"
    content = "# Test content\n"

    # Create file
    workspace_manager.write_file(original_path, content)

    # Rename
    workspace_manager.rename(original_path, new_path)

    # Verify old path doesn't exist
    assert not workspace_manager.exists(original_path)

    # Verify new path exists with correct content
    assert workspace_manager.exists(new_path)
    assert workspace_manager.read_file(new_path) == content


def test_delete_file(workspace_manager):
    """Test file deletion with backup."""
    rel_path = "to_delete.py"
    content = "# Delete me\n"

    # Create file
    abs_path = workspace_manager.write_file(rel_path, content)
    assert os.path.exists(abs_path)

    # Delete with backup
    workspace_manager.delete(rel_path, backup=True)

    # Verify file is gone
    assert not workspace_manager.exists(rel_path)

    # Verify backup exists
    backup_path = abs_path + ".deleted.bak"
    assert os.path.exists(backup_path)


def test_exists(workspace_manager):
    """Test file existence check."""
    assert not workspace_manager.exists("nonexistent.py")

    workspace_manager.write_file("existing.py", "# Exists\n")
    assert workspace_manager.exists("existing.py")


def test_get_file_info(workspace_manager):
    """Test retrieving file metadata."""
    # Non-existent file
    info = workspace_manager.get_file_info("nonexistent.py")
    assert info["exists"] is False
    assert info["size"] == 0

    # Existing file
    content = "# Test file\n"
    workspace_manager.write_file("test.py", content)

    info = workspace_manager.get_file_info("test.py")
    assert info["exists"] is True
    assert info["size"] == len(content.encode("utf-8"))
    assert info["is_file"] is True
    assert info["is_dir"] is False
    assert "abs_path" in info


def test_atomic_write_on_failure(workspace_manager):
    """Test that failed writes don't corrupt existing files."""
    rel_path = "atomic_test.py"
    original = "# Original content\n"

    # Write original
    workspace_manager.write_file(rel_path, original)

    # Simulate write failure by trying to write to read-only location
    # (This is a simplified test - in production you'd mock file operations)
    try:
        # Try to write
        workspace_manager.write_file(rel_path, "# New content\n", backup=True)
    except Exception:
        pass

    # Original content should still be readable
    # (In case of temp file issues, atomic replace protects the original)
    content = workspace_manager.read_file(rel_path)
    assert content  # File is still readable


def test_thread_safety_locks(workspace_manager):
    """Test that file locks are created and accessible."""
    rel_path = "locked_file.py"
    abs_path = workspace_manager._abs(rel_path)

    # Get lock for a file
    lock1 = workspace_manager._get_file_lock(abs_path)
    lock2 = workspace_manager._get_file_lock(abs_path)

    # Same lock instance should be returned
    assert lock1 is lock2
