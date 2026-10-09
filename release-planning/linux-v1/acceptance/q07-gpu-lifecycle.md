# Q07 — Shared GPU lifecycle across all modalities (operator scenario script)

Issue: https://github.com/Capsize-Games/airunner/issues/2146 (Q07).
Parent: https://github.com/Capsize-Games/airunner/issues/2083.
Prerequisites: B12 (#2141), P09 (#2112), C01 (#2114).
R01 inventory: `../feature-matrix.md`. R02 manifest: `../hardware-models.md`.

Status: **PREPARED — NOT RUN.** Every scenario below is `PENDING`.
This script was written by static reading only: no GPU, model, GUI,
network, or live-database action was taken to produce it. An operator
with the approved 16 GB NVIDIA hardware runs these steps and records
results in `q07-results-template.md`.

Scope: cross-modality GPU lifecycle only — switching art/chat/STT/TTS/
embedding workloads, scheduling overlapping GPU jobs, cancel, idle
unload, and OOM recovery without lost user state or orphan processes.
Per-modality functional correctness stays with its own ticket
(Q02 art, Q03 chat, Q04 voice, Q05 embeddings/RAG); Q07 exercises
those paths only far enough to observe load/switch/unload behavior.

## Conventions

- `D=http://127.0.0.1:8188` — daemon control API base. Defaults are
  host `127.0.0.1`, port `8188` (`DaemonConfig._default_config`;
  `services/src/airunner_services/runtimes/daemon_config.py:50-62`;
  also noted in `debian/airunner.airunner-headless.service:6-7`).
- Runtime names are exactly `llm`, `stt`, `tts`, `art`
  (`RuntimeKind`; `services/src/airunner_services/runtimes/contracts.py:12-18`).
  There is no embedding runtime kind; embedding work runs through the
  RAG index flow on the `llm` route (see Q07-S03 sources).
- Runtime control payload: `{"provider": "local",
  "deployment_mode": "default"}` (`RuntimeRouteRequest`;
  `services/src/airunner_services/api/models/runtime_route_request.py:10-16`).
- Core arbitration behavior under test: loading a runtime unloads
  already-loaded runtimes first, "since only one model can occupy
  VRAM at a time"
  (`services/src/airunner_services/api/routes/daemon.py:88-117`).
- All `curl` commands assume loopback access to a running candidate
  installed per Q01 (P06 installer) or the apt unit; starting/stopping
  the daemon itself is Q01 territory, not repeated here.

## Q07-S00 — Environment capture and prerequisite gate

Goal: record the exact candidate, hardware, driver, and model
revisions, and confirm the P09 gates pass before any GPU scenario.

R01: DL-04 (profiling inputs). R02: §1 baseline, §2 models.

Preconditions: candidate installed; daemon reachable at `$D`;
no model loaded yet (fresh daemon start preferred).

Steps:

1. Record the candidate identity from the installed bundle:
   `cat <prefix>/versions/current/bundle-manifest.json`
   (manifest contract: `bundle`, `tool`, `entry`, `base`, `files`
   with `path`/`sha256` per file;
   `packaging/linux/services-bundle-spec.toml:284-288`).
   For an apt install, record the dpkg version and
   `/etc/airunner/daemon.yaml`
   (`debian/airunner.airunner-headless.service:27,38`).
2. Record the GPU/driver baseline with the profiler's own query
   (a driver query; loads no CUDA context, runs no GPU workload):
   `nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free,compute_cap --format=csv,noheader,nounits`
   (exact field list `_NVIDIA_SMI_FIELDS`;
   `services/src/airunner_services/model_management/hardware_profiler.py:19-56`).
3. Record the daemon's view of the same hardware:
   `curl -s $D/api/v1/daemon/hardware`
   (`HardwareProfileResponse`: total/available VRAM+RAM, CUDA
   availability, compute capability, device name;
   `services/src/airunner_services/api/routes/hardware.py:31-59`).
   It must agree with step 2 within normal sampling skew.
4. Record ML runtime module versions without importing them
   (mirrors `collect_module_versions`, which uses
   `importlib.find_spec`/`importlib.metadata`, never imports):
   `python3 -c "import importlib.metadata as m;
   print({n: (m.version(n) if __import__('importlib.util', fromlist=['x']).find_spec(n) else None) for n in ('torch','torchvision','torchaudio')})"`
   (required modules `REQUIRED_ML_MODULES`;
   `services/src/airunner_services/model_management/prerequisite_types.py:24`;
   collector `prerequisites.py:65-70`).
5. Record installed model revisions for every modality exercised
   below (paths under the data dir — `<prefix>/data` for the P06
   installer, `/var/lib/airunner/models` for the apt unit — plus
   repo/revision/digest where the downloader recorded them).
   Model sources: `../hardware-models.md` §2; data-dir defaults from
   `packaging/linux/install.sh:238` and
   `debian/airunner.airunner-headless.service:26`.
6. Evaluate the P09 gate table by hand (no operator-facing
   prerequisite-report CLI or HTTP route was found in the services
   tree — `evaluate_prerequisites`/`report_from_profile`/
   `format_report_text` are library-only via
   `services/src/airunner_services/model_management/__init__.py`;
   recorded as open fact OF-1). Required checks that must all read
   `supported`: `gpu_present`, `vram_capacity` (≥ 16.0 GB,
   `MIN_VRAM_GB`), `gpu_driver`, `free_disk` (≥ 30 GB planning
   floor), `runtime_torch`, `runtime_torchvision`,
   `runtime_torchaudio`; advisory: `gpu_compute` (Ampere 8.0 is an
   optional fast path, not a floor), `system_ram`
   (`prerequisite_types.py:20-36`, `prerequisite_checks.py:200-206`).

Expected observations: steps 2–3 agree (same device name, VRAM
within ~0.5 GB); all required P09 checks evaluate to `supported`.

Pass: every required check is `supported` and the candidate/
hardware/driver/model revisions are recorded in the results
template. Fail: any required check is `unsupported`/`unknown`
(except pre-agreed advisory waivers), or step 2 and step 3
disagree on device/VRAM (file a defect; do not proceed — later
scenarios assume the 16 GB profile).

Result: **PENDING** (operator/date/evidence in
`q07-results-template.md`).

## Q07-S01 — Art → chat switch, single VRAM occupant

Goal: loading `llm` while `art` is loaded unloads art first;
exactly one modality occupies VRAM after the switch.

R01: ART-09 (daemon SD inference), CHAT-03 (local chat inference),
DL-05 (model lifecycle), SRV-05 (lifecycle/VRAM reporting).

Preconditions: Q07-S00 passed; art + LLM models downloaded.

Steps:

1. Baseline: `curl -s $D/api/v1/daemon/status` and
   `curl -s $D/api/v1/daemon/runtimes`
   (combined lifecycle + per-runtime summaries;
   `services/src/airunner_services/api/routes/daemon.py:41-57`).
   Record which runtimes report loaded.
2. `curl -s -X POST $D/api/v1/daemon/runtimes/art/load
   -H 'Content-Type: application/json'
   -d '{"provider":"local","deployment_mode":"default"}'`
   (load route; unloads other runtimes first;
   `services/src/airunner_services/api/routes/daemon.py:88-117`).
3. Submit one small art job:
   `curl -s -X POST $D/api/v1/art/generate
   -H 'Content-Type: application/json'
   -d '{"prompt":"a red square","width":512,"height":512,"steps":10}'`
   then poll `curl -s $D/api/v1/art/status/<job_id>` to `completed`
   (`start_art_generation`/`art_job_status`;
   `services/src/airunner_services/daemon_client/gui_daemon_client.py:332-399`).
4. Switch: `curl -s -X POST $D/api/v1/daemon/runtimes/llm/load
   -H 'Content-Type: application/json'
   -d '{"provider":"local","deployment_mode":"default"}'`.
5. Re-read `GET $D/api/v1/daemon/runtimes` and
   `GET $D/api/v1/daemon/hardware`; record `available_vram_gb`
   before (step 1), during art (step 3), and after the switch.

Expected observations: after step 4 the `art` summary no longer
reports loaded and the `llm` summary does; available VRAM rises
on art unload and drops on LLM load; the completed art job's
result stays retrievable via `GET /api/v1/art/result/<job_id>`
(`gui_daemon_client.py:401-418`).

Pass: post-switch summaries show exactly one loaded runtime
(`llm`); no error payloads; no second load of either model
(single occupant invariant holds). Fail: both runtimes report
loaded at once, the switch errors, or the prior art result is
unretrievable (file a defect with both summary payloads).

Result: **PENDING**.

## Q07-S02 — Chat → STT → TTS voice round trip across switches

Goal: STT transcription and TTS synthesis each work after a
modality switch, with no duplicate model loads.

R01: CHAT-03, VOICE-02 (whisper.cpp sidecar), VOICE-03/VOICE-04
(TTS engines), VOICE-06 (composed loop, lifecycle aspect only).

Preconditions: Q07-S00 passed; STT + TTS models/voices present.

Steps:

1. Load `llm` (same POST form as Q07-S01 step 2 with
   `runtimes/llm/load`); confirm via `GET
   $D/api/v1/daemon/runtimes/llm?provider=local&deployment_mode=default`
   (`runtime_status` query shape;
   `gui_daemon_client.py:231-251`).
2. Switch to `stt` via `POST
   $D/api/v1/daemon/runtimes/stt/load` (same JSON body).
3. Transcribe a short neutral clip (≤ 30 s, operator-provided):
   `curl -s -X POST $D/api/v1/stt/transcribe
   -F 'audio=@clip.wav;type=audio/wav'`
   (multipart `audio` field;
   `services/src/airunner_services/daemon_client/gui_daemon_client.py:734-755`).
4. Switch to `tts` via `POST $D/api/v1/daemon/runtimes/tts/load`.
5. `curl -s -X POST $D/api/v1/tts/synthesize
   -H 'Content-Type: application/json'
   -d '{"text":"Lifecycle check complete.","speed":1.0}'
   --output q07-tts.wav`
   (`synthesize_tts` payload: text/voice/speed/model/model_type/
   request_id; `gui_daemon_client.py:304-330`).
6. After each switch, capture `GET $D/api/v1/daemon/runtimes` and
   confirm exactly one loaded runtime.

Expected observations: transcription JSON returns text for the
clip; `q07-tts.wav` is non-empty audio; every runtime-summary
snapshot shows a single loaded runtime matching the last switch.

Pass: both voice calls succeed after their switches and the
single-occupant invariant holds at every snapshot. Fail: a voice
call fails with a model-not-loaded error after a reported
successful switch, or two runtimes report loaded (defect with
the summary snapshots and voice payloads).

Result: **PENDING**.

## Q07-S03 — Embedding workload switch, index state intact

Goal: run the local-embedding RAG index flow, switch modality
away and back, and confirm index state survives.

R01: RAG-04/RAG-05 (index/search; lifecycle aspect only),
RAG-06 (index identity owned by B04/Q05 — record, do not judge).

Preconditions: Q07-S00 passed; `intfloat/e5-large` available
locally (the selected local embedding model;
`services/src/airunner_services/runtimes/local_embeddings.py:1-38`);
`AIRUNNER_EMBED_ENDPOINT` unset so the local path (not the
opt-in remote Ollama path) is exercised
(`llm/managers/agent/mixins/rag_properties_mixin.py:102`).

Steps:

1. Start indexing one small neutral document set:
   `curl -s -X POST $D/api/v1/llm/rag/index
   -H 'Content-Type: application/json'
   -d '{"file_paths":["/tmp/q07-docs"]}'`
   (`start_rag_document_index`;
   `services/src/airunner_services/daemon_client/gui_bridge_mixin.py:359-370`).
2. Poll `curl -s $D/api/v1/llm/rag/index/status` to completion
   (`rag_document_index_status`; `gui_bridge_mixin.py:380-384`).
3. Switch away: `POST $D/api/v1/daemon/runtimes/art/load`;
   confirm via `GET $D/api/v1/daemon/runtimes`.
4. Switch back: `POST $D/api/v1/daemon/runtimes/llm/load`.
5. Re-read `GET $D/api/v1/llm/rag/index/status` and confirm the
   completed index is still reported (no re-index required).

Expected observations: index completes in step 2; after the
away-and-back switch the status still reports the completed
index with the same document set — no lost embedding state.

Pass: step 5 shows the step-2 index intact. Fail: the index
report is empty/reset after the switch, or any switch errors
(defect with both status payloads).

Result: **PENDING**.

## Q07-S04 — Overlapping GPU jobs serialize, no duplicate loads

Goal: schedule overlapping GPU work (art batch + chat-side
request + RAG index) and confirm the daemon serializes
arbitration instead of loading duplicate models.

R01: ART-11 (batch), CHAT-06 (stream route exists; content
correctness is FOLLOWUP-3, not judged here), RAG-05, DL-05.
B12 acceptance ("exhausted VRAM/resource admission yield
actionable results instead of loading duplicate models";
#2141) is the behavior under test at the operator level.

Preconditions: Q07-S00 passed; art + LLM models present.

Steps:

1. Submit a two-image art batch:
   `curl -s -X POST $D/api/v1/art/generate
   -H 'Content-Type: application/json'
   -d '{"prompt":"a blue circle","width":512,"height":512,"steps":10,"num_images":2}'`
   (batch returns every image per D03;
   `gui_daemon_client.py:436-455`).
2. While the batch is still running (poll
   `GET $D/api/v1/art/status/<job_id>`; do not wait for
   completion), issue `POST $D/api/v1/daemon/runtimes/llm/load`.
3. Immediately capture `GET $D/api/v1/daemon/runtimes` and the
   art job status; record whether the load queued behind the
   job, preempted it, or returned an actionable admission
   error — any of the three is acceptable *iff* the daemon
   says which one happened (no silent duplicate load).
4. If the art job was preempted/cancelled by the switch,
   confirm its status is a terminal, explained state (not
   stuck `running`); then re-run the batch alone and confirm
   both images retrievable via
   `GET $D/api/v1/art/result/<job_id>/0` and `/1`
   (`art_job_result_at`; `gui_daemon_client.py:420-434`).

Expected observations: at no snapshot do two runtimes report
loaded; the art job ends in a terminal state with an
explanation when preempted; the solo re-run returns both
images (D03: no silently dropped batch image).

Pass: single-occupant invariant holds at every snapshot and
every job reaches a terminal, explained state. Fail: duplicate
loaded runtimes, a job stuck non-terminal, or a silently
dropped batch image (defect with snapshots + job payloads).

Result: **PENDING**.

## Q07-S05 — Cancel in-flight GPU work, VRAM freed, no orphans

Goal: cancelling an art job, a runtime request, and a RAG index
each reaches a terminal cancelled state, frees VRAM, and leaves
no orphan job or process.

R01: ART-01/ART-03 (job path), RAG-05 (index path), DL-05, SRV-05.

Preconditions: Q07-S00 passed; art + LLM models present.

Steps:

1. Submit a deliberately slow art job (high steps, e.g.
   `"steps":60,"width":1024,"height":1024`) via
   `POST $D/api/v1/art/generate`; record `available_vram_gb`
   from `GET $D/api/v1/daemon/hardware` while it runs.
2. Cancel it: `curl -s -X DELETE
   $D/api/v1/art/cancel/<job_id>`
   (`cancel_art_job`; `gui_daemon_client.py:555-567`).
   Poll `GET $D/api/v1/art/status/<job_id>` to a terminal
   cancelled/failed state.
3. Cancel at the runtime layer instead of the job layer:
   submit a second slow art job, then
   `curl -s -X POST $D/api/v1/daemon/runtimes/art/cancel
   -H 'Content-Type: application/json'
   -d '{"provider":"local","deployment_mode":"default"}'`
   (`cancel_runtime` → `POST /runtimes/{name}/cancel`;
   `gui_daemon_client.py:281-302,1216-1234`;
   server `api/routes/daemon.py:160-167`).
4. Cancel an embedding workload: start
   `POST $D/api/v1/llm/rag/index` on a larger neutral set,
   then `curl -s -X POST $D/api/v1/llm/rag/index/cancel`
   (`cancel_rag_document_index`; `gui_bridge_mixin.py:372-378`);
   confirm `GET .../index/status` reports cancelled, not stuck.
5. After each cancel, re-read `GET $D/api/v1/daemon/hardware`:
   `available_vram_gb` must recover toward the step-1
   pre-job baseline.
6. Orphan check (host tooling, not app code): `pgrep -af
   'airunner-daemon|llama-server|whisper-server'` must show only
   the supervised daemon tree (sidecar binary names from the
   bundle spec `[runtime]` entries
   `llama-server`/`whisper-server`;
   `packaging/linux/services-bundle-spec.toml:225-233`); no
   leftover compute PIDs beyond it. Also confirm no job still
   reports non-terminal status.

Expected observations: every cancelled job/index reaches a
terminal cancelled state promptly; available VRAM recovers;
no extra processes remain.

Pass: all three cancels terminate cleanly, VRAM recovers to
within ~0.5 GB of baseline, orphan check is clean. Fail: a
cancel hangs or leaves a non-terminal job, VRAM does not
recover, or a stray process remains (defect with job payloads,
hardware snapshots, and the `pgrep` output).

Result: **PENDING**.

## Q07-S06 — Idle unload frees VRAM; next request reloads

Goal: with LLM auto-unload opted in, an idle LLM unloads after
the timeout; the next request loads it again transparently.

R01: CHAT-03, DL-05, SRV-05.

Preconditions: Q07-S00 passed; operator can set the daemon's
environment and restart it (Q01 install paths). Note the
mechanism is OFF by default and stays off unless opted in.

Steps:

1. Enable the opt-in idle path: `AIRUNNER_LLM_AUTO_UNLOAD=1`
   and a short `AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS=120`
   for the test run only (defaults: off / 300 s;
   `services/src/airunner_services/workers/llm_generate_worker.py:96-106`).
   Restart the daemon so the worker picks them up.
2. `POST $D/api/v1/daemon/runtimes/llm/load`; confirm loaded
   via `GET $D/api/v1/daemon/runtimes/llm?...`; record
   `available_vram_gb`.
3. Idle: issue no LLM requests for > 120 s (the worker checks
   once a minute and unloads past the timeout;
   `llm_generate_worker.py:277-310`).
4. Confirm `GET $D/api/v1/daemon/runtimes/llm?...` no longer
   reports loaded and `available_vram_gb` recovered.
5. Issue one more load (`POST .../llm/load`) and confirm it
   reports loaded again — reload-after-idle works.
6. Restore the shipping defaults (unset both variables,
   restart) and confirm `GET $D/api/v1/daemon/runtimes`
   behavior matches the pre-scenario baseline.

Expected observations: step 4 shows the LLM unloaded with VRAM
recovered; step 5 reloads cleanly; step 6 leaves no test-only
configuration behind.

Pass: unload-after-idle observed, reload works, defaults
restored. Fail: the model stays loaded past 2× the timeout, or
reload after idle errors (defect with runtime summaries,
hardware snapshots, and daemon log lines quoting the
auto-unload timer, if any).

Result: **PENDING**.

## Q07-S07 — OOM recovery: actionable error, state intact, daemon up

Goal: an oversized art request fails with an actionable
out-of-memory error (not a hang or daemon death); prior user
state stays intact and the next normal request succeeds.

R01: ART-01 (oversized request path), ART-12/D04 (resource-limit
validation: an oversized request must be rejected or fail
actionably, never hang), SET-05 (persistence intact), DL-05.

Preconditions: Q07-S00 passed; Z-Image-class model present. Have a
completed conversation/thread to re-read afterwards (B02
persistence; any existing thread id works).

Steps:

1. Record baseline: `curl -s $D/health`
   (`health_check`; `gui_daemon_client.py:164-167`) and one
   persisted thread read, e.g.
   `curl -s '$D/api/v1/llm/thread?...'` (thread route;
   `services/src/airunner_services/api/routes/events_handlers.py:163`).
   Save both payloads.
2. Submit an oversized request: `POST $D/api/v1/art/generate`
   with `"width":2048,"height":2048,"steps":50,"num_images":4`
   (past D04 sane limits and past 16 GB headroom; exact
   trigger size is hardware-dependent — record what was used).
3. Observe the outcome: either an immediate actionable
   rejection (D04 validation) or a job that fails with an
   out-of-memory signal. The art engine classifies GPU
   exhaustion by matching "out of memory" /
   `torch.cuda.OutOfMemoryError`
   (`art/managers/stablediffusion/mixins/sd_image_generation_mixin.py:31-36`;
   same predicate in `x4_utility_mixin.py:35-39`). Record the
   exact surfaced message — it must name memory exhaustion
   actionably, never a bare traceback or a silent hang.
4. Poll `GET $D/api/v1/art/status/<job_id>` (if a job was
   created) to a terminal failed state; confirm it does not
   stick at `running`.
5. Recovery: re-run step 1 verbatim — `GET /health` healthy,
   the same thread payload byte-identical (no lost user
   state), and one small art job (`512×512`, 10 steps)
   completes (daemon still serves).
6. Orphan check as in Q07-S05 step 6.

Expected observations: oversized request → actionable OOM
message + terminal job state; daemon healthy throughout;
thread bytes identical; small follow-up job succeeds; no
orphans.

Pass: all of the above. Fail: hang, daemon death/restart loop,
bare traceback as the only message, lost/altered thread bytes,
or a follow-up job that fails (defect with the exact OOM
message, job payload, both thread payloads, and `pgrep`
output). Per the issue, untested/skipped/failed is not pass.

Result: **PENDING**.

## Q07-S08 — Final audit: no orphans, user data intact

Goal: after Q07-S00–S07, confirm no stray processes and that
user data outside the install was never touched by lifecycle
churn.

R01: DL-05, SRV-05, SET-05 (data preserved).

Preconditions: all prior Q07 scenarios executed (any outcome).

Steps:

1. `pgrep -af 'airunner-daemon|llama-server|whisper-server'`
   (sidecar names;
   `packaging/linux/services-bundle-spec.toml:225-233`).
   Only the supervised daemon tree may remain.
2. `GET $D/api/v1/daemon/runtimes`: record the final
   loaded/unloaded state of each runtime (informational —
   whatever the last scenario left is fine, as long as it is
   reported honestly and no job is non-terminal).
3. Confirm the data dir still holds user state and was never
   used as install scratch: `<prefix>/data` (P06 installer;
   `install.sh:238-242` never writes data into versions/ and
   never wipes it) or `/var/lib/airunner` (apt unit working
   dir; `debian/airunner.airunner-headless.service:17-26`).
   Spot-check the database/settings files exist with
   pre-scenario content (bytes compared in Q07-S07 step 5 for
   the thread; settings/DB presence here).
4. Record daemon log location checked (launch log for the P06
   install, or `journalctl -u airunner-headless` /
   `/var/log/airunner` for the apt unit;
   `debian/airunner.airunner-headless.service:23,44-46`).

Expected observations: clean process table, honest final
runtime report, user data present.

Pass: orphan check clean and data present. Fail: stray
process or missing/altered user data (defect with `pgrep`
output and file listing).

Result: **PENDING**.

## R01 coverage in this family

Lifecycle aspect covered by Q07; functional correctness stays
with the owning ticket. "Record" means observed and logged,
not judged, here.

| R01 | Aspect in Q07 | Scenario | Owner |
|---|---|---|---|
| ART-01/03/05/09 | generate → switch/unload/cancel/OOM | S01, S04, S05, S07 | Q02 functional |
| ART-11 | batch intact across arbitration | S04 | D03 |
| ART-12 | oversized-request admission | S07 | D04 |
| CHAT-03/06/10 | chat load/switch/idle lifecycle | S01, S02, S04, S06 | Q03 functional |
| VOICE-02/03/04/06 | STT/TTS switch + round trip | S02 | Q04 functional |
| RAG-04/05 | index switch/cancel, state intact | S03, S05 | Q05 functional |
| RAG-06 | identity recorded, not judged | S03 (record) | B04/Q05 |
| DL-04 | profiling inputs for S00 | S00 | — |
| DL-05 | lifecycle/arbitration core | S01–S08 | — |
| SRV-05 | lifecycle/VRAM reporting | S00–S08 | — |
| SET-05 | persistence intact across OOM/churn | S07, S08 | — |

Capability gaps this script does not cover (no R01 row owns
them; link before Q07 closes per its acceptance clause): none
found in this family — every scenario step above cites an
implemented route, worker, or gate. Open facts OF-1–OF-3
below are evidence/operator-surface gaps, not missing
capabilities.

## Open facts (unresolved in this preparation session)

- OF-1: no operator-facing P09 prerequisite-report entry point
  (CLI or HTTP route) was found; S00 step 6 evaluates the gate
  table by hand. Confirm with the P09 owner whether one exists
  elsewhere or is still to come.
- OF-2: `DaemonConfig` ships `models: {persistence_mode:
  timeout, timeout_minutes: 30}` (`daemon_config.py:63-67`);
  no consumer of `persistence_mode` was confirmed in this
  session, so S06 tests only the `AIRUNNER_LLM_AUTO_UNLOAD`
  worker path. Confirm whether the 30-minute config is live,
  planned, or dead.
- OF-3: minimum NVIDIA driver version and hard minimum compute
  capability are still PENDING in R02 §1; S00 records whatever
  the operator hardware reports without judging a floor.
