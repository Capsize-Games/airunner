"""Focused tests for the coding workspace shell container."""

import os
import sys
import time

import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication, QTabWidget

from airunner.components.agents.runtime import AgentBackgroundRunManager
from airunner.components.agents.runtime import AgentRole
from airunner.components.agents.runtime import AgentSessionRecord
from airunner.components.agents.runtime import AgentTaskRecord
from airunner.components.application.gui.widgets import base_widget as base_widget_module
from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.document_editor.project import (
    AirunnerProjectSettings,
    AirunnerProjectStateService,
    AirunnerPythonEnvironmentSelection,
)
from airunner.components.document_editor.project import airunner_active_project
from airunner.components.document_editor.gui.widgets import (
    document_editor_widget as document_editor_widget_module,
)
from airunner.components.document_editor.workspace_manager import (
    WorkspaceManager,
)

from airunner.components.document_editor.gui.widgets.document_editor_container_widget import (
    DocumentEditorContainerWidget,
)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytestmark = pytest.mark.gui


def _get_app() -> QApplication:
    """Return a QApplication instance for widget tests."""
    app = QApplication.instance()
    if app is not None:
        return app
    return QApplication([])


def _pump_until(predicate, timeout: float = 5.0) -> None:
    """Process Qt events until a widget test condition is true."""
    app = _get_app()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for widget condition")


@pytest.fixture
def isolated_qsettings(monkeypatch, tmp_path):
    """Route widget settings through a temporary INI file."""
    settings_path = tmp_path / "airunner-test.ini"

    def _get_settings():
        settings = QSettings(str(settings_path), QSettings.IniFormat)
        settings.setFallbacksEnabled(False)
        return settings

    monkeypatch.setattr(base_widget_module, "get_qsettings", _get_settings)
    monkeypatch.setattr(
        document_editor_widget_module,
        "get_qsettings",
        _get_settings,
    )
    monkeypatch.setattr(
        airunner_active_project,
        "get_qsettings",
        _get_settings,
    )
    return settings_path


def test_document_editor_container_builds_workspace_shell_tabs():
    """The coding shell should wrap the explorer and terminal in tab sets."""
    _get_app()
    widget = DocumentEditorContainerWidget()

    assert isinstance(widget._workspace_side_tabs, QTabWidget)
    assert isinstance(widget._workspace_bottom_tabs, QTabWidget)
    assert widget._workspace_side_tabs.tabText(0) == "Explorer"
    assert widget._workspace_bottom_tabs.tabText(0) == "Terminal"
    assert widget._workspace_panel_tabs["project-search"][0] is widget._workspace_side_tabs
    assert widget._workspace_panel_tabs["problems"][0] is widget._workspace_bottom_tabs
    assert "No coding project is open yet." in widget._workspace_text_panels[
        "project-search"
    ].toPlainText()
    assert "Pick Ask for Q&A" in widget._workspace_text_panels[
        "agent-activity"
    ].toPlainText()
    widget.deleteLater()


def test_document_editor_public_helpers_open_and_save_file(tmp_path):
    """The public document helpers should open and save active files."""
    _get_app()
    widget = DocumentEditorContainerWidget()
    file_path = tmp_path / "demo.py"
    file_path.write_text("print('before')\n", encoding="utf-8")

    widget.open_file(str(file_path))
    editor = widget.ui.documents.currentWidget()
    editor.editor.setPlainText("print('after')\n")

    assert widget.save_current_document() is True
    assert file_path.read_text(encoding="utf-8") == "print('after')\n"
    widget.deleteLater()


def test_open_document_reloads_after_external_workspace_write(tmp_path):
    """Open tabs should refresh after atomic external file replacements."""
    _get_app()
    widget = DocumentEditorContainerWidget()
    workspace = WorkspaceManager(str(tmp_path))
    workspace.write_file("demo.py", "print('before')\n", backup=False)
    file_path = tmp_path / "demo.py"

    widget.open_file(str(file_path))
    editor = widget.ui.documents.currentWidget()

    assert editor.editor.toPlainText() == "print('before')\n"

    workspace.write_file("demo.py", "print('after')\n", backup=False)

    _pump_until(
        lambda: editor.editor.toPlainText() == "print('after')\n"
    )
    assert editor.is_modified() is False
    widget.deleteLater()


