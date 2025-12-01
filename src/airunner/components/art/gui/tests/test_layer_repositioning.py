"""
Tests for layer image repositioning and persistence.

These tests verify that layer images maintain correct positions during:
- Viewport resizes
- Canvas panning
- Initial load
- Layer creation/deletion
"""

import types
from types import SimpleNamespace

import pytest

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF, QSize
from PySide6.QtGui import QImage

from airunner.components.art.gui.widgets.canvas.custom_view import (
    CustomGraphicsView,
)
from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import (
    LayerImageItem,
)


@pytest.fixture(autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def make_settings(pos_x=0, pos_y=0, working_width=512, working_height=512):
    """Create mock settings objects."""
    active = SimpleNamespace()
    active.pos_x = pos_x
    active.pos_y = pos_y
    active.pos = (pos_x, pos_y)

    grid = SimpleNamespace()
    grid.cell_size = 64
    grid.snap_to_grid = True
    grid.line_color = "#ffffff"
    grid.canvas_color = "#000000"
    grid.line_width = 1
    grid.show_grid = True

    app_settings = SimpleNamespace()
    app_settings.working_width = working_width
    app_settings.working_height = working_height
    app_settings.current_tool = None

    return active, grid, app_settings


def make_layer_settings(layer_id, x_pos=0, y_pos=0):
    """Create mock DrawingPadSettings for a layer."""
    settings = SimpleNamespace()
    settings.layer_id = layer_id
    settings.x_pos = x_pos
    settings.y_pos = y_pos
    settings.pos = (x_pos, y_pos)
    settings.image = None
    settings.mask = None
    return settings


def test_layer_item_position_updates_with_canvas_offset():
    """Test that layer items update position when canvas_offset changes."""
    view = CustomGraphicsView()
    active, grid, app_settings = make_settings()

    def fake_get_or_cache_settings(self, cls, eager_load=None):
        name = getattr(cls, "__name__", str(cls))
        if name == "ActiveGridSettings":
            return active
        if name == "GridSettings":
            return grid
        if name == "ApplicationSettings":
            return app_settings
        return cls()

    view._get_or_cache_settings = types.MethodType(
        fake_get_or_cache_settings, view
    )

    view.setProperty("canvas_type", "image")
    _ = view.scene

    # Create a mock layer image item
    qimage = QImage(512, 512, QImage.Format.Format_ARGB32)
    qimage.fill(0xFF000000)

    layer_item = LayerImageItem(qimage, layer_id=1)
    layer_item.setPos(200, 300)  # Absolute position

    # Add to scene
    view.scene.addItem(layer_item)
    view.scene._layer_items[1] = layer_item

    # Set canvas offset
    view.canvas_offset = QPointF(50, 75)

    # Create mock original_item_positions
    view.scene.original_item_positions = {layer_item: QPointF(200, 300)}

    # Update positions
    view.updateImagePositions()

    # Expected display position: absolute - offset
    expected_x = 200 - 50
    expected_y = 300 - 75

    pos = layer_item.scenePos()
    assert abs(pos.x() - expected_x) < 1.0
    assert abs(pos.y() - expected_y) < 1.0


def test_multiple_layers_maintain_relative_positions():
    """Test that multiple layers maintain their relative positions during viewport changes."""
    view = CustomGraphicsView()
    active, grid, app_settings = make_settings()

    def fake_get_or_cache_settings(self, cls, eager_load=None):
        name = getattr(cls, "__name__", str(cls))
        if name == "ActiveGridSettings":
            return active
        if name == "GridSettings":
            return grid
        if name == "ApplicationSettings":
            return app_settings
        return cls()

    view._get_or_cache_settings = types.MethodType(
        fake_get_or_cache_settings, view
    )

    view.setProperty("canvas_type", "image")
    _ = view.scene
    view._initialized = True
    view._is_restoring_state = False

    # Create multiple layer items
    qimage = QImage(256, 256, QImage.Format.Format_ARGB32)
    qimage.fill(0xFF000000)

    layer1 = LayerImageItem(qimage, layer_id=1)
    layer2 = LayerImageItem(qimage, layer_id=2)

    layer1_abs_pos = QPointF(100, 150)
    layer2_abs_pos = QPointF(400, 350)

    layer1.setPos(layer1_abs_pos)
    layer2.setPos(layer2_abs_pos)

    view.scene.addItem(layer1)
    view.scene.addItem(layer2)
    view.scene._layer_items[1] = layer1
    view.scene._layer_items[2] = layer2

    view.scene.original_item_positions = {
        layer1: QPointF(layer1_abs_pos.x(), layer1_abs_pos.y()),
        layer2: QPointF(layer2_abs_pos.x(), layer2_abs_pos.y()),
    }

    # Calculate initial relative position
    initial_delta_x = layer2_abs_pos.x() - layer1_abs_pos.x()
    initial_delta_y = layer2_abs_pos.y() - layer1_abs_pos.y()

    # Simulate viewport resize
    from PySide6.QtGui import QResizeEvent

    old_size = QSize(800, 600)
    new_size = QSize(1000, 700)
    view._last_viewport_size = old_size
    view.viewport().resize(new_size)

    resize_event = QResizeEvent(new_size, old_size)
    view.resizeEvent(resize_event)

    # Calculate new relative position
    layer1_pos = layer1.scenePos()
    layer2_pos = layer2.scenePos()

    new_delta_x = layer2_pos.x() - layer1_pos.x()
    new_delta_y = layer2_pos.y() - layer1_pos.y()

    # Relative positions should remain the same
    assert abs(new_delta_x - initial_delta_x) < 1.0
    assert abs(new_delta_y - initial_delta_y) < 1.0


def test_layer_position_persists_across_viewport_changes():
    """Test that layer absolute positions remain unchanged in storage during viewport changes."""
    view = CustomGraphicsView()
    active, grid, app_settings = make_settings()

    def fake_get_or_cache_settings(self, cls, eager_load=None):
        name = getattr(cls, "__name__", str(cls))
        if name == "ActiveGridSettings":
            return active
        if name == "GridSettings":
            return grid
        if name == "ApplicationSettings":
            return app_settings
        return cls()

    view._get_or_cache_settings = types.MethodType(
        fake_get_or_cache_settings, view
    )

    view.setProperty("canvas_type", "image")
    _ = view.scene
    view._initialized = True
    view._is_restoring_state = False

    # Create layer item
    qimage = QImage(256, 256, QImage.Format.Format_ARGB32)
    qimage.fill(0xFF000000)

    layer_item = LayerImageItem(qimage, layer_id=1)
    original_abs_pos = QPointF(200, 300)

    layer_item.setPos(original_abs_pos)
    view.scene.addItem(layer_item)
    view.scene._layer_items[1] = layer_item

    # Store in original positions cache (simulates what scene does)
    view.scene.original_item_positions = {
        layer_item: QPointF(original_abs_pos.x(), original_abs_pos.y())
    }

    # Track the "stored" absolute position
    stored_abs_x = original_abs_pos.x()
    stored_abs_y = original_abs_pos.y()

    # Simulate viewport resize
    from PySide6.QtGui import QResizeEvent

    old_size = QSize(800, 600)
    new_size = QSize(1000, 700)
    view._last_viewport_size = old_size
    view.viewport().resize(new_size)

    resize_event = QResizeEvent(new_size, old_size)
    view.resizeEvent(resize_event)

    # Get updated cached position (simulates stored DB value after compensation)
    updated_cached_pos = view.scene.original_item_positions.get(layer_item)

    # The cached position should NOT be updated by viewport compensation
    # Grid compensation handles the visual shift without modifying stored positions
    assert view.canvas_offset.x() == 0.0
    assert view.canvas_offset.y() == 0.0

    # Display position shift comes from grid_compensation, not position changes
    expected_shift_x = (new_size.width() - old_size.width()) / 2
    expected_shift_y = (new_size.height() - old_size.height()) / 2

    # Verify grid_compensation was updated (not the cached positions)
    assert abs(view._grid_compensation_offset.x() - expected_shift_x) < 1.0
    assert abs(view._grid_compensation_offset.y() - expected_shift_y) < 1.0

    # Cached position should remain unchanged (grid_compensation handles the shift)
    if updated_cached_pos:
        assert abs(updated_cached_pos.x() - stored_abs_x) < 1.0
        assert abs(updated_cached_pos.y() - stored_abs_y) < 1.0


def test_scene_update_image_position_applies_offsets():
    """Test that scene.update_image_position correctly applies canvas offset to layer items."""
    view = CustomGraphicsView()
    active, grid, app_settings = make_settings()

    def fake_get_or_cache_settings(self, cls, eager_load=None):
        name = getattr(cls, "__name__", str(cls))
        if name == "ActiveGridSettings":
            return active
        if name == "GridSettings":
            return grid
        if name == "ApplicationSettings":
            return app_settings
        return cls()

    view._get_or_cache_settings = types.MethodType(
        fake_get_or_cache_settings, view
    )

    view.setProperty("canvas_type", "image")
    _ = view.scene

    # Create layer item
    qimage = QImage(256, 256, QImage.Format.Format_ARGB32)
    qimage.fill(0xFF000000)

    layer_item = LayerImageItem(qimage, layer_id=1)
    abs_pos = QPointF(300, 400)

    view.scene.addItem(layer_item)
    view.scene._layer_items[1] = layer_item

    # Set up original positions
    original_positions = {layer_item: QPointF(abs_pos.x(), abs_pos.y())}

    # Set canvas offset
    canvas_offset = QPointF(100, 150)
    view.canvas_offset = canvas_offset

    # Call update_image_position (simulates what updateImagePositions does)
    view.scene.update_image_position(canvas_offset, original_positions)

    # Expected display position
    expected_x = abs_pos.x() - canvas_offset.x()
    expected_y = abs_pos.y() - canvas_offset.y()

    pos = layer_item.scenePos()
    assert abs(pos.x() - expected_x) < 1.0
    assert abs(pos.y() - expected_y) < 1.0


def test_layer_item_stays_centered_during_sequential_resizes():
    """Test that layers remain visually centered through multiple viewport resizes."""
    view = CustomGraphicsView()
    active, grid, app_settings = make_settings()

    def fake_get_or_cache_settings(self, cls, eager_load=None):
        name = getattr(cls, "__name__", str(cls))
        if name == "ActiveGridSettings":
            return active
        if name == "GridSettings":
            return grid
        if name == "ApplicationSettings":
            return app_settings
        return cls()

    view._get_or_cache_settings = types.MethodType(
        fake_get_or_cache_settings, view
    )

    view.setProperty("canvas_type", "image")
    _ = view.scene
    view._initialized = True
    view._is_restoring_state = False

    # Create layer item
    qimage = QImage(256, 256, QImage.Format.Format_ARGB32)
    qimage.fill(0xFF000000)

    layer_item = LayerImageItem(qimage, layer_id=1)
    initial_pos = QPointF(400, 300)

    layer_item.setPos(initial_pos)
    view.scene.addItem(layer_item)
    view.scene._layer_items[1] = layer_item

    view.scene.original_item_positions = {
        layer_item: QPointF(initial_pos.x(), initial_pos.y())
    }

    # Perform multiple resizes
    from PySide6.QtGui import QResizeEvent

    sizes = [
        QSize(800, 600),
        QSize(1000, 700),
        QSize(900, 650),
        QSize(1100, 750),
    ]

    for i in range(len(sizes) - 1):
        old_size = sizes[i]
        new_size = sizes[i + 1]

        view._last_viewport_size = old_size
        view.viewport().resize(new_size)

        resize_event = QResizeEvent(new_size, old_size)
        view.resizeEvent(resize_event)

    # After all resizes, canvas_offset should still be 0 (no user pan)
    assert view.canvas_offset.x() == 0.0
    assert view.canvas_offset.y() == 0.0

    # Grid compensation should have accumulated
    total_shift_x = (sizes[-1].width() - sizes[0].width()) / 2
    total_shift_y = (sizes[-1].height() - sizes[0].height()) / 2

    assert abs(view._grid_compensation_offset.x() - total_shift_x) < 1.0
    assert abs(view._grid_compensation_offset.y() - total_shift_y) < 1.0
