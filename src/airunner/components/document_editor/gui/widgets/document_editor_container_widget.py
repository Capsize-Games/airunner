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
from airunner.gui.widgets.base_widget import BaseWidget
from PySide6.QtWidgets import QWidget, QTabWidget, QFileDialog
from airunner.components.document_editor.gui.widgets.document_editor_widget import (
    DocumentEditorWidget,
)
import os
from airunner.components.browser.gui.widgets.mixins.tab_manager_mixin import (
    TabManagerMixin,
)
from airunner.components.file_explorer.gui.widgets.file_explorer_widget import (
    FileExplorerWidget,
)
from airunner.components.file_explorer.gui.templates.file_explorer_ui import (
    Ui_file_explorer,
)


class DocumentEditorContainerWidget(TabManagerMixin, BaseWidget):
    """Container for the DocumentEditorWidget, for use in tabbed or multi-document interfaces."""

    widget_class_ = Ui_document_editor_container

    def __init__(self, *args, **kwargs):
        self._splitters = ["splitter"]
        self.signal_handlers = {
            SignalCode.FILE_EXPLORER_OPEN_FILE: self.open_file_in_new_tab,
        }
        super().__init__(*args, **kwargs)
        self.setup_tab_manager(
            self.ui.documents,
            self._new_tab,
            self._save_tab,
            self._reopen_tab,
            self._save_as_tab,
        )

    def setup_tab_manager(self, *args, **kwargs):
        # Remove 'parent' from kwargs if present, since TabManagerMixin does not accept it
        kwargs.pop("parent", None)
        super().setup_tab_manager(*args, **kwargs)

    def open_file_in_new_tab(self, data: Dict) -> None:
        """Open a file in a new tab in the document editor tab widget."""
        file_path = data.get("file_path")
        self._open_file_tab(file_path)

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
