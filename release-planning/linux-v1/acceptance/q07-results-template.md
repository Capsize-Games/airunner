# Q07 — Results template (operator fills in; all PENDING until run)

Issue: https://github.com/Capsize-Games/airunner/issues/2146 (Q07).
Scenario script: `q07-gpu-lifecycle.md` (same directory).
R02 matrix rows filled by S00–S08: `../hardware-models.md` §5.

Rules (from the issue): record candidate digest,
hardware/driver/model revisions, and exact scenario IDs/results.
Untested/skipped/failed is not pass. File one-behavior defects
with sanitized evidence (no credentials, customer content, or
sensitive imagery). Never claim manual efficacy passed from
static analysis — this template stays PENDING until a human
operator runs the script on approved hardware.

## Run identity

- Operator name: PENDING
- Operator date (UTC): PENDING
- Reviewer name: PENDING
- Reviewer date (UTC): PENDING
- Candidate: PENDING (`bundle-manifest.json`: tool/entry/base;
  plus dpkg version or `VERSION` label and install prefix)
- Candidate digest (`sha256` of the bundle per the manifest
  `files` table, or the C01 gate record): PENDING
- Install method: PENDING (P06 `install.sh` prefix / apt unit)
- Daemon base URL used: PENDING (default `http://127.0.0.1:8188`)

## Hardware / driver / model revisions (from Q07-S00)

- GPU (nvidia-smi `name`): PENDING
- Driver (nvidia-smi `driver_version`): PENDING
- Total VRAM: PENDING (must be ≥ 16 GB)
- Compute capability: PENDING (advisory; 8.0+ enables one
  optional fast path, not a floor)
- Daemon `/api/v1/daemon/hardware` payload agrees: PENDING
  (yes/no + skew notes)
- torch / torchvision / torchaudio versions: PENDING
- Free disk at data dir: PENDING (planning floor 30 GB)
- P09 required checks (`gpu_present`, `vram_capacity`,
  `gpu_driver`, `free_disk`, `runtime_torch`,
  `runtime_torchvision`, `runtime_torchaudio`): PENDING
  (all `supported` / list any other verdict)
- Art model (repo + revision/digest): PENDING
- LLM model (repo + revision/digest): PENDING
- STT model (whisper.cpp sidecar pin + model file): PENDING
- TTS engine + voice/model: PENDING
- Embedding model (expect `intfloat/e5-large` local;
  `AIRUNNER_EMBED_ENDPOINT` unset): PENDING

## Per-scenario results

Copy one block per scenario. Status is exactly one of
PENDING / PASS / FAIL / SKIPPED (with reason — skipped is
not pass and needs a linked follow-up before Q07 closes).

### Q07-S00 — Environment capture and prerequisite gate

- Status: PENDING
- Operator / date: PENDING
- Evidence: PENDING (manifest excerpt, nvidia-smi output,
  `/hardware` payload, module versions, gate table)
- Defects filed: PENDING (issue links or "none")

### Q07-S01 — Art → chat switch, single VRAM occupant

- Status: PENDING
- Operator / date: PENDING
- Evidence: PENDING (runtime-summary snapshots pre/during/
  post-switch, VRAM readings, art result retrieval)
- Defects filed: PENDING

### Q07-S02 — Chat → STT → TTS voice round trip

- Status: PENDING
- Operator / date: PENDING
- Evidence: PENDING (per-switch runtime snapshots,
  transcription JSON, `q07-tts.wav` size/duration)
- Defects filed: PENDING

### Q07-S03 — Embedding workload switch, index state intact

- Status: PENDING
- Operator / date: PENDING
- Evidence: PENDING (index status pre/post-switch, RAG-06
  identity values recorded)
- Defects filed: PENDING

### Q07-S04 — Overlapping GPU jobs serialize

- Status: PENDING
- Operator / date: PENDING
- Evidence: PENDING (snapshots during overlap, arbitration
  outcome observed: queued / preempted / admission error;
  batch image count on re-run)
- Defects filed: PENDING

### Q07-S05 — Cancel in-flight GPU work, no orphans

- Status: PENDING
- Operator / date: PENDING
- Evidence: PENDING (terminal job/index states, VRAM
  before/after each cancel, `pgrep` output)
- Defects filed: PENDING

### Q07-S06 — Idle unload; reload; defaults restored

- Status: PENDING
- Operator / date: PENDING
- Evidence: PENDING (timeout value used, pre/post-idle
  summaries + VRAM, reload confirmation, defaults-restored
  confirmation)
- Defects filed: PENDING

### Q07-S07 — OOM recovery, state intact, daemon up

- Status: PENDING
- Operator / date: PENDING
- Evidence: PENDING (oversized request actually used, exact
  surfaced OOM message, terminal job state, `/health`
  before/after, thread payload diff (must be empty), small
  follow-up job result, `pgrep` output)
- Defects filed: PENDING

### Q07-S08 — Final audit: no orphans, user data intact

- Status: PENDING
- Operator / date: PENDING
- Evidence: PENDING (`pgrep` output, final runtime report,
  data-dir spot-check, log location checked)
- Defects filed: PENDING

## Sign-off

- All scenarios PASS with evidence attached: PENDING (yes/no)
- Open facts OF-1–OF-3 resolved or linked: PENDING
- R02 §5 rows updated from this run: PENDING (yes/no + commit)
- Reviewer acceptance: PENDING (name/date — the issue stays
  open until this exists)
