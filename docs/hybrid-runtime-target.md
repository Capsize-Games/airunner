# Hybrid Runtime Target

AIRunner's long-term delivery target is a bundled native application that
privately carries the Python runtime it still needs.

The goal is not a wholesale rewrite of the product into a second language.
The goal is to move Python behind explicit runtime boundaries so the host can:

- bundle CPython and Python dependencies without asking users to install them
- supervise, restart, and isolate Python-owned services
- move selected workloads into native sidecars when that is practical
- preserve the existing Python feature surface while tightening ownership

That direction drives the current runtime work:

- daemon lifecycle control separates process supervision from feature code
- runtime registries and neutral envelopes make local and sidecar execution
  look the same to higher layers
- adapter-owned inference paths reduce direct ownership by large manager
  classes and make replacement boundaries clearer

User-facing requirement:

- end users should not need to manage Python, pip, or model-serving
  dependencies directly

Engineering requirement:

- Python-heavy subsystems should sit behind small, explicit APIs so they can
  be embedded, sandboxed, restarted, or replaced incrementally

## Current Delivery Modes

AIRunner currently supports three installation or delivery modes while this
runtime target is being productized:

1. `single-package` for a prebuilt desktop bundle with embedded Python and
  bundled native runtimes
2. `dev` for repo-local editable installs driven by `./scripts/install.sh`
3. `distributed` for separate daemon and GUI-client installs driven by
  `./deployment/install_distributed.sh`

Those modes share the same package split:

- `native/` owns launcher and installer surfaces
- `src/` owns the desktop client
- `services/` owns the daemon and orchestration layer
- `api/` and `model/` provide the shared contract surfaces