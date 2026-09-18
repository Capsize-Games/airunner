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
