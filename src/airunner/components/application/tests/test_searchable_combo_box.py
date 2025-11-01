"""Tests for SearchableComboBox widget."""

import pytest

# Qt imports
try:
    from PySide6.QtWidgets import QApplication
    import sys

    # Create QApplication if it doesn't exist
    if not QApplication.instance():
        app = QApplication(sys.argv)
except ImportError:
    pytest.skip("PySide6 not available", allow_module_level=True)

from airunner.components.application.gui.widgets.searchable_combo_box import (
    SearchableComboBox,
)


class TestSearchableComboBox:
    """Test cases for SearchableComboBox."""

    def test_create_combo_box(self):
        """Test creating searchable combo box."""
        combo = SearchableComboBox()
        assert combo is not None
        assert combo.isEditable()
        assert combo.count() == 0

    def test_add_item_with_data(self):
        """Test adding single item with data."""
        combo = SearchableComboBox()
        combo.addItemWithData("Item 1", {"id": 1})

        assert combo.count() == 1
        assert combo.itemText(0) == "Item 1"
        assert combo.itemData(0) == {"id": 1}

    def test_add_items_with_data(self):
        """Test adding multiple items with data."""
        combo = SearchableComboBox()
        items = [
            ("Item 1", {"id": 1}),
            ("Item 2", {"id": 2}, "Tooltip for item 2"),
            ("Item 3", {"id": 3}),
        ]
        combo.addItemsWithData(items)

        assert combo.count() == 3
        assert combo.itemText(0) == "Item 1"
        assert combo.itemText(1) == "Item 2"
        assert combo.itemText(2) == "Item 3"

    def test_current_data(self):
        """Test getting current data."""
        combo = SearchableComboBox()
        combo.addItemsWithData(
            [
                ("Item 1", {"id": 1}),
                ("Item 2", {"id": 2}),
            ]
        )

        combo.setCurrentIndex(0)
        assert combo.currentData() == {"id": 1}

        combo.setCurrentIndex(1)
        assert combo.currentData() == {"id": 2}

    def test_set_current_data(self):
        """Test setting current selection by data."""
        combo = SearchableComboBox()
        data1 = {"id": 1}
        data2 = {"id": 2}

        combo.addItemsWithData(
            [
                ("Item 1", data1),
                ("Item 2", data2),
            ]
        )

        combo.setCurrentData(data2)
        assert combo.currentData() == data2

    def test_clear(self):
        """Test clearing items."""
        combo = SearchableComboBox()
        combo.addItemsWithData(
            [
                ("Item 1", {"id": 1}),
                ("Item 2", {"id": 2}),
            ]
        )

        assert combo.count() == 2

        combo.clear()
        assert combo.count() == 0

    def test_filter_search(self):
        """Test filtering items by search text."""
        combo = SearchableComboBox()
        combo.addItemsWithData(
            [
                ("Apple", {"fruit": "apple"}),
                ("Banana", {"fruit": "banana"}),
                ("Avocado", {"fruit": "avocado"}),
            ]
        )

        # Simulate typing "app" in line edit
        combo.lineEdit().setText("app")
        combo._on_text_edited("app")

        # Proxy model should filter to show only "Apple"
        assert combo.proxy_model.rowCount() == 1

    def test_item_selected_signal(self):
        """Test that itemSelected signal is emitted."""
        combo = SearchableComboBox()
        data1 = {"id": 1}
        data2 = {"id": 2}
        combo.addItemWithData("Item 1", data1)
        combo.addItemWithData("Item 2", data2)

        # Connect signal
        signal_received = []

        def on_item_selected(item_data):
            signal_received.append(item_data)

        combo.itemSelected.connect(on_item_selected)

        # Change selection to index 1
        combo.setCurrentIndex(1)

        # Signal should be emitted
        assert len(signal_received) == 1
        assert signal_received[0] == data2

    def test_placeholder_text(self):
        """Test setting placeholder text."""
        combo = SearchableComboBox()
        combo.setPlaceholderText("Search models...")

        assert combo.lineEdit().placeholderText() == "Search models..."

    def test_tooltip(self):
        """Test item tooltip."""
        combo = SearchableComboBox()
        combo.addItemWithData("Item 1", {"id": 1}, tooltip="This is item 1")

        item = combo.source_model.item(0)
        assert item.toolTip() == "This is item 1"

    def test_empty_current_data(self):
        """Test currentData with no selection."""
        combo = SearchableComboBox()
        assert combo.currentData() is None

    def test_case_insensitive_search(self):
        """Test case-insensitive filtering."""
        combo = SearchableComboBox()
        combo.addItemsWithData(
            [
                ("Apple", {"id": 1}),
                ("BANANA", {"id": 2}),
                ("AvOcAdO", {"id": 3}),
            ]
        )

        # Search with different case
        combo.lineEdit().setText("apple")
        combo._on_text_edited("apple")

        # Should find "Apple" despite case difference
        assert combo.proxy_model.rowCount() >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
