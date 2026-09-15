import math
from typing import Tuple, Optional
from PySide6.QtCore import QPointF


def snap_to_grid(
    settings,
    x: float,
    y: float,
    use_floor: bool = True,
    grid_origin: Optional[QPointF] = None,
) -> Tuple[float, float]:
    """Snap coordinates to grid intersections.

    Args:
        settings: Grid settings object with cell_size and snap_to_grid attributes
        x: X coordinate to snap
        y: Y coordinate to snap
        use_floor: If True, snap to floor (top-left), else round to nearest
        grid_origin: Optional grid origin offset (absolute coordinates where grid (0,0) is anchored)

    Returns:
        Tuple of (snapped_x, snapped_y) as floats
    """
    cell_size = float(settings.cell_size)
    if settings.snap_to_grid and cell_size > 0:
        # If grid_origin is provided, adjust coordinates relative to that origin
        if grid_origin is not None:
            origin_x = grid_origin.x()
            origin_y = grid_origin.y()
        else:
            origin_x = 0.0
            origin_y = 0.0

        # Translate to grid-relative coordinates
        rel_x = x - origin_x
        rel_y = y - origin_y

        # Snap in grid space
        if use_floor:
            snapped_rel_x = math.floor(rel_x / cell_size) * cell_size
            snapped_rel_y = math.floor(rel_y / cell_size) * cell_size
        else:
            snapped_rel_x = round(rel_x / cell_size) * cell_size
            snapped_rel_y = round(rel_y / cell_size) * cell_size

        # Translate back to absolute coordinates
        x = snapped_rel_x + origin_x
        y = snapped_rel_y + origin_y

    return float(x), float(y)
