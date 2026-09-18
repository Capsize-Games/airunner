"""Run the six #2231 canvas benchmark scenarios and print a results table.

Run from the repo root (Qt is forced to the offscreen platform, so no
display is required):

    venv/bin/python -m scripts.bench.canvas.bench_canvas --reps 30

Add ``--profile`` to dump the top cumulative ``cProfile`` functions, and
``--json PATH`` to also write the machine-readable results.
"""

from __future__ import annotations

import argparse
import cProfile
import io
import json
import os
import pstats
import tracemalloc
from typing import Callable, Dict, List, Tuple

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPen, QTransform
from PySide6.QtWidgets import QApplication

from . import scenarios as sc
from .metrics import Result, measure, peak_tracemalloc_mb, rss_mb

Runner = Tuple[str, Callable[[], None], int]


def _runners(reps: int) -> List[Runner]:
    scene = sc.build_scene()
    target = sc.make_target()
    layer = sc.make_target()
    mask = sc.make_target()
    generated = sc.to_qimage(sc.solid_pil((10, 200, 80, 255)))
    pen = QPen(QColor(220, 40, 40), 24)
    state = {"x": 0.0, "pan": 0.0, "zoom": False}

    def frame() -> None:
        sc.render(scene, target)

    def stroke() -> None:
        state["x"] = (state["x"] + 34.0) % (sc.SIZE - 40)
        sc.brush_segment(layer, pen, state["x"])
        sc.render(scene, target)

    def pan() -> None:
        state["pan"] = (state["pan"] + 8.0) % 256.0
        src = QRectF(state["pan"], 0.0, float(sc.SIZE), float(sc.SIZE))
        sc.render(scene, target, src=src)

    def zoom() -> None:
        scale = 0.5 if state["zoom"] else 1.0
        state["zoom"] = not state["zoom"]
        sc.render(scene, target, transform=QTransform().scale(scale, scale))

    def mask_step() -> None:
        state["x"] = (state["x"] + 34.0) % (sc.SIZE - 40)
        sc.mask_segment(mask, state["x"])

    def apply_step() -> None:
        sc.apply_generated(layer, generated)

    def undo_step() -> None:
        sc.snapshot(layer)

    return [
        ("1_ten_layer_frame", frame, reps),
        ("2_brush_stroke_segment", stroke, sc.TABLET_HZ),
        ("3_pan_frame", pan, reps),
        ("3_zoom_frame", zoom, reps),
        ("4_inpaint_mask_segment", mask_step, sc.TABLET_HZ),
        ("5_apply_generated_to_layer", apply_step, 30),
        ("6_undo_snapshot_50", undo_step, 50),
    ]


def run(reps: int) -> Dict[str, object]:
    """Run every scenario and return the scenario + memory report."""
    if QApplication.instance() is None:
        QApplication([])
    tracemalloc.start()
    baseline = rss_mb()
    scenarios: List[Dict[str, object]] = []
    for name, fn, count in _runners(reps):
        result = Result(name)
        measure(result, fn, count)
        summary: Dict[str, object] = dict(result.summary())
        summary["name"] = name
        scenarios.append(summary)
    peak_mb = peak_tracemalloc_mb()
    tracemalloc.stop()
    return {
        "scenarios": scenarios,
        "memory": {
            "rss_baseline_mb": round(baseline, 1),
            "rss_peak_mb": round(rss_mb(), 1),
            "tracemalloc_peak_mb": round(peak_mb, 1),
        },
    }


def _print_table(report: Dict[str, object]) -> None:
    header = (
        f"{'scenario':<28}{'n':>5}{'mean':>11}{'p50':>11}"
        f"{'p95':>11}{'max':>11}"
    )
    print(header)
    for row in report["scenarios"]:  # type: ignore[union-attr]
        print(
            f"{row['name']:<28}{row['count']:>5}{row['mean_ms']:>11.3f}"
            f"{row['p50_ms']:>11.3f}{row['p95_ms']:>11.3f}"
            f"{row['max_ms']:>11.3f}"
        )
    memory = report["memory"]  # type: ignore[assignment]
    print(
        f"rss baseline {memory['rss_baseline_mb']:.1f} MiB | "
        f"rss peak {memory['rss_peak_mb']:.1f} MiB | "
        f"tracemalloc peak {memory['tracemalloc_peak_mb']:.1f} MiB"
    )


def _dump_profile(profiler: cProfile.Profile) -> None:
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(25)
    print(stream.getvalue())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=30)
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--json", type=str, default="")
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    if args.profile:
        profiler = cProfile.Profile()
        profiler.enable()
        report = run(args.reps)
        profiler.disable()
        _dump_profile(profiler)
    else:
        report = run(args.reps)

    _print_table(report)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
