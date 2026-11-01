# W21 — Real token generation through the services daemon

Date: 2026-11-01. Base: `5b0e77ed8` (includes sidecar
`name:null` fix `555b3dd7e`). Verdict: **generation proven**.
Chat, completion and websocket paths all returned real model
tokens through the booted `APIServer` leg and the supervised
llama.cpp sidecar. One honesty defect in the same path was
root-caused and fixed with regression tests (below). No git
writes were made; the fix is in the working tree.

## Model used (no downloads)

- Task-named target `qwen3-vl:4b-instruct-q4_K_M` resolves via
  `ollama show --modelfile` to
  `/usr/share/ollama/.ollama/models/blobs/sha256-3a859c…`
  (plus projector `sha256-70ac57…`). That tree is `0700`
  `ollama:ollama`; user `joe` gets `Permission denied`. It is
  also a vision model needing `--mmproj`, which
  `SidecarLauncher.command()` does not pass. Not usable here.
- Used instead: user-readable Ollama blob for `qwen3:8b` —
  `~/.ollama/models/blobs/sha256-a3de86cd…` (5,225,374,496
  bytes; manifest `registry.ollama.ai/library/qwen3/8b`;
  config blob: `qwen3`, `8.2B`, `Q4_K_M`; first 4 bytes
  `GGUF`). The launcher requires a `.gguf` suffix
  (`resolve_existing_file(..., allowed_suffixes=(".gguf",))`)
  and `normalize_local_path` resolves symlinks, so a symlink
  would fail the suffix check. A hardlink was used:
  `ln ~/.ollama/models/blobs/sha256-a3de86… /tmp/w21/qwen3-8b.gguf`
  (same filesystem; no copy, no download).
- `llama-server`: `/usr/local/lib/ollama/llama-server`.

## GPU contention → CPU

`nvidia-smi` at start: RTX 5080, 4560/16303 MiB used, rising
to 11798 MiB used / 4133 MiB free during the session. Two
foreign `llama-server` processes were already resident
(Ollama `qwen3-vl` on an ephemeral port, 3386 MiB; a prior
AIRunner sidecar on port 8011 serving
`Qwen3.5-9B-Q8_0.gguf` with `--n-gpu-layers 10`). Port 8011
was therefore occupied and the GPU busy, so the proof ran
on CPU: `AIRUNNER_LLAMA_N_GPU_LAYERS=0` (supported by
`_gpu_layers()` in `llama_cpp_runtime_settings.py`), sidecar
port moved to 18091. The sandbox also reported
`warning: no usable GPU found` for the direct server, so CPU
was the only honest mode in this session anyway. Foreign
processes were left running untouched.

## Commands (verbatim shape)

Probe: `/tmp/w21_gen_probe.py` (W16
`/tmp/w16_qwen_probe.py` shape: `setup_database()`,
loopback token, `APIServer` thread, `POST /api/v1/llm/chat`;
adds completion + websocket probes). Run:

```
cd /home/joe/Projects/airunnerdesktop && env \
  W21_PORT=18089 AIRUNNER_BASE_PATH=/tmp/w21_base4 \
  AIRUNNER_LLAMA_MODEL_PATH=/tmp/w21/qwen3-8b.gguf \
  AIRUNNER_LLAMA_SERVER_BIN=/usr/local/lib/ollama/llama-server \
  AIRUNNER_LLAMA_N_CTX=4096 AIRUNNER_LLAMA_N_GPU_LAYERS=0 \
  AIRUNNER_LLAMA_PORT=18091 AIRUNNER_LLAMA_STARTUP_TIMEOUT=300 \
  ./.venv/bin/python /tmp/w21_gen_probe.py
```

## Results — pre-fix run (`/tmp/w21_probe4.out`)

| Probe | Result |
|---|---|
| B `/no_think`, 48 tok (warmup+load) | `200 in 14.1s {"content":"pong",…}` |
| A bare, no `max_tokens` (default think) | `200 in 21.8s {"content":"pong",…}` |
| C think, 128 tok | `200 in 18.6s {"content":"pong",…}` |
| D completion, 32 tok | `200 in 8.3s {"text":"","finish_reason":"stop"}` |
| E websocket `/api/v1/llm/stream` | `ok in 2.1s chunks=3 text='pong'` |

Chat generation works end-to-end, including the client
websocket variant. Probe D is the anomaly: empty text
reported as a clean `stop`.

## Thinking-budget hypothesis — confirmed (direct sidecar)

`/api/v1/llm/chat` has **no** `enable_thinking` field
(`ChatCompletionRequest` in `llm_contracts.py`), so the
hypothesis was tested directly against a throwaway
`llama-server` on port 18092 with the same GGUF (killed
after use; cmdline verified before signaling):

