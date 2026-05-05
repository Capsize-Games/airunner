"""
document_editor_container_widget.py

Container widget for the document/code editor, suitable for integration in larger layouts or tabbed interfaces.

Provides a place to host the DocumentEditorWidget and manage document-level actions (e.g., file open/save, tab management, etc.).
"""

from typing import Dict
import hashlib
from airunner.components.document_editor.gui.templates.document_editor_container_ui import (
    Ui_document_editor_container,
)
from airunner.components.document_editor.project import (
    AirunnerProjectPromptService,
    AirunnerProjectService,
    AirunnerProjectStateService,
    AirunnerPythonWorkflowService,
)
from airunner.components.document_editor.project.airunner_active_project import (
    set_active_project_path,
)
from airunner.components.document_editor.workspace_shell_support import (
    active_document_summary,
    agent_activity_entry,
    bottom_panel_definitions,
    meeting_workflow_summary,
    python_workflow_summary,
    problem_entry,
    side_panel_definitions,
    workspace_roots_summary,
)
from airunner.components.document_editor.terminal import (
    TerminalSessionManager,
)
from airunner.components.agents.runtime import AgentBackgroundRunManager
from airunner.enums import SignalCode
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QPlainTextEdit,
    QTabWidget,
)
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtCore import Qt
from airunner.components.document_editor.gui.widgets.document_editor_widget import (
    DocumentEditorWidget,
)
import os
import sys


