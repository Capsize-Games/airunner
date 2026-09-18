"""Unit tests for the composite-once / dirty-rect frame cache (#2231).

The cache is the renderer primitive the canvas uses to stop paying a
full-document flatten and a full-document blit on every frame and every
brush segment. These tests pin the two properties the optimisation
depends on: the composite is built once, and only the dirty rectangle is
touched afterwards.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter

from airunner.components.art.gui.widgets.canvas.brush_scene import BrushScene
from airunner.components.art.gui.widgets.canvas.composite_frame_cache import (
    CompositeFrameCache,
)


@pytest.fixture(scope="module")
def qapp():
    """Create one offscreen QApplication for the module."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _solid(size: QSize, color: QColor) -> QImage:
    image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(color)
    return image


def _target(size: QSize) -> QImage:
    image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    return image


def test_build_flattens_layers_bottom_to_top(qapp) -> None:
    """The frame holds the topmost layer's pixels."""
    cache = CompositeFrameCache()
    size = QSize(32, 32)
    frame = cache.build(
        size,
        [
            _solid(size, QColor(255, 0, 0, 255)),
            _solid(size, QColor(0, 0, 255, 255)),
        ],
    )
    assert cache.frame is frame
    assert cache.size() == size
    assert frame.pixelColor(5, 5) == QColor(0, 0, 255, 255)


def test_build_is_reusable_without_recompositing(qapp) -> None:
    """A clean cache hands back the same frame object on re-read."""
    cache = CompositeFrameCache()
    size = QSize(16, 16)
    frames = [cache.build(size, [_solid(size, QColor("red"))])]
    frames.append(cache.frame)  # the "once per change" read path
    assert frames[0] is frames[1]


def test_apply_touches_only_the_dirty_rectangle(qapp) -> None:
    """A dirty-rect blit leaves every pixel outside the rect untouched."""
    cache = CompositeFrameCache()
    size = QSize(32, 32)
    cache.build(size, [_solid(size, QColor(0, 0, 0, 255))])
    inset = _solid(size, QColor(0, 255, 0, 255))
    rect = QRect(8, 8, 8, 8)

    cache.apply(inset, rect)

    frame = cache.frame
    assert frame.pixelColor(10, 10) == QColor(0, 255, 0, 255)
    assert frame.pixelColor(7, 7) == QColor(0, 0, 0, 255)
    assert frame.pixelColor(30, 30) == QColor(0, 0, 0, 255)


def test_apply_can_erase_a_rectangle(qapp) -> None:
    """Erasing clears alpha inside the rect only."""
    cache = CompositeFrameCache()
    size = QSize(32, 32)
    cache.build(size, [_solid(size, QColor(0, 0, 0, 255))])

    cache.apply(
        _solid(size, QColor(255, 255, 255, 255)),
        QRect(0, 0, 16, 32),
        erase=True,
    )

    frame = cache.frame
    assert frame.pixelColor(4, 4).alpha() == 0
    assert frame.pixelColor(24, 4).alpha() == 255


def test_apply_requires_a_built_frame(qapp) -> None:
    """Blitting before building is a programming error, not silence."""
    cache = CompositeFrameCache()
    size = QSize(8, 8)
    with pytest.raises(RuntimeError):
        cache.apply(_solid(size, QColor("red")), QRect(0, 0, 4, 4))


def test_paint_draws_only_the_requested_region(qapp) -> None:
    """Painting one rect copies that rect and nothing else."""
    cache = CompositeFrameCache()
    size = QSize(32, 32)
    cache.build(size, [_solid(size, QColor(255, 0, 0, 255))])
    target = _target(size)
    painter = QPainter(target)
    cache.paint(painter, QRect(16, 16, 8, 8))
    painter.end()

    assert target.pixelColor(18, 18).alpha() == 255
    assert target.pixelColor(2, 2).alpha() == 0


def test_rects_outside_the_frame_are_ignored(qapp) -> None:
    """An out-of-bounds dirty rect is clipped away, not an error."""
    cache = CompositeFrameCache()
    size = QSize(16, 16)
    cache.build(size, [_solid(size, QColor(255, 0, 0, 255))])
    before = cache.frame.copy()

    cache.apply(_solid(size, QColor(0, 255, 0, 255)), QRect(64, 64, 8, 8))

    assert cache.frame == before


class _DirtyStub:
    """Minimal host for the scene's pure dirty-rect helpers."""

    def __init__(self) -> None:
        self._stroke_dirty = None


def test_mark_stroke_dirty_pads_by_pen_width() -> None:
    """A segment's rect is padded by the brush radius and aligned."""
    stub = _DirtyStub()
    BrushScene._mark_stroke_dirty(stub, QRectF(100.0, 50.0, 20.0, 40.0), 24)
    assert stub._stroke_dirty == QRect(86, 36, 48, 68)


def test_mark_stroke_dirty_replaces_the_previous_segment() -> None:
    """Each segment reports its own rect, so no stale region is reused."""
    stub = _DirtyStub()
    BrushScene._mark_stroke_dirty(stub, QRectF(0.0, 0.0, 4.0, 4.0), 4)
    first = stub._stroke_dirty
    BrushScene._mark_stroke_dirty(stub, QRectF(500.0, 500.0, 4.0, 4.0), 4)
    assert stub._stroke_dirty != first
    assert stub._stroke_dirty.left() > 400


def test_stroke_dirty_rect_falls_back_to_full_bounds() -> None:
    """With no segment yet the whole surface is treated as dirty."""
    stub = _DirtyStub()
    fallback = QRect(0, 0, 64, 64)
    assert BrushScene._stroke_dirty_rect(stub, fallback) == fallback
    stub._stroke_dirty = QRect(4, 4, 8, 8)
    assert BrushScene._stroke_dirty_rect(stub, fallback) == QRect(4, 4, 8, 8)
