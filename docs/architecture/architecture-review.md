# AIRunner Architecture Review & Solution Design

Date: 2026-08-16
Scope: post-C++-strip architecture assessment, simplification opportunities,
gaps, and a prioritized set of solutions.

---

## 1. Executive Summary

AIRunner's core architecture is **sound** and worth keeping: a PySide6
desktop client (`src/`) that talks to a locally owned FastAPI daemon
(`services/`) over loopback HTTP, where the daemon owns model loading,
runtime supervision (llama.cpp / whisper.cpp sidecars, torch-based art/TTS),
downloads, and persistence. That boundary is what makes headless, remote,
and multi-machine deployment possible, and it should not be collapsed.

The problems are **not** architectural — they are organizational:
duplicated modules across packages, two competing `airunner` entry points,
undeclared cross-package dependencies, a crash-unfriendly GUI (no exception
handler), documentation that describes packages and a distribution model
that no longer exist, and roughly 350k lines of Python with evident dead
code. Each is addressable with small, safe, incremental changes. No
big-bang rewrite is warranted.

---

## 2. As-Is Architecture

### 2.1 Packages

| Package | Contents | Approx. LOC | Role |
|---|---|---|---|
| `src/` (`airunner`) | PySide6 GUI, dialogs, widgets, daemon client | ~205k | Desktop client |
| `services/` (`airunner_services`) | FastAPI daemon, runtimes, downloads, model management, CLI | ~140k | Headless daemon + API |
| `native/` (`airunner_native`) | Python launcher entry, layout/path helpers, startup env | ~1k | Launcher + runtime helpers |
| `scripts/` | Dev/install/build/test tooling | ~3.7k | Repo tooling |

### 2.2 Runtime topology

```
airunner (Python launcher)
  └─ PySide6 GUI (src/airunner)
        │  HTTP (127.0.0.1:8188, /api/v1/*)
        ▼
   airunner_services.daemon (FastAPI)
        ├─ runtimes: llama-server / whisper-server (sidecar binaries)
        ├─ runtimes: torch-based art + TTS
        ├─ downloads: HuggingFace / CivitAI job service
        └─ persistence: SQLite / DB + knowledge base
```

### 2.3 Entry points (after the strip)

- `airunner` console script — defined in **both** `setup.py`
  (`airunner=airunner.launcher:main`) and `native/package_metadata.py`
  (`airunner=airunner_native.launcher:main`). The winner depends on
  editable-install order. This is a latent bug.
- `airunner-daemon`, `airunner-headless`, `airunner-hf-download`,
  `airunner-civitai-download` from `services`.
- Dev/test console scripts from `setup.py`.

### 2.4 Dev flow

`./scripts/install.sh` creates/reuses `venv/`, installs `services[native
extras]`, `native`, and `.` editably, then builds the pinned sidecars.
`./scripts/run.sh` starts the daemon, health-checks it, and execs the GUI
launcher.

---

## 3. What Is Sound (Keep)

1. **GUI ⇄ daemon HTTP boundary.** It enables headless operation,
   remote/`distributed` deployment, and isolates GUI crashes from model
   loading. Do not merge `src/` and `services/` into one process without a
   compelling reason.
2. **Daemon owns runtimes and model lifecycle.** Single model loader,
   centralized memory management, and worker orchestration. Correct
   ownership for GPU memory.
3. **Python-only distribution (post-strip).** Removes the C++ build chain,
   embedded-Python bundling, and installer packaging from the critical
   path. `./install.sh`, `./scripts/run.sh`, and `pip install airunner`
   are now the only distribution surfaces.
4. **Editable dev installs + dev scripts.** Fast iteration, clear
   boundaries (`run_services.sh`, `run_gui.sh`, `test_services.sh`).
5. **Sidecars as pinned runtime binaries.** llama.cpp/whisper.cpp stay out
   of the Python packaging graph and are version-pinned.

---

## 4. Problems & Simplification Opportunities

### P1 — Duplicated modules across packages (high value)

| Module | Copies | Drift risk |
|---|---|---|
| `settings.py` | `src/`, `services/`, `native/` (3) | High |
| `linux_bundle_layout.py` | `src/`, `native/` (2) | High |
| `startup_env.py` | `services/`, `native/` (2) | Medium |
| `dev_build_token.py` | `src/`, `services/` (2) | Medium |
| daemon client | `src/airunner/daemon_client/` (~2.2k LOC) + `services/.../daemon_client/` (~1.2k LOC) | High |

The daemon-client duplication is the most expensive: two implementations of
the same HTTP client contract that must be kept in lockstep.

### P2 — Two `airunner` entry points (bug, not just smell)

`setup.py:73` and `native/package_metadata.py:24` both register `airunner`.
Whichever editable install runs last overwrites the other's script. The GUI
and headless dispatches live in different modules, so behavior silently
depends on install order.

### P3 — Undeclared cross-package dependencies

`src/` imports `airunner_services` and `airunner_native` at runtime, but
`setup.py`'s `install_requires` only lists PySide6 + facehuggershield.
A bare `pip install airunner` produces a broken GUI, and there is no single
place that states the true dependency graph.

### P4 — No crash capture in the GUI

There is **no `sys.excepthook`** in the launcher or app. The "Download
Models" crash (a missing-import `NameError`) produced no on-disk log and
took the whole app down. GUI exceptions are only visible in a terminal
that usually does not exist for end users.

### P5 — Documentation drift

