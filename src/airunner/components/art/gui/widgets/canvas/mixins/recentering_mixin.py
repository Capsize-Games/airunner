"""Mixin for recentering logic in CustomGraphicsView."""

from PySide6.QtCore import QPointF

from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)


class RecenteringMixin:
    """Provides recentering functionality for graphics view.

    This mixin manages:
    - Viewport recentering
    - Grid-anchor synchronization
    - Canvas offset persistence

    Dependencies:
        - self.scene: CustomScene instance
        - self.logger: Logging instance
        - self.canvas_offset: QPointF canvas offset property
        - self._grid_compensation_offset: QPointF grid compensation
        - self.center_pos: QPointF center position
        - self.save_canvas_offset(): Save offset to settings
        - self.api: API instance
        - self.update_active_grid_area_position(): Update grid position
        - self.updateImagePositions(): Update image positions
    """

    def on_recenter_grid_signal(self):
        """Handle recenter grid signal.

        Recenter the viewport without moving canvas items.

        The canvas and all item absolute positions remain unchanged.
        Only the viewport transform changes so the stored canvas layout stays
        intact while the current viewport is centered for its present size.
        """
        view_state = self._current_view_state()
        item_positions = self._capture_canvas_item_positions(view_state)
        self._grid_compensation_offset = QPointF(0, 0)
        self.canvas_offset = self.get_centered_total_offset()

        self.save_canvas_offset()
        self.api.art.canvas.update_grid_info(self.get_grid_info_payload())

        if not self.scene:
            return

        self.update_active_grid_area_position()
        if item_positions:
            self.updateImagePositions(item_positions)
        else:
            self.updateImagePositions()

        self.logger.info("[RECENTER] Recenter grid signal processing complete")

    def _current_view_state(self) -> ViewState:
        """Return the current viewport transform state."""
        return ViewState(
            canvas_offset=QPointF(self.canvas_offset),
            grid_compensation=QPointF(self._grid_compensation_offset),
        )

    def _capture_canvas_item_positions(
        self,
        view_state: ViewState,
    ) -> dict:
        """Capture current absolute positions for scene items."""
        if not self.scene:
            return {}
        positions = {}
        scene_item = getattr(self.scene, "item", None)
        self._store_item_position(positions, scene_item, view_state)
        for layer_item in getattr(self.scene, "_layer_items", {}).values():
            self._store_item_position(positions, layer_item, view_state)
        return positions

    def _store_item_position(
        self,
        positions: dict,
        item,
        view_state: ViewState,
    ) -> None:
        """Store one item's current absolute canvas position."""
        if item is None:
            return
        positions[item] = self._get_item_absolute_position(
            item,
            view_state,
        )

    def _get_item_absolute_position(
        self,
        item,
        view_state: ViewState,
    ) -> QPointF:
        """Convert one item's current display position to canvas space."""
        return CanvasPositionManager.display_to_absolute(
            QPointF(item.pos()),
            view_state,
        )

    def _preview_centered_layout(self) -> None:
        """Apply centered positions in memory before startup restoration ends.

        This previews the recenter path without mutating item
        coordinates while the main window is still settling.
        """
        if not self.scene:
            return

        view_state = self._current_view_state()
        item_positions = self._capture_canvas_item_positions(view_state)
        self._grid_compensation_offset = QPointF(0, 0)
        self.canvas_offset = self.get_centered_total_offset()

        if hasattr(self.scene, "original_item_positions"):
            self.scene.original_item_positions.clear()

        self.update_active_grid_area_position()
        if item_positions:
            self.updateImagePositions(item_positions)
        else:
            self.updateImagePositions()
