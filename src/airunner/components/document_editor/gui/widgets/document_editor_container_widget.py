"""
document_editor_container_widget.py

Container widget for the document/code editor, suitable for integration in larger layouts or tabbed interfaces.

Provides a place to host the DocumentEditorWidget and manage document-level actions (e.g., file open/save, tab management, etc.).
"""

from typing import Dict
from airunner.components.document_editor.gui.templates.document_editor_container_ui import (
    Ui_document_editor_container,
)
from airunner.enums import SignalCode
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from PySide6.QtWidgets import QFileDialog
from airunner.components.document_editor.gui.widgets.document_editor_widget import (
    DocumentEditorWidget,
)
import os
import sys
from PySide6.QtCore import QProcess


class DocumentEditorContainerWidget(BaseWidget):
    """Container for the DocumentEditorWidget, for use in tabbed or multi-document interfaces."""

    widget_class_ = Ui_document_editor_container

    def __init__(self, *args, **kwargs):
        self.splitters = ["splitter", "vertical_splitter"]
        self.signal_handlers = {
            SignalCode.FILE_EXPLORER_OPEN_FILE: self.open_file_in_new_tab,
            SignalCode.RUN_SCRIPT: self.run_script,
        }
        super().__init__(*args, **kwargs)

    def setup_tab_manager(self, *args, **kwargs):
        # Remove 'parent' from kwargs if present, since TabManagerMixin does not accept it
        kwargs.pop("parent", None)
        super().setup_tab_manager(*args, **kwargs)

    def open_file_in_new_tab(self, data: Dict) -> None:
        """Open a file in a new tab in the document editor tab widget."""
        file_path = data.get("file_path")
        self._open_file_tab(file_path)

    def run_script(self, data: Dict) -> None:
        document_path = data.get("document_path")
        if os.path.exists(document_path) and os.path.isfile(document_path):
            suffix = os.path.splitext(document_path)[1].lower()
            if suffix in [".py"]:
                # Ensure only one process at a time
                if (
                    hasattr(self, "_script_process")
                    and self._script_process is not None
                ):
                    self._script_process.kill()
                    self._script_process = None
                self.ui.terminal.clear()
                process = QProcess(self)
                self._script_process = process
                script_dir = os.path.dirname(document_path)
                python_exe = sys.executable
                process.setProgram(python_exe)
                process.setArguments([document_path])
                process.setWorkingDirectory(script_dir)
                process.setProcessChannelMode(
                    QProcess.ProcessChannelMode.MergedChannels
                )
                process.readyReadStandardOutput.connect(
                    lambda: self._append_process_output(process)
                )
                process.readyReadStandardError.connect(
                    lambda: self._append_process_output(process)
                )
                process.finished.connect(
                    lambda code, status: self._on_process_finished(
                        code, status
                    )
                )
                process.errorOccurred.connect(
                    lambda err: self._on_process_error(err)
                )
                process.start()

    def _append_process_output(self, process: QProcess) -> None:
        data = process.readAllStandardOutput().data().decode("utf-8")
        if data:
            self.ui.terminal.appendPlainText(data)
        err = process.readAllStandardError().data().decode("utf-8")
        if err:
            self.ui.terminal.appendPlainText(err)

    def _on_process_finished(self, exit_code: int, exit_status) -> None:
        self.ui.terminal.appendPlainText(
            f"\n[Process finished with exit code {exit_code}]"
        )
        self._script_process = None

    def _on_process_error(self, error) -> None:
        self.ui.terminal.appendPlainText(f"\n[Process error: {error}]")
        self._script_process = None

    def _open_file_tab(self, file_path: str):
        editor = DocumentEditorWidget()
        editor.load_file(file_path)
        editor.file_path = file_path
        filename = os.path.basename(file_path)
        self.ui.documents.addTab(editor, filename)
        self.ui.documents.setCurrentWidget(editor)

    def _new_tab(self):
        print("NEW TAB PRESSED")
        editor = DocumentEditorWidget()
        editor.file_path = None
        self.ui.documents.addTab(editor, "Untitled")
        self.ui.documents.setCurrentWidget(editor)

    def _save_tab(self, editor):
        # Use the DocumentEditorWidget API for saving
        file_path = getattr(editor, "file_path", None)
        if hasattr(editor, "save_file"):
            if not file_path:
                return self._save_as_tab(editor)
            editor.save_file()
            idx = self.ui.documents.indexOf(editor)
            if idx != -1:
                self.ui.documents.setTabText(
                    idx, os.path.basename(editor.file_path)
                )
        else:
            # fallback for legacy
            if not file_path:
                return self._save_as_tab(editor)
            with open(editor.file_path, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
            idx = self.ui.documents.indexOf(editor)
            if idx != -1:
                self.ui.documents.setTabText(
                    idx, os.path.basename(editor.file_path)
                )

    def _save_as_tab(self, editor):
        # Use the DocumentEditorWidget API for save-as
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File As")
        if not file_path:
            return
        editor.file_path = file_path
        if hasattr(editor, "save_file"):
            editor.save_file(file_path)
        else:
            with open(editor.file_path, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
        idx = self.ui.documents.indexOf(editor)
        if idx != -1:
            self.ui.documents.setTabText(
                idx, os.path.basename(editor.file_path)
            )

    def _reopen_tab(self, file_path):
        self._open_file_tab(file_path)
