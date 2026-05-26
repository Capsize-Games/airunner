# Package Split Contract

This document records what each top-level package is expected to own and
how to validate changes without blurring those boundaries again.

## Ownership Contract

| Package | Primary ownership |
|---------|-------------------|
| `api/` | transport contracts, shared messages, bootstrap adapters |
| `services/` | daemon routes, lifecycle, runtime orchestration, downloads, persistence |
| `model/` | shared runtime contracts, settings, ORM models, runtime helpers |
| `src/` | desktop UI, daemon clients, user workflow surfaces |
| `native/` | launcher, bundle assembly, install or distribution tooling |

## Boundary Examples

- CivitAI browse, search, model-detail fetches, and download jobs belong to
	`services/`.
- `src/` owns the desktop browser popup, daemon client calls, worker polling,
	and local thumbnail presentation.
- GUI code may cache preview images through the shared URL-safety helpers in
	`model/`, but GUI code should not stream provider model downloads directly.

## Validation Matrix

### `api/`

Use these when changing transport contracts, bootstrap code, or HTTP
surface behavior.

```bash
./venv/bin/python -m pytest api/tests/test_service_bootstrap.py -v
./venv/bin/python -m pytest api/tests/test_tts_runtime_load.py -v
```

### `services/`

Use these when changing daemon routes, workers, runtime routing, or
service-owned orchestration.

```bash
./venv/bin/python scripts/run_tests.py --llm-runtime-smoke
./venv/bin/python scripts/run_tests.py --stt-runtime-smoke
./venv/bin/python scripts/run_tests.py --art-runtime-smoke
./venv/bin/python scripts/run_tests.py --tts-runtime-smoke
```

Pair those with the relevant functional suite in `api/tests/` whenever the
change affects real daemon behavior.

### `model/`

Use consumer-facing validations because the model package is shared across
all higher layers.

```bash
./venv/bin/python -m pytest api/tests/test_tts_runtime_load.py -v
./venv/bin/python -m pytest api/tests/test_stt_transcribe_functional.py -v --timeout=1200
./venv/bin/python -m pytest api/tests/test_llm_functional.py -v --timeout=900
```

### `src/`

Use the desktop unit suite first, then the offscreen GUI functional tests
for real desktop-to-daemon behavior.

```bash
./venv/bin/python scripts/run_tests.py --unit
./venv/bin/python -m pytest api/tests/test_gui_llm_tts_functional.py -v --timeout=1200
./venv/bin/python -m pytest api/tests/test_gui_stt_llm_tts_functional.py -v --timeout=1200
```

### `native/`

Use installer or launcher smoke checks and the functional suites that rely
on bundled sidecars.

```bash
./scripts/install.sh --help
./deployment/install_distributed.sh --help
./scripts/build_runtime_sidecars.sh --target-platform linux
./venv/bin/python -m pytest api/tests/test_llm_functional.py -v --timeout=900
./venv/bin/python -m pytest api/tests/test_stt_transcribe_functional.py -v --timeout=1200
```

## Functional Test Placement

Most real end-to-end tests live in `api/tests/` even when the primary code
under test belongs to `services/`, `model/`, `src/`, or `native/`.

That is intentional. Those tests validate the composed product boundary:

- daemon bootstrap
- runtime loading and unloading
- real inference requests
- GUI-to-daemon handoff
- native sidecar resolution

Do not treat their directory placement as package ownership.

## Installer Contract

AIRunner currently supports three install modes and each one should remain
documented and working:

1. `single-package` for prebuilt desktop bundles
2. `dev` for repo-local editable development installs
3. `distributed` for separate daemon and GUI-client installs

Changes that affect installer scripts, bundle layout, or sidecar
resolution should update the package README files and the root README at
the same time.