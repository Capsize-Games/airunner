"""
Widget for displaying a list of items (bookmarks or history) in a tree or list view.

This widget is used in the browser left panel for bookmarks/history, using the generated items_ui.py template.
"""

from PySide6.QtWidgets import (
    QWidget,
    QTreeView,  # Changed from QListView
    QVBoxLayout,
    QMenu,
    QMessageBox,
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal, Slot, QModelIndex, Qt
from airunner.components.browser.gui.widgets.templates.items_ui import (
    Ui_items_widget,
)


class ItemsWidget(QWidget):
    """Widget for displaying and interacting with a list of items (bookmarks/history)."""

    item_activated = Signal(dict)  # Emitted when an item is clicked/activated
    items_deleted = Signal(list)  # List of item_data dicts
    item_edit_requested = Signal(dict)
    delete_all_requested = Signal()
    sort_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_items_widget()
        self.ui.setupUi(self)
        self.model = None
        # Replace QListView with QTreeView
        self.tree = QTreeView(self)
        self.tree.setObjectName("items")
        self.tree.setSelectionMode(QTreeView.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        self.tree.doubleClicked.connect(self._on_item_double_clicked)
        self.tree.clicked.connect(self._on_item_clicked)
        self.tree.keyPressEvent = self._on_key_press
        # Replace the QListView in the layout with QTreeView
        layout = self.layout() or QVBoxLayout(self)
        # Remove old QListView if present
        if hasattr(self.ui, "items"):
            self.ui.items.setParent(None)
        layout.addWidget(self.tree)
        self.setLayout(layout)
        # TODO: Connect delete all button and sort combo box when added to UI

    def set_model(self, model):
        self.model = model
        self.tree.setModel(model)
        self.tree.expandAll()

    @Slot(QModelIndex)
    def _on_item_clicked(self, index: QModelIndex):
        if not self.model:
            return
        item_data = self.model.data(index, role=Qt.UserRole)
        if item_data and item_data.get("type") == "bookmark":
            self.item_activated.emit(item_data)

    @Slot(QModelIndex)
    def _on_item_double_clicked(self, index: QModelIndex):
        self._on_item_clicked(index)

    def _on_context_menu(self, pos):
        indexes = self.tree.selectedIndexes()
        if not indexes:
            return
        item_data = self.model.data(indexes[0], role=Qt.UserRole)
        menu = QMenu(self)
        if item_data.get("type") == "bookmark":
            edit_action = QAction("Edit", self)
            delete_action = QAction("Delete", self)
            menu.addAction(edit_action)
            menu.addAction(delete_action)
            edit_action.triggered.connect(
                lambda: self.item_edit_requested.emit(item_data)
            )
            delete_action.triggered.connect(lambda: self._delete_selected())
        elif item_data.get("type") == "history":
            delete_action = QAction("Delete", self)
            menu.addAction(delete_action)
            delete_action.triggered.connect(lambda: self._delete_selected())
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _delete_selected(self):
        indexes = self.tree.selectedIndexes()
        items = [self.model.data(idx, role=Qt.UserRole) for idx in indexes]
        # Only emit bookmarks/history, not folders
        items = [
            i for i in items if i and i.get("type") in ("bookmark", "history")
        ]
        if items:
            self.items_deleted.emit(items)

    def _on_key_press(self, event):
        if event.key() == Qt.Key_Delete:
            self._delete_selected()
        else:
            QTreeView.keyPressEvent(self.tree, event)

    def set_delete_all_button(self, button):
        button.clicked.connect(self._on_delete_all_clicked)

    def _on_delete_all_clicked(self):
        reply = QMessageBox.question(
            self,
            "Delete All",
            "Delete all items?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.delete_all_requested.emit()

    def set_sort_combo(self, combo):
        combo.currentTextChanged.connect(self.sort_requested.emit)

    # TODO: Implement drag-and-drop, custom delegate for highlight, sorting logic
