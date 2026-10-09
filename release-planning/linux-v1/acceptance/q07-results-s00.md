# Q07-S00 evidence — 2026-10-09 (FAILED: frozen boot defect)

Scenario: `q07-gpu-lifecycle.md` Q07-S00 (record candidate, hardware,
driver, model revisions). Operator: agent boot probe on the build box.
Verdict: **FAIL** — the gate-passing candidate cannot boot (defect
filed as #2245). S01–S08 remain PENDING behind that defect.

## Candidate identity

- Bundle dir: `/tmp/bundle/dist/airunner-daemon` (8.4G)
- Entry: `airunner_services.daemon:main`, frozen with
  `pyinstaller==6.12.0`, manifest base `51b0aee63`
- `sha256(airunner-daemon)`:
  `51911a1630f66c0abba598476bf7d6d70979c463295c156dc4046cf8b39baded`
- `sha256(bundle-manifest.json)`:
  `571d32b967984c9da4b7c8b53376325bab41a1068fbb6376cfd3a42e31b1a3c0`
- Inspector: exit 0 ("passes bundle inspection"), two expected
  release-provided-sidecar warnings (llama-server, whisper-server)

## Hardware and driver (nvidia-smi, observed)

- GPU: NVIDIA GeForce RTX 5080, 16303 MiB, compute capability 12.0
- Driver: 615.71.09
- Box state at probe: GPU 7% / 2441 MiB used (operator's long-running
  engine daemon); box under memory pressure (see #2242)

## Boot probe (observed)

- `--help` works (usage + `--config`/`--generate-config` shown).
- Full boot on loopback test config (127.0.0.1:18289, scratch
  `AIRUNNER_BASE_PATH`, empty models) **crashes before serving**:
  `llm_generate_worker` import → `llm_model_manager` →
  `transformers.models` lazy `__init__` calls
  `os.scandir(.../_internal/transformers/models/__init__.pyc)` →
  `FileNotFoundError`. Full traceback and repro in #2245.
- Daemon `/health` and `/api/v1/daemon/hardware` were unreachable
  (no listener; process exited). No daemon-side hardware record
  exists for this candidate.
- Secondary observation (same run, non-fatal): first boot on the
  empty scratch dir logs a caught `no such table:
  application_settings` from the knowledge-migration check before
  schema setup completes (also noted in #2245).

## What unblocks S00

#2245 fixed (frozen transformers import) plus a successful boot to
`/health` + `/api/v1/daemon/hardware` on this candidate. Re-run this
scenario from the top against the fixed candidate; do not carry these
digests forward (the binary will change).
