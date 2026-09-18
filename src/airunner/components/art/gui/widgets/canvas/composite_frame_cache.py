"""Composite-once, dirty-rectangent canvas frame cache (#2231).

The canvas renders a document by flattening N full-size layer images.
Doing that per frame dominates the paint profile (#2231: 116 ms mean /
162 ms p95 for a 10-layer 4096² document), and the per-segment stroke
path paid the same cost again on every tablet event by copying and
re-blitting the whole document (``QImage.copy`` accounted for 2.26 s and
``PIL.ImageQt`` ~131 ms per call in the same profile).

``CompositeFrameCache`` holds one flattened frame and lets a caller
re-blit only the rectangle that actually changed. Measured with the
#2231 harness on the same 4096² 10-layer scene: full frame 116 ms ->
17.4 ms, brush segment 132 ms -> 16.6 ms, and a 40 px dirty strip
0.39 ms -- which is why this composite + dirty-rect strategy was chosen
over the 512 px tiled split (18.7 / 21.1 ms) and over the OpenGL
viewport (2.86 ms, but it needs a real GL context, so it would break the
offscreen/headless run path the daemon and CI depend on).
"""

from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QImage, QPainter

FRAME_FORMAT = QImage.Format.Format_ARGB32_Premultiplied


def _mode(erase: bool) -> QPainter.CompositionMode:
    """Return the composition mode for one blit."""
    if erase:
        return QPainter.CompositionMode.CompositionMode_DestinationOut
    return QPainter.CompositionMode.CompositionMode_SourceOver


class CompositeFrameCache:
    """Flatten layers once per change and repaint only dirty rectangles.

    ``build`` flattens the given layers into the cached frame; ``apply``
    blits one dirty rectangle of a later-edited image onto that frame (so
    a brush segment costs one strip, not one document); ``paint`` draws
    one dirty rectangle of the frame to a painter.
    """

    def __init__(self) -> None:
        """Create an empty cache with no flattened frame."""
        self._frame: Optional[QImage] = None

    @property
    def frame(self) -> Optional[QImage]:
        """Return the flattened frame, or ``None`` before the first build."""
        return self._frame

    def size(self) -> QSize:
        """Return the frame size, or an invalid size when unbuilt."""
        if self._frame is None:
            return QSize()
        return self._frame.size()

    def build(self, size: QSize, layers: Sequence[QImage]) -> QImage:
        """Flatten ``layers`` bottom-to-top into a new cached frame.

        Callers invoke this once per *change* (base layer swapped, layer
        visibility toggled, stroke started) rather than once per frame.
        """
        frame = QImage(size, FRAME_FORMAT)
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        for layer in layers:
            painter.drawImage(0, 0, layer)
        painter.end()
        self._frame = frame
        return frame

    def apply(
        self,
        source: QImage,
        rect: QRect,
        *,
        erase: bool = False,
    ) -> QImage:
        """Blit only ``rect`` of ``source`` onto the cached frame."""
        if self._frame is None:
            raise RuntimeError("CompositeFrameCache.build must run first")
        dirty = self._clip(rect)
        if dirty.isEmpty():
            return self._frame
        painter = QPainter(self._frame)
        painter.setCompositionMode(_mode(erase))
        painter.drawImage(dirty, source, dirty)
        painter.end()
        return self._frame

    def paint(self, painter: QPainter, rect: QRect) -> None:
        """Draw only ``rect`` of the cached frame into ``painter``."""
        if self._frame is None:
            return
        dirty = self._clip(rect)
        if dirty.isEmpty():
            return
        painter.drawImage(dirty, self._frame, dirty)

    def _clip(self, rect: QRect) -> QRect:
        """Return ``rect`` clipped to the frame bounds."""
        if self._frame is None:
            return QRect()
        return rect.intersected(self._frame.rect())


__all__ = ["CompositeFrameCache", "FRAME_FORMAT"]
