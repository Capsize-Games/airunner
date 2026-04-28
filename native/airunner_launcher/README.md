# Native AIRunner Launcher

This directory contains the first scaffold for the native AIRunner launcher.

## Goal

The launcher gives AIRunner two explicit runtime modes:

- `dev`: use the repository's existing `venv` and `src/` tree
- `prod`: use a manifest-driven bundled runtime tree with embedded Python and
  pinned native sidecar binaries

This matches the product requirement discussed in issue #82:
- developers should be able to build and run the native bootstrap locally
  without installing a separate packaged AIRunner build
- end users should eventually receive one installed AIRunner product with no
  system Python dependency

## Current Scope

The scaffold does three things:

1. resolves a runtime plan for `dev` or `prod`
2. sets the key AIRunner environment variables
3. launches `python -m airunner.launcher`

It does not yet:
- bundle embedded Python
- supervise sidecars directly from C++
- produce Linux or Windows installer artifacts
- vendored-build `llama.cpp` or `whisper.cpp`

Those remain tracked in issue #82 and its follow-on child issues.

## Development Flow

Build the launcher:

```bash
./scripts/build_airunner_launcher.sh
```

Run AIRunner through the native launcher in dev mode:

```bash
./scripts/run_airunner_dev.sh
```

That flow uses the repository `venv` when present and sets `PYTHONPATH` to
`src/` so the existing Python application code runs unchanged.

## Production Flow

Production mode expects a manifest file with relative runtime paths.
See `runtime_manifest.example.env` for the current contract.

For the full launcher contract, including mode resolution, required and
optional manifest keys, exported environment variables, and failure modes, see
`CONTRACT.md`.

The launcher reads:
- `AIRUNNER_BUNDLE_ROOT`
- `AIRUNNER_PYTHON`
- `AIRUNNER_PYTHONPATH`
- `AIRUNNER_ENTRYPOINT`
- `AIRUNNER_LLAMA_SERVER_BIN`
- `AIRUNNER_WHISPER_SERVER_BIN`

At the current boundary, Python still owns runtime-client and sidecar
supervision. The native launcher is responsible for startup layout selection,
environment export, and Python process launch.

## Reference Inputs

This scaffold is informed by:
- `~/Projects/airunnercpp`, which already uses a native app plus Python worker
  bridge pattern
- `~/Projects/cowboycasino`, which already vendors and pins `llama.cpp`
  through CMake and uses GGUF runtime paths directly