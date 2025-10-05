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
from PySide6.QtWidgets import QFileDialog, QMessageBox
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
        self._script_process = None
        self._splitters = ["vertical_splitter", "splitter"]
        self.signal_handlers = {
            SignalCode.FILE_EXPLORER_OPEN_FILE: self.open_file_in_new_tab,
            SignalCode.RUN_SCRIPT: self.run_script,
            SignalCode.NEW_DOCUMENT: self.handle_new_document_signal,
        }
        super().__init__(*args, **kwargs)
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

    def handle_new_document_signal(self, data: Dict):
        self._new_tab()

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
                        return
                except Exception:
                    # ignore path normalization errors and continue
                    pass

        editor = DocumentEditorWidget()
        editor.load_file(file_path)
        # load_file sets editor.current_file_path; avoid setting editor.file_path attribute
        filename = os.path.basename(file_path)
        self.ui.documents.addTab(editor, filename)
        self.ui.documents.setCurrentWidget(editor)

    def _new_tab(self):
        editor = DocumentEditorWidget()
        # Leave editor.current_file_path as the source of truth; do not set an attribute
        self.ui.documents.addTab(editor, "Untitled")
        self.ui.documents.setCurrentWidget(editor)

    def _save_tab(self, editor):
        # Use the DocumentEditorWidget API for saving
        # Resolve file path using available API (method or attributes)
        if hasattr(editor, "file_path") and callable(
            getattr(editor, "file_path")
        ):
            try:
                file_path = editor.file_path()
            except Exception:
                file_path = None
        else:
            file_path = getattr(editor, "current_file_path", None) or getattr(
                editor, "file_path", None
            )

        if hasattr(editor, "save_file"):
            if not file_path:
                return self._save_as_tab(editor)
            editor.save_file()
            idx = self.ui.documents.indexOf(editor)
            if idx != -1:
                # compute fresh file path for tab label
                label_path = None
                if hasattr(editor, "file_path") and callable(
                    getattr(editor, "file_path")
                ):
                    try:
                        label_path = editor.file_path()
                    except Exception:
                        label_path = None
                else:
                    label_path = getattr(
                        editor, "current_file_path", None
                    ) or getattr(editor, "file_path", None)
                if label_path:
                    self.ui.documents.setTabText(
                        idx, os.path.basename(label_path)
                    )
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

    def _save_as_tab(self, editor):
        # Use the DocumentEditorWidget API for save-as
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File As")
        if not file_path:
            return
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
                    prev_tab_count = self.ui.documents.count()
                    self._save_tab(widget)

        # Remove the tab and schedule the widget for deletion
        self.ui.documents.removeTab(index)
        widget.deleteLater()
