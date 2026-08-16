# API and Model Consolidation Notes

This note captures the current state of the split between the service-owned
daemon API surface and the removed top-level `api/` and `model/` packages.

## Current State

The top-level `api/` and `model/` wrapper packages have been removed.

- `services/` owns the live FastAPI and WebSocket daemon surface, shared
  runtime contracts and enums (`airunner_services.contract_enums`), runtime
  helpers, and the canonical daemon HTTP client.
- `src/` owns GUI workflow surfaces and a thin `airunner.daemon_client`
  re-export layer over the service-owned client.
- `native/` owns the Python launcher entry point and runtime layout helpers.

## Completed Slices

### `services/`

- shared runtime contract enums in `airunner_services.contract_enums`
- transport-neutral runtime envelopes
- runtime helper modules used by multiple packages
- the canonical daemon HTTP client in `airunner_services.daemon_client`

### `src/`

- desktop GUI and user workflow surfaces
- `airunner.daemon_client` as a compatibility re-export of the canonical
  service-owned daemon client

## Remaining Transitional Areas

- some runtime helpers and sidecar coordination logic still span
  `services/` and `src/`
- some client code still assumes the older package layout in docs or test
  runner paths

## Near-Term Direction

1. Keep transport-neutral runtime contracts and envelope schemas in
   `airunner_services`.
2. Keep daemon orchestration and HTTP/WebSocket server ownership in `services/`.
3. Keep GUI-facing clients in `src/` as re-exports of the service-owned client.
4. Avoid recreating wrapper packages that forward one layer into another.

## Validation Gates

Use these checks when changing the split surfaces:

```bash
./venv/bin/python -m pytest services/tests/test_service_bootstrap.py -v
./venv/bin/python scripts/run_tests.py --llm-runtime-smoke
./venv/bin/python scripts/run_tests.py --stt-runtime-smoke
./venv/bin/python scripts/run_tests.py --tts-runtime-smoke
```

Use the daemon-backed functional suites in `services/tests/` whenever a change
crosses package boundaries in a way that could affect the composed product.
