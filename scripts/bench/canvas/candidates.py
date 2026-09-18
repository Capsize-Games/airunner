"""Throwaway renderer prototypes for #2231 — never merged into src/.

Each prototype re-draws the same 4096x4096, 10-layer scene under a
different strategy so the benchmark can compare them on identical
scenarios:

* ``baseline``  — the current canvas: 10 full-size pixmap items.
* ``composite`` — the 10 layers pre-composited once into one pixmap
  (removes the per-frame N-layer raster the profile flags).
* ``tiled``     — the composite split into 512 px tiles so a stroke can
  repaint only the touched tiles (dirty-tile granularity).

The OpenGL viewport candidate is not prototyped here: the offscreen Qt
platform has no GL context, so it cannot be measured reproducibly in
this harness (noted in the report).
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene

from . import scenarios as sc

TILE = 512


def composite_image() -> QImage:
    """Flatten the 10 layers into one full-canvas QImage."""
    target = sc.make_target()
    target.fill(Qt.GlobalColor.transparent)
    painter = QPainter(target)
    for index in range(sc.LAYERS):
        color = ((index * 20) % 200, 60, 120, 40)
        painter.drawImage(0, 0, sc.to_qimage(sc.solid_pil(color)))
    painter.end()
    return target


def _new_scene() -> QGraphicsScene:
    scene = QGraphicsScene()
    scene.setSceneRect(QRectF(0.0, 0.0, float(sc.SIZE), float(sc.SIZE)))
    return scene


def composite_scene(image: QImage) -> QGraphicsScene:
    """A scene holding the single flattened pixmap."""
    scene = _new_scene()
    scene.addItem(QGraphicsPixmapItem(QPixmap.fromImage(image)))
    return scene


def tiled_scene(image: QImage, tile: int = TILE) -> QGraphicsScene:
    """A scene holding the composite split into ``tile``-px items."""
    scene = _new_scene()
    for y in range(0, sc.SIZE, tile):
        for x in range(0, sc.SIZE, tile):
            patch = image.copy(x, y, tile, tile)
            item = QGraphicsPixmapItem(QPixmap.fromImage(patch))
            item.setPos(float(x), float(y))
            scene.addItem(item)
    return scene


def render_region(
    scene: QGraphicsScene, target: QImage, x: int, width: int
) -> None:
    """Repaint only one vertical strip (dirty-rect update)."""
    strip = QRectF(float(x), 0.0, float(width), float(sc.SIZE))
    painter = QPainter(target)
    scene.render(painter, strip, strip)
    painter.end()
