# AIRunner Native Launcher Contract

This document defines the runtime contract for the native AIRunner launcher.

The launcher supports two runtime modes and one fallback mode selector:
- `dev`
- `prod`
- `auto`

The launcher is the native bootstrap layer. It is responsible for selecting
the runtime layout, exporting the expected AIRunner environment variables, and
starting `python -m airunner.launcher`.

It is not yet the owner of sidecar supervision. At the current boundary,
Python remains responsible for starting and managing the runtime clients and
their sidecar processes.

## Mode Selection

Mode resolution order is:

1. `--mode <value>` when provided
2. `AIRUNNER_LAUNCH_MODE` when set
3. `auto` fallback

`auto` currently means:
- try `dev`
- if `dev` cannot resolve a usable repo root and venv Python, fall back to
  `prod`

## Dev Mode Contract

`dev` mode exists so AIRunner can be launched through the native bootstrap on
the development machine without requiring a separately packaged install.

### Inputs

Dev mode resolves the repository root from:
- `--repo-root`
- `AIRUNNER_REPO_ROOT`
- repository discovery by walking upward from the current working directory or
  launcher location

Dev mode resolves Python from:
- `--python`
- `AIRUNNER_DEV_PYTHON`
- `<repo>/venv/bin/python` on Linux
- `<repo>/.venv/bin/python` on Linux
- the equivalent `Scripts/python.exe` paths on Windows

### Effective Runtime Values

Dev mode sets:
- bundle root: repository root
- Python executable: repository venv interpreter
- `PYTHONPATH`: `<repo>/src`
- entrypoint: `airunner.launcher`

### Dev Failure Conditions

Dev mode is considered invalid when:
- the repository root cannot be located
- no repository venv Python can be resolved
- the explicitly requested Python path does not exist

The launcher should fail with actionable errors rather than silently falling
through once `dev` mode is explicitly requested.

## Prod Mode Contract

`prod` mode exists for packaged AIRunner installs that bundle Python and the
native sidecar binaries.

### Manifest Resolution

Prod mode resolves the runtime manifest from:
- `--manifest`
- `AIRUNNER_RUNTIME_MANIFEST`
- a default manifest search near the launcher binary

Current default manifest search paths are:
- `<launcher-dir>/runtime_manifest.env`
- `<launcher-dir>/../share/airunner/runtime_manifest.env`
- `<launcher-dir>/share/airunner/runtime_manifest.env`

### Manifest Path Rules

- relative paths are resolved relative to the manifest file location
- absolute paths are allowed but should be avoided for shipped bundles
- the manifest is the contract between packaging and launcher startup

### Required Manifest Keys

- `AIRUNNER_PYTHON`

### Optional Manifest Keys

- `AIRUNNER_BUNDLE_ROOT`
- `AIRUNNER_PYTHONPATH`
- `AIRUNNER_ENTRYPOINT`
- `AIRUNNER_LLAMA_SERVER_BIN`
- `AIRUNNER_WHISPER_SERVER_BIN`

### Effective Defaults

If `AIRUNNER_BUNDLE_ROOT` is omitted, the launcher uses the manifest
directory.

If `AIRUNNER_ENTRYPOINT` is omitted, the launcher uses:
- `airunner.launcher`

### Prod Failure Conditions

Prod mode is considered invalid when:
- no runtime manifest can be found
- the manifest cannot be opened
- `AIRUNNER_PYTHON` is missing from the manifest
- the resolved Python executable path does not exist

The launcher may resolve sidecar binary paths from the manifest, but missing
sidecar executables are not yet treated as a launcher-time fatal error because
the Python runtime still owns sidecar startup and can present more contextual
diagnostics.

## Environment Export Contract

The launcher exports these environment variables before Python startup:
- `AIRUNNER_LAUNCH_MODE`
- `AIRUNNER_BUNDLE_ROOT`
- `AIRUNNER_PYTHON`
- `AIRUNNER_NATIVE_LAUNCHER`
- `DEV_ENV`

When available, it also exports:
- `AIRUNNER_RUNTIME_MANIFEST`
- `PYTHONPATH`
- `AIRUNNER_LLAMA_SERVER_BIN`
- `AIRUNNER_WHISPER_SERVER_BIN`

## Current Command Surface

The launcher currently supports:
- `--mode auto|dev|prod`
- `--manifest <path>`
- `--repo-root <path>`
- `--python <path>`
- `--print-plan`
- `--dry-run`

`--dry-run` prints the resolved launch plan and exits without starting
Python.

## Boundary With Python Runtime Ownership

At the current stage:
- native code selects the runtime layout and bootstraps Python
- Python still owns AIRunner application startup
- Python still owns runtime client and sidecar supervision

If future packaging work moves sidecar supervision partly into native code,
this contract must be updated before that behavior changes.