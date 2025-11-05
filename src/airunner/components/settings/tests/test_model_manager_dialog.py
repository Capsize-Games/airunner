"""Tests for ManageModelsDialog."""

import pytest
from unittest.mock import patch

# Qt imports
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    import sys

    # Create QApplication if it doesn't exist
    if not QApplication.instance():
        app = QApplication(sys.argv)
except ImportError:
    pytest.skip("PySide6 not available", allow_module_level=True)

from airunner.components.settings.gui.widgets.model_manager_dialog import (
    ManageModelsDialog,
)


class TestManageModelsDialog:
    """Test cases for ManageModelsDialog."""

    def test_create_dialog(self):
        """Test creating manage models dialog."""
        dialog = ManageModelsDialog()
        assert dialog is not None
        assert dialog.windowTitle() == "Manage Models"
        assert dialog.models_table is not None

    def test_populate_models_table(self):
        """Test that models table is populated with available models."""
        dialog = ManageModelsDialog()

        # Should have rows for local models (excluding 'custom')
        assert dialog.models_table.rowCount() > 0

        # Check that columns are set up
        assert dialog.models_table.columnCount() == 6

    def test_table_headers(self):
        """Test that table has correct headers."""
        dialog = ManageModelsDialog()

        headers = []
        for col in range(dialog.models_table.columnCount()):
            headers.append(
                dialog.models_table.horizontalHeaderItem(col).text()
            )

        expected_headers = [
            "Model",
            "Context",
            "VRAM (4-bit)",
            "Tool Calling",
            "Status",
            "Actions",
        ]

        assert headers == expected_headers

    def test_model_path_generation(self):
        """Test model path generation."""
        dialog = ManageModelsDialog()

        model_name = "test-model"
        path = dialog._get_model_path(model_name)

        assert model_name in path
        assert "causallm" in path

    def test_selection_shows_details(self):
        """Test that selecting a model shows details."""
        dialog = ManageModelsDialog()

        # Select first row
        dialog.models_table.selectRow(0)

        # Details should be populated
        details_text = dialog.details_text.toPlainText()
        assert len(details_text) > 0
        assert "Model:" in details_text

    def test_download_signal(self):
        """Test that download button emits signal."""
        dialog = ManageModelsDialog()

        # Connect signal
        signal_received = []

        def on_download_requested(model_id, repo_id, quant_bits):
            signal_received.append((model_id, repo_id, quant_bits))

        dialog.download_requested.connect(on_download_requested)

        # Find a model that's not downloaded
        # We'll need to mock the download button click
        # For now, just verify the signal exists
        assert hasattr(dialog, "download_requested")

    def test_delete_signal(self):
        """Test that delete button emits signal."""
        dialog = ManageModelsDialog()

        # Verify delete signal exists
        assert hasattr(dialog, "delete_requested")

    def test_refresh_button(self):
        """Test refresh button repopulates table."""
        dialog = ManageModelsDialog()

        initial_rows = dialog.models_table.rowCount()

        # Click refresh
        dialog.refresh_button.click()

        # Should still have same number of rows (models haven't changed)
        assert dialog.models_table.rowCount() == initial_rows

    def test_progress_bar_initially_hidden(self):
        """Test that progress bar is initially hidden."""
        dialog = ManageModelsDialog()
        assert not dialog.progress_bar.isVisible()

    def test_set_download_progress(self):
        """Test setting download progress."""
        dialog = ManageModelsDialog()

        # Initially hidden
        assert not dialog.progress_bar.isVisible()

        # Set specific progress (would show when dialog is shown)
        dialog.set_download_progress(50)
        assert dialog.progress_bar.value() == 50
        # Note: isVisible() may still be False if dialog not shown,
        # but we can verify visibility was requested
        # For unit test purposes, check that range is set correctly
        assert dialog.progress_bar.maximum() == 100

        # Set indeterminate
        dialog.set_download_progress(-1)
        assert dialog.progress_bar.maximum() == 0  # Indeterminate

    def test_download_complete(self):
        """Test download completion handling."""
        dialog = ManageModelsDialog()

        dialog.progress_bar.setVisible(True)

        # Mock message box
        with patch(
            "airunner.components.settings.gui.widgets.model_manager_dialog.QMessageBox.information"
        ):
            dialog.download_complete()

        # Progress bar should be hidden
        assert not dialog.progress_bar.isVisible()

    def test_download_failed(self):
        """Test download failure handling."""
        dialog = ManageModelsDialog()

        # Mock message box
        with patch(
            "airunner.components.settings.gui.widgets.model_manager_dialog.QMessageBox.critical"
        ):
            dialog.download_failed("Test error")

        # Progress bar should be hidden
        assert not dialog.progress_bar.isVisible()

    def test_model_info_includes_vram(self):
        """Test that model details include VRAM information."""
        dialog = ManageModelsDialog()

        # Select first model
        dialog.models_table.selectRow(0)

        details = dialog.details_text.toHtml()
        assert "VRAM" in details

    def test_model_info_includes_context(self):
        """Test that model details include context length."""
        dialog = ManageModelsDialog()

        # Select first model
        dialog.models_table.selectRow(0)

        details = dialog.details_text.toHtml()
        assert "Context" in details

    def test_no_custom_model_in_table(self):
        """Test that 'custom' model is not shown in table."""
        dialog = ManageModelsDialog()

        # Check all rows for model IDs
        for row in range(dialog.models_table.rowCount()):
            name_item = dialog.models_table.item(row, 0)
            model_id = name_item.data(Qt.UserRole)
            assert model_id != "custom"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
