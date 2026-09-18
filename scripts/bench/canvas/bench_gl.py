"""OpenGL-viewport prototype for #2231 (throwaway — never for src/).

The offscreen Qt platform has no GL context, so this candidate runs on a
real display instead:

    DISPLAY=:0.0 QT_QPA_PLATFORM=xcb \
      venv/bin/python -m scripts.bench.canvas.bench_gl --reps 30

It renders the same 10-layer 4096² scene as ``bench_canvas`` through a
``QGraphicsView`` whose viewport is a ``QOpenGLWidget``, and measures the
GL frame path (``grabFramebuffer`` forces one full paint + read-back).
"""

from __future__ import annotations

import argparse
import os
from typing import Tuple

from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication, QGraphicsView

from . import scenarios as sc
from .metrics import Result, measure


def build() -> Tuple[QGraphicsView, QOpenGLWidget]:
    """Build a GL-viewport view over the baseline 10-layer scene."""
    scene = sc.build_scene()
    view = QGraphicsView(scene)
    gl = QOpenGLWidget()
    view.setViewport(gl)
    view.resize(1200, 800)
    view.show()
    return view, gl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=30)
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    app = QApplication([])
    view, gl = build()
    app.processEvents()
    result = Result("gl_viewport_frame")
    measure(result, gl.grabFramebuffer, args.reps)
    print(result.summary())
    view.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
