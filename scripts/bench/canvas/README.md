# Canvas benchmark harness (#2231)

Measurement-only. Nothing here is imported by `src/`, and nothing here
should be merged into the app. See issue #2231.

## Run

```sh
# from the repo root
AIRUNNER_BASE_PATH=tmp/airunner-base QT_QPA_PLATFORM=offscreen \
  venv/bin/python -m scripts.bench.canvas.bench_canvas --reps 10

# add --profile for a cProfile hotspot dump, --json PATH for machine output
AIRUNNER_BASE_PATH=tmp/airunner-base QT_QPA_PLATFORM=offscreen \
  venv/bin/python -m scripts.bench.canvas.bench_canvas --reps 5 --profile

# candidate comparison
AIRUNNER_BASE_PATH=tmp/airunner-base QT_QPA_PLATFORM=offscreen \
  venv/bin/python -m scripts.bench.canvas.bench_candidates --reps 10

# the shipped renderer (src, not a prototype) — the before/after evidence
AIRUNNER_BASE_PATH=tmp/airunner-base QT_QPA_PLATFORM=offscreen \
  venv/bin/python -m scripts.bench.canvas.bench_shipping --reps 20
```

The harness forces the offscreen Qt platform before creating the
`QApplication`, so no display or GPU is required. `AIRUNNER_BASE_PATH`
points at a repo-local temp directory; no model, network, or live data
is touched.

## Scenarios

| # | Scenario | What is driven |
|---|---|---|
| 1 | 4096² canvas, 10 layers | 10 full-size pixmap items, one full-scene render |
| 2 | continuous brush stroke | per-segment stroke on the layer + repaint, 120 segments (= 1 s at the tablet rate) |
| 3 | pan / zoom | source-rect shift / `QTransform` scale + full render |
| 4 | inpaint mask | white mask segments on a mask image |
| 5 | apply generated image | composite a generated image onto a layer |
| 6 | 50 undo steps | 50 full-layer `QImage.copy()` snapshots |

Measured: wall-clock ms per operation (mean / p50 / p95 / max), process
RSS and `tracemalloc` peak.

## Scope (honest)

The harness drives Qt's own image and `QGraphicsScene` classes with the
canvas's conversion path (`PIL.ImageQt`) — the same rasterisation and
conversion work the app performs — but it does **not** boot the
app-orchestrated `CustomGraphicsView`/`BrushScene` (SettingsMixin DB,
mediator, painter lifecycle). It therefore measures the canvas's render
and image cost model, not end-to-end app latency.

The OpenGL-viewport candidate needs a real GL context, so it is measured
separately from the offscreen harness:

```sh
DISPLAY=:0.0 QT_QPA_PLATFORM=xcb \
  venv/bin/python -m scripts.bench.canvas.bench_gl --reps 30
```

It renders the same 10-layer 4096² scene through a `QGraphicsView` whose
viewport is a `QOpenGLWidget`, measuring the GL frame path
(`grabFramebuffer` forces one full paint + read-back).

## Decision (#2231)

`bench_shipping` measures the shipped implementation —
`airunner/components/art/gui/widgets/canvas/composite_frame_cache.py` —
so its numbers come from the code the app runs, not from a prototype.

Chosen: **composite the document once per change + dirty-rect repaint.**
The 512 px tiled split buys nothing over it (18.7 / 21.1 ms against
17.4 / 16.6 ms) while adding per-tile bookkeeping, and the OpenGL
viewport, though fastest (2.86 ms), needs a real GL context — the
daemon, the offscreen runner and CI all have none, so it would trade a
measurable win for an unverifiable and non-headless code path.

Measured on this machine (4096², 10 layers, offscreen Qt):

| Path | before | after |
|---|---|---|
| 10-layer frame (10 items vs cached composite) | 101.1 ms | 16.4 ms |
| per-segment stroke buffer → pixmap sync | 48.4 ms | 0.17 ms (p50) |
| 40 px dirty strip | 0.42 ms | 0.27 ms |
| composite build (once per change, not per frame) | — | 128.7 ms |

The composite build is paid once per change (layer swapped, visibility
toggled, stroke started), not once per frame.
