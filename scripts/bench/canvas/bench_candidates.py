"""Compare throwaway renderer prototypes on the #2231 scenarios.

Run from the repo root (offscreen Qt, no display required):

    venv/bin/python -m scripts.bench.canvas.bench_candidates --reps 10
"""

from __future__ import annotations

import argparse
import os
from typing import Callable, Dict, List, Tuple

from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QApplication

from . import candidates as cand
from . import scenarios as sc
from .metrics import Result, measure

Row = Dict[str, object]
Step = Callable[[], None]


def _time(name: str, fn: Step, count: int) -> Row:
    result = Result(name)
    measure(result, fn, count)
    summary = dict(result.summary())
    summary["name"] = name
    return summary


def _variants() -> Dict[str, object]:
    image = cand.composite_image()
    return {
        "baseline_10_items": sc.build_scene(),
        "composite_1_item": cand.composite_scene(image),
        "tiled_512": cand.tiled_scene(image),
    }


def _full_step(scene, target, layer, pen, state) -> Step:
    def step() -> None:
        state["x"] = (state["x"] + 34.0) % (sc.SIZE - 40)
        sc.brush_segment(layer, pen, state["x"])
        sc.render(scene, target)

    return step


def _dirty_step(scene, target, layer, pen, state) -> Step:
    def step() -> None:
        state["x"] = (state["x"] + 34.0) % (sc.SIZE - 40)
        sc.brush_segment(layer, pen, state["x"])
        cand.render_region(scene, target, int(state["x"]), 40)

    return step


def _frame_rows(reps: int, variants, target) -> List[Row]:
    rows = []
    for label, scene in variants.items():
        rows.append(
            _time(f"{label}/frame", lambda s=scene: sc.render(s, target), reps)
        )
    return rows


def _stroke_rows(variants, target, layer, pen) -> List[Row]:
    state = {"x": 0.0}
    rows = []
    for label, scene in variants.items():
        fn = _full_step(scene, target, layer, pen, state)
        rows.append(_time(f"{label}/stroke_full", fn, sc.TABLET_HZ))
    for label in ("composite_1_item", "tiled_512"):
        fn = _dirty_step(variants[label], target, layer, pen, state)
        rows.append(_time(f"{label}/stroke_dirty40", fn, sc.TABLET_HZ))
    return rows


def run(reps: int) -> List[Row]:
    """Run frame + stroke scenarios across every prototype."""
    if QApplication.instance() is None:
        QApplication([])
    target = sc.make_target()
    layer = sc.make_target()
    pen = QPen(QColor(220, 40, 40), 24)
    variants = _variants()
    rows = _frame_rows(reps, variants, target)
    rows.extend(_stroke_rows(variants, target, layer, pen))
    return rows


def _print(rows: List[Row]) -> None:
    print(
        f"{'prototype/scenario':<40}{'n':>5}{'mean':>11}{'p50':>11}"
        f"{'p95':>11}"
    )
    for row in rows:
        print(
            f"{row['name']:<40}{row['count']:>5}{row['mean_ms']:>11.3f}"
            f"{row['p50_ms']:>11.3f}{row['p95_ms']:>11.3f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=10)
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _print(run(args.reps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
