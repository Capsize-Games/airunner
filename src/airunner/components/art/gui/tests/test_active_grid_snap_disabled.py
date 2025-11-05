"""Test active grid area dragging with snap-to-grid DISABLED."""

import types
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF, Qt

from airunner.components.art.gui.widgets.canvas.custom_view import (
    CustomGraphicsView,
)
from airunner.components.art.gui.widgets.canvas.draggables.active_grid_area import (
    ActiveGridArea,
)
from airunner.enums import CanvasToolName


@pytest.fixture(autouse=True)
def qapp():
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    except RuntimeError:
        app = QApplication([])
    return app


def make_settings(pos_x=0, pos_y=0, snap_to_grid=False):
    """Create fake settings with snap-to-grid configurable."""
    active = SimpleNamespace()
    active.pos_x = pos_x
    active.pos_y = pos_y
    active.pos = (pos_x, pos_y)

    grid = SimpleNamespace()
    grid.cell_size = 64
    grid.snap_to_grid = snap_to_grid  # Configurable
    grid.line_color = "#ffffff"
    grid.canvas_color = "#000000"
    grid.line_width = 1
    grid.show_grid = True

    app = SimpleNamespace()
    app.working_width = 512
    app.working_height = 512
    app.current_tool = CanvasToolName.ACTIVE_GRID_AREA.value

    return active, grid, app


def test_active_grid_drag_without_snap():
    """Test dragging active grid area with snap-to-grid DISABLED.

    This tests the bug where:
    1. Disable snap to grid
    2. Drag the active grid area to a new location
    3. Release the mouse button -> it should stay at the release location
    4. It should NOT jump to a different location
    """
    view = CustomGraphicsView()

    # Start at (100, 100) with snap DISABLED
    active, grid, app_settings = make_settings(
        pos_x=100, pos_y=100, snap_to_grid=False
    )

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

    # Ensure active grid area exists
    view.show_active_grid_area()
    aga: ActiveGridArea = view.active_grid_area
    assert aga is not None

    # Monkeypatch aga to return our fake settings
    aga._get_or_cache_settings = types.MethodType(
        fake_get_or_cache_settings, aga
    )

    # Track calls to update_active_grid_settings
    update_calls = []

    def track_update(**kwargs):
        update_calls.append(kwargs.copy())
        if "pos_x" in kwargs:
            active.pos_x = kwargs["pos_x"]
        if "pos_y" in kwargs:
            active.pos_y = kwargs["pos_y"]

    aga.update_active_grid_settings = track_update

    # Provide a no-op API
    aga.api = SimpleNamespace(
        art=SimpleNamespace(
            canvas=SimpleNamespace(generate_mask=lambda: None),
            active_grid_area_updated=lambda: None,
        )
    )

    # Create mouse event helper
    class Evt:
        def __init__(self, button, scene_pos, pos):
            self._button = button
            self._scene_pos = scene_pos
            self._pos = pos

        def button(self):
            return self._button

        def scenePos(self):
            return self._scene_pos

        def pos(self):
            return self._pos

        def accept(self):
            pass

    # Simulate drag: press at (100, 100), move by (50, 75) to (150, 175)
    press = Evt(Qt.MouseButton.LeftButton, QPointF(100, 100), QPointF(0, 0))
    aga.mousePressEvent(press)

    # Move to (150, 175) - delta of (50, 75)
    move = Evt(None, QPointF(150, 175), QPointF(0, 0))
    aga.mouseMoveEvent(move)

    # Get position after move but before release
    pos_after_move = aga.scenePos()
    print(f"Position after move: ({pos_after_move.x()}, {pos_after_move.y()})")

    # Release at the same position
    release = Evt(None, QPointF(150, 175), QPointF(0, 0))
    aga.mouseReleaseEvent(release)

    # Position immediately after release
    pos_after_release = aga.scenePos()
    print(
        f"Position after release: ({pos_after_release.x()}, {pos_after_release.y()})"
    )

    # With snap DISABLED, the position should NOT change from move to release
    # It should stay at the dragged position
    assert abs(pos_after_release.x() - pos_after_move.x()) < 1.0, (
        f"X position changed from {pos_after_move.x()} to {pos_after_release.x()} "
        f"after release (should stay the same when snap is disabled)"
    )
    assert abs(pos_after_release.y() - pos_after_move.y()) < 1.0, (
        f"Y position changed from {pos_after_move.y()} to {pos_after_release.y()} "
        f"after release (should stay the same when snap is disabled)"
    )

    # The database should have been updated with the final position
    assert (
        len(update_calls) > 0
    ), "update_active_grid_settings should have been called"

    final_update = update_calls[-1]
    expected_x = int(pos_after_release.x())
    expected_y = int(pos_after_release.y())

    assert (
        final_update["pos_x"] == expected_x
    ), f"Database pos_x should be {expected_x}, got {final_update['pos_x']}"
    assert (
        final_update["pos_y"] == expected_y
    ), f"Database pos_y should be {expected_y}, got {final_update['pos_y']}"


def test_active_grid_no_jump_after_click():
    """Test that clicking after dragging doesn't cause position to jump.

    This tests step 5 of the bug:
    5. Click once and the active grid area jumps back to where originally released
    """
    view = CustomGraphicsView()

    active, grid, app_settings = make_settings(
        pos_x=100, pos_y=100, snap_to_grid=False
    )

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

    view.show_active_grid_area()
    aga: ActiveGridArea = view.active_grid_area

    aga._get_or_cache_settings = types.MethodType(
        fake_get_or_cache_settings, aga
    )

    def track_update(**kwargs):
        if "pos_x" in kwargs:
            active.pos_x = kwargs["pos_x"]
        if "pos_y" in kwargs:
            active.pos_y = kwargs["pos_y"]

    aga.update_active_grid_settings = track_update
    aga.api = SimpleNamespace(
        art=SimpleNamespace(
            canvas=SimpleNamespace(generate_mask=lambda: None),
            active_grid_area_updated=lambda: None,
        )
    )

    class Evt:
        def __init__(self, button, scene_pos, pos):
            self._button = button
            self._scene_pos = scene_pos
            self._pos = pos

        def button(self):
            return self._button

        def scenePos(self):
            return self._scene_pos

        def pos(self):
            return self._pos

        def accept(self):
            pass

    # Drag to new position
    press = Evt(Qt.MouseButton.LeftButton, QPointF(100, 100), QPointF(0, 0))
    aga.mousePressEvent(press)

    move = Evt(None, QPointF(200, 250), QPointF(0, 0))
    aga.mouseMoveEvent(move)

    release = Evt(None, QPointF(200, 250), QPointF(0, 0))
    aga.mouseReleaseEvent(release)

    pos_after_drag = aga.scenePos()

    # Now simulate a click (press and immediate release at same position)
    click_press = Evt(Qt.MouseButton.LeftButton, pos_after_drag, QPointF(0, 0))
    aga.mousePressEvent(click_press)

    click_release = Evt(None, pos_after_drag, QPointF(0, 0))
    aga.mouseReleaseEvent(click_release)

    pos_after_click = aga.scenePos()

    # Position should NOT change after click
    assert (
        abs(pos_after_click.x() - pos_after_drag.x()) < 1.0
    ), f"Position jumped from {pos_after_drag.x()} to {pos_after_click.x()} after click"
    assert (
        abs(pos_after_click.y() - pos_after_drag.y()) < 1.0
    ), f"Position jumped from {pos_after_drag.y()} to {pos_after_click.y()} after click"