README and several `docs/architecture/*` files reference `api/` and
`model/` packages that do not exist, plus a `single-package` / end-user
bundle distribution model that has been removed. Partially cleaned in this
session; a full pass is still needed.

### P6 — ~350k LOC with evident dead code

`gui_vulture_whitelist.py` and `services_vulture_whitelist.py` exist
precisely because large portions of `src/` and `services/` are
unreferenced. The included scanners (`gui_dead_code_scanner.py`,
`services_dead_code_scanner.py`, `remove_unused_imports.py`) are the tooling
to prune this surface.

### P7 — Install friction

- `scripts/install.sh` forces a torch reinstall in `auto` mode unless torch
  is already importable (mitigated this session), and always attempts a
  network `git fetch` + rebuild of llama.cpp/whisper.cpp. Sidecar builds
  need `cmake` + network and can take tens of minutes.
- `facehuggershield` is installed from a GitHub tarball URL (supply-chain
  fragility; should be published to PyPI or vendored).

### P8 — Dev tooling sprawl

`scripts/` contains ~25 ad-hoc analysis scripts (complexity, dead-code,
unused-import scanners, reports). Useful, but they are a separate tool
surface to maintain; consider consolidating into one `airunner-dev-tools`
console command.

---

## 5. Gaps

1. **No global exception handler / crash log** for the GUI (P4).
2. **No declarative, machine-readable dependency contract** between
   packages (P3, P2).
3. **No GUI smoke test in CI.** `eval-tests.yml` covers runtime contracts
   and runtime smoke; nothing boots the PySide6 GUI headlessly.
4. **Single machine of truth missing** for settings/layout defaults (P1).
5. **Unused/retired feature surface** (FHE/TenSEAL logging, `mslk.so`
   loading, cloud-deployment branches in `service_app.py`) suggests a
   merged/legacy code path that is never exercised locally; it should be
   audited for removal or made explicit behind a flag.

---

## 6. Solution Design (prioritized)

### S1 — One `airunner` entry point + declared dependency graph (this week)

- Make `src/airunner/launcher.py` the single desktop entry.
- Have `native/src/airunner_native/launcher.py` delegate to it
  (`from airunner.launcher import main`) or drop its `airunner` console
  script, keeping `airunner_native` as pure helper modules.
- Declare real dependencies in `setup.py`:
  `airunner-services==X` and `airunner-native==X` in `install_requires`
  (or in the `gui`/`desktop` extras that CI and docs already reference).
- Verify with a clean-venv install in CI.

### S2 — Global crash capture in the GUI (this week)

- In `src/airunner/launcher.py::main()` (and the native launcher), install
  before any Qt code:
  - `sys.excepthook` → append traceback to
    `~/.local/share/airunner/logs/gui.log` and show a one-time error dialog.
  - `faulthandler.enable(file=...)` for native-level crashes.
  - A `sys.unraisablehook` for background-thread failures.
- This converts today's silent crash (the "Download Models" `NameError`)
  into a logged, user-visible failure — and would have surfaced the root
  cause immediately.

### S3 — Consolidate duplicated modules (next)

- Introduce a small shared package, `airunner_common` (or reuse
  `airunner_services` as the dependency anchor), and move these there:
  `settings`, `startup_env`, `dev_build_token`, `linux_bundle_layout`,
  `logging_utils`/`get_logger`.
- `src/`, `services/`, `native/` import from the single source; delete the
  per-package copies.
- **One daemon client:** make `services/.../daemon_client/gui_daemon_client.py`
  canonical; convert `src/airunner/daemon_client/` mixins to thin re-exports
  or delete them and import directly from `airunner_services`.

### S4 — Dead-code and legacy-surface pruning (next)

- Run `scripts/gui_dead_code_scanner.py` /
  `scripts/services_dead_code_scanner.py`, review the vulture whitelists,
  and delete unreferenced modules in a sequence of reviewable commits.
- Audit the "cloud deployment" branches in `service_app.py` /
  `runtime_mixin.py`; if unused locally, gate them behind
  `AIRUNNER_DEPLOYMENT=cloud` or remove them.
- Remove the FHE/TenSEAL critical-logging code path or the dependency that
  triggers it.

### S5 — CI and docs alignment (next)

- Add a headless GUI smoke job to `eval-tests.yml`
  (`QT_QPA_PLATFORM=offscreen`, instantiate `DownloadModelsDialog` /
  `MainWindow`, assert no exception) — this would have caught the crash.
- Add a clean-venv install test that exercises `scripts/install.sh
  --sidecars skip` + a minimal import check.
- Finish removing `api/`, `model/`, `single-package` references from
  `README.md` and `docs/architecture/*`.

### S6 — Install friction (backlog)

- Default `scripts/install.sh` to skip the sidecar rebuild when binaries
  are already present and pinned commits match (add a stamp check), making
  re-installs seconds instead of tens of minutes.
- Publish `facehuggershield` to PyPI (or vendor it) to remove the GitHub
  URL dependency.

---

## 7. Decisions & Rationale

- **Keep the daemon boundary.** It is the source of headless/remote value;
  merging it would be a regression.
- **Keep sidecars as runtime binaries.** They are model runtimes, not
  application distribution.
- **Do not rebuild the packages.** Consolidate, prune, and declare — the
  layout is already correct.
- **Make the GUI fail loudly and locally.** S2 is the single highest-impact
  fix for the user experience observed today.
