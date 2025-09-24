"""
file_explorer_widget.py

FileExplorerWidget for browsing and managing files/directories. Emits a signal when a file is requested to be opened.
"""

from typing import Optional
from PySide6.QtCore import QDir, QFileInfo, QModelIndex, Qt, QPoint
from PySide6.QtWidgets import (
    QWidget,
    QFileSystemModel,
    QMenu,
    QMessageBox,
)

from airunner.components.file_explorer.gui.templates.file_explorer_ui import (
    Ui_file_explorer,
)
from airunner.enums import SignalCode
from airunner.components.application.gui.widgets.base_widget import BaseWidget


class FileExplorerWidget(BaseWidget):
    """File explorer widget with file open signal and context menu for file operations."""

    widget_class_ = Ui_file_explorer

    def __init__(
        self,
        path_to_display: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        # Robust handling for UI-instantiated widgets: if first arg is QWidget, treat as parent
        self.emit_signal = None
        self._file_open_slot = None
        if isinstance(path_to_display, QWidget) and parent is None:
            parent = path_to_display
            path_to_display = None
        super().__init__(parent)
        self.model = QFileSystemModel(self)
        # Use path_to_display if provided, else self.user_web_dir, else current path
        root_path = (
            path_to_display
            if isinstance(path_to_display, str) and path_to_display
            else getattr(self, "user_web_dir", None) or QDir.currentPath()
        )
        self.model.setRootPath(root_path)
        self.model.setFilter(
            QDir.Filter.NoDotAndDotDot
            | QDir.Filter.AllDirs
            | QDir.Filter.Files
        )
        self.tree_view = self.ui.treeView
        self.tree_view.setModel(self.model)
        self.tree_view.setRootIndex(self.model.index(root_path))
        self.tree_view.setAnimated(False)
        self.tree_view.setIndentation(20)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.tree_view.setColumnHidden(1, True)
        self.tree_view.setColumnHidden(2, True)
        self.tree_view.setColumnHidden(3, True)
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)
        self.tree_view.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.tree_view.customContextMenuRequested.connect(
            self._show_context_menu
        )

    def _on_item_double_clicked(self, index: QModelIndex):
        file_path = self.model.filePath(index)
        file_info = QFileInfo(file_path)
        if file_info.isFile():
            self.emit_signal(
                SignalCode.FILE_EXPLORER_OPEN_FILE, {"file_path": file_path}
            )

    def set_root_directory(self, path_str: str):
        self.model.setRootPath(path_str)
        self.tree_view.setRootIndex(self.model.index(path_str))

    def _show_context_menu(self, position: QPoint):
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return
        menu = QMenu(self)
        file_path = self.model.filePath(index)
        file_info = self.model.fileInfo(index)
        if file_info.isFile():
            open_action = menu.addAction("Open")
            open_action.triggered.connect(
                lambda: self.emit_signal(
                    SignalCode.FILE_EXPLORER_OPEN_FILE, file_path
                )
            )
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self._rename_item(index))
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._delete_item(index))
        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def _rename_item(self, index: QModelIndex):
        self.tree_view.edit(index)

    def _delete_item(self, index: QModelIndex):
        file_path = self.model.filePath(index)
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{file_path}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.model.fileInfo(index).isDir():
                self.model.rmdir(index)
            else:
                self.model.remove(index)

    def connect_signal(self, signal_code, slot):
        # Only supports FILE_EXPLORER_OPEN_FILE for now
        if signal_code == SignalCode.FILE_EXPLORER_OPEN_FILE:
            self._file_open_slot = slot

            # Patch emit_signal to call the slot directly for this code
            def emit_signal(code, data):
                if code == SignalCode.FILE_EXPLORER_OPEN_FILE:
                    slot(data)

            self.emit_signal = emit_signal
        else:
            raise NotImplementedError(
                "Only FILE_EXPLORER_OPEN_FILE is supported in connect_signal."
            )
