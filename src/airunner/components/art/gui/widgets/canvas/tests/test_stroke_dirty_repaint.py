"""Functional tests for the dirty-rect brush sync path (#2231).

The cache's own behaviour is covered by
``test_composite_frame_cache.py``. These tests exercise the three scene
methods that consume it -- ``_compose_stroke_image``,
``_sync_stroke_pixmap`` and ``_invalidate_stroke_dirty_region`` -- to prove
a stroke segment touches only its own rectangle instead of copying and
re-blitting the whole document on every tablet event.

The host and its pixmap item are plain doubles rather than Qt objects:
the methods under test only call ``scene()``, ``setPixmap`` and
``scene.update`` on them, and a double keeps the assertions about
*which rectangle* was touched exact.
"""

from __future__ import annotations

from typing import List, Optional

import pytest
from PySide6.QtCore import QPointF, QRect, QRectF, QSize
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

from airunner.components.art.gui.widgets.canvas.brush_scene import BrushScene
from airunner.components.art.gui.widgets.canvas.composite_frame_cache import (
    CompositeFrameCache,
)

SIZE = QSize(64, 64)
ORIGIN = QPointF(10.0, 20.0)


@pytest.fixture(scope="module")
def qapp():
    """Create one offscreen QApplication for the module."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _solid(color: QColor) -> QImage:
    """Return a solid, premultiplied image of the test size."""
    image = QImage(SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(color)
    return image


def _fill_rect(image: QImage, rect: QRect, color: QColor) -> None:
    """Fill one rectangle of an image with a solid colour."""
    painter = QPainter(image)
    painter.fillRect(rect, color)
    painter.end()


class _RecordingScene:
    """Scene double that records the rectangles it is asked to repaint."""

    def __init__(self) -> None:
        self.updated: List[QRectF] = []

    def update(self, rect: QRectF) -> None:
        """Record one repaint request."""
        self.updated.append(QRectF(rect))


class _StrokeItem:
    """Stand-in for the stroke ``QGraphicsPixmapItem``."""

    def __init__(self, scene: Optional[_RecordingScene]) -> None:
        self._scene = scene
        self._pixmap: Optional[QPixmap] = None

    def scene(self) -> Optional[_RecordingScene]:
        """Return the scene this item belongs to."""
        return self._scene

    def setPixmap(self, pixmap: QPixmap) -> None:
        """Record the pixmap assigned to this item."""
        self._pixmap = pixmap

    def pixmap(self) -> Optional[QPixmap]:
        """Return the pixmap assigned to this item."""
        return self._pixmap


class _StrokeHost:
    """Minimal host exposing the scene's stroke-sync state."""

    # The scene methods under test call this helper on ``self``.
    _stroke_dirty_rect = BrushScene._stroke_dirty_rect

    def __init__(self, scene: Optional[_RecordingScene] = None) -> None:
        self._stroke_base_image: Optional[QImage] = None
        self._stroke_buffer_image: Optional[QImage] = None
        self._stroke_dirty: Optional[QRect] = None
        self._stroke_item: Optional[_StrokeItem] = None
        self._stroke_item_pixmap: Optional[QPixmap] = None
        self._stroke_frame_cache = CompositeFrameCache()
        self._stroke_frame_base_id: Optional[int] = None
        self._scene = scene

    def _document_display_origin(self) -> QPointF:
        return ORIGIN

    def build(self) -> _StrokeItem:
        """Return the stroke item, attached to the double scene."""
        self._stroke_item = _StrokeItem(self._scene)
        return self._stroke_item


def test_stroke_frame_is_composed_once_per_base(qapp) -> None:
    """The base is flattened once; later segments reuse the same frame."""
    host = _StrokeHost()
    base = _solid(QColor(10, 10, 10, 255))
    buffer = _solid(QColor(0, 0, 0, 0))

    first = BrushScene._compose_stroke_image(host, base, buffer, False)
    second = BrushScene._compose_stroke_image(host, base, buffer, False)

    assert first is second
    assert host._stroke_frame_base_id == id(base)
    assert first.pixelColor(4, 4) == QColor(10, 10, 10, 255)


