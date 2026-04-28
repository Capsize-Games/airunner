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

The scaffold currently launches Python and sets runtime environment variables.
It does not yet replace the Python-side sidecar supervision or installer
assembly work.

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

## Non-Goals

These are not the target:
- requiring users to install Python first
- requiring users to clone the repo
- requiring users to build `llama.cpp` or `whisper.cpp`
- requiring users to configure sidecar paths manually
- treating a developer virtualenv as the shipping product

## Engineering Work Breakdown

This work is tracked in #82 and should be split into at least these slices:

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

What remains is productization and distribution engineering, not another
full runtime rewrite.