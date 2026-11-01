# W16 — Desktop services headless smoke census (G3/D2)

Repo: `airunnerdesktop`, branch `release/linux-v1-services-stack`
@d056fe61e. Census only; no production code changed. No license or
copy claims (H2 unconfirmed). All artifacts under `/tmp`.

## 1. Intended headless launch (inspected)

- Console scripts (`services/setup.py:273-285`,
  `SERVICE_CONSOLE_SCRIPTS`): `airunner-daemon`
  (`airunner_services.daemon:main`), `airunner-headless`
  (`airunner_services.bin.airunner_headless:main`),
  `airunner-service`, plus download/cert helpers.
- `airunner-headless` is a supervisor: it clones the daemon config
  with per-invocation host/port, sets `AIRUNNER_HEADLESS=1`
  (`bin/airunner_headless.py:285`), launches a managed daemon via
  `DaemonLauncher`, and stops only its own child. Defaults:
  `127.0.0.1:8080` (11434 with `--ollama-mode`); non-loopback bind
  without `AIRUNNER_API_KEY` is refused (`_validate_host_binding`).
- `airunner-daemon` owns the process: `AIRunnerDaemon.start()`
  (`daemon.py:281`) takes a per-port flock, builds `ServiceApp`
  headlessly (or degrades to API-only without torch, #2243), then
  starts `APIServer` (`api/server.py:512`, uvicorn) and blocks in
  `_run_loop`. `--generate-config` writes defaults and exits 0
  (verified, §5).
- Docker path: `Dockerfile` installs `./services[desktop]` +
  `./native`, `docker-entrypoint.sh` exports `AIRUNNER_HEADLESS=1`,
  defaults `--host 127.0.0.1 --port 8080`, execs
  `airunner-headless`; `HEALTHCHECK` curls `/health` (token-exempt).
- Auth: `/health` and `/api/v1/health` are unauthenticated
  (`api/server.py:340`); everything else needs the per-user
  loopback token (`X-Airunner-Token`, file mode 0600,
  `api/loopback_token.py`), an `AIRUNNER_API_KEY`, or the explicit
  `AIRUNNER_INSECURE_NO_AUTH=1` override.

## 2. Real boot on loopback (evidence)

Booted the daemon's own HTTP leg (`APIServer`, the exact object
`daemon._start_api_server` constructs) in `.venv` on an ephemeral
loopback port with temp data dirs. Script: `/tmp/w16_boot_probe.py`;
log: `/tmp/w16-out/boot.log`.

Verbatim command (port 41499 chosen by bind-to-0):

```
W16_PORT=41499 AIRUNNER_HEADLESS=1 \
AIRUNNER_BASE_PATH=/tmp/w16-data AIRUNNER_DATA_DIR=/tmp/w16-data \
AIRUNNER_RUNTIME_ROOT=/tmp/w16-data/runtime HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 HF_HOME=/tmp/w16-data/hf \
AIRUNNER_API_ACCESS_LOG=1 timeout 240 \
.venv/bin/python /tmp/w16_boot_probe.py
```

`setup_database()` ran the full Alembic chain against a fresh
SQLite DB under `/tmp/w16-data`; `WAIT_UNTIL_STARTED True`;
uvicorn `Application startup complete`.

Verbatim statuses (token = `X-Airunner-Token` from
`get_or_create_loopback_token()`):

| Request | Status | Body (trimmed) |
|---|---|---|
| `GET /health` (no token) | 200 | `{"status":"ready","version":"6.1.7","contract_version":"1.0.0","art_model_status":"unloaded","services":{"llm":true,"art":false,"tts":false,"stt":false}}` |
| `GET /api/v1/health` (no token) | 200 | `{"status":"healthy","version":"6.1.7","contract_version":"1.0.0"}` |
| `GET /` | 200 | `{"status":"ready","service":"airunner"}` |
| `GET /api/v1/health/daemon` | 200 | `{"lifecycle_initialized":false,"worker_manager_ready":false,"loaded_models":[],"runtime_registry_ready":false}` |
| `GET /api/v1/llm/local-inference` | 200 | see §3 |
| `GET /api/v1/llm/models` | 200 | 8 models, every `loaded:false` |
| `GET /api/v1/catalog/bootstrap` | 404 | `{"detail":"Not Found"}` |
| `GET /api/v1/llm/local-inference` (no token) | 401 | `{"error":"Unauthorized"}` |
| `POST /api/v1/llm/chat` (no GGUF configured) | 502 | `{"detail":"No GGUF model is configured for llama.cpp"}` |

