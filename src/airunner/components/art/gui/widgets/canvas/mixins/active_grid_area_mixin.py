"""Mixin for managing the active grid area display in CustomGraphicsView.

This mixin handles showing, positioning, and mouse interaction for the active grid area.
"""

from PySide6.QtCore import QPointF, Qt

from airunner.components.art.gui.widgets.canvas.draggables.active_grid_area import (
    ActiveGridArea,
)
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)
from airunner.enums import SignalCode, CanvasToolName


class ActiveGridAreaMixin:
    """Provides active grid area management for graphics view.

    This mixin manages:
    - Active grid area visibility and positioning
    - Mouse interaction based on current tool
    - Position persistence and loading

    Dependencies:
        - self.scene: CustomScene instance
        - self.logger: Logging instance
        - self._do_show_active_grid_area: Bool property
        - self.active_grid_settings: Settings for active grid
        - self.application_settings: Application settings
        - self.canvas_offset: QPointF canvas offset
        - self._grid_compensation_offset: QPointF grid compensation
        - self.current_tool: Current tool property
        - self.viewport(): Viewport widget
        - self.update_active_grid_settings(): Update settings method
        - self.remove_scene_item(): Remove item from scene
        - self.update_active_grid_area_position(): Position update callback
    """

    def show_active_grid_area(self):
        """Show or hide the active grid area based on settings.

        Creates the active grid area if needed, positions it according to
        saved absolute coordinates, and configures mouse interaction.
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

        # If settings are somehow None (e.g., first run), default and save
        if absolute_x is None or absolute_y is None:
            # Default to centering in the initial view, considering the initial offset
            viewport_center_x = self.viewport().width() / 2
            viewport_center_y = self.viewport().height() / 2
            # Calculate absolute position needed to appear centered with current offset
            absolute_x = (
                viewport_center_x
                + self.canvas_offset_x
                - (self.application_settings.working_width / 2)
            )
            absolute_y = (
                viewport_center_y
                + self.canvas_offset_y
                - (self.application_settings.working_height / 2)
            )

            # Save this initial absolute position
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

    def _update_active_grid_mouse_acceptance(self):
        """Make the active grid area ignore mouse events while the MOVE tool is active.

        When the MOVE tool is selected users need to be able to interact with items
        beneath the active grid area. Setting accepted mouse buttons to NoButton
        makes the item transparent to mouse events so clicks fall through.
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
