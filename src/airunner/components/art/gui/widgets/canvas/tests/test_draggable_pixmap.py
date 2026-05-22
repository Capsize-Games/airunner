"""Tests for draggable image item mouse handling and image updates."""

from unittest.mock import Mock

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QGraphicsItem

from airunner.enums import CanvasToolName
from airunner.components.art.gui.widgets.canvas.draggables.draggable_pixmap import (
    DraggablePixmap,
)


class DraggablePixmapStub(DraggablePixmap):
    """DraggablePixmap with controllable tool state for tests."""

    def __init__(self, qimage: QImage):
        self._test_current_tool = None
        super().__init__(qimage=qimage, use_layer_context=False)

    @property
    def current_tool(self):
        return self._test_current_tool


class TestDraggablePixmapMouseHandling:
    """Non-move tools should not start item-level drag handling."""

    def test_initial_state_disables_item_mouse_without_move_tool(self, qapp):
        item = DraggablePixmapStub(QImage(8, 8, QImage.Format_ARGB32))

        assert item.acceptedMouseButtons() == Qt.MouseButton.NoButton
        assert not bool(
            item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )

    def test_tool_change_enables_item_mouse_for_move_tool(self, qapp):
        item = DraggablePixmapStub(QImage(8, 8, QImage.Format_ARGB32))
        item._test_current_tool = CanvasToolName.MOVE

        item.on_tool_changed_signal()

        assert item.acceptedMouseButtons() == Qt.MouseButton.LeftButton
        assert bool(
            item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )

    def test_mouse_press_ignores_non_move_tool(self, qapp):
        item = DraggablePixmapStub(QImage(8, 8, QImage.Format_ARGB32))
        item._test_current_tool = CanvasToolName.BRUSH
        item.on_tool_changed_signal()
        event = Mock()

        item.mousePressEvent(event)

        event.ignore.assert_called_once_with()

    def test_mouse_move_ignores_non_move_tool(self, qapp):
        item = DraggablePixmapStub(QImage(8, 8, QImage.Format_ARGB32))
        item._test_current_tool = CanvasToolName.BRUSH
        item.on_tool_changed_signal()
        event = Mock()

        item.mouseMoveEvent(event)

        event.ignore.assert_called_once_with()

    def test_mouse_release_ignores_non_move_tool(self, qapp):
        item = DraggablePixmapStub(QImage(8, 8, QImage.Format_ARGB32))
        item._test_current_tool = CanvasToolName.BRUSH
        item.on_tool_changed_signal()
        event = Mock()

        item.mouseReleaseEvent(event)

        event.ignore.assert_called_once_with()


class TestDraggablePixmapImageUpdates:
    """Image updates should not queue stale work against deleted items."""

    def test_update_image_skips_geometry_change_when_size_stable(
        self, qapp
    ):
        item = DraggablePixmapStub(QImage(8, 8, QImage.Format_ARGB32))
        item.prepareGeometryChange = Mock()
        item.update = Mock()
        item.sceneBoundingRect = Mock(return_value=Mock())
        mock_view = Mock()
        mock_view.viewport.return_value = Mock()
        mock_scene = Mock()
        mock_scene.views.return_value = [mock_view]
        item.scene = Mock(return_value=mock_scene)

        new_image = QImage(8, 8, QImage.Format_ARGB32)
        item.updateImage(new_image)

        assert item.qimage is new_image
        item.prepareGeometryChange.assert_not_called()
        item.update.assert_called_once_with()
        mock_scene.update.assert_called_once_with(
            item.sceneBoundingRect.return_value
        )
        mock_view.viewport.return_value.update.assert_called_once_with()

    def test_update_image_prepares_geometry_when_size_changes(
        self, qapp
    ):
        item = DraggablePixmapStub(QImage(8, 8, QImage.Format_ARGB32))
        item.prepareGeometryChange = Mock()
        item.update = Mock()
        item.sceneBoundingRect = Mock(return_value=Mock())
        mock_view = Mock()
        mock_view.viewport.return_value = Mock()
        mock_scene = Mock()
        mock_scene.views.return_value = [mock_view]
        item.scene = Mock(return_value=mock_scene)

        new_image = QImage(16, 16, QImage.Format_ARGB32)

        item.updateImage(new_image)

        item.prepareGeometryChange.assert_called_once_with()

    def test_update_image_can_skip_scene_invalidation(self, qapp):
        item = DraggablePixmapStub(QImage(8, 8, QImage.Format_ARGB32))
        item.prepareGeometryChange = Mock()
        item.update = Mock()
        item.sceneBoundingRect = Mock(return_value=Mock())
        mock_view = Mock()
        mock_view.viewport.return_value = Mock()
        mock_scene = Mock()
        mock_scene.views.return_value = [mock_view]
        item.scene = Mock(return_value=mock_scene)

        new_image = QImage(8, 8, QImage.Format_ARGB32)

        item.updateImage(new_image, invalidate_scene=False)

        item.update.assert_called_once_with()
        mock_scene.update.assert_not_called()
        mock_view.viewport.return_value.update.assert_not_called()

    def test_update_image_ignores_deleted_qt_item(self, qapp):
        item = DraggablePixmapStub(QImage(8, 8, QImage.Format_ARGB32))
        item.prepareGeometryChange = Mock(side_effect=RuntimeError())

        new_image = QImage(16, 16, QImage.Format_ARGB32)

        item.updateImage(new_image)

        assert item.qimage is not new_image