class DocumentEditorContainerWidget(BaseWidget):
    """Container for the DocumentEditorWidget, for use in tabbed or multi-document interfaces."""

    widget_class_ = Ui_document_editor_container

    def __init__(self, *args, **kwargs):
        self._active_terminal_session_id = None
        self._agent_run_manager = None
        self._project_service = None
        self._restoring_project_session = False
        self._terminal_session_manager = TerminalSessionManager()
        self._terminal_temp_files = {}
        self._workspace_panel_tabs = {}
        self._workspace_text_panels = {}
        self._splitters = ["vertical_splitter", "splitter"]
        self.signal_handlers = {
            SignalCode.FILE_EXPLORER_OPEN_FILE: self.open_file_in_new_tab,
            SignalCode.RUN_SCRIPT: self.run_script,
            SignalCode.NEW_DOCUMENT: self.handle_new_document_signal,
            SignalCode.OPEN_MEETING_DOCUMENT: self.handle_open_meeting_document,
            SignalCode.OPEN_RESEARCH_DOCUMENT: self.handle_open_research_document,
            SignalCode.UNLOCK_RESEARCH_DOCUMENT: self.handle_unlock_research_document,
            SignalCode.UPDATE_DOCUMENT_CONTENT: self.handle_update_document_content,
            SignalCode.STREAM_TO_DOCUMENT: self.handle_stream_to_document,
            SignalCode.SAVE_STATE: self.save_state,
        }
        super().__init__(*args, **kwargs)
        # Register a Ctrl+W shortcut at the container level so closing a
        # document triggers the container's tab-close flow (prompts, cleanup,
        # and removal from the QTabWidget). The shortcut is active when this
        # container or its children have focus.
        try:
            self._close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
            self._close_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            try:
                # Prevent the shortcut from auto-repeating when key is held
                self._close_shortcut.setAutoRepeat(False)
            except Exception:
                pass
            self._close_shortcut.activated.connect(self._on_close_shortcut)
        except Exception:
            # Non-fatal; continue without keyboard shortcut
            pass
        # Register Ctrl+S to save the currently active document
        try:
            self._save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
            self._save_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            try:
                self._save_shortcut.setAutoRepeat(False)
            except Exception:
                pass
            self._save_shortcut.activated.connect(self._on_save_shortcut)
        except Exception:
            pass
        # Register Ctrl+Shift+S as Save As
        try:
            self._save_as_shortcut = QShortcut(
                QKeySequence("Ctrl+Shift+S"), self
            )
            self._save_as_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            try:
                self._save_as_shortcut.setAutoRepeat(False)
            except Exception:
                pass
            self._save_as_shortcut.activated.connect(self._on_save_as_shortcut)
        except Exception:
            pass
        # Guard to avoid re-entrant or duplicate save dialogs when both SaveAs
        # and Save shortcuts might get triggered for the same key event.
        self._in_save_as = False
        # Ensure the tab close signal is connected to our handler. Some UI auto-connect
        # setups may not attach correctly in all contexts, so connect explicitly.
        try:
            self.ui.documents.tabCloseRequested.connect(
                self.on_documents_tabCloseRequested
            )
        except Exception:
            # If the UI isn't fully constructed or the documents widget doesn't exist,
            # just ignore; auto-connect may still work.
            pass
        # Ensure when a tab becomes current we focus its editor so typing starts
        # immediately without a click.
        try:
            self.ui.documents.currentChanged.connect(self._on_tab_changed)
        except Exception:
            pass
        self._terminal_session_manager.outputReceived.connect(
            self._on_terminal_output
        )
        self._terminal_session_manager.sessionFinished.connect(
            self._on_terminal_session_finished
        )
        self._terminal_session_manager.sessionError.connect(
            self._on_terminal_session_error
        )
        self._setup_workspace_shell()
        self._show_workspace_welcome()

    def handle_new_document_signal(self, data: Dict):
        self._new_tab()
        self.append_agent_activity(
            agent_activity_entry("Created document", "Untitled")
        )

    def _setup_workspace_shell(self) -> None:
        """Wrap explorer and terminal surfaces in workspace shell tabs."""
        self._workspace_side_tabs = self._build_workspace_tabs(
            splitter=self.ui.splitter,
            base_widget=self.ui.file_explorer,
            base_key="explorer",
            base_title="Explorer",
            panel_definitions=side_panel_definitions(),
            object_name="workspace_side_tabs",
        )
        self._workspace_bottom_tabs = self._build_workspace_tabs(
            splitter=self.ui.vertical_splitter,
            base_widget=self.ui.terminal,
            base_key="terminal",
            base_title="Terminal",
            panel_definitions=bottom_panel_definitions(),
            object_name="workspace_bottom_tabs",
        )

    def _welcome_search_text(self) -> str:
        """Return the initial coding workspace guidance."""

        return (
            "No coding project is open yet.\n\n"
            "Use Documents > New Project... to create a starter Python "
            "workspace, or Documents > Open Project... to load an existing "
            "folder with .airunner metadata."
        )

    def _welcome_problems_text(self) -> str:
        """Return the initial problems-panel guidance."""

        return (
            "Project checks will appear here after you open a coding "
            "workspace.\n\n"
            "Start with a small Python CLI project so AIRunner can edit "
            "files, run tests, and review changes in one place."
        )

    def _welcome_activity_text(self) -> str:
        """Return the initial agent-activity guidance."""

        return (
            "Agent activity will appear here.\n\n"
            "Pick Ask for Q&A, Plan for implementation planning, or Agent "
            "to let the coding workflow inspect and modify the project."
        )

    def _show_workspace_welcome(self) -> None:
        """Seed workspace panels with a first-run welcome state."""

        self.set_project_search_results(self._welcome_search_text())
        self.set_problems_text(self._welcome_problems_text())
        self.set_agent_activity(self._welcome_activity_text())

    def _build_workspace_tabs(
        self,
        splitter,
        base_widget,
        base_key: str,
        base_title: str,
        panel_definitions,
        object_name: str,
    ) -> QTabWidget:
        """Create a tabbed workspace region around an existing widget."""
        insert_index = splitter.indexOf(base_widget)
        tab_widget = QTabWidget(splitter)
        tab_widget.setObjectName(object_name)
        tab_widget.addTab(base_widget, base_title)
        self._workspace_panel_tabs[base_key] = (tab_widget, 0)
        for panel in panel_definitions:
            panel_widget = self._create_workspace_text_panel(
                panel.placeholder
            )
            self._workspace_text_panels[panel.key] = panel_widget
            tab_index = tab_widget.addTab(panel_widget, panel.title)
            self._workspace_panel_tabs[panel.key] = (tab_widget, tab_index)
        splitter.insertWidget(insert_index, tab_widget)
        return tab_widget

    def _create_workspace_text_panel(self, placeholder: str) -> QPlainTextEdit:
        """Create a read-only workspace panel surface."""
        panel = QPlainTextEdit(self)
        panel.setReadOnly(True)
        panel.setPlaceholderText(placeholder)
        return panel

    def activate_workspace_panel(self, panel_key: str) -> None:
        """Activate a named workspace shell panel if it exists."""
        tab_info = self._workspace_panel_tabs.get(panel_key)
        if tab_info is None:
            return
        tab_widget, tab_index = tab_info
        tab_widget.setCurrentIndex(tab_index)

    def set_project_search_results(self, text: str) -> None:
        """Replace the project search panel contents."""
        self._set_workspace_panel_text("project-search", text)

    def set_review_summary(self, text: str) -> None:
        """Replace the review panel contents."""
        self._set_workspace_panel_text("review", text)

    def set_problems_text(self, text: str) -> None:
        """Replace the problems panel contents."""
        self._set_workspace_panel_text("problems", text)

    def append_problem(self, text: str) -> None:
        """Append a problem entry and focus the problems panel."""
        self._append_workspace_panel_text("problems", text)
        self.activate_workspace_panel("problems")

    def set_agent_activity(self, text: str) -> None:
        """Replace the agent activity panel contents."""
        self._set_workspace_panel_text("agent-activity", text)

    def append_agent_activity(self, text: str) -> None:
        """Append an entry to the agent activity panel."""
        self._append_workspace_panel_text("agent-activity", text)

    def bind_agent_run_manager(
        self,
        manager: AgentBackgroundRunManager | None,
    ) -> None:
        """Bind a background agent runner to the coding shell panels."""
        current = getattr(self, "_agent_run_manager", None)
        if current is manager:
            return
        if current is not None:
            self._disconnect_agent_run_manager(current)
        self._agent_run_manager = manager
        if manager is None:
            return
        manager.runProgressUpdated.connect(self._on_agent_run_progress)
        manager.runStatusUpdated.connect(self._on_agent_run_status)
        manager.runMessageLogged.connect(self._on_agent_run_message)
        manager.runFinished.connect(self._on_agent_run_finished)

    def _disconnect_agent_run_manager(
        self,
        manager: AgentBackgroundRunManager,
    ) -> None:
        """Disconnect the current background runner from shell callbacks."""
        try:
            manager.runProgressUpdated.disconnect(self._on_agent_run_progress)
        except Exception:
            pass
        try:
            manager.runStatusUpdated.disconnect(self._on_agent_run_status)
        except Exception:
            pass
        try:
            manager.runMessageLogged.disconnect(self._on_agent_run_message)
        except Exception:
            pass
        try:
            manager.runFinished.disconnect(self._on_agent_run_finished)
        except Exception:
            pass

    def _on_agent_run_progress(self, run_id: str, value: object) -> None:
        """Append a progress update from the background run manager."""
        self.append_agent_activity(
            agent_activity_entry("Run progress", f"{run_id}: {value}")
        )

    def _on_agent_run_status(self, run_id: str, status: str) -> None:
        """Append a status update from the background run manager."""
        self.append_agent_activity(
            agent_activity_entry("Run status", f"{run_id}: {status}")
        )

    def _on_agent_run_message(
        self,
        run_id: str,
        channel: str,
        message: str,
    ) -> None:
        """Append a channelled run message from the background manager."""
        self.append_agent_activity(
            agent_activity_entry(
                f"Run {channel}",
                f"{run_id}: {message}",
            )
        )

    def _on_agent_run_finished(
        self,
        run_id: str,
        payload: Dict,
    ) -> None:
        """Handle run completion and surface failures in the shell."""
        result = payload.get("result", {}) if isinstance(payload, dict) else {}
        status = result.get("status") or (
            "failed" if payload.get("error") else "completed"
        )
        self.append_agent_activity(
            agent_activity_entry("Run finished", f"{run_id}: {status}")
        )
        if payload.get("error"):
            self.append_problem(
                problem_entry(
                    f"Agent run {run_id} failed: {payload['error']}"
                )
            )

    def _set_workspace_panel_text(self, panel_key: str, text: str) -> None:
        """Replace the contents of a text-based workspace panel."""
        panel = self._workspace_text_panels.get(panel_key)
        if panel is None:
            return
        panel.setPlainText(text)

    def _append_workspace_panel_text(
        self,
        panel_key: str,
        text: str,
    ) -> None:
        """Append a line to a text-based workspace panel."""
        panel = self._workspace_text_panels.get(panel_key)
        if panel is None:
            return
        panel.appendPlainText(text)

    def setup_tab_manager(self, *args, **kwargs):
        # Remove 'parent' from kwargs if present, since TabManagerMixin does not accept it
        kwargs.pop("parent", None)
        super().setup_tab_manager(*args, **kwargs)

    def open_file_in_new_tab(self, data: Dict) -> None:
        """Open a file in a new tab in the document editor tab widget."""
        file_path = data.get("file_path")
        self._open_file_tab(file_path)
        if file_path:
            self.append_agent_activity(
                agent_activity_entry("Opened file", file_path)
            )

    def load_project(
        self,
        project_service: AirunnerProjectService,
    ) -> bool:
        """Load an AIRunner project into the embedded workspace shell."""

        self._project_service = project_service
        set_active_project_path(project_service.project_path)
        root_paths = [
            project_service.resolve_root_path(root.name)
            for root in project_service.list_roots()
        ]
        self.ui.file_explorer.set_project_service(project_service)
        self.set_workspace_roots(root_paths)
        restored = self._restore_project_session()
        self.ui.file_explorer.restore_state()
        return restored

    def new_document(self) -> None:
        """Create a new untitled document tab."""

        self._new_tab()

    def open_file(self, file_path: str) -> None:
        """Open one file in a document tab."""

        self._open_file_tab(file_path)

    def save_current_document(self) -> bool:
        """Save the active document tab."""

        editor = self._current_editor()
        if editor is None:
            return False
        return self._save_tab(editor)

    def save_current_document_as(self) -> bool:
        """Save the active document tab to a new path."""

        editor = self._current_editor()
        if editor is None:
            return False
        return bool(self._save_as_tab(editor))

    def _current_editor(self) -> DocumentEditorWidget | None:
        """Return the active document editor widget if one exists."""

        current = self.ui.documents.currentWidget()
        if isinstance(current, DocumentEditorWidget):
            return current
        return None

    def _editor_file_path(self, editor) -> str | None:
        """Return the saved file path for one editor widget."""
        if editor is None:
            return None
        if hasattr(editor, "file_path") and callable(editor.file_path):
            try:
                return editor.file_path()
            except Exception:
                return None
        return getattr(editor, "current_file_path", None) or getattr(
            editor,
            "file_path",
            None,
        )

    def save_state(self):
        """Persist splitter state and project workspace session data."""
        super().save_state()
        self.ui.file_explorer.save_state()
        self._save_project_session()

    def _project_session_group(self) -> str | None:
        """Return the settings group used for the active project."""
        if self._project_service is None:
            return None
        project_path = os.path.abspath(self._project_service.project_path)
        session_id = hashlib.sha1(project_path.encode("utf-8")).hexdigest()
        return f"coding_workspace/project_sessions/{session_id}"

    def _save_project_session(self) -> None:
        """Persist open document tabs for the active project."""
        if self._restoring_project_session:
            return
        group = self._project_session_group()
        if group is None:
            return
        self.settings.beginGroup(group)
        self.settings.setValue("open_files", self._open_document_paths())
        self.settings.setValue("current_file", self._current_document_path())
        self.settings.endGroup()
        self.settings.sync()

    def _open_document_paths(self) -> list[str]:
        """Return saved document paths for all open file-backed tabs."""
        paths: list[str] = []
        for index in range(self.ui.documents.count()):
            file_path = self._editor_file_path(self.ui.documents.widget(index))
            if file_path and os.path.isfile(file_path):
                paths.append(os.path.abspath(file_path))
        return paths

    def _current_document_path(self) -> str:
        """Return the active saved file path for the current tab."""
        file_path = self._editor_file_path(self._current_editor())
        if not file_path:
            return ""
        return os.path.abspath(file_path)

    def _restore_project_session(self) -> bool:
        """Restore open files and the active tab for one project."""
        group = self._project_session_group()
        if group is None:
            return False
        self.settings.beginGroup(group)
        open_files = self._list_project_setting("open_files")
        current_file = self.settings.value("current_file", "", type=str)
        self.settings.endGroup()
        if not open_files:
            return False
        restored = False
        self._restoring_project_session = True
        try:
            for file_path in open_files:
                if self._restorable_project_file(file_path):
                    self._open_file_tab(file_path)
                    restored = True
            self._focus_document_path(current_file)
        finally:
            self._restoring_project_session = False
        self._save_project_session()
        return restored

    def _list_project_setting(self, key: str) -> list[str]:
        """Return one list-valued project-session setting."""
        value = self.settings.value(key, [])
        if isinstance(value, str):
            return [value] if value else []
        return [str(item) for item in value or [] if item]

    def _restorable_project_file(self, file_path: str) -> bool:
        """Return whether one saved path still belongs to this project."""
        if not file_path or not os.path.isfile(file_path):
            return False
        if self._project_service is None:
            return False
        return self._project_service.contains_path(file_path)

    def _focus_document_path(self, file_path: str) -> None:
        """Activate one already-open editor tab by its saved path."""
        if not file_path:
            return
        target = os.path.abspath(file_path)
        for index in range(self.ui.documents.count()):
            candidate = self._editor_file_path(self.ui.documents.widget(index))
            if candidate and os.path.abspath(candidate) == target:
                self.ui.documents.setCurrentIndex(index)
                return

    def set_workspace_roots(self, root_paths: list[str]) -> None:
        """Configure the embedded explorer for one or more workspace roots."""
        self.ui.file_explorer.configure_root_paths(root_paths)
        self.set_project_search_results(
            workspace_roots_summary(root_paths)
        )
        self._refresh_python_workflow_summary(root_paths)
        self.append_agent_activity(
            agent_activity_entry(
                "Configured workspace roots",
                f"{len(root_paths)} root(s)",
            )
        )

    def _refresh_python_workflow_summary(
        self,
        root_paths: list[str],
    ) -> None:
        """Refresh the problems panel with Python workflow guidance."""
        if not root_paths:
            return
        project_service = self._project_service
        if project_service is None:
            project_service = AirunnerProjectService(root_paths[0])
        if not project_service.exists():
            return
        python_text = python_workflow_summary(
            AirunnerPythonWorkflowService(project_service).summary()
        )
        meeting_text = self._meeting_workflow_text(project_service)
        self.set_problems_text(
            "\n\n".join(text for text in (python_text, meeting_text) if text)
        )

    def _meeting_workflow_text(
        self,
        project_service: AirunnerProjectService,
    ) -> str:
        """Return a document-editor summary of meeting workflow state."""
        state_service = AirunnerProjectStateService(project_service)
        prompt_service = AirunnerProjectPromptService(project_service)
        deliverables = state_service.list_meeting_deliverables()
        latest = self._latest_meeting_deliverable(deliverables)
        return meeting_workflow_summary(
            {
                "commands": self._meeting_template_commands(prompt_service),
                "meeting_run_count": len(state_service.list_meeting_runs()),
                "deliverable_count": len(deliverables),
                "review_required_count": self._review_required_count(
                    deliverables
                ),
                "latest_deliverable_title": getattr(latest, "title", ""),
                "latest_review_status": (
                    latest.review_status.value if latest else ""
                ),
            }
        )

    def _meeting_template_commands(
        self,
        prompt_service: AirunnerProjectPromptService,
    ) -> list[str]:
        """Return the project slash commands reserved for meeting workflows."""
        templates = prompt_service.prompt_templates()
        return [
            template.command_name
            for template in templates
            if template.command_name.startswith("meeting")
        ]

    def _latest_meeting_deliverable(self, deliverables):
        """Return the latest meeting deliverable pack, if any."""
        if not deliverables:
            return None
        return max(deliverables, key=lambda item: item.created_at)

    def _review_required_count(self, deliverables) -> int:
        """Return the number of meeting packs that still need review."""
        return sum(
            1
            for deliverable in deliverables
            if deliverable.review_status.value != "approved"
        )

    def run_script(self, data: Dict) -> None:
        payload = self._script_run_payload(data)
        if payload is None:
            return
        document_path, temp_file_path = payload
        self._prepare_script_run(document_path)
        try:
            command = self._project_python_run_command(document_path)
        except Exception as exc:
            self._on_terminal_session_error("", str(exc))
            return
        if command is None:
            self.start_terminal_session(
                [sys.executable, document_path],
                working_directory=os.path.dirname(document_path),
                temp_file_path=temp_file_path,
            )
            return
        command_text, working_directory = command
        self._start_shell_session(
            command_text,
            working_directory,
            temp_file_path,
        )

    def _script_run_payload(
        self,
        data: Dict,
    ) -> tuple[str, str | None] | None:
        """Return the validated script path and optional temp file path."""
        document_path = data.get("document_path")
        if not document_path:
            self._warn_missing_run_target()
            return None
        if not os.path.isfile(document_path):
            return None
        if os.path.splitext(document_path)[1].lower() != ".py":
            return None
        temp_file = document_path if bool(data.get("temp_file", False)) else None
        return document_path, temp_file

    def _warn_missing_run_target(self) -> None:
        """Warn when the user tries to run an unsaved document."""
        try:
            QMessageBox.warning(
                self,
                "Run Error",
                "No file to run. Please save the document before running.",
            )
        except Exception:
            return

    def _prepare_script_run(self, document_path: str) -> None:
        """Reset the terminal UI and track a new script run."""
        self.ui.terminal.clear()
        self.activate_workspace_panel("terminal")
        self.append_agent_activity(
            agent_activity_entry("Started run", document_path)
        )
        if self._active_terminal_session_id is not None:
            self.stop_terminal_session(self._active_terminal_session_id)

    def _project_python_run_command(
        self,
        document_path: str,
    ) -> tuple[str, str] | None:
        """Return the resolved project Python command for one script."""
        project_service = self._project_service
        if project_service is None:
            return None
        ownership = project_service.project_relative_path(document_path)
        if ownership is None:
            return None
        root_name, rel_path = ownership
        workflows = AirunnerPythonWorkflowService(project_service)
        context = workflows.context(
            root_name,
            os.path.dirname(rel_path),
            ensure_environment=True,
        )
        self._refresh_python_workflow_summary([project_service.project_path])
        return workflows.build_run_command(context, document_path), context.working_directory

    def _start_shell_session(
        self,
        command: str,
        working_directory: str,
        temp_file_path: str | None,
    ) -> str | None:
        """Start a shell-backed terminal session and track temp files."""
        try:
            session_id = self._terminal_session_manager.start_shell_session(
                command,
                working_directory=working_directory,
            )
        except Exception as exc:
            self._on_terminal_session_error("", str(exc))
            return None
        self._active_terminal_session_id = session_id
        if temp_file_path:
            self._terminal_temp_files[session_id] = temp_file_path
        return session_id

    def handle_open_research_document(self, data: Dict) -> None:
        """Open a research document in a locked (read-only) tab."""
        self._open_locked_document(data)

    def handle_open_meeting_document(self, data: Dict) -> None:
        """Open one meeting workflow artifact in a locked tab."""
        self._open_locked_document(data)

    def _open_locked_document(self, data: Dict) -> None:
        """Open one locked workspace artifact in the document editor."""
        file_path = data.get("path")
        if not file_path:
            return

        title = data.get("title")
        locked = data.get("locked", True)

        # Normalize path for comparison
        try:
            target = os.path.abspath(file_path)
        except Exception:
            target = file_path

        # Check if already open, and update lock status if so
        for i in range(self.ui.documents.count()):
            w = self.ui.documents.widget(i)
            candidate = None
            if hasattr(w, "file_path") and callable(getattr(w, "file_path")):
                try:
                    candidate = w.file_path()
                except Exception:
                    candidate = None
            else:
                candidate = getattr(w, "current_file_path", None) or getattr(
                    w, "file_path", None
                )
            if candidate:
                try:
                    if os.path.abspath(candidate) == target:
                        # Tab already exists, just update lock status
                        self.ui.documents.setCurrentIndex(i)
                        if hasattr(w, "set_locked"):
                            w.set_locked(locked)
                        # Update tab title with lock indicator
                        tab_title = title or os.path.basename(file_path)
                        if locked:
                            tab_title = f"🔒 {tab_title}"
                        self.ui.documents.setTabText(i, tab_title)
                        return
                except Exception:
                    pass

        # Create new tab
        editor = DocumentEditorWidget()
        editor.load_file(file_path)

        # Set lock status
        if hasattr(editor, "set_locked"):
            editor.set_locked(locked)

        # Set tab title with lock indicator
        tab_title = title or os.path.basename(file_path)
        if locked:
            tab_title = f"🔒 {tab_title}"

        self.ui.documents.addTab(editor, tab_title)

        # Connect document modification signal
        try:
            doc = getattr(editor, "editor").document()
            doc.modificationChanged.connect(
                lambda modified, ed=editor: self._on_editor_modified(
                    ed, modified
                )
            )
        except Exception:
            pass

        self.ui.documents.setCurrentWidget(editor)

        # Give keyboard focus to the editor
        try:
            if hasattr(editor, "editor"):
                editor.editor.setFocus()
        except Exception:
            pass

    def handle_unlock_research_document(self, data: Dict) -> None:
        """Unlock a research document to allow editing.

        Args:
            data: Dict containing:
                - path: str - File path to unlock
        """
        file_path = data.get("path")
        if not file_path:
            return

        # Normalize path for comparison
        try:
            target = os.path.abspath(file_path)
        except Exception:
            target = file_path

        # Find the tab and unlock it
        for i in range(self.ui.documents.count()):
            w = self.ui.documents.widget(i)
            candidate = None
            if hasattr(w, "file_path") and callable(getattr(w, "file_path")):
                try:
                    candidate = w.file_path()
                except Exception:
                    candidate = None
            else:
                candidate = getattr(w, "current_file_path", None) or getattr(
                    w, "file_path", None
                )
            if candidate:
                try:
                    if os.path.abspath(candidate) == target:
                        # Unlock the document
                        if hasattr(w, "set_locked"):
                            w.set_locked(False)

                        # Remove lock indicator from tab title
                        current_title = self.ui.documents.tabText(i)
                        if current_title.startswith("🔒 "):
                            new_title = current_title[
                                3:
                            ]  # Remove "🔒 " prefix
                            self.ui.documents.setTabText(i, new_title)
                        return
                except Exception:
                    pass

    def handle_update_document_content(self, data: Dict) -> None:
        """Update document content in memory without saving to disk.

        This allows live updating of documents during research/generation.
        The autosave mechanism will save to disk automatically.

        Args:
            data: Dict containing:
                - path: str - File path of document to update
                - content: str - New content to set (replaces current content)
                - append: bool - If True, append instead of replace (default: False)
        """
        file_path = data.get("path")
        content = data.get("content", "")
        append = data.get("append", False)

        if not file_path:
            return

        # Normalize path
        try:
            target = os.path.abspath(file_path)
        except Exception:
            target = file_path

        # Find the editor tab
        for i in range(self.ui.documents.count()):
            w = self.ui.documents.widget(i)
            candidate = None
            if hasattr(w, "file_path") and callable(getattr(w, "file_path")):
                try:
                    candidate = w.file_path()
                except Exception:
                    candidate = None
            else:
                candidate = getattr(w, "current_file_path", None) or getattr(
                    w, "file_path", None
                )

            if candidate:
                try:
                    if os.path.abspath(candidate) == target:
                        # Update the editor content
                        editor = getattr(w, "editor", w)
                        if hasattr(editor, "toPlainText"):
                            if append:
                                # Append to existing content
                                current = editor.toPlainText()
                                editor.setPlainText(current + content)
                            else:
                                # Replace content
                                editor.setPlainText(content)
                        return
                except Exception as e:
                    self.logger.exception(
                        f"Failed to update document content: {e}"
                    )

    def handle_stream_to_document(self, data: Dict) -> None:
        """Stream content to document (append text chunk by chunk).

        This is used for streaming LLM responses directly to research documents.

        Args:
            data: Dict containing:
                - path: str - File path of document to stream to
                - chunk: str - Text chunk to append
        """
        file_path = data.get("path")
        chunk = data.get("chunk", "")

        if not file_path or not chunk:
            return

        # Normalize path
        try:
            target = os.path.abspath(file_path)
        except Exception:
            target = file_path

        # Find the editor tab
        for i in range(self.ui.documents.count()):
            w = self.ui.documents.widget(i)
            candidate = None
            if hasattr(w, "file_path") and callable(getattr(w, "file_path")):
                try:
                    candidate = w.file_path()
                except Exception:
                    candidate = None
            else:
                candidate = getattr(w, "current_file_path", None) or getattr(
                    w, "file_path", None
                )

            if candidate:
                try:
                    if os.path.abspath(candidate) == target:
                        # Append chunk to editor
                        editor = getattr(w, "editor", w)
                        if hasattr(editor, "insertPlainText"):
                            # Move cursor to end and insert
                            cursor = editor.textCursor()
                            cursor.movePosition(cursor.End)
                            editor.setTextCursor(cursor)
                            editor.insertPlainText(chunk)
                        elif hasattr(editor, "toPlainText") and hasattr(
                            editor, "setPlainText"
                        ):
                            # Fallback: append via get+set
                            current = editor.toPlainText()
                            editor.setPlainText(current + chunk)
                        return
                except Exception as e:
                    self.logger.exception(f"Failed to stream to document: {e}")

    def start_terminal_session(
        self,
        argv: list[str],
        working_directory: str | None = None,
        temp_file_path: str | None = None,
    ) -> str | None:
        """Start a PTY-backed terminal session and track it as active."""
        try:
            session_id = self._terminal_session_manager.start_session(
                argv,
                working_directory=working_directory,
            )
        except Exception as exc:
            self._on_terminal_session_error("", str(exc))
            return None
        self._active_terminal_session_id = session_id
        if temp_file_path:
            self._terminal_temp_files[session_id] = temp_file_path
        return session_id

    def run_terminal_command(
        self,
        command: str,
        working_directory: str | None = None,
    ) -> str | None:
        """Run a shell command inside the integrated terminal."""
        self.ui.terminal.clear()
        self.activate_workspace_panel("terminal")
        self.append_agent_activity(
            agent_activity_entry("Started terminal command", command)
        )
        try:
            session_id = self._terminal_session_manager.start_shell_session(
                command,
                working_directory=working_directory,
            )
        except Exception as exc:
            self._on_terminal_session_error("", str(exc))
            return None
        self._active_terminal_session_id = session_id
        return session_id

    def send_terminal_input(
        self,
        text: str,
        session_id: str | None = None,
    ) -> bool:
        """Send user or agent input to the active terminal session."""
        target_session = session_id or self._active_terminal_session_id
        if target_session is None:
            return False
        return self._terminal_session_manager.send_input(
            target_session,
            text,
        )

    def stop_terminal_session(
        self,
        session_id: str | None = None,
    ) -> bool:
        """Stop an active terminal session."""
        target_session = session_id or self._active_terminal_session_id
        if target_session is None:
            return False
        self.append_agent_activity(
            agent_activity_entry("Stopped terminal session", target_session)
        )
        return self._terminal_session_manager.stop_session(target_session)

    def terminal_session_output(
        self,
        session_id: str | None = None,
    ) -> str:
        """Return captured output for the active terminal session."""
        target_session = session_id or self._active_terminal_session_id
        if target_session is None:
            return ""
        return self._terminal_session_manager.session_output(
            target_session
        )

    def _on_terminal_output(self, session_id: str, text: str) -> None:
        """Append live PTY output for the active session to the UI."""
        if session_id != self._active_terminal_session_id:
            return
        self.activate_workspace_panel("terminal")
        self.ui.terminal.moveCursor(QTextCursor.End)
        self.ui.terminal.insertPlainText(text)
        self.ui.terminal.ensureCursorVisible()

    def _on_terminal_session_finished(
        self,
        session_id: str,
        exit_code: int,
    ) -> None:
        """Handle terminal session completion and temp-file cleanup."""
        self.append_agent_activity(
            agent_activity_entry(
                "Finished run",
                f"session {session_id} exit code {exit_code}",
            )
        )
        if exit_code != 0:
            self.append_problem(
                problem_entry(
                    f"Terminal session {session_id} exited with {exit_code}"
                )
            )
        if session_id == self._active_terminal_session_id:
            self.ui.terminal.moveCursor(QTextCursor.End)
            self.ui.terminal.insertPlainText(
                f"\n[Process finished with exit code {exit_code}]"
            )
            self.ui.terminal.ensureCursorVisible()
            self._active_terminal_session_id = None
        self._cleanup_terminal_temp_file(
            self._terminal_temp_files.pop(session_id, None)
        )

    def _on_terminal_session_error(
        self,
        session_id: str,
        error: str,
    ) -> None:
        """Handle terminal session errors and surface them in the UI."""
        message = (
            f"Session {session_id} error: {error}"
            if session_id
            else f"Terminal error: {error}"
        )
        self.append_agent_activity(agent_activity_entry("Process error", message))
        self.append_problem(problem_entry(message))
        if not session_id or session_id == self._active_terminal_session_id:
            self.activate_workspace_panel("terminal")
            self.ui.terminal.moveCursor(QTextCursor.End)
            self.ui.terminal.insertPlainText(f"\n[{message}]")
            self.ui.terminal.ensureCursorVisible()

    def _cleanup_terminal_temp_file(self, temp_path: str | None) -> None:
        """Remove a temporary run file when its terminal session ends."""
        if not temp_path:
            return
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            self.ui.terminal.moveCursor(QTextCursor.End)
            self.ui.terminal.insertPlainText(
                f"\n[Warning: failed to remove temp file {temp_path}]"
            )
            self.ui.terminal.ensureCursorVisible()

    def _open_file_tab(self, file_path: str):
        if not file_path:
            return

        # Normalize path for comparison
        try:
            target = os.path.abspath(file_path)
        except Exception:
            target = file_path

        # If a tab for this file is already open, switch to it instead of opening a new one
        for i in range(self.ui.documents.count()):
            w = self.ui.documents.widget(i)
            candidate = None
            if hasattr(w, "file_path") and callable(getattr(w, "file_path")):
                try:
                    candidate = w.file_path()
                except Exception:
                    candidate = None
            else:
                candidate = getattr(w, "current_file_path", None) or getattr(
                    w, "file_path", None
                )
            if candidate:
                try:
                    if os.path.abspath(candidate) == target:
                        self.ui.documents.setCurrentIndex(i)
                        self._save_project_session()
                        return
                except Exception:
                    # ignore path normalization errors and continue
                    pass

        editor = DocumentEditorWidget()
        editor.load_file(file_path)
        # load_file sets editor.current_file_path; avoid setting editor.file_path attribute
        filename = os.path.basename(file_path)
        self.ui.documents.addTab(editor, filename)
        # Connect document modification signal to update tab title with an unsaved marker
        try:
            doc = getattr(editor, "editor").document()
            doc.modificationChanged.connect(
                lambda modified, ed=editor: self._on_editor_modified(
                    ed, modified
                )
            )
        except Exception:
            pass
        self.ui.documents.setCurrentWidget(editor)
        # Give keyboard focus to the editor so the cursor is active immediately
        try:
            if hasattr(editor, "editor"):
                editor.editor.setFocus()
        except Exception:
            pass
        self._save_project_session()

    def _new_tab(self):
        editor = DocumentEditorWidget()
        # Leave editor.current_file_path as the source of truth; do not set an attribute
        self.ui.documents.addTab(editor, "Untitled")
        try:
            doc = getattr(editor, "editor").document()
            doc.modificationChanged.connect(
                lambda modified, ed=editor: self._on_editor_modified(
                    ed, modified
                )
            )
        except Exception:
            pass
        self.ui.documents.setCurrentWidget(editor)
        try:
            if hasattr(editor, "editor"):
                editor.editor.setFocus()
        except Exception:
            pass

    def _on_tab_changed(self, index: int) -> None:
        """Called when a different tab is activated; focus the editor there."""
        try:
            self.logger.info(f"=== TAB CHANGED: index={index} ===")

            if index is None or index < 0:
                # No active tab - clear active document
                self.logger.info(
                    "No active tab (index < 0), clearing active document"
                )
                self._notify_active_document(None)
                self._save_project_session()
                return
            w = self.ui.documents.widget(index)
            if w is None:
                self.logger.info(
                    "Tab widget is None, clearing active document"
                )
                self._notify_active_document(None)
                self._save_project_session()
                return

            # Get the file path for this tab
            file_path = getattr(w, "current_file_path", None)
            self.logger.info(f"Tab widget file_path: {file_path}")
            self._notify_active_document(file_path)
            self._save_project_session()

            if hasattr(w, "editor"):
                try:
                    w.editor.setFocus()
                except Exception:
                    pass
        except Exception as e:
            self.logger.error(f"Error in _on_tab_changed: {e}", exc_info=True)

    def _notify_active_document(self, file_path: str) -> None:
        """
        Notify the LLM agent about the currently active document.

        This allows the agent to know which file to edit when the user
        says "modify this file" or "edit the current file".

        Args:
            file_path: Absolute path to active document, or None if no active document
        """
        try:
            self.logger.info(
                f"=== ATTEMPTING TO NOTIFY ACTIVE DOCUMENT: {file_path} ==="
            )

            normalized_path = (
                os.path.abspath(file_path) if file_path else None
            )
            self.set_review_summary(
                active_document_summary(normalized_path)
            )

            # Store in shared settings cache so the agent can pick it up later
            shared_settings = getattr(
                self, "settings_mixin_shared_instance", None
            )
            if shared_settings is not None:
                if normalized_path:
                    shared_settings.set_cached_setting_by_key(
                        "active_document_path", normalized_path
                    )
                    self.logger.info(
                        "✓ Stored active document in settings cache: %s",
                        normalized_path,
                    )
                else:
                    shared_settings.set_cached_setting_by_key(
                        "active_document_path", None
                    )
                    self.logger.info(
                        "✓ Cleared active document in settings cache",
                    )
            else:
                self.logger.warning(
                    "SettingsMixinSharedInstance unavailable; cannot cache active document"
                )

            # Also try to notify agent directly if available
            main_window = self.window()
            if main_window is None:
                return

            api = getattr(main_window, "api", None)
            if getattr(api, "daemon_client", None) is not None:
                return

            if not hasattr(main_window, "worker_manager"):
                return

            worker_manager = main_window.worker_manager
            if worker_manager is None:
                return

            if not hasattr(worker_manager, "llm_generate_worker"):
                return

            llm_worker = worker_manager.llm_generate_worker
            if llm_worker is None:
                return

            if not hasattr(llm_worker, "model_manager"):
                return

            model_manager = llm_worker.model_manager
            if model_manager is None:
                return

            if not hasattr(model_manager, "agent"):
                return

            agent = model_manager.agent
            if agent is None:
                return

            if not hasattr(agent, "set_active_document"):
                return

            agent.set_active_document(file_path)
            self.logger.info(f"✓ Also notified agent directly: {file_path}")

        except Exception as e:
            self.logger.error(
                f"Error notifying active document: {e}", exc_info=True
            )

    def _on_editor_modified(
        self, editor: DocumentEditorWidget, modified: bool
    ) -> None:
        """Update the tab title for editor to include a star when modified.

        The tab label will be the base filename (or 'Untitled') followed by ' *'
        when modified is True.
        """
        try:
            idx = self.ui.documents.indexOf(editor)
            if idx == -1:
                return
            # Determine base label
            base = "Untitled"
            try:
                if hasattr(editor, "file_path") and callable(
                    getattr(editor, "file_path")
                ):
                    base_path = editor.file_path()
                else:
                    base_path = getattr(editor, "current_file_path", None)
                if base_path:
                    base = os.path.basename(base_path)
            except Exception:
                pass
            label = f"{base}"
            if modified:
                label = f"{label} *"
            try:
                self.ui.documents.setTabText(idx, label)
            except Exception:
                pass
        except Exception:
            pass

    def _save_tab(self, editor):
        # Use the DocumentEditorWidget API for saving
        # Resolve file path using available API (method or attributes)
        file_path = self._editor_file_path(editor)

        if hasattr(editor, "save_file"):
            if not file_path:
                return self._save_as_tab(editor)
            saved = bool(editor.save_file())
            idx = self.ui.documents.indexOf(editor)
            if idx != -1:
                # compute fresh file path for tab label
                label_path = self._editor_file_path(editor)
                if label_path:
                    self.ui.documents.setTabText(
                        idx, os.path.basename(label_path)
                    )
            if saved:
                self._save_project_session()
            return saved
        else:
            # fallback for legacy
            if not file_path:
                return self._save_as_tab(editor)
            path_to_write = getattr(
                editor, "current_file_path", None
            ) or getattr(editor, "file_path", None)
            with open(path_to_write, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
            idx = self.ui.documents.indexOf(editor)
            if idx != -1 and path_to_write:
                self.ui.documents.setTabText(
                    idx, os.path.basename(path_to_write)
                )
            self._save_project_session()
            return True

    def _save_as_tab(self, editor):
        # Use the DocumentEditorWidget API for save-as
        try:
            self.logger.debug(
                "_save_as_tab: ENTRY - opening Save File As dialog"
            )
        except Exception:
            pass
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File As")
        try:
            self.logger.debug(
                f"_save_as_tab: dialog returned file_path={file_path}"
            )
        except Exception:
            pass
        if not file_path:
            return False
        # Prefer storing in the widget's `current_file_path` so we don't shadow methods
        if hasattr(editor, "current_file_path"):
            try:
                editor.current_file_path = file_path
            except Exception:
                pass
        else:
            # last resort: set attribute
            try:
                setattr(editor, "file_path", file_path)
            except Exception:
                pass
        if hasattr(editor, "save_file"):
            try:
                editor.save_file(file_path)
            except Exception as e:
                try:
                    QMessageBox.warning(
                        self, "Save As Error", f"Failed to save file: {e}"
                    )
                except Exception:
                    pass
                return False
        else:
            try:
                # Determine a concrete path to write to. editor.file_path may be
                # a method on some implementations, so prefer current_file_path
                # attribute or call the method if callable.
                try:
                    if hasattr(editor, "file_path") and callable(
                        getattr(editor, "file_path")
                    ):
                        write_path = editor.file_path()
                    else:
                        write_path = getattr(
                            editor, "current_file_path", None
                        ) or getattr(editor, "file_path", None)
                except Exception:
                    write_path = getattr(
                        editor, "current_file_path", None
                    ) or getattr(editor, "file_path", None)

                if not write_path:
                    # As a last resort, use the file_path we just selected
                    write_path = file_path

                with open(write_path, "w", encoding="utf-8") as f:
                    # editor may provide a text accessor; fallback to toPlainText
                    if hasattr(editor, "editor") and hasattr(
                        editor.editor, "toPlainText"
                    ):
                        f.write(editor.editor.toPlainText())
                    elif hasattr(editor, "toPlainText"):
                        f.write(editor.toPlainText())
                    else:
                        # Nothing sensible to write
                        f.write("")
            except Exception as e:
                try:
                    QMessageBox.warning(
                        self, "Save As Error", f"Failed to save file: {e}"
                    )
                except Exception:
                    pass
                return False
        # Update tab label using a safe path lookup (method vs attribute)
        idx = self.ui.documents.indexOf(editor)
        if idx != -1:
            label_path = self._editor_file_path(editor)

            if not label_path:
                label_path = file_path

            if label_path:
                try:
                    self.ui.documents.setTabText(
                        idx, os.path.basename(label_path)
                    )
                except Exception:
                    pass
        self._save_project_session()
        return True

    def _reopen_tab(self, file_path):
        self._open_file_tab(file_path)

    def on_documents_tabCloseRequested(self, index: int) -> None:
        """Handle the QTabWidget tabCloseRequested signal for `documents`.

        Prompts to save if the document is modified. Supports Save / Discard / Cancel.
        """
        widget = self.ui.documents.widget(index)
        if widget is None:
            return

        # Determine the editor's associated file path (if any)
        try:
            if hasattr(widget, "file_path") and callable(
                getattr(widget, "file_path")
            ):
                try:
                    editor_path = widget.file_path()
                except Exception:
                    editor_path = None
            else:
                editor_path = getattr(
                    widget, "current_file_path", None
                ) or getattr(widget, "file_path", None)
        except Exception:
            editor_path = None

        # If the widget exposes an is_modified() API, use it to decide whether to prompt
        try:
            modified = False
            if hasattr(widget, "is_modified") and callable(
                getattr(widget, "is_modified")
            ):
                modified = widget.is_modified()
        except Exception:
            modified = False

        if modified:
            # If the editor has an associated file, auto-save to that file without prompting.
            if editor_path:
                try:
                    if hasattr(widget, "save_file") and callable(
                        getattr(widget, "save_file")
                    ):
                        ok = widget.save_file()
                        # If save_file returns False or failed, abort close
                        if ok is False:
                            return
                    else:
                        # Fallback: write contents directly
                        try:
                            content = None
                            if hasattr(widget, "editor") and hasattr(
                                widget.editor, "toPlainText"
                            ):
                                content = widget.editor.toPlainText()
                            elif hasattr(widget, "toPlainText"):
                                content = widget.toPlainText()
                            else:
                                content = ""
                            with open(editor_path, "w", encoding="utf-8") as f:
                                f.write(content)
                        except Exception as e:
                            QMessageBox.warning(
                                self,
                                "Error",
                                f"Error saving file {editor_path}: {e}",
                            )
                            return
                except Exception:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "Failed to autosave document before closing.",
                    )
                    return
            else:
                # No associated file: ask the user whether to save changes
                resp = QMessageBox.question(
                    self,
                    "Save changes?",
                    "The document has unsaved changes. Do you want to save them?",
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                    | QMessageBox.StandardButton.Cancel,
                )
                if resp == QMessageBox.StandardButton.Cancel:
                    return
                if resp == QMessageBox.StandardButton.Yes:
                    # Attempt to save using existing helper; if user cancels save-as, abort close
                    self._save_tab(widget)

        # Remove the tab and schedule the widget for deletion
        self.ui.documents.removeTab(index)
        widget.deleteLater()
        self._save_project_session()

    def _on_close_shortcut(self) -> None:
        """Handle Ctrl+W: close the currently active document tab using the
        same logic as if the tab close button was pressed.
        """
        try:
            idx = self.ui.documents.currentIndex()
            if idx is None or idx < 0:
                return
            # Reuse existing handler which handles prompts and cleanup.
            self.on_documents_tabCloseRequested(idx)
        except Exception:
            try:
                QMessageBox.warning(
                    self, "Error", "Failed to close document tab"
                )
            except Exception:
                pass

    def _on_save_shortcut(self) -> None:
        """Handle Ctrl+S: save the currently active document tab."""
        try:
            self.logger.debug("_on_save_shortcut: ENTRY")
        except Exception:
            pass
        try:
            idx = self.ui.documents.currentIndex()
            if idx is None or idx < 0:
                try:
                    self.logger.debug(
                        "_on_save_shortcut: no valid index, returning"
                    )
                except Exception:
                    pass
                return
            widget = self.ui.documents.widget(idx)
            if widget is None:
                try:
                    self.logger.debug(
                        "_on_save_shortcut: no valid widget, returning"
                    )
                except Exception:
                    pass
                return
            # Reuse _save_tab to handle save-or-save-as logic
            try:
                try:
                    self.logger.debug("_on_save_shortcut: calling _save_tab")
                except Exception:
                    pass
                self._save_tab(widget)
            except Exception:
                # try to call widget.save_file directly as a fallback
                try:
                    if hasattr(widget, "save_file"):
                        widget.save_file()
                except Exception:
                    QMessageBox.warning(
                        self, "Save Error", "Failed to save document"
                    )
        except Exception:
            pass
        finally:
            try:
                self.logger.debug("_on_save_shortcut: EXIT")
            except Exception:
                pass

    def _on_save_as_shortcut(self) -> None:
        """Handle Ctrl+Shift+S: perform Save As for the currently active tab.

        This implementation disables the plain Save shortcut while Save As
        runs, calls the save-as helper, and logs any exception. It avoids
        opening a second Save As dialog as a fallback.
        """
        try:
            self.logger.debug("_on_save_as_shortcut: ENTRY")
        except Exception:
            pass

        if getattr(self, "_in_save_as", False):
            try:
                self.logger.debug(
                    "_on_save_as_shortcut: ALREADY IN SAVE_AS, returning"
                )
            except Exception:
                pass
            return
        self._in_save_as = True

        try:
            idx = self.ui.documents.currentIndex()
            if idx is None or idx < 0:
                try:
                    self.logger.debug(
                        "_on_save_as_shortcut: no valid index, returning"
                    )
                except Exception:
                    pass
                return

            widget = self.ui.documents.widget(idx)
            if widget is None:
                try:
                    self.logger.debug(
                        "_on_save_as_shortcut: no valid widget, returning"
                    )
                except Exception:
                    pass
                return

            # Temporarily disable the save shortcut object to avoid it being
            # triggered while Save As dialog is open.
            if (
                hasattr(self, "_save_shortcut")
                and self._save_shortcut is not None
            ):
                try:
                    self.logger.debug(
                        "_on_save_as_shortcut: disabling save shortcut"
                    )
                    self._save_shortcut.setEnabled(False)
                except Exception:
                    pass

            self.logger.debug("_on_save_as_shortcut: calling _save_as_tab")
            ok = False
            try:
                ok = bool(self._save_as_tab(widget))
            except Exception:
                # capture exception and log it
                try:
                    import traceback

                    self.logger.debug(
                        "_on_save_as_shortcut: exception from _save_as_tab:\n"
                        + traceback.format_exc()
                    )
                except Exception:
                    pass
                ok = False

            if not ok:
                try:
                    QMessageBox.warning(
                        self, "Save As Error", "Failed to Save As"
                    )
                except Exception:
                    pass

        finally:
            # Re-enable save shortcut and clear guard
            try:
                if (
                    hasattr(self, "_save_shortcut")
                    and self._save_shortcut is not None
                ):
                    try:
                        self.logger.debug(
                            "_on_save_as_shortcut: re-enabling save shortcut"
                        )
                        self._save_shortcut.setEnabled(True)
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                self.logger.debug("_on_save_as_shortcut: EXIT")
            except Exception:
                pass
            self._in_save_as = False
