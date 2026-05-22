"""Tests for canvas layer alignment callbacks."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import QPointF, QRectF

from airunner.components.art.gui.widgets.canvas.canvas_widget import (
    CanvasWidget,
)


def test_align_center_horizontal_updates_selected_layer_position():
    """Horizontal centering should persist the selected layer position."""
    layer_item = Mock()
    layer_item.boundingRect.return_value = QRectF(0, 0, 200, 100)
    scene = SimpleNamespace(
        _layer_items={7: layer_item},
        original_item_positions={},
        _begin_layer_history_transaction=Mock(),
        _commit_layer_history_transaction=Mock(),
        _cancel_layer_history_transaction=Mock(),
    )
    widget = CanvasWidget.__new__(CanvasWidget)
    widget.ui = SimpleNamespace(canvas_container=SimpleNamespace(scene=scene))
    widget.api = SimpleNamespace(
        art=SimpleNamespace(
            canvas=SimpleNamespace(
                update_image_positions=Mock(),
                update_grid_info=Mock(),
            )
        )
    )
    widget.logger = Mock()
    widget.update_drawing_pad_settings = Mock()
    widget._update_status_labels = Mock()
    widget._get_current_selected_layer_id = Mock(return_value=7)
    widget._get_layer_specific_settings = Mock(
        return_value=SimpleNamespace(x_pos=120, y_pos=210, image=b"")
    )
    widget._document_origin = Mock(return_value=(100, 50))
    widget._document_width = Mock(return_value=800)
    widget._document_height = Mock(return_value=600)

    CanvasWidget.on_align_center_horizontal_clicked(widget)

    widget.update_drawing_pad_settings.assert_called_once_with(
        layer_id=7,
        x_pos=400,
        y_pos=210,
    )
    cached_position = scene.original_item_positions[layer_item]
    assert cached_position == QPointF(400.0, 210.0)
    scene._begin_layer_history_transaction.assert_called_once_with(
        7,
        "position",
    )
    scene._commit_layer_history_transaction.assert_called_once_with(
        7,
        "position",
    )
    scene._cancel_layer_history_transaction.assert_not_called()
    widget.api.art.canvas.update_image_positions.assert_called_once_with()
    widget.api.art.canvas.update_grid_info.assert_called_once_with({})
    widget._update_status_labels.assert_called_once_with()


def test_align_center_vertical_updates_selected_layer_position():
    """Vertical centering should persist the selected layer position."""
    layer_item = Mock()
    layer_item.boundingRect.return_value = QRectF(0, 0, 200, 100)
    scene = SimpleNamespace(
        _layer_items={7: layer_item},
        original_item_positions={},
        _begin_layer_history_transaction=Mock(),
        _commit_layer_history_transaction=Mock(),
        _cancel_layer_history_transaction=Mock(),
    )
    widget = CanvasWidget.__new__(CanvasWidget)
    widget.ui = SimpleNamespace(canvas_container=SimpleNamespace(scene=scene))
    widget.api = SimpleNamespace(
        art=SimpleNamespace(
            canvas=SimpleNamespace(
                update_image_positions=Mock(),
                update_grid_info=Mock(),
            )
        )
    )
    widget.logger = Mock()
    widget.update_drawing_pad_settings = Mock()
    widget._update_status_labels = Mock()
    widget._get_current_selected_layer_id = Mock(return_value=7)
    widget._get_layer_specific_settings = Mock(
        return_value=SimpleNamespace(x_pos=120, y_pos=210, image=b"")
    )
    widget._document_origin = Mock(return_value=(100, 50))
    widget._document_width = Mock(return_value=800)
    widget._document_height = Mock(return_value=600)

    CanvasWidget.on_align_center_vertical_clicked(widget)

    widget.update_drawing_pad_settings.assert_called_once_with(
        layer_id=7,
        x_pos=120,
        y_pos=300,
    )
    cached_position = scene.original_item_positions[layer_item]
    assert cached_position == QPointF(120.0, 300.0)


def test_align_center_callbacks_ignore_missing_layer_selection():
    """No-op when no layer is selected."""
    widget = CanvasWidget.__new__(CanvasWidget)
    widget.ui = SimpleNamespace(canvas_container=SimpleNamespace(scene=None))
    widget.api = SimpleNamespace(
        art=SimpleNamespace(
            canvas=SimpleNamespace(
                update_image_positions=Mock(),
                update_grid_info=Mock(),
            )
        )
    )
    widget.logger = Mock()
    widget.update_drawing_pad_settings = Mock()
    widget._update_status_labels = Mock()
    widget._get_current_selected_layer_id = Mock(return_value=None)

    CanvasWidget.on_align_center_horizontal_clicked(widget)
    CanvasWidget.on_align_center_vertical_clicked(widget)

    widget.update_drawing_pad_settings.assert_not_called()
    widget.api.art.canvas.update_image_positions.assert_not_called()
    widget.api.art.canvas.update_grid_info.assert_not_called()