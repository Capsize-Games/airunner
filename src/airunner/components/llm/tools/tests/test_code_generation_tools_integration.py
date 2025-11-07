"""Integration tests for code generation tools."""

import pytest
import tempfile

from airunner.components.llm.tools.code_generation_tools import (
    create_code_file,
    edit_code_file,
    read_code_file,
    validate_code,
    format_code_file,
    list_workspace_files,
    delete_code_file,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_create_and_read_code_file(temp_workspace):
    """Test creating and reading a code file."""
    code = """def hello():
    print("Hello, world!")
"""

    # Create file
    result = create_code_file(
        "test.py",
        code,
        workspace_path=temp_workspace,
    )
    assert "✓ Created file: test.py" in result

    # Read it back
    content = read_code_file("test.py", workspace_path=temp_workspace)
    assert content == code


def test_edit_code_file(temp_workspace):
    """Test editing a code file."""
    original = "def old():\n    pass\n"
    updated = "def new():\n    return 42\n"

    # Create original
    create_code_file("edit_test.py", original, workspace_path=temp_workspace)

    # Edit it
    result = edit_code_file(
        "edit_test.py", updated, workspace_path=temp_workspace
    )
    assert "✓ Edited file: edit_test.py" in result

    # Verify edit
    content = read_code_file("edit_test.py", workspace_path=temp_workspace)
    assert content == updated


def test_validate_valid_code(temp_workspace):
    """Test validating syntactically correct code."""
    code = '''def valid_function(x: int) -> int:
    """A valid function."""
    return x * 2
'''

    create_code_file("valid.py", code, workspace_path=temp_workspace)
    result = validate_code("valid.py", workspace_path=temp_workspace)
    # Should not have errors
    assert "0 errors" in result or "valid" in result.lower()


def test_validate_invalid_code(temp_workspace):
    """Test validating code with syntax errors."""
    code = """def invalid_function(
    # Missing closing parenthesis
    return x * 2
"""

    create_code_file("invalid.py", code, workspace_path=temp_workspace)
    result = validate_code("invalid.py", workspace_path=temp_workspace)
    assert "✗" in result or "error" in result.lower()


def test_list_workspace_files(temp_workspace):
    """Test listing files in workspace."""
    # Create some files
    create_code_file("file1.py", "pass", workspace_path=temp_workspace)
    create_code_file("file2.py", "pass", workspace_path=temp_workspace)
    create_code_file("readme.txt", "text", workspace_path=temp_workspace)

    # List all files
    result = list_workspace_files("*", workspace_path=temp_workspace)
    assert "file1.py" in result
    assert "file2.py" in result
    assert "readme.txt" in result

    # List only Python files
    result = list_workspace_files("*.py", workspace_path=temp_workspace)
    assert "file1.py" in result
    assert "file2.py" in result
    assert "readme.txt" not in result


def test_delete_code_file(temp_workspace):
    """Test deleting a code file."""
    # Create file
    create_code_file("to_delete.py", "pass", workspace_path=temp_workspace)

    # Verify it exists
    content = read_code_file("to_delete.py", workspace_path=temp_workspace)
    assert content == "pass"

    # Delete it
    result = delete_code_file("to_delete.py", workspace_path=temp_workspace)
    assert "✓ Deleted file: to_delete.py" in result

    # Verify it's gone
    content = read_code_file("to_delete.py", workspace_path=temp_workspace)
    assert "Error" in content


def test_format_code_file(temp_workspace):
    """Test formatting a code file."""
    # Poorly formatted code
    code = """def  messy(x,y,z):
  return x+y+z
"""

    create_code_file("messy.py", code, workspace_path=temp_workspace)

    # Format it (will fail if black/isort not available, but shouldn't crash)
    result = format_code_file("messy.py", workspace_path=temp_workspace)
    # Just verify it returns a result
    assert result is not None
    assert isinstance(result, str)


def test_read_nonexistent_file(temp_workspace):
    """Test reading a file that doesn't exist."""
    result = read_code_file("nonexistent.py", workspace_path=temp_workspace)
    assert "Error" in result


def test_create_file_with_subdirectory(temp_workspace):
    """Test creating a file in a subdirectory."""
    code = "# Module file"

    result = create_code_file(
        "src/module.py",
        code,
        workspace_path=temp_workspace,
    )
    assert "✓ Created file: src/module.py" in result

    # Verify it exists
    content = read_code_file("src/module.py", workspace_path=temp_workspace)
    assert content == code
