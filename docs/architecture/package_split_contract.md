# Package Split Contract

This document records what each top-level package is expected to own and
how to validate changes without blurring those boundaries again.

## Ownership Contract

| Package | Primary ownership |
|---------|-------------------|
| `services/` | daemon routes, HTTP/WebSocket API surface, lifecycle, runtime orchestration, downloads, persistence, and the canonical daemon HTTP client |
| `src/` | desktop UI, GUI workflow surfaces, and the thin `airunner.daemon_client` re-export layer |
| `native/` | Python launcher entry point, runtime layout helpers, startup environment configuration, and sidecar support |
| `scripts/` | developer tooling: test runner, UI build, install helpers, and quality reports |

The top-level `api/` and `model/` packages from earlier split-plan documents
no longer exist in the tree. Shared runtime contracts and enums live in
`airunner_services.contract_enums`.

## Boundary Examples

- CivitAI browse, search, model-detail fetches, and download jobs belong to
	`services/`.
- `src/` owns the desktop browser popup, GUI widgets, worker polling, and
	local thumbnail presentation.
- The desktop daemon client is a thin re-export of
	`airunner_services.daemon_client`, so the wire format stays in one place.
- GUI code may cache preview images through the shared URL-safety helpers in
	`services/`, but GUI code should not stream provider model downloads directly.

## Validation Matrix

### `services/`

Use these when changing daemon routes, workers, runtime routing, the
daemon HTTP client, or service-owned orchestration.

```bash
./venv/bin/python scripts/run_tests.py --llm-runtime-smoke
./venv/bin/python scripts/run_tests.py --stt-runtime-smoke
./venv/bin/python scripts/run_tests.py --art-runtime-smoke
./venv/bin/python scripts/run_tests.py --tts-runtime-smoke
```

Pair those with the relevant functional suite in `services/tests/` whenever the
change affects real daemon behavior.

### `src/`

Use the desktop unit suite first, then the offscreen GUI functional tests
for real desktop-to-daemon behavior.

```bash
./venv/bin/python scripts/run_tests.py --unit
./venv/bin/python -m pytest services/tests/test_gui_llm_tts_functional.py -v --timeout=1200
./venv/bin/python -m pytest services/tests/test_gui_stt_llm_tts_functional.py -v --timeout=1200
```

### `native/`

Use launcher smoke checks and the functional suites that rely on bundled
sidecars.

```bash
./scripts/install.sh --help
./deployment/install_distributed.sh --help
./scripts/build_runtime_sidecars.sh --target-platform linux
./venv/bin/python -m pytest services/tests/test_llm_functional.py -v --timeout=900
./venv/bin/python -m pytest services/tests/test_stt_transcribe_functional.py -v --timeout=1200
```

### `scripts/`

Use the tooling itself as its smoke surface, since it is not part of the
runtime product.

```bash
./venv/bin/python scripts/run_tests.py --unit
./venv/bin/python scripts/run_tests.py --help
```

## Functional Test Placement

Most real end-to-end tests live in `services/tests/` even when the primary code
under test belongs to `services/`, `src/`, or `native/`.

That is intentional. Those tests validate the composed product boundary:

- daemon bootstrap
- runtime loading and unloading
- real inference requests
- GUI-to-daemon handoff
- native sidecar resolution

Do not treat their directory placement as package ownership.

## Installer Contract

AIRunner currently supports two install modes and each one should remain
documented and working:

1. `dev` for repo-local editable development installs
2. `distributed` for separate daemon and GUI-client installs

Changes that affect installer scripts, bundle layout, or sidecar
resolution should update the package README files and the root README at
the same time.
