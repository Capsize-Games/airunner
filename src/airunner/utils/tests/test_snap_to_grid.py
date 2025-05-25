"""
Unit tests for airunner.utils.application.snap_to_grid.snap_to_grid
"""

import pytest
from airunner.utils import snap_to_grid


class DummySettings:
    def __init__(self, cell_size, snap_to_grid):
        self.cell_size = cell_size
        self.snap_to_grid = snap_to_grid


def test_snap_to_grid_floor():
    settings = DummySettings(cell_size=10, snap_to_grid=True)
    x, y = snap_to_grid(settings, 23, 37)
    assert x == 20.0
    assert y == 30.0


def test_snap_to_grid_round():
    settings = DummySettings(cell_size=10, snap_to_grid=True)
    x, y = snap_to_grid(settings, 26, 37, use_floor=False)
    assert x == 30.0
    assert y == 40.0


def test_snap_to_grid_disabled():
    settings = DummySettings(cell_size=10, snap_to_grid=False)
    x, y = snap_to_grid(settings, 23, 37)
    assert x == 23.0
    assert y == 37.0


def test_snap_to_grid_zero_cell_size():
    settings = DummySettings(cell_size=0, snap_to_grid=True)
    x, y = snap_to_grid(settings, 23, 37)
    assert x == 23.0
    assert y == 37.0


def test_snap_to_grid_negative_cell_size():
    settings = DummySettings(cell_size=-5, snap_to_grid=True)
    x, y = snap_to_grid(settings, 23, 37)
    assert x == 23.0
    assert y == 37.0
