# API and Model Extraction Plan

This note captures the current state of the split between `api/`,
`model/`, and the remaining service-owned implementation details.

## Current State

The extraction has already produced real top-level `api/` and `model/`
packages.

- `api/` owns the shared messages, request or response contracts, and
  bootstrap wrappers.
- `model/` owns shared runtime contracts, ORM models, settings, and
  runtime helpers.
- `services/` still owns most of the live FastAPI server and daemon
  orchestration code that consumes those packages.

## Completed Slices

### `api/`

- transport-neutral envelopes in `airunner_api.messages`
- bootstrap or compatibility wrappers used by the daemon
- route or transport adapter surfaces that higher layers can import

### `model/`

- shared runtime contract types
- shared settings and ORM model surfaces
- runtime helper modules used by multiple packages

## Remaining Transitional Areas

- some route wrappers still delegate into service-owned modules
- some runtime helpers and sidecar coordination logic still span
  `services/` and `model/`
- some client code still imports compatibility wrappers rather than only
  the final package-owned surface

## Near-Term Direction

1. Keep new transport-schema work in `api/`.
2. Keep shared runtime-contract and settings work in `model/`.
3. Keep daemon orchestration and HTTP-server ownership in `services/`.
4. Retire compatibility wrappers only after callers have moved to the
   correct package surface.

## Validation Gates

Use these checks when changing the split surfaces:

```bash
./venv/bin/python -m pytest api/tests/test_service_bootstrap.py -v
./venv/bin/python scripts/run_tests.py --llm-runtime-smoke
./venv/bin/python scripts/run_tests.py --stt-runtime-smoke
./venv/bin/python scripts/run_tests.py --tts-runtime-smoke
```

Use the daemon-backed functional suites in `api/tests/` whenever a change
crosses package boundaries in a way that could affect the composed product.