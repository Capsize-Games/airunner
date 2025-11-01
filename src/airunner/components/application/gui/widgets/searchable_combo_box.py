"""Searchable Combo Box Widget with VSCode-style filtering.

Provides a combo box with integrated search functionality, similar to
VSCode's quick pick interface.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
)
from PySide6.QtCore import Qt, Signal, QSortFilterProxyModel
from PySide6.QtGui import QStandardItemModel, QStandardItem


class SearchableComboBox(QComboBox):
    """Combo box with integrated search/filter functionality.

    Features:
    - Live search as you type
    - Fuzzy matching support
    - Preserves item data
    - Custom item rendering
    """

    # Signal emitted when selection changes (passes item data)
    itemSelected = Signal(object)

    def __init__(self, parent=None):
        """Initialize searchable combo box.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Make combo box editable for search
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)

        # Set up the model and proxy for filtering
        self.source_model = QStandardItemModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(0)

        self.setModel(self.proxy_model)

        # Set up completer for auto-completion
        self.completer_obj = QCompleter(self.proxy_model, self)
        self.completer_obj.setCompletionMode(QCompleter.PopupCompletion)
        self.completer_obj.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(self.completer_obj)

        # Connect signals
        self.lineEdit().textEdited.connect(self._on_text_edited)
        self.currentIndexChanged.connect(self._on_index_changed)

    def _on_text_edited(self, text: str):
        """Handle text editing for live filtering.

        Args:
            text: Current text in line edit
        """
        # Apply filter to proxy model
        self.proxy_model.setFilterWildcard(f"*{text}*")

        # Show popup if hidden
        if not self.view().isVisible():
            self.showPopup()

    def _on_index_changed(self, index: int):
        """Handle selection change.

        Args:
            index: New index
        """
        if index >= 0:
            # Get the actual data from the proxy model
            proxy_index = self.proxy_model.index(index, 0)
            source_index = self.proxy_model.mapToSource(proxy_index)
            item = self.source_model.itemFromIndex(source_index)

            if item:
                data = item.data(Qt.UserRole)
                self.itemSelected.emit(data)

    def addItemWithData(
        self, text: str, data: object, tooltip: Optional[str] = None
    ):
        """Add item with associated data.

        Args:
            text: Display text
            data: Associated data object
            tooltip: Optional tooltip text
        """
        item = QStandardItem(text)
        item.setData(data, Qt.UserRole)

        if tooltip:
            item.setToolTip(tooltip)

        self.source_model.appendRow(item)

    def addItemsWithData(self, items: List[tuple]):
        """Add multiple items with data.

        Args:
            items: List of (text, data, tooltip?) tuples
        """
        for item_info in items:
            if len(item_info) == 2:
                text, data = item_info
                self.addItemWithData(text, data)
            elif len(item_info) == 3:
                text, data, tooltip = item_info
                self.addItemWithData(text, data, tooltip)

    def clear(self):
        """Clear all items."""
        self.source_model.clear()

    def currentData(self) -> Optional[object]:
        """Get data for currently selected item.

        Returns:
            Data object or None
        """
        current_index = self.currentIndex()
        if current_index < 0:
            return None

        proxy_index = self.proxy_model.index(current_index, 0)
        source_index = self.proxy_model.mapToSource(proxy_index)
        item = self.source_model.itemFromIndex(source_index)

        return item.data(Qt.UserRole) if item else None

    def setCurrentData(self, data: object):
        """Set current selection by data.

        Args:
            data: Data to match
        """
        for row in range(self.source_model.rowCount()):
            item = self.source_model.item(row)
            if item and item.data(Qt.UserRole) == data:
                # Map source index to proxy index
                source_index = self.source_model.indexFromItem(item)
                proxy_index = self.proxy_model.mapFromSource(source_index)
                self.setCurrentIndex(proxy_index.row())
                break

    def setPlaceholderText(self, text: str):
        """Set placeholder text for line edit.

        Args:
            text: Placeholder text
        """
        if self.lineEdit():
            self.lineEdit().setPlaceholderText(text)

    def count(self) -> int:
        """Get number of items in source model.

        Returns:
            Item count
        """
        return self.source_model.rowCount()

    def itemText(self, index: int) -> str:
        """Get text for item at index.

        Args:
            index: Item index in source model

        Returns:
            Item text or empty string
        """
        item = self.source_model.item(index)
        return item.text() if item else ""

    def itemData(self, index: int) -> Optional[object]:
        """Get data for item at index.

        Args:
            index: Item index in source model

        Returns:
            Item data or None
        """
        item = self.source_model.item(index)
        return item.data(Qt.UserRole) if item else None
