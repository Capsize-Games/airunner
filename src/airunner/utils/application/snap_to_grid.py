import math


def snap_to_grid(
    settings, x: float, y: float, use_floor: bool = True
):  # Accept floats
    cell_size = float(
        settings.cell_size
    )  # Ensure cell_size is float for division
    if settings.snap_to_grid and cell_size > 0:  # Add check for cell_size > 0
        if use_floor:
            x = math.floor(x / cell_size) * cell_size
            y = math.floor(y / cell_size) * cell_size
        else:
            # Round to the nearest grid point
            x = round(x / cell_size) * cell_size
            y = round(y / cell_size) * cell_size
    # Return floats for potentially more precise positioning if needed downstream
    return float(x), float(y)
