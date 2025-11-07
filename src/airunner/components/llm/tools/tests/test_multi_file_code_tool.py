"""Unit tests for MultiFileCodeTool and MultiFileCodeSession."""

import pytest

from airunner.components.llm.tools.multi_file_code_tool import (
    MultiFileCodeSession,
    MultiFileCodeTool,
    FileSpec,
)
from airunner.components.llm.tools.code_session import (
    CodeSessionConfig,
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
def multi_file_tool(temp_workspace):
    """Create MultiFileCodeTool instance."""
    return MultiFileCodeTool(str(temp_workspace))


def test_file_spec_creation():
    """Test FileSpec dataclass."""
    spec = FileSpec(
        rel_path="test.py",
        operation=CodeOperationType.CREATE,
        initial_content="# Test",
    )

    assert spec.rel_path == "test.py"
    assert spec.operation == CodeOperationType.CREATE
    assert spec.initial_content == "# Test"


def test_multi_file_session_creation(workspace_manager):
    """Test MultiFileCodeSession initialization."""
    file_specs = [
        FileSpec("file1.py"),
        FileSpec("file2.py"),
        FileSpec("file3.py"),
    ]

    session = MultiFileCodeSession(
        multi_session_id="test_001",
        workspace=workspace_manager,
        file_specs=file_specs,
    )

    assert session.multi_session_id == "test_001"
    assert len(session.sessions) == 3
    assert "file1.py" in session.sessions
    assert "file2.py" in session.sessions
    assert "file3.py" in session.sessions


def test_receive_token_to_specific_file(workspace_manager):
    """Test sending tokens to a specific file."""
    file_specs = [
        FileSpec("file1.py"),
        FileSpec("file2.py"),
    ]

    session = MultiFileCodeSession(
        multi_session_id="test_002",
        workspace=workspace_manager,
        file_specs=file_specs,
    )

    # Send tokens to file1
    session.receive_token("file1.py", "import")
    session.receive_token("file1.py", " sys\n")

    # Send tokens to file2
    session.receive_token("file2.py", "import")
    session.receive_token("file2.py", " os\n")

    # Check accumulated content
    file1_session = session.get_session("file1.py")
    file2_session = session.get_session("file2.py")

    assert "import sys" in file1_session.get_accumulated_code()
    assert "import os" in file2_session.get_accumulated_code()


def test_complete_single_file(workspace_manager):
    """Test completing a single file in multi-file session."""
    file_specs = [
        FileSpec("file1.py"),
        FileSpec("file2.py"),
    ]

    config = CodeSessionConfig(
        flush_token_count=100,  # High threshold to avoid auto-flush
        auto_format=False,
    )

    session = MultiFileCodeSession(
        multi_session_id="test_003",
        workspace=workspace_manager,
        file_specs=file_specs,
        config=config,
    )

    # Add content to file1
    session.receive_token("file1.py", "print('hello')")

    # Complete file1
    abs_path = session.complete_file("file1.py")

    assert abs_path is not None
    assert abs_path.endswith("file1.py")
    assert session.is_complete("file1.py")
    assert not session.is_complete("file2.py")
    assert not session.are_all_complete()

    # Verify file exists
    assert workspace_manager.exists("file1.py")


def test_complete_all_files(workspace_manager):
    """Test completing all files in multi-file session."""
    file_specs = [
        FileSpec("file1.py"),
        FileSpec("file2.py"),
        FileSpec("file3.py"),
    ]

    config = CodeSessionConfig(flush_token_count=100, auto_format=False)

    session = MultiFileCodeSession(
        multi_session_id="test_004",
        workspace=workspace_manager,
        file_specs=file_specs,
        config=config,
    )

    # Add content to all files
    session.receive_token("file1.py", "# File 1")
    session.receive_token("file2.py", "# File 2")
    session.receive_token("file3.py", "# File 3")

    # Complete all
    completed = session.complete_all()

    assert len(completed) == 3
    assert session.are_all_complete()

    # Verify all files exist
    assert workspace_manager.exists("file1.py")
    assert workspace_manager.exists("file2.py")
    assert workspace_manager.exists("file3.py")


def test_file_flush_callback(workspace_manager):
    """Test file flush callback is called with correct data."""
    flush_events = []

    def on_file_flush(file_path: str, session_id: str, content: str):
        flush_events.append((file_path, session_id, content))

    file_specs = [FileSpec("file1.py")]

    config = CodeSessionConfig(flush_token_count=5)

    session = MultiFileCodeSession(
        multi_session_id="test_005",
        workspace=workspace_manager,
        file_specs=file_specs,
        config=config,
        on_file_flush=on_file_flush,
    )

    # Send enough tokens to trigger flush (5 chars)
    for char in "import sys\n":
        session.receive_token("file1.py", char)

    # Should have triggered at least one flush
    assert len(flush_events) >= 1
    assert flush_events[0][0] == "file1.py"
    # After 5 tokens we get "impor"
    assert "impor" in flush_events[0][2]


def test_file_complete_callback(workspace_manager):
    """Test file completion callback."""
    complete_events = []

    def on_file_complete(file_path: str, session_id: str):
        complete_events.append((file_path, session_id))

    file_specs = [FileSpec("file1.py")]

    config = CodeSessionConfig(auto_format=False)

    session = MultiFileCodeSession(
        multi_session_id="test_006",
        workspace=workspace_manager,
        file_specs=file_specs,
        config=config,
        on_file_complete=on_file_complete,
    )

    session.receive_token("file1.py", "code")
    session.complete_file("file1.py")

    assert len(complete_events) == 1
    assert complete_events[0][0] == "file1.py"


def test_multi_file_tool_create_session(multi_file_tool):
    """Test MultiFileCodeTool session creation."""
    file_specs = [
        FileSpec("app.py"),
        FileSpec("utils.py"),
    ]

    session = multi_file_tool.create_multi_file_session(file_specs)

    assert session is not None
    assert session.multi_session_id.startswith("multi_code_")
    assert len(session.get_file_paths()) == 2


def test_multi_file_tool_get_session(multi_file_tool):
    """Test retrieving sessions from tool."""
    file_specs = [FileSpec("test.py")]

    session = multi_file_tool.create_multi_file_session(
        file_specs, multi_session_id="custom_id"
    )

    retrieved = multi_file_tool.get_multi_session("custom_id")
    assert retrieved is session


def test_multi_file_tool_remove_session(multi_file_tool):
    """Test removing completed sessions."""
    file_specs = [FileSpec("test.py")]

    session = multi_file_tool.create_multi_file_session(
        file_specs, multi_session_id="remove_me"
    )

    # Remove it
    multi_file_tool.remove_multi_session("remove_me")

    # Should be gone
    assert multi_file_tool.get_multi_session("remove_me") is None


def test_multi_file_tool_active_sessions(multi_file_tool):
    """Test filtering active sessions."""
    file_specs1 = [FileSpec("file1.py")]
    file_specs2 = [FileSpec("file2.py")]

    config = CodeSessionConfig(auto_format=False)

    session1 = multi_file_tool.create_multi_file_session(
        file_specs1,
        multi_session_id="active1",
        config=config,
    )

    session2 = multi_file_tool.create_multi_file_session(
        file_specs2,
        multi_session_id="active2",
        config=config,
    )

    # Both active initially
    active = multi_file_tool.get_active_multi_sessions()
    assert len(active) == 2

    # Complete session1
    session1.receive_token("file1.py", "code")
    session1.complete_all()

    # Only session2 should be active
    active = multi_file_tool.get_active_multi_sessions()
    assert len(active) == 1
    assert active[0].multi_session_id == "active2"


def test_initial_content(workspace_manager):
    """Test file specs with initial content."""
    file_specs = [
        FileSpec("file1.py", initial_content="# Header\n"),
    ]

    config = CodeSessionConfig(flush_token_count=100, auto_format=False)

    session = MultiFileCodeSession(
        multi_session_id="test_007",
        workspace=workspace_manager,
        file_specs=file_specs,
        config=config,
    )

    # Add more content
    session.receive_token("file1.py", "print('hello')")

    # Complete
    session.complete_file("file1.py")

    # Check content includes initial and added content
    content = workspace_manager.read_file("file1.py")
    assert "# Header" in content
    assert "print('hello')" in content


def test_invalid_file_path(workspace_manager):
    """Test handling of invalid file path."""
    file_specs = [FileSpec("file1.py")]

    session = MultiFileCodeSession(
        multi_session_id="test_008",
        workspace=workspace_manager,
        file_specs=file_specs,
    )

    # Try to send token to non-existent file
    session.receive_token("nonexistent.py", "code")

    # Should not crash, just log warning
    assert session.get_session("nonexistent.py") is None