def test_stroke_segment_only_changes_its_own_rect(qapp) -> None:
    """A dirty-rect segment leaves the rest of the composite untouched."""
    host = _StrokeHost()
    base = _solid(QColor(10, 10, 10, 255))
    buffer = _solid(QColor(0, 0, 0, 0))
    BrushScene._compose_stroke_image(host, base, buffer, False)

    host._stroke_dirty = QRect(8, 8, 16, 16)
    _fill_rect(buffer, host._stroke_dirty, QColor(0, 255, 0, 255))
    frame = BrushScene._compose_stroke_image(host, base, buffer, False)

    assert frame.pixelColor(12, 12) == QColor(0, 255, 0, 255)
    assert frame.pixelColor(40, 40) == QColor(10, 10, 10, 255)


def test_composition_requires_a_base_image(qapp) -> None:
    """Without a base there is nothing to composite onto."""
    host = _StrokeHost()
    assert BrushScene._compose_stroke_image(host, None, None, False) is None


def test_pixmap_sync_reuses_one_pixmap_per_stroke(qapp) -> None:
    """The stroke pixmap is allocated once and updated by rectangle."""
    host = _StrokeHost()
    item = host.build()
    host._stroke_buffer_image = _solid(QColor(0, 0, 0, 255))
    BrushScene._sync_stroke_pixmap(host)
    allocated = host._stroke_item_pixmap

    _fill_rect(host._stroke_buffer_image, QRect(4, 4, 8, 8), QColor("red"))
    host._stroke_dirty = QRect(4, 4, 8, 8)
    BrushScene._sync_stroke_pixmap(host)

    assert host._stroke_item_pixmap is allocated
    synced = item.pixmap()
    assert synced is not None
    assert synced.toImage().pixelColor(6, 6) == QColor(255, 0, 0, 255)


def test_dirty_region_invalidation_covers_only_the_segment(qapp) -> None:
    """Scene invalidation is translated to the dirty rect, not the item."""
    scene = _RecordingScene()
    host = _StrokeHost(scene)
    host.build()
    host._stroke_buffer_image = _solid(QColor(0, 0, 0, 255))
    host._stroke_item_pixmap = QPixmap.fromImage(host._stroke_buffer_image)
    host._stroke_dirty = QRect(8, 8, 4, 4)

    BrushScene._invalidate_stroke_dirty_region(host)

    assert scene.updated
    assert scene.updated[-1] == _expected_scene_rect()


def _expected_scene_rect() -> QRectF:
    """Return the scene-space rect a (8,8,4,4) dirty rect maps to."""
    return QRectF(8.0, 8.0, 4.0, 4.0).translated(ORIGIN)


def test_invalidation_is_a_no_op_without_an_item(qapp) -> None:
    """No stroke item means nothing to invalidate."""
    host = _StrokeHost(_RecordingScene())
    host._stroke_buffer_image = _solid(QColor(0, 0, 0, 255))
    BrushScene._invalidate_stroke_dirty_region(host)


def test_removing_the_stroke_item_clears_the_pixmap(qapp) -> None:
    """A new stroke must allocate its own pixmap."""
    host = _StrokeHost(_RecordingScene())
    host.build()
    host._stroke_item_pixmap = QPixmap.fromImage(
        _solid(QColor(255, 0, 0, 255))
    )

    BrushScene._remove_stroke_item(host)

    assert host._stroke_item is None
    assert host._stroke_item_pixmap is None


def test_marked_dirty_rect_is_reported(qapp) -> None:
    """A recorded segment rect is what the sync path uses."""
    host = _StrokeHost()
    fallback = QRect(0, 0, 4, 4)
    assert host._stroke_dirty_rect(fallback) == fallback
    host._stroke_dirty = QRect(1, 2, 3, 4)
    assert host._stroke_dirty_rect(fallback) == QRect(1, 2, 3, 4)