def test_open_document_defers_external_reload_while_modified(tmp_path):
    """External writes should not overwrite an unsaved local buffer."""
    _get_app()
    widget = DocumentEditorContainerWidget()
    workspace = WorkspaceManager(str(tmp_path))
    workspace.write_file("demo.py", "print('before')\n", backup=False)
    file_path = tmp_path / "demo.py"

    widget.open_file(str(file_path))
    editor = widget.ui.documents.currentWidget()
    editor.editor.selectAll()
    editor.editor.insertPlainText("print('local')\n")

    _pump_until(editor.is_modified)
    workspace.write_file("demo.py", "print('external')\n", backup=False)

    _pump_until(lambda: editor._pending_external_disk_state is not None)
    assert editor.editor.toPlainText() == "print('local')\n"

    editor.editor.undo()
    _pump_until(lambda: not editor.is_modified())
    _pump_until(
        lambda: editor.editor.toPlainText() == "print('external')\n"
    )
    widget.deleteLater()


def test_run_script_starts_integrated_terminal_session(tmp_path):
    """Running a Python document should delegate into the terminal manager."""
    _get_app()
    widget = DocumentEditorContainerWidget()
    document_path = tmp_path / "demo.py"
    document_path.write_text("print('hello')\n", encoding="utf-8")
    captured = {}

    def fake_start(argv, working_directory=None, temp_file_path=None):
        captured["argv"] = argv
        captured["working_directory"] = working_directory
        captured["temp_file_path"] = temp_file_path
        return "session-1"

    widget.start_terminal_session = fake_start
    widget.run_script({"document_path": str(document_path)})

    assert captured["argv"] == [sys.executable, str(document_path)]
    assert captured["working_directory"] == str(tmp_path)
    assert captured["temp_file_path"] is None
    widget.deleteLater()


def test_run_script_uses_project_python_environment(tmp_path):
    """Loaded projects should run scripts through the selected venv."""
    _get_app()
    project_path = tmp_path / "python-project"
    service = AirunnerProjectService(str(project_path))
    service.initialize(
        project_name="Python Project",
        settings=AirunnerProjectSettings(
            bootstrap_profile="python-package",
            python_environment=AirunnerPythonEnvironmentSelection(
                manager="venv",
                interpreter_path="/tmp/python-project/.venv/bin/python",
                environment_path="/tmp/python-project/.venv",
                python_version="3.13",
                activate_command=(
                    "source /tmp/python-project/.venv/bin/activate"
                ),
            ),
        ),
    )
    document_path = project_path / "src" / "demo.py"
    document_path.parent.mkdir(parents=True, exist_ok=True)
    document_path.write_text("print('hello')\n", encoding="utf-8")
    widget = DocumentEditorContainerWidget()
    widget.load_project(service)
    captured = {}

    def fake_start(command, working_directory=None):
        captured["command"] = command
        captured["working_directory"] = working_directory
        return "session-2"

    widget._terminal_session_manager.start_shell_session = fake_start
    widget.run_script({"document_path": str(document_path)})

    assert "/tmp/python-project/.venv/bin/python" in captured["command"]
    assert str(document_path) in captured["command"]
    assert captured["working_directory"] == str(document_path.parent)
    widget.deleteLater()


def test_run_script_surfaces_environment_errors_in_terminal(tmp_path):
    """Run failures before PTY start should still reach the terminal UI."""
    _get_app()
    project_path = tmp_path / "python-project"
    service = AirunnerProjectService(str(project_path))
    service.initialize(project_name="Python Project")
    document_path = project_path / "src" / "demo.py"
    document_path.parent.mkdir(parents=True, exist_ok=True)
    document_path.write_text("print('hello')\n", encoding="utf-8")
    widget = DocumentEditorContainerWidget()
    widget.load_project(service)

    def fake_run_command(_document_path):
        raise PermissionError("blocked /usr/bin/python3.13")

    widget._project_python_run_command = fake_run_command

    widget.run_script({"document_path": str(document_path)})

    assert "Terminal error" in widget.ui.terminal.toPlainText()
    assert "blocked /usr/bin/python3.13" in widget.ui.terminal.toPlainText()
    assert "blocked /usr/bin/python3.13" in (
        widget._workspace_text_panels["problems"].toPlainText()
    )
    assert widget._workspace_bottom_tabs.currentIndex() == 0
    widget.deleteLater()