Notes:

- `/health/daemon` reports not-ready because this boot passes
  `app_instance=None` (no `ServiceApp`/lifecycle). That is the
  API-only degraded shape, honestly reported, not a false-ready.
- `/api/v1/catalog/bootstrap` 404: `catalog_bootstrap.router`
  (`api/routes/catalog_bootstrap.py`, `GET /bootstrap`) is not
  mounted by `create_app`; the mounted `catalog_router` is the
  generic domain-resource router (`/api/v1/catalog`). The
  bootstrap payload is static in-process data (no fetch) wherever
  it is mounted. Census finding, not fixed here.

## 3. Local-inference metadata honesty (configured vs loaded)

`GET /api/v1/llm/local-inference` → 200 with:

- `qwen3.5-9b`: `"configured":true,"loaded":false`,
  `context_length 262144`, GGUF `unsloth/Qwen3.5-9B-GGUF` /
  `Qwen3.5-9B-Q8_0.gguf`; `gpt-oss-20b` and `custom`:
  `configured:false, loaded:false`.
- `runtime`: `{"status":"stopped","details":"not loaded"}` with a
  local sidecar descriptor; `routing.remote_requires_consent:true`.

Source contract (`api/routes/llm_local_routes.py`,
`llm/local_capability.py`, `api/routes/llm_model_routes.py:93`):
`configured` is the effective selection (persisted row, else the
documented default `qwen3.5-9b`); `loaded` is READY-proven via
`proven_loaded_model_id` — the selection alone never claims a
load. A fresh DB has no `LLMGeneratorSettings` row
(`objects.first()` is `None`, probed), yet `configured:true` for
the default model with `loaded:false`. Honesty gate holds.

## 4. History / conversation round trip

The API owns conversations at `/api/v1/llm/conversations`
(`api/routes/conversations.py`). All against the §2 boot:

- `GET /conversations?limit=5` → 200 `{"conversations":[]}`
- `POST /conversations {}` → 200, `conversation_id 1`
- `GET /conversations/session?conversation_id=1` → 200,
  `messages:[]`
- `PUT /conversations/1/messages` (`w16 smoke ping`) → 200
  `{"conversation_id":1,"updated":true}`
- `GET` session again → 200, `message_count 1`, the stored
  message round-trips verbatim
- `DELETE /conversations/1` → 200 `{"deleted":true}`

Cosmetic defect logged during the trip (x3, non-fatal):
`Failed to summarize conversation 1: 'ConversationData' object
has no attribute 'summarize'`
(`conversations/conversation_history_manager.py:242`). Census
only.

## 5. Offline behavior and update check

- Offline-first default: with no env set,
  `airunner_common.settings.AIRUNNER_OFFLINE_MODE` is `True`
  (probed in `.venv`); `downloads/update_check.py:97` mirrors it —
  only explicit `AIRUNNER_OFFLINE_MODE=0` allows egress.
  Provider downloads refuse up front with that switch named
  (`downloads/service.py`, `url_safety.is_offline_mode`).
- Boot-log egress watch: `grep` for
  `huggingface|pypi|github|openrouter|civitai` URLs in
  `/tmp/w16-out/boot.log` returned nothing. The boot ran with
  `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` and completed every
  §2–§4 check on loopback only. No `pricing` module exists under
  `services/src/airunner_services/` (grep: no files), so there is
  no pricing fetch to disable; the catalog/bootstrap data is
  static in-process Python data (§2 note).
