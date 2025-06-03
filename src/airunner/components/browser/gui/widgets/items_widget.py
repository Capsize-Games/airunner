"""
Widget for displaying a list of items (bookmarks or history) in a tree or list view.

This widget is used in the browser left panel for bookmarks/history, using the generated items_ui.py template.
"""

from PySide6.QtWidgets import QWidget, QListView, QVBoxLayout
from PySide6.QtCore import Signal, Slot, QModelIndex
from airunner.components.browser.gui.widgets.templates.items_ui import (
    Ui_items_widget,
)


class ItemsWidget(QWidget):
    """Widget for displaying and interacting with a list of items (bookmarks/history)."""

    item_activated = Signal(dict)  # Emitted when an item is clicked/activated

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_items_widget()
        self.ui.setupUi(self)
        self.model = None
        self.ui.items.clicked.connect(self._on_item_clicked)

    def set_model(self, model):
        self.model = model
        self.ui.items.setModel(model)

    @Slot(QModelIndex)
    def _on_item_clicked(self, index: QModelIndex):
        if not self.model:
            return
        item_data = self.model.data(index, role=Qt.UserRole)
        if item_data:
            self.item_activated.emit(item_data)
