# AIRunner End-User Distribution Plan

This document defines the product requirement that sits above the completed
hybrid runtime migration.

## Product Contract

End users should be able to install AIRunner on Linux or Windows and run it
without installing Python, creating a virtual environment, or manually
providing `llama.cpp` and `whisper.cpp` executables.

From the user's perspective there should be one installed AIRunner
application and one primary `airunner` entry point.

## What "Single Binary" Should Mean

A true single-file executable that statically absorbs Python, Qt, native
sidecars, CUDA-dependent libraries, and AIRunner assets is possible in
theory, but it is not the right engineering target here.

The practical requirement is:
- one installed AIRunner product
- one primary launcher or command exposed to the user
- zero system Python dependency
- zero manual sidecar setup

The installed bundle may still contain multiple internal files as long as the
user never has to reason about them.

## Recommended Architecture

The distribution should be built around a native launcher and a bundled
runtime tree.

### Native launcher

Build a small C or C++ launcher with CMake for Linux and Windows.

Responsibilities:
- locate the AIRunner install root
- initialize runtime environment variables
- start the bundled Python runtime with the AIRunner application entry point
- supervise bundled `llama.cpp` and `whisper.cpp` binaries when needed
- surface actionable startup errors when the install is damaged

Current scaffold in this repo:
- `native/airunner_launcher/` contains the first launcher project
- `scripts/build_airunner_launcher.sh` builds it locally
- `scripts/run_airunner_dev.sh` runs AIRunner through the native launcher in
	dev mode using the repository `venv`

The launcher currently owns bundle-plan resolution, runtime environment
export, and Python process launch. Python still owns runtime-client and
sidecar supervision inside the packaged product.

### Bundled runtime tree

The install artifact should contain:
- embedded Python runtime
- AIRunner application code and assets
- pinned `llama.cpp` runtime binary
- pinned `whisper.cpp` runtime binary
- runtime manifest describing relative paths, versions, and integrity data

### Installer outputs

Recommended initial outputs:
- Linux: AppImage plus a tarball or native package format
- Windows: MSI or another standard installer format

The installer should create a single desktop entry and a single primary
`airunner` command.

## Current Implementation

The no-Python end-user distribution delivery now includes:
- a native launcher in `native/airunner_launcher/` plus
	`scripts/build_airunner_launcher.sh`
- pinned `llama.cpp` and `whisper.cpp` sidecar build inputs in
	`native/runtime_sidecars/` plus `scripts/build_runtime_sidecars.sh`
- pinned embedded Python metadata in `native/embedded_python/`
- staged bundle assembly in `src/airunner/bin/build_end_user_bundle.py`
- a local Linux bundle wrapper in `scripts/build_airunner_bundle.sh`
- AppImage packaging in `scripts/package_linux_appimage.sh`
- Windows NSIS packaging in `scripts/package_windows_nsis.ps1`
- Linux tarball installation support in `install.sh --bundle-archive`
- launcher and bundle smoke coverage in
	`src/airunner/distribution/tests/test_launcher_smoke.py`
- Linux and Windows installer validation in
	`.github/workflows/pypi-dispatch.yml`

The bundle layout currently stages:
- `python/` for the embedded runtime
- `app/site-packages/` for AIRunner and Python dependencies
- `bin/` for the native launcher plus sidecar binaries
- `share/airunner/` for runtime manifest and bundle metadata

## Non-Goals

These are not the target:
- requiring users to install Python first
- requiring users to clone the repo
- requiring users to build `llama.cpp` or `whisper.cpp`
- requiring users to configure sidecar paths manually
- treating a developer virtualenv as the shipping product

## Engineering Work Breakdown

Issue #82 is satisfied in-repo by these slices:

1. Define the distribution contract and manifest.
2. Build the native launcher/bootstrapper with CMake.
3. Produce pinned platform binaries for `llama.cpp` and `whisper.cpp`.
4. Bundle embedded Python and AIRunner into installable artifacts.
5. Add fresh-machine smoke tests and release validation.

## Relationship To The Hybrid Migration

The hybrid runtime branch completed the architectural preconditions for this
work:
- AIRunner now has explicit runtime boundaries
- LLM and STT can run behind native sidecar launchers
- art and TTS already use isolated Python runtimes
- runtime filesystem layout and service templates are explicit

The follow-on productization work for #82 now exists in-repo as a native
launcher, pinned sidecar build flow, embedded-Python bundle builder,
installer packagers, and installer validation pipeline.

What remains is productization and distribution engineering, not another
full runtime rewrite.