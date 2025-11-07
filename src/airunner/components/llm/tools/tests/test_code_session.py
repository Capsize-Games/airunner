"""Unit tests for CodeSession and CodeSessionManager."""

import time
import pytest

from airunner.components.llm.tools.code_session import (
    CodeSession,
    CodeSessionConfig,
    CodeSessionManager,
)
from airunner.components.document_editor.workspace_manager import (
    WorkspaceManager,
)
from airunner.enums import CodeOperationType


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace directory."""
    workspace_dir = tmp_path / "test_workspace"
    workspace_dir.mkdir()
    return workspace_dir


@pytest.fixture
def workspace_manager(temp_workspace):
    """Create WorkspaceManager instance."""
    return WorkspaceManager(str(temp_workspace))


@pytest.fixture
def session_manager(workspace_manager):
    """Create CodeSessionManager instance."""
    return CodeSessionManager(workspace_manager)


def test_session_initialization(workspace_manager):
    """Test CodeSession initialization."""
    session = CodeSession(
        session_id="test_001",
        workspace=workspace_manager,
        rel_path="test.py",
        operation=CodeOperationType.CREATE,
    )

    assert session.session_id == "test_001"
    assert session.rel_path == "test.py"
    assert session.operation == CodeOperationType.CREATE
    assert not session.is_complete
    assert session.get_char_count() == 0
    assert session.get_line_count() == 1  # Empty string has 1 line


def test_receive_and_buffer_tokens(workspace_manager):
    """Test token buffering without flushing."""
    config = CodeSessionConfig(flush_token_count=100)  # High threshold

    session = CodeSession(
        session_id="test_002",
        workspace=workspace_manager,
        rel_path="test.py",
        operation=CodeOperationType.CREATE,
        config=config,
    )

    # Send tokens that won't trigger flush
    session.receive_token("def ")
    session.receive_token("hello")
    session.receive_token("():\n")

    # Should be buffered but not flushed
    assert session.get_accumulated_code() == "def hello():\n"

    # File shouldn't exist yet (not flushed)
    assert not workspace_manager.exists("test.py")


def test_flush_on_token_count(workspace_manager):
    """Test automatic flush when token count threshold reached."""
    config = CodeSessionConfig(
        flush_token_count=3, flush_interval_seconds=100.0
    )

    session = CodeSession(
        session_id="test_003",
        workspace=workspace_manager,
        rel_path="test.py",
        operation=CodeOperationType.CREATE,
        config=config,
    )

    # Send 3 tokens (should trigger flush)
    session.receive_token("import ")
    session.receive_token("sys\n")
    session.receive_token("import ")

    # Should be flushed to file
    content = workspace_manager.read_file("test.py")
    assert content == "import sys\nimport "


def test_flush_on_time_interval(workspace_manager):
    """Test automatic flush when time interval exceeded."""
    config = CodeSessionConfig(
        flush_token_count=100, flush_interval_seconds=0.05
    )

    session = CodeSession(
        session_id="test_004",
        workspace=workspace_manager,
        rel_path="test.py",
        operation=CodeOperationType.CREATE,
        config=config,
    )

    # Send one token
    session.receive_token("import sys\n")

    # Wait for time interval
    time.sleep(0.1)

    # Send another token (should trigger time-based flush)
    session.receive_token("import os\n")

    # Should be flushed
    content = workspace_manager.read_file("test.py")
    assert "import sys\n" in content


def test_flush_callback(workspace_manager):
    """Test flush callback is called with correct data."""
    callback_data = []

    def on_flush(abs_path: str, content: str):
        callback_data.append((abs_path, content))

    config = CodeSessionConfig(flush_token_count=2)

    session = CodeSession(
        session_id="test_005",
        workspace=workspace_manager,
        rel_path="test.py",
        operation=CodeOperationType.CREATE,
        config=config,
        on_flush=on_flush,
    )

    # Trigger flush
    session.receive_token("line1\n")
    session.receive_token("line2\n")

    # Callback should have been called
    assert len(callback_data) == 1
    abs_path, content = callback_data[0]
    assert abs_path.endswith("test.py")
    assert content == "line1\nline2\n"


def test_complete_session(workspace_manager):
    """Test session completion."""
    session = CodeSession(
        session_id="test_006",
        workspace=workspace_manager,
        rel_path="test.py",
        operation=CodeOperationType.CREATE,
    )

    # Add some code
    session.receive_token("def test():\n")
    session.receive_token("    return 42\n")

    # Complete session
    abs_path = session.complete()

    assert session.is_complete
    assert abs_path.endswith("test.py")

    # File should exist with content
    content = workspace_manager.read_file("test.py")
    assert "def test():" in content
    assert "return 42" in content


def test_strip_markdown_blocks(workspace_manager):
    """Test markdown code block stripping."""
    config = CodeSessionConfig(strip_markdown=True, flush_token_count=100)

    session = CodeSession(
        session_id="test_007",
        workspace=workspace_manager,
        rel_path="test.py",
        operation=CodeOperationType.CREATE,
        config=config,
    )

    # Send code with markdown
    session.receive_token("```python\n")
    session.receive_token("def hello():\n")
    session.receive_token("    print('hi')\n")
    session.receive_token("```")

    # Complete to trigger cleanup
    session.complete()

    # Markdown should be stripped
    content = workspace_manager.read_file("test.py")
    assert "```python" not in content
    assert "```" not in content
    assert "def hello():" in content
    # Note: black may change quotes from 'hi' to "hi"
    assert "print(" in content and "hi" in content


def test_get_line_count(workspace_manager):
    """Test line count tracking."""
    session = CodeSession(
        session_id="test_008",
        workspace=workspace_manager,
        rel_path="test.py",
        operation=CodeOperationType.CREATE,
    )

    assert session.get_line_count() == 1  # Empty = 1 line

    session.receive_token("line1\n")
    assert session.get_line_count() == 2

    session.receive_token("line2\n")
    assert session.get_line_count() == 3


def test_session_manager_create(session_manager):
    """Test CodeSessionManager creates sessions with unique IDs."""
    session1 = session_manager.create_session("file1.py")
    session2 = session_manager.create_session("file2.py")

    assert session1.session_id != session2.session_id
    assert session1.rel_path == "file1.py"
    assert session2.rel_path == "file2.py"


def test_session_manager_get_session(session_manager):
    """Test retrieving sessions by ID."""
    session = session_manager.create_session("test.py")

    retrieved = session_manager.get_session(session.session_id)
    assert retrieved is session

    # Non-existent session
    assert session_manager.get_session("nonexistent") is None


def test_session_manager_remove_session(session_manager):
    """Test removing completed sessions."""
    session = session_manager.create_session("test.py")
    session_id = session.session_id

    # Session should exist
    assert session_manager.get_session(session_id) is not None

    # Remove it
    session_manager.remove_session(session_id)

    # Should be gone
    assert session_manager.get_session(session_id) is None


def test_session_manager_get_active_sessions(session_manager):
    """Test filtering active sessions."""
    session1 = session_manager.create_session("file1.py")
    session2 = session_manager.create_session("file2.py")

    # Both active
    active = session_manager.get_active_sessions()
    assert len(active) == 2

    # Complete one
    session1.receive_token("test")
    session1.complete()

    # Only one active
    active = session_manager.get_active_sessions()
    assert len(active) == 1
    assert active[0].session_id == session2.session_id


def test_session_manager_complete_all(session_manager):
    """Test completing all active sessions."""
    session1 = session_manager.create_session("file1.py")
    session2 = session_manager.create_session("file2.py")

    session1.receive_token("code1")
    session2.receive_token("code2")

    # Complete all
    session_manager.complete_all()

    # Both should be complete
    assert session1.is_complete
    assert session2.is_complete

    # No active sessions
    assert len(session_manager.get_active_sessions()) == 0


def test_ignore_tokens_after_complete(workspace_manager):
    """Test that tokens are ignored after session is complete."""
    session = CodeSession(
        session_id="test_009",
        workspace=workspace_manager,
        rel_path="test.py",
        operation=CodeOperationType.CREATE,
    )

    session.receive_token("first")
    session.complete()

    # Try to add more tokens
    session.receive_token("ignored")

    # Should still only have "first" (may have trailing newline from black)
    content = workspace_manager.read_file("test.py")
    assert content.strip() == "first"
    assert "ignored" not in content


def test_backup_creation_on_write(workspace_manager):
    """Test backup files are created when overwriting."""
    config = CodeSessionConfig(create_backup=True, flush_token_count=1)

    # Create initial file
    workspace_manager.write_file("test.py", "original content")

    # Create session that will overwrite
    session = CodeSession(
        session_id="test_010",
        workspace=workspace_manager,
        rel_path="test.py",
        operation=CodeOperationType.EDIT,
        config=config,
    )

    session.receive_token("new content")

    # Backup should exist
    assert workspace_manager.exists("test.py.bak")
    backup_content = workspace_manager.read_file("test.py.bak")
    assert backup_content == "original content"

    # Main file should have new content
    content = workspace_manager.read_file("test.py")
    assert content == "new content"
