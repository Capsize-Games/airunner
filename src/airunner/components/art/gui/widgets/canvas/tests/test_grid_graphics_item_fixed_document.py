"""Focused tests for document-bounded grid rendering."""

from types import SimpleNamespace

from PySide6.QtCore import QPointF, QRectF

from airunner.components.art.gui.widgets.canvas.grid_graphics_item import (
    GridGraphicsItem,
)


def test_bounding_rect_uses_document_rect_when_available(qapp):
    """The canvas grid should only exist within the fixed document."""
    document_rect = QRectF(24.0, 18.0, 640.0, 512.0)
    view = SimpleNamespace(
        document_rect=lambda: document_rect,
        canvas_offset=QPointF(0.0, 0.0),
        grid_compensation_offset=QPointF(0.0, 0.0),
    )

    item = GridGraphicsItem(view, QPointF(0.0, 0.0))

    assert item.boundingRect() == document_rect


def test_bounding_rect_tracks_display_document_rect_when_offsets_apply(qapp):
    """Grid geometry should follow the display-space document position."""
    document_rect = QRectF(24.0, 18.0, 640.0, 512.0)
    view = SimpleNamespace(
        document_rect=lambda: document_rect,
        canvas_offset=QPointF(50.0, 30.0),
        grid_compensation_offset=QPointF(20.0, 10.0),
    )

    item = GridGraphicsItem(view, QPointF(0.0, 0.0))

    assert item.boundingRect() == QRectF(-6.0, -2.0, 640.0, 512.0)


def test_grid_origin_tracks_display_space_offsets(qapp):
    """Grid line phase should use the same display-space basis as items."""
    document_rect = QRectF(24.0, 18.0, 640.0, 512.0)
    view = SimpleNamespace(
        document_rect=lambda: document_rect,
        center_pos=QPointF(24.0, 18.0),
        canvas_offset=QPointF(50.0, 30.0),
        grid_compensation_offset=QPointF(40.0, 20.0),
    )

    item = GridGraphicsItem(view, QPointF(0.0, 0.0))

    assert item._display_grid_origin() == QPointF(14.0, 8.0)