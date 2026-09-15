"""Grid drawing mixin for CustomGraphicsView.

This mixin handles grid rendering, active grid area display, and grid-related
visual updates including mouse event handling for grid interaction.
"""

from typing import Optional
from PySide6.QtCore import QPointF, Qt, QSize

from airunner.components.art.gui.widgets.canvas.grid_graphics_item import (
    GridGraphicsItem,
)
from airunner.components.art.gui.widgets.canvas.draggables.active_grid_area import (
    ActiveGridArea,
)
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)
from airunner.enums import SignalCode, CanvasToolName


class GridDrawingMixin:
    """Mixin for grid rendering and active grid area management.

    This mixin handles:
    - Grid line drawing and updates
    - Active grid area creation and positioning
    - Grid mouse event handling (accepting/ignoring events)
    - Grid clearing

    Attributes:
        grid_item: GridGraphicsItem for rendering grid lines
        active_grid_area: ActiveGridArea visual representation
        drawing: Flag indicating if drawing is in progress
    """

    def _get_saved_center_anchor(self):
        """Return the persisted home anchor when one exists."""
        center_x = self.settings.value("center_pos_x", None)
        center_y = self.settings.value("center_pos_y", None)
        if center_x is None or center_y is None:
            return None
        return QPointF(float(center_x), float(center_y))

    def _get_existing_grid_anchor(self):
        """Return the current home anchor for the canvas grid."""
        if self.center_pos != QPointF(0, 0):
            return QPointF(self.center_pos)
        return self._get_saved_center_anchor()

    def _should_initialize_active_grid_position(self, pos_x, pos_y):
        """Return whether the grid position still needs startup seeding."""
        if pos_x is None or pos_y is None:
            return True
        if pos_x != 0 or pos_y != 0:
            return False

        anchor = self._get_existing_grid_anchor()
        if anchor is None:
            return True
        if not getattr(self.grid_settings, "snap_to_grid", False):
            return False

        cell_size = getattr(self.grid_settings, "cell_size", 0) or 0
        if cell_size <= 0:
            return False

        offset_x = int(round(pos_x - anchor.x()))
        offset_y = int(round(pos_y - anchor.y()))
        return offset_x % cell_size != 0 or offset_y % cell_size != 0

    def _get_initial_active_grid_anchor(self) -> QPointF:
        """Return the startup anchor for a fresh active grid position."""
        anchor = self._get_existing_grid_anchor()
        if anchor is None:
            target_x, target_y = self.get_recentered_position(
                self.application_settings.working_width,
                self.application_settings.working_height,
            )
            anchor = QPointF(target_x, target_y)

        self.center_pos = QPointF(anchor)
        return anchor

    def do_draw(
        self, force_draw: bool = False, size: Optional[QSize] = None
    ) -> None:
        """Draw or redraw the grid and active grid area.

        Args:
            force_draw: If True, force redraw even if already drawing.
            size: Optional size parameter (unused, kept for compatibility).
        """
        if self.scene is None:
            return
        if (self.drawing or not self.initialized) and not force_draw:
            return
        self.drawing = True
        self.set_scene_rect()

        # Remove old grid item if it exists
        if self.grid_item is not None:
            self.scene.removeItem(self.grid_item)
            self.grid_item = None

        # Add a single efficient grid item
        if self.grid_settings.show_grid:
            self.grid_item = GridGraphicsItem(self, self.center_pos)
            self.scene.addItem(self.grid_item)

        self.show_active_grid_area()
        self.update_scene()
        self.drawing = False

    def draw_grid(self, size: Optional[QSize] = None) -> None:
        """Trigger grid redraw if grid item exists.

        Args:
            size: Optional size parameter (unused, kept for compatibility).
        """
        if self.grid_item:
            self.grid_item.update()

    def clear_lines(self) -> None:
        """Clear grid lines from the scene."""
        if self.grid_item is not None:
            self.scene.removeItem(self.grid_item)
            self.grid_item = None

    def show_active_grid_area(self) -> None:
        """Display and position the active grid area.

        Creates active grid area if needed, positions it based on saved settings,
        and registers signal handlers for position updates.
        """
        if not self._do_show_active_grid_area:
            # Ensure it's removed if disabled
            if self.active_grid_area:
                self.remove_scene_item(self.active_grid_area)
                self.active_grid_area = None
            return

        # Skip repositioning during drag to prevent interference
        if self.scene and getattr(self.scene, "is_dragging", False):
            self.logger.info(
                "[ACTIVE GRID] Skipping show_active_grid_area - is_dragging is True"
            )
            return

        # Create if it doesn't exist
        if not self.active_grid_area:
            self.active_grid_area = ActiveGridArea()
            self.active_grid_area.setZValue(10000)
            self.scene.addItem(self.active_grid_area)
            # Connect the signal emitted by the updated update_position
            self.active_grid_area.register(
                SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED,
                self.update_active_grid_area_position,  # Call view's update method
            )

        # Get the stored absolute position (defaults to 0,0 if not found)
        # Use active_grid_settings as the primary source, QSettings as fallback/persistence
        absolute_x = self.active_grid_settings.pos_x
        absolute_y = self.active_grid_settings.pos_y

        self.logger.info(
            f"[LOAD GRID] Active grid absolute position from DB: x={absolute_x}, y={absolute_y}, canvas_offset=({self.canvas_offset_x}, {self.canvas_offset_y})"
        )

        # Fresh databases create a default row before the viewport home anchor
        # has been written. Seed the first absolute position from the current
        # home anchor so the grid border, grid lines, and centered viewport all
        # share the same basis.
        if self._should_initialize_active_grid_position(
            absolute_x,
            absolute_y,
        ):
            anchor = self._get_initial_active_grid_anchor()
            absolute_x = anchor.x()
            absolute_y = anchor.y()

            self.update_active_grid_settings(
                pos_x=int(round(absolute_x)), pos_y=int(round(absolute_y))
            )
            self.settings.sync()

        # Calculate and set the display position using CanvasPositionManager
        # to account for both canvas_offset and grid_compensation
        manager = CanvasPositionManager()
        view_state = ViewState(
            canvas_offset=self.canvas_offset,
            grid_compensation=self._grid_compensation_offset,
        )
        absolute_pos = QPointF(absolute_x, absolute_y)
        display_pos = manager.absolute_to_display(absolute_pos, view_state)

        self.logger.info(
            f"[LOAD GRID] Setting grid display position: x={display_pos.x()}, y={display_pos.y()} (absolute: {absolute_x}, {absolute_y}, offset: {self.canvas_offset_x}, {self.canvas_offset_y}, compensation: {self._grid_compensation_offset.x()}, {self._grid_compensation_offset.y()})"
        )
        self.active_grid_area.setPos(display_pos.x(), display_pos.y())

        # Log actual scene position after setPos
        actual_pos = self.active_grid_area.scenePos()
        self.logger.info(
            f"[LOAD GRID] Active grid actual scene position after setPos: ({actual_pos.x()}, {actual_pos.y()})"
        )

        # Ensure active grid mouse acceptance matches current tool
        try:
            self._update_active_grid_mouse_acceptance()
        except Exception:
            pass

    def _update_active_grid_mouse_acceptance(self) -> None:
        """Update active grid area mouse event handling based on current tool.

        When the MOVE tool is active, makes the grid area transparent to mouse
        events so users can interact with items beneath it. Otherwise, restores
        normal mouse event handling.
        """
        if not self.active_grid_area:
            return

        try:
            # If MOVE tool is active, let clicks pass through the active grid area
            if self.current_tool is CanvasToolName.MOVE:
                self.active_grid_area.setAcceptedMouseButtons(
                    Qt.MouseButton.NoButton
                )
                # Also disable hover events so hover cursors don't block underlying items
                try:
                    self.active_grid_area.setAcceptHoverEvents(False)
                except Exception:
                    pass
            else:
                # Restore acceptance for left/right buttons when not moving
                accepted = (
                    Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
                )
                self.active_grid_area.setAcceptedMouseButtons(accepted)
                try:
                    self.active_grid_area.setAcceptHoverEvents(True)
                except Exception:
                    pass
        except Exception:
            # Best-effort; do not break flow if ActiveGridArea doesn't support these methods
            self.logger.exception(
                "Failed updating active grid mouse acceptance"
            )
