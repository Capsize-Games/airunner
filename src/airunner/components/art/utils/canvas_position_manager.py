"""Canvas Position Manager - Single source of truth for all canvas positioning.

This module provides a centralized, tested system for handling canvas positioning
calculations. All position conversions should go through this manager to ensure
consistency and eliminate bugs.

Key Concepts:
- Absolute Position: Position in the canvas coordinate system (persisted to DB)
- Display Position: Position in the viewport (what user sees on screen)
- Grid Origin: The anchor point for grid snapping (center_pos)
- Canvas Offset: User's pan position
- Grid Compensation: Viewport resize adjustment

Formula:
    display_pos = absolute_pos - canvas_offset + grid_compensation
    absolute_pos = display_pos + canvas_offset - grid_compensation
"""

from dataclasses import dataclass
from typing import Tuple, Optional
from PySide6.QtCore import QPointF
import math


@dataclass
class ViewState:
    """Encapsulates the view state needed for position calculations.

    Attributes:
        canvas_offset: User's pan offset (increases when panning right/down)
        grid_compensation: Viewport resize compensation offset
    """

    canvas_offset: QPointF
    grid_compensation: QPointF = None

    def __post_init__(self):
        if self.grid_compensation is None:
            self.grid_compensation = QPointF(0, 0)

    @property
    def total_offset(self) -> QPointF:
        """Combined offset for position calculations."""
        return QPointF(
            self.canvas_offset.x() - self.grid_compensation.x(),
            self.canvas_offset.y() - self.grid_compensation.y(),
        )


class CanvasPositionManager:
    """Manages all canvas position calculations with a single source of truth."""

    @staticmethod
    def absolute_to_display(
        absolute_pos: QPointF, view_state: ViewState
    ) -> QPointF:
        """Convert absolute position to display position.

        Args:
            absolute_pos: Position in canvas coordinates
            view_state: Current view state (offset + compensation)

        Returns:
            Position in viewport coordinates (what user sees)

        Formula:
            display = absolute - canvas_offset + grid_compensation
        """
        return QPointF(
            absolute_pos.x() - view_state.total_offset.x(),
            absolute_pos.y() - view_state.total_offset.y(),
        )

    @staticmethod
    def display_to_absolute(
        display_pos: QPointF, view_state: ViewState
    ) -> QPointF:
        """Convert display position to absolute position.

        Args:
            display_pos: Position in viewport coordinates
            view_state: Current view state (offset + compensation)

        Returns:
            Position in canvas coordinates (for DB persistence)

        Formula:
            absolute = display + canvas_offset - grid_compensation
        """
        return QPointF(
            display_pos.x() + view_state.total_offset.x(),
            display_pos.y() + view_state.total_offset.y(),
        )

    @staticmethod
    def snap_to_grid(
        position: QPointF,
        cell_size: float,
        grid_origin: Optional[QPointF] = None,
        use_floor: bool = True,
        enabled: bool = True,
    ) -> QPointF:
        """Snap a position to grid intersections.

        Args:
            position: Position to snap (in any coordinate system)
            cell_size: Grid cell size in pixels
            grid_origin: Grid anchor point (defaults to 0,0)
            use_floor: If True, snap to top-left. If False, snap to nearest.
            enabled: If False, return position unchanged

        Returns:
            Snapped position in the same coordinate system as input
        """
        if not enabled or cell_size <= 0:
            return QPointF(position)

        # Default grid origin to (0, 0)
        origin_x = grid_origin.x() if grid_origin else 0.0
        origin_y = grid_origin.y() if grid_origin else 0.0

        # Translate to grid-relative coordinates
        rel_x = position.x() - origin_x
        rel_y = position.y() - origin_y

        # Snap in grid space
        if use_floor:
            snapped_rel_x = math.floor(rel_x / cell_size) * cell_size
            snapped_rel_y = math.floor(rel_y / cell_size) * cell_size
        else:
            snapped_rel_x = round(rel_x / cell_size) * cell_size
            snapped_rel_y = round(rel_y / cell_size) * cell_size

        # Translate back to original coordinate system
        return QPointF(
            snapped_rel_x + origin_x,
            snapped_rel_y + origin_y,
        )

    @staticmethod
    def get_centered_position(
        item_size: Tuple[float, float], viewport_size: Tuple[float, float]
    ) -> QPointF:
        """Calculate position to center an item in the viewport.

        Args:
            item_size: (width, height) of item
            viewport_size: (width, height) of viewport

        Returns:
            Absolute position that will center the item
        """
        item_width, item_height = item_size
        viewport_width, viewport_height = viewport_size

        # Calculate position so item center aligns with viewport center
        x = (viewport_width - item_width) / 2.0
        y = (viewport_height - item_height) / 2.0

        return QPointF(x, y)

    @classmethod
    def calculate_drag_position(
        cls,
        initial_absolute_pos: QPointF,
        mouse_delta: QPointF,
        view_state: ViewState,
        cell_size: float = 0,
        grid_origin: Optional[QPointF] = None,
        snap_enabled: bool = False,
    ) -> Tuple[QPointF, QPointF]:
        """Calculate new position during drag operation.

        Args:
            initial_absolute_pos: Item's absolute position when drag started
            mouse_delta: Mouse movement since drag start (in scene coords)
            view_state: Current view state
            cell_size: Grid cell size for snapping
            grid_origin: Grid anchor point
            snap_enabled: Whether to snap to grid

        Returns:
            Tuple of (absolute_position, display_position)
        """
        # Calculate new absolute position
        new_absolute = QPointF(
            initial_absolute_pos.x() + mouse_delta.x(),
            initial_absolute_pos.y() + mouse_delta.y(),
        )

        # Apply grid snapping if enabled
        if snap_enabled and cell_size > 0:
            new_absolute = cls.snap_to_grid(
                new_absolute,
                cell_size,
                grid_origin,
                use_floor=True,
                enabled=True,
            )

        # Convert to display position
        new_display = cls.absolute_to_display(new_absolute, view_state)

        return new_absolute, new_display
