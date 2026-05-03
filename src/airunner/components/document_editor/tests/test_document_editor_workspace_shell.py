"""Focused tests for the coding workspace shell container."""

import os
import sys
import time

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QTabWidget

from airunner.components.agents.runtime import AgentBackgroundRunManager
from airunner.components.agents.runtime import AgentRole
from airunner.components.agents.runtime import AgentSessionRecord
from airunner.components.agents.runtime import AgentTaskRecord
from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)

from airunner.components.document_editor.gui.widgets.document_editor_container_widget import (
    DocumentEditorContainerWidget,
)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


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