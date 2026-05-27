# API and Model Consolidation Notes

This note captures the current state of the remaining split between
`model/` and the service-owned daemon API surface.

## Current State

The top-level `api/` wrapper package has been removed.

- `services/` owns the live FastAPI and WebSocket daemon surface.
- `model/` owns shared runtime contracts, transport-neutral runtime
  envelopes, ORM models, settings, and runtime helpers.

## Completed Slices

### `model/`

- shared runtime contract types
- transport-neutral runtime envelopes in `airunner_model.runtimes.messages`
- shared settings and ORM model surfaces
- runtime helper modules used by multiple packages

## Remaining Transitional Areas

- some runtime helpers and sidecar coordination logic still span
  `services/` and `model/`
- some client code still assumes the older package layout in docs or test
  runner paths

## Near-Term Direction

1. Keep transport-neutral runtime contracts and envelope schemas in `model/`.
2. Keep daemon orchestration and HTTP/WebSocket server ownership in `services/`.
3. Keep GUI-facing clients in `src/`.
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