- Default thinking, `max_tokens:32`, "The capital of France
  is" → `finish_reason:"length"`, `content:""`, all 32
  completion tokens in `reasoning_content` ("Okay, the user
  is asking for the capital of France. Let me think…"),
  `predicted_per_second: 4.13` (CPU).
- Same + `"chat_template_kwargs":{"enable_thinking":false}`
  → `finish_reason:"stop"`,
  `content:"The capital of France is Paris."`, 8 tokens.

Root cause chain in daemon code:

1. `SidecarLLMClient._completion_payload()` dropped the
   sidecar `finish_reason` (and `reasoning_content`).
2. `llm_generation_routes.py` hardcoded
   `finish_reason="stop"` for both `/chat` and
   `/completion`, so a truncated empty reply looked healthy.
3. No surface forwarded `enable_thinking` to llama.cpp
   `chat_template_kwargs`, so callers on these routes could
   not avoid the trap except by the `/no_think` prompt hack.

## Fix (working tree, defaults unchanged)

Opt-in only: unset `enable_thinking` (`None`) sends no
`chat_template_kwargs`, so the sidecar payload is identical
for existing callers. Files:

- `runtimes/contracts.py`: `LLMInvocationRequest.enable_thinking`.
- `runtimes/sidecar_llm_client.py`: forward kwargs when set;
  preserve `finish_reason` in `_completion_payload()`.
- `api/routes/llm_contracts.py`: `enable_thinking` on
  `ChatCompletionRequest` + `CompletionRequest`.
- `api/routes/llm_runtime.py`: `invoke_llm_runtime()` returns
  `(content, finish_reason)` (2 callers, both updated).
- `api/routes/llm_generation_routes.py`: return the real
  finish reason; pass `enable_thinking` through.
- `services/tests/test_sidecar_llm_payload.py`: 4 new tests
  (kwargs absent by default; `False` forwarded; `length`
  preserved on empty content; missing reason → `stop`).

## Results — post-fix re-probe (`/tmp/w21_probe_fixed.out`)

| Probe | Result |
|---|---|
| B `/no_think` 48 tok | `200 in 4.1s content="pong" finish="stop"` |
| A bare default think | `200 in 25.9s content="pong" finish="stop"` |
| C think 128 tok | `200 in 18.1s content="pong" finish="stop"` |
| D completion 32 tok | `200 in 7.3s text="" finish="length"` (honest) |
| F completion `enable_thinking:false` | `200 in 2.1s text="The capital of France is Paris." finish="stop"` |
| G chat 32-tok budget, default think | `200 in 7.2s content="" finish="length"` (honest) |
| E websocket stream | `ok in 1.2s chunks=3 text='pong'` |

## Tests (counts from `--junitxml`)

- `pytest services/tests/test_sidecar_llm_payload.py
  --junitxml=/tmp/w21_junit_payload.xml -q` →
  XML: `tests=6 failures=0 errors=0 skipped=0`.
- Touched area (`test_sidecar_llm_payload.py`,
  `test_sidecar_configs.py`, `test_release_p03.py`,
  `test_llm_local_capability.py`, `test_llm_models_loaded.py`,
  `test_llm_capability_loaded_proof.py`,
  `--junitxml=/tmp/w21_junit_touched.xml`) →
  XML: `tests=47 failures=0 errors=0 skipped=0`.
- `mypy` on the 4 touched API/contract modules: 1 error,
  byte-identical on the untouched base (pre-existing
  `to_thread` overload in `llm_runtime.py`, line 140 base /
  151 after shift). Zero new type errors. `ruff` is not
  installed in `.venv`. No added diff line exceeds 79 cols
  (checked over `git diff`); long lines in touched files
  predate this change. `git diff --stat`: 6 files,
  93 insertions, 8 deletions.

## Adjacent findings (not fixed here)

1. **Fresh-DB mapper failure.** `setup_database()` on a
   pristine `AIRUNNER_BASE_PATH` fails in
   `_ensure_startup_rows` with `Mapper[AIModels]` →
   `'GeneratorSettings' failed to locate a name`. Standalone
   `import airunner_services.database.models` +
   `configure_mappers()` succeeds. Bisected trigger:
   `AIRUNNER_SAVE_LOG_TO_FILE=1` alone reproduces the
   failure in `/tmp/w21_mapper_dbg.py`; every other probe
   env var passes. Without the flag, pre-importing models +
   `configure_mappers()` before `setup_database()` also
   succeeds (`/tmp/w21_base2` run: `SETUP OK`). Looks like
   the file-logging import path loads a models subset first
   and poisons mapper configuration. Needs its own ticket
   with that repro; the daemon's normal boot
   (`_prepare_managed_daemon_launch`) calls bare
   `setup_database()`.
2. **Streaming drops reasoning deltas.**
   `SidecarLLMClient._stream_response()` forwards only
   `delta.content`; during a long think the websocket emits
   empty chunks. Same family as the fix above; left for a
   follow-up (needs a client-visible thinking event shape).
3. A stale AIRunner `llama-server` (PID 1592273, port 8011,
   started 04:35) still holds the default sidecar port. Any
   future proof must override `AIRUNNER_LLAMA_PORT` or reap
   it through its owner. A direct 64-token request to it
   timed out at 120s (10 GPU layers, Q8 9B) — recorded as
   observed, not diagnosed further.

4. **Orphaned sidecar after `APIServer.stop()`.** The probe
   sidecar (port 18091, `/tmp/w21/qwen3-8b.gguf`) survived
   `STOP ok` as a PPID-1 orphan and was killed manually
   after cmdline verification. Shutdown does not close the
   sidecar client/launcher on this path.

## Unresolved / limits

- The task-named `qwen3-vl:4b` blob could not be read
  (permissions) and needs `--mmproj` the launcher lacks;
  proof used `qwen3:8b` Q4_K_M instead. Vision-model
  sidecar support is unproven.
- No GPU proof: contention + sandbox GPU invisibility.
  `Qwen3.5-9B-Q8_0.gguf` (the W16 model) GPU re-proof is
  still open; the file does exist at
  `/media/joe/Megatron/airunner/text/models/llm/causallm/Qwen/`.
- Websocket `LLMStreamMessage` still has no
  `enable_thinking` field; `/no_think` remains the stream
  workaround.
- Legacy (`legacy_llm_*`) generation path not exercised;
  it already carries its own `enable_thinking` handling.
