# T01: Linux custom-tool execution isolation boundary (design)

Status: **design gate only** (issue #2142). Not an implementation, not a
security proof. No claim is made here that any sandbox is secure or that
isolated execution currently works. T02 (#2145) implements the worker and
the single dispatch adapter from this document after review.

Parent spec: #2083 (decision 6: arbitrary code needs a real process/OS
isolation boundary or explicit trusted-code behavior; restricted Python
builtins are not a sandbox). Prerequisites: #2084 (R01), #2140 (B11).

## 1. Threat model

Two code classes, distinguished by provenance, not by content scan:

- **Trusted operator code**: first-party tool functions shipped in the
  repository (`services/src/airunner_services/llm/tools/`,
  `.../llm/managers/tools/`). Reviewed in-tree, runs in-process with the
  application's full ambient authority (filesystem, DB, signals, GPU).
  A bug here is a normal defect, not a boundary violation.
- **Model/untrusted code**: anything whose bytes the model (or an
  unreviewed operator paste) chose at runtime — custom-tool records in
  the `llm_tool` table, and code strings passed to the math compute
  tools. Must never execute in the application process, even when a
  static scan calls it safe.

Current posture (verified in this checkout): both classes execute in
the application process today. `ToolManager._compile_custom_tool`
(`services/src/airunner_services/llm/tool_manager.py:224`) calls
`exec(tool_record.code, namespace)` at line 246 with only
`create_safe_builtins()` (`.../llm/core/code_sandbox.py`, 39 lines) as
mitigation; the module docstring itself states this is not a security
boundary. `SafePythonExecutor.execute`
(`.../llm/core/math_executor.py:322`) likewise `exec`s model-supplied
strings in-process (lines 354–371) after an AST/denylist scan. The
`safety_validated` flag (`.../database/models/llm_tool.py:81`,
validator at :110–:172) is a static-analysis admission signal, not
isolation: it cannot see runtime behavior, resource use, or blocking.

## 2. Inventory of existing execution / computer-control paths

Verified by reading each file; line numbers are this checkout
(base `742a686c2`).

| # | Path | What runs where |
|---|---|---|
| E1 | `services/src/airunner_services/llm/tool_manager.py:192-283` | Custom tools: loaded from DB (`_load_custom_tools`), compiled with in-process `exec` (`_compile_custom_tool:246`). **Primary T02 target.** |
| E2 | `services/src/airunner_services/llm/core/math_executor.py:322-371` | `sympy_compute`/`numpy_compute`/`python_compute` (`.../llm/tools/math_tools.py:72-145`) exec model code in-process with a 5 s timeout attribute but no process boundary. Proposed split ticket (see §6), not T02. |
| E3 | `services/src/airunner_services/llm/managers/tools/file_tools.py` + registry `.../llm/tools/system_tools.py:73-157` | Model-invoked `list_files`/`read_file`/`write_file`/`list_directory` with unrestricted absolute paths (`os.path.abspath`, no root jail). Trusted-operator code, but ambient authority; capability allow-list is a follow-up. |
| E4 | `services/src/airunner_services/llm/managers/tools/system_tools.py:110-175` | `emit_signal`: model can emit app signals incl. `QUIT_APPLICATION` and `SD_GENERATE_IMAGE_SIGNAL` via `dispatch_tool_action`. In-process by design; stays, but custom-worker code must never receive the dispatch handle. |
| E5 | `services/src/airunner_services/llm/managers/tools/autonomous_control_*.py` (via `autonomous_control_tools.py`) | App-state inspection, mode control, scheduling, behavior analysis. Trusted-operator, in-process; no OS-level input control (no pyautogui/keyboard/mouse calls found in `llm/`). |
| E6 | `services/src/airunner_services/llm/long_running/project_manager_git_exec.py` | `subprocess.run` of git with `cwd=repo_path`, no timeout. Trusted-operator path; needs timeout/cwd-validation hardening, out of T02 scope. |
| E7 | `services/src/airunner_services/llm/tools/intelligent_crawl_tool.py` (+ Scrapy `CrawlerProcess`, search providers) | Network egress from tools; admission-gated per-link by `validate_url_for_fetch` but transport bypasses `safe_fetch_url` (see `release-planning/linux-v1/egress-coverage-ledger.md`). Worker must default to no network. |
| E8 | `services/src/airunner_services/llm/managers/mixins/tool_execution_mixin.py:44-95` | LangGraph `ToolNode(self._tools).invoke(state)` — the in-process fan-out point where T02's adapter interposes for custom tools only. |
| E9 | `services/src/airunner_services/llm/companion/tool_routing.py:44-56,143-196` | B11 dispatch: offline gate (`NETWORK_TOOL_NAMES`, `is_offline_mode`) + publication check. Worker dispatch must reuse this preflight, not fork it. |

No `pyautogui`/keyboard/mouse OS-input control exists under `llm/`;
"computer control" in this tree means E3–E5 (files, signals, app
state), all currently ambient-authority and in-process.

## 3. Proposed worker contract

One Linux worker process per custom-tool invocation (spawn-on-call;
pooling is a later optimization, not T02):

- **Spawn**: `multiprocessing` with `spawn` (never `fork` — no GPU/Qt
  handle inheritance), or `subprocess` running a `worker_main` entry
  point. Parent never `exec`s tool bytes.
- **Interface**: structured IPC over an OS pipe/socketpair with a
  length-prefix framing: request `{tool_name, code_hash, args_json,
  capabilities, timeout_ms, cancel_token}` → response `{status,
  result_json|error, truncated: bool, usage}`. JSON only; no pickled
  callables crossing the boundary. Stdout captured and size-capped.
- **Filesystem capabilities**: explicit per-call grant, default none.
  Granted roots passed as already-opened directory fds or as
  canonicalized path prefixes re-validated after `realpath`; worker
  `chdir`s to an empty temp dir and resolves every access against the
  grant. No grant → any file builtin raises.
- **Network capabilities**: default deny. A grant names hosts/ports and
  is enforced by the absence of socket access in the worker namespace
  plus a parent-side `validate_url_for_fetch` preflight; worker has no
  proxy credentials and no route except loopback IPC to the parent.
- **Resource limits**: wall timeout (default ≤ 10 s, caller-overridable
  down), address-space cap (`RLIMIT_AS`), CPU cap (`RLIMIT_CPU`),
  output byte cap (default 64 KiB, `truncated: true` beyond), no child
  processes (`RLIMIT_NPROC 0`). Parent kills on timeout; kill is
  `SIGKILL` after a short `SIGTERM` grace.
- **Cancellation**: parent drops the IPC endpoint and kills the worker;
  a late worker result after cancel is discarded by `cancel_token`
  mismatch. LangGraph cancellation propagates through the adapter in
  E8, not into worker internals.
- **Failure protocol**: statuses `ok | tool_error | timeout |
  cancelled | capability_denied | worker_crash | oversized`. Tracebacks
  stay in the parent log; the model receives a bounded error string.
  Worker crash (nonzero exit, signal) maps to `worker_crash`, never a
  retry of the same bytes without operator consent.
- **Provenance preserved**: `LLMTool.increment_usage` still runs in
  the parent after the worker result lands; `safety_validated`
  remains the static admission pre-check but is no longer the thing
  that makes execution acceptable.

`ToolManager` keeps one dispatch adapter: `_compile_custom_tool`
returns a handle whose call marshals through the worker instead of
closing over an in-process function. All other tools are untouched —
no launch features disabled to avoid the problem.

## 4. Neutral abuse / failure tests (for T02's `test_release_t02.py`)

Fixtures must be behavior-neutral (no private policy vocabulary, no
real credentials, no sensitive imagery):

1. Filesystem escape: tool reading `/etc/hostname` (or writing
   outside the grant) with no grant → `capability_denied`.
2. Network egress: tool opening a socket to a test-local listener →
   denied; assert the listener saw no connection.
3. Import escape: `import os` / `__class__.__subclasses__` traversal
   → rejected before or inside the worker without parent effects.
4. Infinite loop → `timeout` within the bound; worker reaped (no
   zombie, no leaked process).
5. Output bomb (10 MB print) → `oversized`/`truncated`, bounded bytes.
6. Cancel mid-run → `cancelled`, worker reaped.
7. Crash (`os._exit(1)` equivalent / segfault stub) → `worker_crash`,
   parent healthy, usage counters still persisted.
8. Grant honored: read/write inside a granted temp dir works and
   round-trips bytes exactly.
9. Offline mode: network-granted tool while `AIRUNNER_OFFLINE_MODE=1`
   → `offline_blocked` via the shared preflight, worker never spawned.
10. Provenance: success and failure both update `usage_count` /
    `success_count` / `error_count` exactly once.

## 5. Exact implementation tickets

- **T02 (#2145)** — implement §3 worker + the single `ToolManager`
  adapter for E1 only, with §4 tests. Boundary: `.../llm/core/`
  (new `tool_worker.py` + IPC), `tool_manager.py` (adapter).
- **Proposed split T03** (to file, not implement): route E2 math
  executor through the same worker with a numeric-only capability
  profile; `math_executor.py` keeps its AST scan as pre-check.
- **Proposed split T04** (to file, not implement): capability
  allow-list + path jailing for E3 trusted file tools, and timeout/
  cwd validation for E6 git exec. E4/E5 stay in-process by design.

## 6. Open questions (not invented)

1. Exact spawn primitive (`multiprocessing.spawn` vs `subprocess` +
   entry point) — T02 decides on packaging evidence (PyInstaller
   bundle constraints), recorded in its result.
2. Whether granted-root enforcement needs OS-level Landlock/seccomp
   or namespace validation suffices for v1 — needs the independent
   security review the guardrails require; this doc assumes the
   review may demand more.
3. Worker startup latency budget on the 16 GB NVIDIA baseline —
   unmeasured; spawn-on-call stands until T02 measures it.
4. E3 trusted-tool jailing scope (per-user-dir vs per-call grants) —
   deferred to proposed T04.
