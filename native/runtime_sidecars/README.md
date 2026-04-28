# Native Runtime Sidecars

This directory defines the pinned AIRunner build inputs for the native
runtime sidecars shipped with packaged installs.

## Pinned Upstreams

The authoritative pins live in `runtime_pins.env`:

- `llama.cpp` commit `71a81f6fcc2c7e4bf17c3c2484c9498358d173b2`
  (`b8688`)
- `whisper.cpp` commit `9386f239401074690479731c1e41683fbbeac557`
  (`v1.8.4`)

These are exact commit hashes so AIRunner's runtime bundles do not drift
with upstream `master`.

## Build Flow

Build Linux sidecar binaries:

```bash
./scripts/build_runtime_sidecars.sh --clean --target-platform linux
```

Cross-build Windows sidecar binaries from Linux when MinGW-w64 is present:

```bash
./scripts/build_runtime_sidecars.sh --clean --target-platform windows
```

The script produces a bundle-style layout under:

- `build/runtime-sidecars/linux/`
- `build/runtime-sidecars/windows/`

Each output contains:

- `bin/llama-server` or `bin/llama-server.exe`
- `bin/whisper-server` or `bin/whisper-server.exe`
- `share/airunner/runtime_manifest.env`
- `share/airunner/runtime_pins.env`

The generated manifest points AIRunner at the bundled sidecar binaries
using paths relative to `share/airunner/runtime_manifest.env`.

## CI

The `.github/workflows/native-runtime-sidecars.yml` workflow runs the same
script in a Linux and Windows matrix so CI can reproduce the pinned runtime
artifacts.