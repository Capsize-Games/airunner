"""Measure the shipping renderer against the #2231 baseline.

``bench_canvas``/``bench_candidates`` measure throwaway prototypes. This
module measures the *shipping* implementation instead:
``airunner.components.art.gui.widgets.canvas.composite_frame_cache``
(the composite-once + dirty-rect strategy chosen in #2231), on the same
4096² 10-layer scene, so the before/after numbers in the report come
from the code that actually runs in the app.

    AIRUNNER_BASE_PATH=tmp/airunner-base QT_QPA_PLATFORM=offscreen \
      venv/bin/python -m scripts.bench.canvas.bench_shipping --reps 10
"""

from __future__ import annotations

import argparse
import os
from typing import List

from PySide6.QtCore import QPointF, QRect, QSize
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

from airunner.components.art.gui.widgets.canvas.composite_frame_cache import (
    CompositeFrameCache,
)

from . import scenarios as sc
from .metrics import Result, measure

DIRTY_WIDTH = 40
_FRAME_SIZE = QSize(sc.SIZE, sc.SIZE)


def _layer_images() -> List[QImage]:
    """Return one QImage per baseline layer, bottom-to-top."""
    return [
        sc.to_qimage(sc.solid_pil(((index * 20) % 200, 60, 120, 40)))
        for index in range(sc.LAYERS)
    ]


def _full_frame_step(cache: CompositeFrameCache, target: QImage):
    """Return the full-frame repaint step for the cached frame."""

    def step() -> None:
        target.fill(0)
        painter = QPainter(target)
        cache.paint(painter, target.rect())
        painter.end()

    return step


def _dirty_strip_step(cache: CompositeFrameCache, target: QImage):
    """Return the dirty-strip repaint step for the cached frame."""
    state = {"x": 0}

    def step() -> None:
        state["x"] = (state["x"] + 34) % (sc.SIZE - DIRTY_WIDTH)
        painter = QPainter(target)
        cache.paint(painter, QRect(state["x"], 0, DIRTY_WIDTH, sc.SIZE))
        painter.end()

    return step


def _shipping_frame_rows(reps: int) -> List[Result]:
    """Full-frame and dirty-strip paint costs out of the cached frame."""
    cache = CompositeFrameCache()
    cache.build(_FRAME_SIZE, _layer_images())
    target = sc.make_target()
    full = Result("shipping/frame_cached_composite")
    measure(full, _full_frame_step(cache, target), reps)
    strip = Result("shipping/frame_dirty40_strip")
    measure(strip, _dirty_strip_step(cache, target), sc.TABLET_HZ)
    return [full, strip]


def _shipping_build_row(reps: int) -> Result:
    """The one-off composite cost, paid once per change not per frame."""
    layers = _layer_images()
    cache = CompositeFrameCache()
    result = Result("shipping/composite_build_once_per_change")
    measure(result, lambda: cache.build(_FRAME_SIZE, layers), reps)
    return result


def _baseline_stroke_row() -> Result:
    """Baseline per-segment sync: copy the document, convert it all.

    This is exactly what ``BrushScene._sync_stroke_item`` did on every
    tablet event before #2231 (``QPixmap.fromImage(full_buffer)`` over a
    freshly copied document-sized image), measured without the frame
    render so the two variants differ only in the code under test.
    """
    layer = sc.make_target()
    pen = QPen(QColor(220, 40, 40), 24)
    state = {"x": 0.0}

    def step() -> None:
        state["x"] = (state["x"] + 34.0) % (sc.SIZE - 40)
        sc.brush_segment(layer, pen, state["x"])
        pixmap = QPixmap.fromImage(layer.copy())
        del pixmap

    result = Result("baseline/segment_full_pixmap_sync")
    measure(result, step, sc.TABLET_HZ)
    return result


def _shipping_stroke_row() -> Result:
    """Shipping per-segment sync: dirty-rect blit, one pixmap per stroke."""
    buffer = sc.make_target()
    pen = QPen(QColor(220, 40, 40), 24)
    pixmap = QPixmap.fromImage(buffer)
    state = {"x": 0}

    def step() -> None:
        state["x"] = (state["x"] + 34) % (sc.SIZE - 40)
        sc.brush_segment(buffer, pen, float(state["x"]))
        rect = QRect(state["x"], 0, DIRTY_WIDTH, sc.SIZE)
        painter = QPainter(pixmap)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Source
        )
        painter.drawImage(rect, buffer, rect)
        painter.end()

    result = Result("shipping/segment_dirty_rect_pixmap_sync")
    measure(result, step, sc.TABLET_HZ)
    return result


def _print(results: List[Result]) -> None:
    print(
        f"{'scenario':<40}{'n':>5}{'mean':>11}{'p50':>11}{'p95':>11}"
    )
    for result in results:
        summary = result.summary()
        print(
            f"{result.name:<40}{summary['count']:>5}"
            f"{summary['mean_ms']:>11.3f}{summary['p50_ms']:>11.3f}"
            f"{summary['p95_ms']:>11.3f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=10)
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if QApplication.instance() is None:
        QApplication([])

    results = [
        _shipping_build_row(args.reps),
        _baseline_stroke_row(),
        _shipping_stroke_row(),
    ]
    results.extend(_shipping_frame_rows(args.reps))
    _print(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