- Update check: `downloads/update_check.py` is library-only.
  `check_for_updates()` requires `opt_in=True`, raises
  `UpdateOffline` while offline, verifies a signed manifest, and
  its docstring states "Nothing runs at import or startup."
  No caller exists under `services/src/` and no HTTP route wraps
  it (grep: single defining file). It contacts nothing by
  default; the disable switch is the default itself plus
  `AIRUNNER_OFFLINE_MODE=1`. Production transport wiring is
  explicitly out of scope in that module (P10).

## 6. Packaged smoke — BLOCKED on yanked dependencies (proven)

Existing path: `.github/workflows/pypi-dispatch.yml` builds and
publishes `services` + `native` (workflow_dispatch default
`"services native"`); `services/setup.py` is the build surface
(`airunner-services 6.1.5`).

Builds (artifacts in `/tmp/w16-dist/`):

```
.venv/bin/python -m pip wheel ./services --no-deps -w /tmp/w16-dist
# -> airunner_services-6.1.5-py3-none-any.whl (2.5 MB), exit 0
(cd services && /…/.venv/bin/python setup.py sdist --dist-dir /tmp/w16-dist)
# -> airunner_services-6.1.5.tar.gz (2.4 MB), exit 0
```

Clean-venv install (`/tmp/w16-clean`) fails at resolution.
Verbatim resolver output (`/tmp/w16-out/clean-install.log`):

```
ERROR: Ignored the following yanked versions: 6.1.3, 6.1.4, 6.1.5, 6.1.6, 6.1.7
ERROR: Could not find a version that satisfies the requirement
  airunner-common~=6.1.7 (from airunner-services) (from versions: none)
ERROR: No matching distribution found for airunner-common~=6.1.7
```

`airunner-tts-vendor~=0.1` (the `tts-python`/OpenVoice extras)
fails identically (`/tmp/w16-out/ttsvendor.log`):

```
ERROR: Ignored the following yanked versions: 0.1.0
ERROR: No matching distribution found for airunner-tts-vendor~=0.1
```

Both suspected yanked deps are therefore **proven**, not
refuted. A `--no-deps` wheel install lands all 10 console
scripts, but the first entry point cannot boot:

```
$ /tmp/w16-clean/bin/airunner-daemon --generate-config …
ModuleNotFoundError: No module named 'airunner_common'
```

In the dev `.venv` (where `airunner-common 6.1.7` is already
installed) the same entry points work: `airunner-headless
--help` exit 0; `airunner-daemon --generate-config --config
/tmp/w16-out/daemon.yaml` exit 0 with loopback defaults
(`127.0.0.1:8188`). **A from-artifact boot is not possible until
non-yanked `airunner-common` (and, for TTS extras,
`airunner-tts-vendor`) releases exist on the index.** No pin was
changed here.

## 7. Wave 10 qwen3.5-9b empty-generation — re-probe verdict

