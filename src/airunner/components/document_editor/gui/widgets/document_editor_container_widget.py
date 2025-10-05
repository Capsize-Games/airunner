"""
document_editor_container_widget.py

Container widget for the document/code editor, suitable for integration in larger layouts or tabbed interfaces.

Provides a place to host the DocumentEditorWidget and manage document-level actions (e.g., file open/save, tab management, etc.).
"""

from typing import Dict
import logging
from airunner.components.document_editor.gui.templates.document_editor_container_ui import (
    Ui_document_editor_container,
)
from airunner.enums import SignalCode
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
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
        # Track temporary files created for running unsaved buffers so they
        # can be removed after execution.
        self._temp_run_files = set()
        self._splitters = ["vertical_splitter", "splitter"]
        self.signal_handlers = {
            SignalCode.FILE_EXPLORER_OPEN_FILE: self.open_file_in_new_tab,
            SignalCode.RUN_SCRIPT: self.run_script,
            SignalCode.NEW_DOCUMENT: self.handle_new_document_signal,
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
        temp_file_flag = bool(data.get("temp_file", False))
        # Defensive: if no document_path provided (e.g., unsaved new doc),
        # warn the user and abort instead of passing None to os.path
        if not document_path:
            try:
                QMessageBox.warning(
                    self,
                    "Run Error",
                    "No file to run. Please save the document before running.",
                )
            except Exception:
                pass
            return
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
                if temp_file_flag:
                    try:
                        self._temp_run_files.add(document_path)
                    except Exception:
                        pass
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
                        code, status, document_path if temp_file_flag else None
                    )
                )
                process.errorOccurred.connect(
                    lambda err: self._on_process_error(
                        err, document_path if temp_file_flag else None
                    )
                )
                process.start()

    def _append_process_output(self, process: QProcess) -> None:
        data = process.readAllStandardOutput().data().decode("utf-8")
        if data:
            self.ui.terminal.appendPlainText(data)
        err = process.readAllStandardError().data().decode("utf-8")
        if err:
            self.ui.terminal.appendPlainText(err)

    def _on_process_finished(
        self, exit_code: int, exit_status, temp_path: str | None = None
    ) -> None:
        self.ui.terminal.appendPlainText(
            f"\n[Process finished with exit code {exit_code}]"
        )
        self._script_process = None
        # Cleanup temporary run file if one was used
        if temp_path:
            try:
                if temp_path in self._temp_run_files:
                    self._temp_run_files.discard(temp_path)
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        # Non-fatal: log and continue
                        self.ui.terminal.appendPlainText(
                            f"\n[Warning: failed to remove temp file {temp_path}]"
                        )
            except Exception:
                # Don't block on cleanup failures; log to terminal
                self.ui.terminal.appendPlainText(
                    f"\n[Warning: failed during temp file cleanup for {temp_path}]"
                )

    def _on_process_error(self, error, temp_path: str | None = None) -> None:
        self.ui.terminal.appendPlainText(f"\n[Process error: {error}]")
        # If a temporary run file was used, attempt to clean it up
        if temp_path:
            try:
                if temp_path in self._temp_run_files:
                    self._temp_run_files.discard(temp_path)
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        self.ui.terminal.appendPlainText(
                            f"\n[Warning: failed to remove temp file {temp_path}]"
                        )
            except Exception:
                self.ui.terminal.appendPlainText(
                    f"\n[Warning: failed during temp file cleanup for {temp_path}]"
                )

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
            if index is None or index < 0:
                return
            w = self.ui.documents.widget(index)
            if w is None:
                return
            if hasattr(w, "editor"):
                try:
                    w.editor.setFocus()
                except Exception:
                    pass
        except Exception:
            pass

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
            label_path = None
            try:
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
            except Exception:
                label_path = getattr(
                    editor, "current_file_path", None
                ) or getattr(editor, "file_path", None)

            if not label_path:
                label_path = file_path

            if label_path:
                try:
                    self.ui.documents.setTabText(
                        idx, os.path.basename(label_path)
                    )
                except Exception:
                    pass
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
                    prev_tab_count = self.ui.documents.count()
                    self._save_tab(widget)

        # Remove the tab and schedule the widget for deletion
        self.ui.documents.removeTab(index)
        widget.deleteLater()

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
