"""
Tests for the circle_brush cursor creation functionality.
Follows project pytest and PySide6 GUI test guidelines.
"""

import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QCursor
from airunner.gui.cursors.circle_brush import circle_cursor


@pytest.mark.parametrize(
    "outline, fill",
    [
        ("red", "blue"),
        ("green", "yellow"),
        ("#FF5733", "#C70039"),
        ("rgb(255,0,0)", "rgb(0,255,0)"),
    ],
)
def test_circle_cursor_with_different_colors(outline: str, fill: str) -> None:
    """Test circle_cursor with various outline and fill color combinations."""
    cursor = circle_cursor(outline, fill)
    assert isinstance(cursor, QCursor)


@pytest.mark.parametrize("size", [16, 32, 48, 64])
def test_circle_cursor_hotspot(size: int) -> None:
    """Test that cursor hotspot is set correctly for various sizes."""
    cursor = circle_cursor("black", "white", pixmap_size=size)
    assert isinstance(cursor, QCursor)
    pixmap = cursor.pixmap()
    assert pixmap.width() == size
    assert pixmap.height() == size


@pytest.mark.parametrize("size", [32, 64])
def test_circle_cursor_with_custom_size(size: int) -> None:
    """Test circle_cursor with custom size."""
    cursor = circle_cursor("black", "white", pixmap_size=size)
    pixmap = cursor.pixmap()
    assert pixmap.width() == size
    assert pixmap.height() == size


def test_circle_cursor_with_default_size() -> None:
    """Test circle_cursor with default size."""
    cursor = circle_cursor("black", "white")
    pixmap = cursor.pixmap()
    assert pixmap.width() == 32
    assert pixmap.height() == 32


def test_circle_cursor_creates_qcursor() -> None:
    """Test that circle_cursor returns a QCursor object."""
    cursor = circle_cursor("black", "white")
    assert isinstance(cursor, QCursor)


def test_circle_cursor_drawing_operations_with_factories():
    """Test drawing operations using dependency injection instead of patching."""
    mock_pixmap = MagicMock()
    mock_painter = MagicMock()
    mock_cursor = MagicMock()

    def pixmap_factory(w, h):
        assert w == 48 and h == 48
        return mock_pixmap

    def painter_factory(pixmap):
        assert pixmap is mock_pixmap
        return mock_painter

    def cursor_factory(pixmap, x, y):
        assert pixmap is mock_pixmap
        assert x == 24 and y == 24
        return mock_cursor

    result = circle_cursor(
        "red",
        "blue",
        pixmap_size=48,
        pixmap_factory=pixmap_factory,
        painter_factory=painter_factory,
        cursor_factory=cursor_factory,
    )
    mock_pixmap.fill.assert_called_once_with(Qt.GlobalColor.transparent)
    mock_painter.setRenderHint.assert_called_once_with(QPainter.RenderHint.Antialiasing)
    assert mock_painter.setPen.call_count == 2
    assert mock_painter.setBrush.call_count == 2
    assert mock_painter.drawEllipse.call_count == 2
    mock_painter.end.assert_called_once()
    assert result is mock_cursor


def test_circle_cursor_integer_size() -> None:
    """Test that non-integer size is converted to integer and invalid raises ValueError."""
    cursor = circle_cursor("black", "white", pixmap_size=32.5)
    pixmap = cursor.pixmap()
    assert pixmap.width() == 32
    assert pixmap.height() == 32
    with pytest.raises(ValueError):
        circle_cursor("black", "white", pixmap_size="not-a-number")