Classification: **services payload defect (generation-request
construction), not model artifact and not an empty
generation-config default.** Evidence only; no fix landed (the
one-line fix below is not a config default, so it stays out
under this slice's no-production-changes rule).

Probe (`/tmp/w16_qwen_probe.py`, log `/tmp/w16-out/qwen2.log`)
booted the §2 stack with the real on-disk artifact
(`Qwen3.5-9B-Q8_0.gguf`, 9.2 GB, present in the default data
dir), `AIRUNNER_LLAMA_MODEL_PATH` set, `AIRUNNER_LLAMA_N_CTX=4096`,
`AIRUNNER_LLAMA_N_GPU_LAYERS=10`, sidecar binary
`/usr/local/lib/ollama/llama-server` (no `llama-server` on PATH;
first attempt without `AIRUNNER_LLAMA_SERVER_BIN` failed fast
with `[Errno 2] No such file or directory: 'llama-server'` —
itself an env gap worth noting for bundle layout).

Three `POST /api/v1/llm/chat` variants (bare; `/no_think` +
`max_tokens 64`; `max_tokens 512`) all returned the same 502.
The first took 56.4 s (sidecar spawn + 9B load), the rest 0.0 s:

```
{"detail":"{\"error\":{\"code\":500,\"message\":\"Failed to parse
messages: [json.exception.type_error.302] type must be string,
but is null\",\"type\":\"server_error\"}}"}
```

Root cause, inspected: `runtimes/contracts.py:49-56`
`ChatMessage` carries `name: Optional[str] = None`;
`runtimes/sidecar_llm_client.py:189` serializes with bare
`message.model_dump()`, emitting `"name": null` (verified:
`{'role': 'user', 'content': 'hi', 'name': None}`). The
llama.cpp chat parser rejects the null before any token is
generated — so on a stack whose sidecar tolerates or strips it
differently this same defect plausibly surfaces as the slow,
empty generation Wave 10 saw; here it is a clean, fast 502
after load. Generation defaults are not empty:
`ChatCompletionRequest.max_tokens` is `None` (omitted downstream,
not 0) and `CompletionRequest.max_tokens` defaults to 100
(`api/routes/llm_contracts.py:27,44`);
`llm_generator_settings.enable_thinking` defaults `True`, which
can still make small budgets look empty once the payload bug is
fixed, but it is not the blocker observed.

Proposed one-line fix (not applied): `model_dump(exclude_none=True)`
at `sidecar_llm_client.py:189`, plus a unit test asserting the
sidecar payload omits `name` when unset. No existing test covers
`_chat_payload` (grep over `services/tests/test_*.py`: none).

## 8. Tests run (counts from JUnit XML only)

```
.venv/bin/python -m pytest \
  services/tests/test_llm_local_capability.py \
  services/tests/test_llm_models_loaded.py \
  services/tests/test_llm_capability_loaded_proof.py \
  services/tests/test_local_model_selection.py \
  services/tests/test_release_2243_boot.py \
  services/tests/test_dependency_constraints.py \
  -q -p no:cacheprovider --junitxml=/tmp/w16-out/junit.xml
```

XML (`/tmp/w16-out/junit.xml`): tests 34, failures 0, errors 0,
skipped 0, time 3.548 s. Exit 0.

## 9. Unresolved / not exercised

- Full `airunner-headless` → managed-daemon → `ServiceApp` boot
  (worker graph, lifecycle preload) was not run; §2 boots the
  daemon's `APIServer` leg directly. `/health/daemon`
  not-ready fields reflect that scope. **Resolved after this
  census: see §10.**
- No successful token generation yet (blocked by §7 payload
  defect); thinking-budget emptiness after that fix is unprobed.
- Packaged boot from a clean install is blocked by §6 yanked
  releases; `native` package was not built in this slice.
- Working tree after census: this file only (uncommitted).

## 10. Addendum — full managed-daemon boot run (W16 gap)

Run after the census above, same repo/branch, dev `.venv`.
Probe: `/tmp/w16d_probe.py`; logs: `/tmp/w16d-out/probe.log`
(boot 2, `probe1.log` boot 1), `/tmp/w16d-out/headless.log`.
Fresh config from `airunner-daemon --generate-config --config
/tmp/w16d-out/daemon.yaml` (exit 0); temp data
`AIRUNNER_BASE_PATH=/tmp/w16d-data`, `HF_HUB_OFFLINE=1`,
`AIRUNNER_NO_PRELOAD=1`, `AIRUNNER_KNOWLEDGE_ON=0`.

Verbatim supervisor command (port chosen by bind-to-0):

```
.venv/bin/airunner-headless --host 127.0.0.1 --port 42039 \
  --no-preload --daemon-config /tmp/w16d-out/daemon.yaml
```

First attempt failed before any daemon launch, exit 1:

```
Fatal error: No module named 'airunner_native'
  bin/airunner_headless.py:474 in _prepare_managed_daemon_launch
    from airunner_native.launcher import _configure_test_mode
```

Root cause: that helper is only called when
`AIRUNNER_ENVIRONMENT=test`, but two of the three launch
preparers imported it unconditionally; the art sidecar launcher
already imported it inside the test branch. Fix (uncommitted):
`bin/airunner_headless.py` and
`runtimes/sidecar_tts_launcher.py` now match the art launcher
(import after the non-test early return);
`scripts/import_boundary_allowlist.py` line pins updated
474→479 and 78→83; new regression test
`services/tests/test_managed_daemon_launch_prep.py` blocks
`airunner_native` and pins both branches. The dev `.venv` has
no `airunner_native` installed (services editable +
`airunner_common` only), so this was a real services-only boot
blocker, not a test-mode path.

Boot results (two consecutive boots on the same data dir;
healthy after 14.0 s and 10.0 s; daemon pid distinct from
supervisor pid and echoed in `/health` `pid`):

| Request | Status | Body (trimmed) |
|---|---|---|
| `GET /health` (no token) | 200 | `{"status":"ready","version":"6.1.7",…,"art_model_status":"unloaded","services":{"llm":true,"art":true,"tts":true,"stt":true}}` |
| `GET /api/v1/health/daemon` (token) | 200 | `{"lifecycle_initialized":true,"worker_manager_ready":true,"model_load_balancer_ready":true,"loaded_models":[],"runtime_registry_ready":true,"embedded_api_server_running":false,"preloaded_model_path":null}` |
| `GET /api/v1/daemon/status` (token) | 200 | same lifecycle block; every runtime `status:"stopped", loaded:false` |
| `GET /api/v1/health/daemon` (no token) | 401 | `{"error":"Unauthorized"}` |

Log proof: `Headless lifecycle initialized`, `Model loading
deferred to first request`, `AI Runner daemon started
successfully`, `Managed daemon ready`. Heartbeat file fresh
(age 1.6 s / 1.7 s); per-port lock `daemon-<port>.lock` holds
the daemon pid; loopback token file mode 0600. No model was
loaded (`loaded_models:[]`, all `loaded:false`) — lazy by
default, honestly reported. `loaded` vs `configured` note:
this fresh-DB boot's `local-inference` reports
`qwen3.5-9b configured:false` (lifecycle preload logged
`Database schema not ready; LLM preload deferred`), where §3's
API-only boot reported `configured:true`; both report
`loaded:false`. Not investigated further here.

Stop: SIGTERM to the supervisor only; supervisor exit 0 after
5.8 s (boot 2, timed), port refused afterwards, no orphan
pids. Wart, recorded not fixed: neither boot's log contains
the daemon's own `Shutting down AI Runner daemon...` /
`Daemon shutdown complete` lines, only `ServiceApp cleanup
complete`; 5.8 s matches `DaemonLauncher.stop()`
terminate → 5 s wait → kill (`launcher.py:124-129`).
Consistent with code order: `AIRunnerDaemon.start()` installs
its signal handlers (`daemon.py:284`) before constructing
`ServiceApp`, whose `_init_headless_mode` overwrites
SIGINT/SIGTERM with `ServiceApp.signal_handler`
(`headless_runtime_mixin.py:70-71`), which cleans up but
never sets the daemon shutdown flag or exits. Distinct
defect; left as a named follow-up, not fixed in this slice.

Tests (JUnit XML counts): `test_managed_daemon_launch_prep.py`
+ `test_import_boundaries.py` +
`scripts/tests/test_import_boundary_rules.py` +
`test_release_f12_f14_supervisor.py` +
`test_release_2243_boot.py` → tests 28, failures 0, errors 0,
skipped 0 (`/tmp/w16d-out/junit.xml`);
`test_voice_wave2_fixes.py` → tests 68, failures 0, errors 0,
skipped 0 (`junit2.xml`).
`scripts/check_import_boundaries.py` exit 0
(`No import-boundary violations found.`). Ruff is not
installed in this `.venv` or on PATH, so no ruff run is
claimed; `py_compile` passed on all touched files.

Working tree after addendum (uncommitted, no git writes):
modified `services/src/airunner_services/bin/airunner_headless.py`,
`services/src/airunner_services/runtimes/sidecar_tts_launcher.py`,
`scripts/import_boundary_allowlist.py`; new
`services/tests/test_managed_daemon_launch_prep.py`; this doc.
