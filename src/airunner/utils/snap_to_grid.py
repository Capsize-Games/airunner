import math

from airunner.data.models import GridSettings


def snap_to_grid(settings: GridSettings, x: int, y: int, use_floor: bool = True):
    cell_size = settings.cell_size
    if settings.snap_to_grid:
        x_is_negative = x < 0
        y_is_negative = y < 0

        if use_floor:
            x = abs(x)
            y = abs(y)
            x = math.floor(x / cell_size) * cell_size
            y = math.floor(y / cell_size) * cell_size
            if x_is_negative:
                x = -x
            if y_is_negative:
                y = -y
        else:
            x = round(x / cell_size) * cell_size
            y = round(y / cell_size) * cell_size

    return x, y
