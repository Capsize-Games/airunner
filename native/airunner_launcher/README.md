# Native AIRunner Launcher

This directory contains the native AIRunner launcher implementation.

## Goal

The launcher gives AIRunner two explicit runtime modes:

- `dev`: use the repository's existing `venv` and `src/` tree
- `prod`: use a manifest-driven bundled runtime tree with embedded Python and
  pinned native sidecar binaries

This matches the product requirement discussed in issue #82:
- developers should be able to build and run the native bootstrap locally
  without installing a separate packaged AIRunner build
- end users should receive one installed AIRunner product with no
  system Python dependency

## Current Scope

The current launcher does three things:

1. resolves a runtime plan for `dev` or `prod`
2. sets the key AIRunner environment variables
3. launches `python -m airunner.launcher`

It does not yet:
- supervise sidecars directly from C++
- move sidecar supervision into native code

Those responsibilities remain intentionally in Python. The native launcher is
responsible for startup layout selection, environment export, and Python
process launch.

## Development Flow

Build the launcher:

```bash
./scripts/build_airunner_launcher.sh
```

Cross-build the Windows launcher from Linux when MinGW-w64 is available:

```bash
./scripts/build_airunner_launcher.sh --target-platform windows
```

Run AIRunner through the native launcher in dev mode:

```bash
./scripts/run_airunner_dev.sh
```

Capture a native crash under gdb while following the launcher child process:

```bash
./scripts/run_airunner_dev.sh --gdb
```

That workflow switches the native launcher into an internal no-fork mode so
gdb stays attached to the main AIRunner Python process instead of drifting into
short-lived helper children. When the crash stops in gdb, run
`airunner_dump` to write a full backtrace and local core file under
`build/debug/core/`.

Enable kernel core dumps around the same dev launch flow:

```bash
./scripts/run_airunner_dev.sh --coredump
```

If the host is using `systemd-coredump`, inspect the resulting crash with
`coredumpctl list airunner` and `coredumpctl info airunner`.

If `kernel.core_pattern` is disabled on the host, the script reports that
immediately and points you to `--gdb`, which can still write a local core file
without changing system-wide settings.

That flow uses the repository `venv` when present and sets `PYTHONPATH` to
`src/` so the existing Python application code runs unchanged.

## Production Flow

Production mode expects a manifest file with relative runtime paths.
See `runtime_manifest.example.env` for the current contract.

Issue #85 adds a pinned sidecar build flow in
`native/runtime_sidecars/` and `scripts/build_runtime_sidecars.sh`.
That script emits bundle-ready `llama-server` and `whisper-server`
artifacts plus a platform-specific runtime manifest under
`share/airunner/runtime_manifest.env`.

Issue #86 adds pinned embedded Python metadata in
`native/embedded_python/`, staged bundle assembly in
`src/airunner/bin/build_end_user_bundle.py`, and installer packagers in
`scripts/package_linux_appimage.sh` and
`scripts/package_windows_nsis.ps1`.

The shipped bundle layout installs AIRunner into `app/site-packages/`
inside the bundle, so production manifests should point
`AIRUNNER_PYTHONPATH` there instead of the repository `src/` tree used in
dev mode.

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

For diagnostics and support workflows, the launcher also supports:
- `--print-plan` to print the resolved launch plan
- `--dry-run` to print the plan without starting Python
- `--diagnose` to print the plan plus validation warnings and errors

At the current boundary, Python still owns runtime-client and sidecar
supervision. The native launcher is responsible for startup layout selection,
environment export, and Python process launch.

## Reference Inputs

This scaffold is informed by:
- `~/Projects/airunnercpp`, which already uses a native app plus Python worker
  bridge pattern
- `~/Projects/cowboycasino`, which already vendors and pins `llama.cpp`
  through CMake and uses GGUF runtime paths directly