def test_load_project_restores_open_tabs_and_explorer_state(
    tmp_path,
    isolated_qsettings,
):
    """Project reload should restore tabs and explorer layout."""
    del isolated_qsettings
    _get_app()
    project_path = tmp_path / "python-project"
    nested_path = project_path / "src" / "pkg"
    nested_path.mkdir(parents=True)
    file_a = nested_path / "a.py"
    file_b = nested_path / "b.py"
    file_a.write_text("print('a')\n", encoding="utf-8")
    file_b.write_text("print('b')\n", encoding="utf-8")
    service = AirunnerProjectService(str(project_path))
    service.initialize(project_name="Python Project")

    first_widget = DocumentEditorContainerWidget()
    first_widget.load_project(service)
    first_widget.open_file(str(file_a))
    first_widget.open_file(str(file_b))
    _pump_until(
        lambda: first_widget.ui.file_explorer._proxy_index_for_path(
            str(nested_path)
        ).isValid()
    )
    dir_index = first_widget.ui.file_explorer._proxy_index_for_path(
        str(nested_path)
    )
    file_index = first_widget.ui.file_explorer._proxy_index_for_path(
        str(file_b)
    )
    first_widget.ui.file_explorer.tree_view.expand(dir_index)
    first_widget.ui.file_explorer.tree_view.setCurrentIndex(file_index)
    first_widget.save_state()
    first_widget.deleteLater()

    second_widget = DocumentEditorContainerWidget()
    restored = second_widget.load_project(service)

    _pump_until(lambda: second_widget.ui.documents.count() == 2)
    _pump_until(
        lambda: second_widget.ui.file_explorer._proxy_index_for_path(
            str(nested_path)
        ).isValid()
    )
    restored_dir_index = second_widget.ui.file_explorer._proxy_index_for_path(
        str(nested_path)
    )
    _pump_until(
        lambda: second_widget.ui.file_explorer.tree_view.isExpanded(
            restored_dir_index
        )
    )

    current_editor = second_widget.ui.documents.currentWidget()
    current_index = second_widget.ui.file_explorer.tree_view.currentIndex()

    assert restored is True
    assert second_widget.ui.documents.count() == 2
    assert current_editor.current_file_path == str(file_b)
    assert second_widget.ui.file_explorer._file_path_for_index(
        current_index
    ) == str(file_b)
    second_widget.deleteLater()


def test_widget_binds_background_run_manager_and_streams_updates(tmp_path):
    """The coding shell should surface background run updates in its panels."""
    _get_app()
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)
    session = AgentSessionRecord(
        project_path=str(project_service.project_path),
        title="Shell-bound background run",
    )
    task = AgentTaskRecord(
        title="Stream run updates",
        role=AgentRole.CODER,
        session_id=session.record_id,
    )
    state_service.save_session(session)
    state_service.save_task(task)
    manager = AgentBackgroundRunManager()
    widget = DocumentEditorContainerWidget()
    widget.bind_agent_run_manager(manager)

    run_id = manager.start_scripted_run(
        state_service,
        session,
        task,
        AgentRole.CODER,
        steps=[
            {
                "status": "planning",
                "progress": 50,
                "commentary": "Analyzing files.",
                "delay_seconds": 0.02,
            },
            {
                "status": "done",
                "progress": 100,
                "commentary": "Run complete.",
                "delay_seconds": 0.02,
            },
        ],
    )

    _pump_until(
        lambda: "Run finished" in widget._workspace_text_panels[
            "agent-activity"
        ].toPlainText()
    )

    activity_text = widget._workspace_text_panels[
        "agent-activity"
    ].toPlainText()
    assert run_id in activity_text
    assert "Run commentary" in activity_text
    assert "Run finished" in activity_text
    widget.deleteLater()