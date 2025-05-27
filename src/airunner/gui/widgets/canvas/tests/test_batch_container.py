"""
Unit tests for BatchContainer widget logic (headless, no real Qt GUI).
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.gui.widgets.canvas.batch_container import BatchContainer
from PySide6.QtGui import QShowEvent


@pytest.fixture
def mock_batch_container():
    # Patch BaseWidget.__init__ to avoid real Qt init
    with patch(
        "airunner.gui.widgets.base_widget.BaseWidget.__init__",
        lambda self, *a, **k: None,
    ):
        # Patch Ui_batch_conatiner to avoid real UI
        with patch(
            "airunner.gui.widgets.canvas.templates.batch_container_ui.Ui_batch_conatiner",
            autospec=True,
        ) as ui_cls:
            ui = MagicMock()
            # Patch image_folders with a currentTextChanged signal
            image_folders = MagicMock()
            image_folders.currentTextChanged.connect = MagicMock()
            ui.image_folders = image_folders
            ui_cls.return_value = ui
            # Patch path_settings property using PropertyMock
            path_settings = MagicMock()
            path_settings.image_path = "/tmp/fake_path"
            # Patch logic
            logic = MagicMock()
            # Patch SignalCode
            with patch(
                "airunner.gui.widgets.canvas.batch_container.SignalCode",
                MagicMock(),
            ):

                def basewidget_init(self, *a, **k):
                    self.ui = ui

                with patch(
                    "airunner.gui.widgets.base_widget.BaseWidget.__init__",
                    basewidget_init,
                ):
                    with patch.object(
                        BatchContainer,
                        "path_settings",
                        new_callable=PropertyMock,
                        return_value=path_settings,
                    ):
                        widget = BatchContainer()
                        widget.ui = ui
                        widget.logic = logic
                        widget.populate_date_folders = MagicMock()
                        widget.populate_current_folder = MagicMock()
                        return widget


def test_setup_ui_connections_connects_signal(mock_batch_container):
    mock_batch_container.ui.image_folders.currentTextChanged.connect.assert_called()


def test_clear_layout_removes_widgets(mock_batch_container):
    layout = MagicMock()
    widget1 = MagicMock()
    widget2 = MagicMock()
    item1 = MagicMock(widget=MagicMock(return_value=widget1))
    item2 = MagicMock(widget=MagicMock(return_value=widget2))
    layout.count.return_value = 2
    layout.itemAt.side_effect = [item1, item2]
    mock_batch_container._clear_layout(layout)
    widget1.setParent.assert_called_with(None)
    widget2.setParent.assert_called_with(None)


def test_showEvent_initializes_and_populates(mock_batch_container):
    event = QShowEvent()
    mock_batch_container.initialized = False
    with patch(
        "airunner.gui.widgets.base_widget.BaseWidget.showEvent",
        return_value=None,
    ):
        mock_batch_container.showEvent(event)
    assert mock_batch_container.initialized is True
    mock_batch_container.populate_date_folders.assert_called()
    mock_batch_container.populate_current_folder.assert_called()
