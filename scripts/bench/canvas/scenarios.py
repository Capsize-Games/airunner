"""The six #2231 scenarios, driven against the canvas's Qt primitives.

Each scenario reproduces one cost path the real canvas takes (see
``src/airunner/components/art/gui/widgets/canvas/``): full-canvas
``ImageQt`` conversion, full-scene repaint, per-segment brush repaint,
transform repaint, mask strokes, layer composite, and full-image
history snapshots. The harness drives Qt's own image/scene classes, not
the app-orchestrated ``CustomGraphicsView`` (see README for scope).
"""

from __future__ import annotations

from PIL import Image, ImageQt
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPen,
    QPixmap,
    QTransform,
)
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene

SIZE = 4096
LAYERS = 10
TABLET_HZ = 120


def solid_pil(color) -> Image.Image:
    """One full-canvas RGBA PIL image."""
    return Image.new("RGBA", (SIZE, SIZE), color)


def to_qimage(image: Image.Image) -> QImage:
    """Convert via ImageQt — the canvas's own conversion path."""
    return ImageQt.ImageQt(image)


def make_target() -> QImage:
    """A blank full-canvas target image."""
    return QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)


def build_scene() -> QGraphicsScene:
    """A 4096x4096 scene with 10 stacked layer items."""
    scene = QGraphicsScene()
    scene.setSceneRect(QRectF(0.0, 0.0, float(SIZE), float(SIZE)))
    for index in range(LAYERS):
        color = ((index * 20) % 200, 60, 120, 40)
        pixmap = QPixmap.fromImage(to_qimage(solid_pil(color)))
        scene.addItem(QGraphicsPixmapItem(pixmap))
    return scene


def render(
    scene: QGraphicsScene,
    target: QImage,
    src: QRectF | None = None,
    transform: QTransform | None = None,
) -> None:
    """Render one full frame (the view's paint cost)."""
    target.fill(Qt.GlobalColor.transparent)
    painter = QPainter(target)
    if transform is not None:
        painter.setTransform(transform)
    source = src if src is not None else scene.sceneRect()
    scene.render(painter, QRectF(target.rect()), source)
    painter.end()


def brush_segment(layer: QImage, pen: QPen, x: float) -> None:
    """One brush segment stroked onto the active layer."""
    painter = QPainter(layer)
    painter.setPen(pen)
    painter.drawLine(QPointF(x, 0.0), QPointF(x + 40.0, float(SIZE)))
    painter.end()


def mask_segment(mask: QImage, x: float) -> None:
    """One white inpaint-mask segment."""
    painter = QPainter(mask)
    painter.setPen(QPen(QColor(255, 255, 255), 24))
    painter.drawLine(QPointF(x, 0.0), QPointF(x + 40.0, float(SIZE)))
    painter.end()


def apply_generated(layer: QImage, generated: QImage) -> None:
    """Composite a generated image onto a layer (apply-to-layer op)."""
    painter = QPainter(layer)
    painter.drawImage(0, 0, generated)
    painter.end()


def snapshot(layer: QImage) -> QImage:
    """Copy a full layer — the cost the undo history pays per step."""
    return layer.copy()
