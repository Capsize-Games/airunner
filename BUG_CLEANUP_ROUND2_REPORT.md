# BUG_CLEANUP_ROUND2_REPORT

Round 2 of the 2026-08 bug-fix engagement (`plans/security-bug-fixes-2026-08.md`).
Closes out the remaining three open `🐛 bug` issues: **#2052**, **#2050**, **#2077**.

---

## 1. Branch & commits

Branch: `bug/close-audit-issues-round2` (off `master`, which is at `v6.0.1`).

```
$ git log --oneline master..HEAD
65adffb4c refactor(logging): expose resolve_log_base_path as a public name
41b3d3b50 docs: add build, license, and community badges to README header
befc78a06 docs: add BUG_CLEANUP_ROUND2_REPORT for issues #2052, #2050, #2077
7a4879e53 fix(sidecars): bump llama.cpp pin to mingw-safe revision; keep matrix legs independent
e1807d82b refactor(logging): replace print() instrumentation with logger calls
920235d70 refactor(logging): consolidate get_logger into shared airunner_common
5d53fb478 fix(scripts): make airunner-mypy use project mypy config; lock report parity
```

Each commit carries `Co-Authored-By: DeepSeek <noreply@deepseek.com>`.
`git status` is clean except the new `BUG_CLEANUP_ROUND2_REPORT.md` (added at the end).

---

## 2. Task 1 — #2052: mypy shortcut + complexity report parity

### Status: `DONE`

### Files changed
| File | What |
|---|---|
| `scripts/mypy_shortcut.py` | Dropped hard-coded `--ignore-missing-imports --follow-imports=skip`; now runs `python -m mypy <filename>` and lets `[tool.mypy]` in `pyproject.toml` supply all flags. Docstring updated. |
| `services/tests/test_complexity_report_parity.py` | New guard test (10 tests) asserting identical `DEFAULT_EXCLUDES` and `_is_generated` verdicts between the GUI and services complexity scripts. |
| `docs/complexity-and-typing.md` | New committed docs section stating the advisory (non-gating) CI stance for mypy + complexity reports, referencing issue #2052. |

### Acceptance bullets
- **"`scripts/mypy_shortcut.py` no longer passes `--ignore-missing-imports` / `--follow-imports=skip` on the command line (grep the file)."** ✅
  ```
  $ grep -n "ignore-missing-imports\|follow-imports" scripts/mypy_shortcut.py
  (no output; exit 1)
  ```
  The flags remain in `pyproject.toml` (`[tool.mypy]`), which mypy discovers from the cwd upward, so both entry points agree.
- **"`mypy scripts/mypy_shortcut.py` and `scripts/mypy_shortcut.py scripts/mypy_shortcut.py` produce the same exit behaviour."** ✅
  ```
  $ .venv-ci/bin/python -m mypy scripts/mypy_shortcut.py
  Success: no issues found in 1 source file   (exit 0)
  $ .venv-ci/bin/python scripts/mypy_shortcut.py scripts/mypy_shortcut.py
  (no output; exit 0)
  ```
  Both exit 0 and both use the project config (neither passes CLI flags).
- **"The new parity test passes in `.venv-ci` and would fail if either script's skip rule changed."** ✅
  ```
  $ .venv-ci/bin/python -m pytest services/tests/test_complexity_report_parity.py -q
  10 passed in 0.03s
  ```
  Mutation check: temporarily changed `gui_complexity_report._is_generated` to skip only `*_ui.py`; the test failed (`4 failed, 6 passed`) on `foo_rc.py` / `feather_rc.py` / `x/y/baz_rc.py` verdict divergence, then the file was restored.
- **"A committed docs section states the mypy + complexity CI stance (advisory or gating), referencing #2052."** ✅
  `docs/complexity-and-typing.md` states mypy is a **non-gating local aid** and the Radon/Xenon complexity reports are **advisory artifacts, not a CI gate**, with regeneration commands and the parity-test reference.

### CI decision
Chose the **Preferred (advisory)** option. No new workflow step was added; the docs section satisfies acceptance point 3.

---

## 3. Task 2 — #2050: one logger, no stray `print()`

### Status: `DONE`

### Part 2A — consolidate `get_logger`

### Files changed
| File | What |
|---|---|
| `shared/airunner_common/get_logger.py` | **New canonical implementation** of `Logger` + `get_logger()` + `set_log_base_path_resolver()`. Union of both previous implementations' behaviour (env log level, `LogHygieneFilter` on every handler, console always, file handler when `AIRUNNER_SAVE_LOG_TO_FILE=1`, flatpak/XDG handling, `0o700` log dir, fail-safe on handler errors). Imports **no** app package. |
| `src/airunner/utils/application/get_logger.py` | Thin re-export shim of `airunner_common.get_logger` (no `class Logger` / `def get_logger` body). |
| `services/src/airunner_services/utils/application/get_logger.py` | Thin re-export shim **plus** one-time `set_log_base_path_resolver(_path_settings_resolver)` registration (import-time, lazy `PathSettings` import inside the resolver). |
| `shared/airunner_common/logging_utils.py` | Root-logger file-path resolution now delegates to the shared resolver in `get_logger` (removed the hard-wired `airunner_services` import). |

### Acceptance bullets
- **"Exactly one `Logger`/`get_logger` implementation lives in `shared/airunner_common`; both `get_logger.py` modules are shims (grep)."** ✅
  ```
  $ grep -rn "^class Logger\|^def get_logger" src/ services/src/ scripts/ --include="*.py" | grep -v vendor
  (no output)
  $ grep -rn "class Logger\|def get_logger" shared/airunner_common/get_logger.py
  class Logger:  /  def get_logger(...)
  ```
- **"`import airunner`, `import airunner_services`, and the `get_logger('t').info('ok')` call all succeed."** ✅
  ```
  $ .venv-ci/bin/python -c "import airunner; import airunner_services; from airunner.utils.application.get_logger import get_logger; get_logger('t').info('ok'); print('imports-ok')"
  2026-08-29 07:13:05,951 - t - INFO - <string>::<module> - 1 - ok
  imports-ok
  ```
- **"No import cycle (`shared` imports neither app package)."** ✅
  ```
  $ grep -rn "import airunner\b\|import airunner_services\|from airunner\b\|from airunner_services" shared/airunner_common/
  (no output)
  ```
  (The untracked `shared/build/` stale copy is not on the import path and is gitignored.)
- **"All existing imports keep working unchanged."** ✅
  Dominant forms `from airunner.utils.application import get_logger` (23×) and `from airunner_services.utils.application import get_logger` (102×) resolve via each `utils/application/__init__.py` re-export line (unchanged). Direct `from ...get_logger import get_logger` (22×) also works. `Logger` is exported from both shims.
- **"No behaviour change to logging output format/levels for existing `logger.*` calls. Existing logging tests still pass."** ✅
  ```
  $ .venv-ci/bin/python -m pytest -q -k "log or logger or hygiene"
  14 passed, 3 skipped
  ```

### Part 2B — `print()` sweep

### Files changed
58 files across `src/airunner` and `services/src/airunner_services` (see §4 census). Instrumentation/debug/status `print()` replaced with module-level `logger = get_logger(__name__)` calls (`logger.debug/info/warning/error`); genuine CLI output kept and marked `# intentional CLI output`.

### Acceptance bullets
- **"`grep -rn "print(" src/airunner --include="*.py" | grep -v "/tests/"` — every remaining line is under `bin/`/`scripts/` or carries the `# intentional CLI output` marker."** ✅
  ```
  $ grep -rn "print(" src/airunner --include="*.py" | grep -v "/tests/" | grep -v "intentional CLI output" | wc -l
  0
  ```
- **"The guard test enforces this and passes in `.venv-ci`."** ✅
  `services/tests/test_no_stray_print.py` is AST-based (matches only real builtin `print(...)` call nodes, so `debug_print(...)`/docstring examples are not false-positives). It walks both `src/airunner` and `services/src`:
  ```
  $ .venv-ci/bin/python -m pytest services/tests/test_no_stray_print.py -q
  11 passed in 1.34s
  ```
- **"The `services/src` sweep is done to the same standard (ambiguous cases itemised)."** ✅
  Every remaining print under `services/src` (non-test, non-vendor, non-`bin/`) is either CLI-marked or is a docstring/comment (see §4). Ambiguous cases and their resolution are listed in §4.

---

## 4. `print()` census (before/after)

| Tree | Before (non-test) | After | Notes |
|---|---|---|---|
| `src/airunner` | 83 | 19 | all remaining lines are `# intentional CLI output` |
| `services/src` (non-test, non-vendor, non-`bin/`) | ~90 | 26 | all remaining are CLI-marked or docstring/comment |

### Lines kept as `# intentional CLI output` (grouped by file)

`src/airunner`:
- `src/airunner/launcher.py` (lines 243, 261, 265, 287, 291, 313) — localhost cert generation progress printed by the `airunner` CLI entry point.
- `src/airunner/components/llm/utils/model_downloader.py` (363, 365) — `__main__` example usage.
- `src/airunner/gui/resources/icons/feather/invert_colors.py` and `invert_svg_colors.py` — developer CLI icon-inversion tools (`__main__` usage/errors/debug output; `debug_print()` calls marked too so the literal grep is clean).

`services/src`:
- `airunner_services/daemon.py` (375) — `airunner-daemon --generate-config` CLI output.
- `airunner_services/database/alembic/versions/7fb526dc074c_...py` (101, 103) — alembic migration progress output.
- `airunner_services/llm/utils/stream_debug.py` (30) — opt-in terminal stream diagnostics (`AIRUNNER_DEBUG_STREAM_CHUNKS=1`), by design stdout, not a logger.
- `airunner_services/llm/workers/mixins/model_download_mixin.py` (47, 55, 74, 84, 102, 124, 299–301) — headless download terminal progress (tqdm fallback path).
- `airunner_services/utils/gguf_ops.py` (284–292) — headless GGUF quantization statistics report.
- `airunner_services/llm/utils/model_downloader.py` (367, 369) — `__main__` example usage.

### Ambiguous `services/src` cases (itemised with reasoning)
| File | Lines | Resolution |
|---|---|---|
| `eval/client.py` 11, 14, 277, 344 | `>>> print(...)` inside module/function **docstrings** | Not AST `print` calls; guard test ignores. No change needed. |
| `art/managers/zimage/native/embedders.py` 240 | `# print(f"DEBUG apply_rope...")` commented out | Comment, not a call; AST ignores. Left as-is. |
| `eval/math_tools.py` (12 prints) | Agent eval terminal progress | Converted to `logger.info/error` (module logger already present) — these are instrumentation, not user CLI output. |
| `workers/sd_worker.py` (4 prints) | Debug status in worker | Converted to `self.logger` / module `logger`. |

---

## 5. Task 3 — #2077: Windows sidecar cross-compile

### Status: `DONE`

### Root-cause research
The thread power-throttling API (`THREAD_POWER_THROTTLING_STATE` /
`THREAD_POWER_THROTTLING_CURRENT_VERSION` /
`THREAD_POWER_THROTTLING_EXECUTION_SPEED`) is used in
`ggml/src/ggml-cpu/ggml-cpu.c` inside `ggml_thread_apply_priority()`. Upstream
history:
- `199a83842` / `053b1539c` ("threading: support for GGML_SCHED_PRIO_LOW,
  update thread info on Windows to avoid throttling", #12995) introduced the
  calls.
- `9087dd266` ("threading: disable SetThreadInfo() calls for older Windows
  versions") wrapped them in `#if _WIN32_WINNT >= 0x0602`.
- `ef75a89fd` (#17736) moved the `_WIN32_WINNT 0x0A00` definition into
  `ggml/include/ggml.h` (and `common/common.h`), so the guard is effective
  without CMake-forced defines — this is what makes mingw-w64 headers declare
  the API.

**Chosen revision:** tag **`b10000`**, commit
`47a39665e7081dc482feec169961acc09750a5c4` (2026-07-14) — verified to contain
both the `#if _WIN32_WINNT >= 0x0602` guard and the `ggml.h` define. Bumped
from the stale `b8688`/`71a81f6fcc2c7e4bf17c3c2484c9498358d173b2` (2026-04-07).

Upstream commit URL: https://github.com/ggerganov/llama.cpp/commit/47a39665e7081dc482feec169961acc09750a5c4

### Files changed
| File | What |
|---|---|
| `native/runtime_sidecars/runtime_pins.env` | `LLAMA_CPP_COMMIT` → `47a39665e...`, `LLAMA_CPP_VERSION` → `b10000`. Whisper.cpp pins untouched (Windows whisper build passes). |
| `.github/workflows/native-runtime-sidecars.yml` | Added `fail-fast: false` under `strategy:`. |

### Acceptance bullets
- **"`runtime_pins.env` bumped to a documented mingw-safe upstream revision (commit URL in the report)."** ✅ — see above.
- **"`native-runtime-sidecars.yml` has `fail-fast: false` on the matrix."** ✅
  ```yaml
  strategy:
    fail-fast: false
    matrix:
      target-platform: [linux, windows]
  ```
- **"Local `--target-platform windows` and `--target-platform linux` both succeed, with pasted evidence."** ✅

  **Windows build tail** (b10000, mingw-w64 GCC 14-posix):
  ```
  [  5%] Building C object ggml/src/CMakeFiles/ggml-cpu.dir/ggml-cpu/ggml-cpu.c.obj   <- the power-throttling TU compiles cleanly
  [  8%] Building CXX object ggml/src/CMakeFiles/ggml-cpu.dir/ggml-cpu/ops.cpp.obj
  [ 10%] Linking CXX static library ggml-cpu.a
  ...
  [100%] Linking CXX executable ../../bin/llama-server.exe
  [100%] Built target llama-server
  ...
  Built native runtime sidecars in: /home/joe/Projects/airunnerdesktop/build/runtime-sidecars/windows
  ```
  ```
  $ ls -la build/runtime-sidecars/windows/bin/
  -rwxrwxr-x  llama-server.exe   (18109478 bytes, PE32+ x86-64 console)
  -rwxrwxr-x  whisper-server.exe (3718392 bytes, PE32+ x86-64 console)
  $ file build/runtime-sidecars/windows/bin/llama-server.exe
  PE32+ executable for MS Windows 5.02 (console), x86-64, 18 sections
  ```

  **Linux build tail**:
  ```
  [100%] Linking CXX executable ../../bin/llama-server
  [100%] Built target llama-server
  ...
  Built native runtime sidecars in: /home/joe/Projects/airunnerdesktop/build/runtime-sidecars/linux
  ```
  ```
  $ ls -la build/runtime-sidecars/linux/bin/
  -rwxrwxr-x  llama-server   (16881768 bytes, ELF 64-bit x86-64 PIE)
  -rwxrwxr-x  whisper-server (3096104 bytes)
  ```
- **"Sidecar-launch flag/endpoint check done; any launcher change documented."** ✅
  The launcher (`services/src/airunner_services/runtimes/sidecar_launcher.py:58`)
  invokes `llama-server --host <host> --port <port> --model <path> --ctx-size <n> --n-gpu-layers <n>`, and the health check hits the HTTP endpoint.
  `./build/runtime-sidecars/linux/bin/llama-server --help` confirms all five
  flags are still accepted (13 matching help lines). **No launcher change needed.**
- **"Report includes the `gh workflow run` hand-off command."** ✅
  ```
  gh workflow run "Native Runtime Sidecars" --ref bug/close-audit-issues-round2
  ```
  Expected outcome: both matrix legs (`linux`, `windows`) green. Local
  cross-compilation with the same mingw-w64 toolchain is the primary proof;
  the CI run is the definitive check and should be run post-merge.

---

## 6. Test evidence (run in `.venv-ci`)

```
$ .venv-ci/bin/python -m pytest \
    services/tests/test_service_bootstrap.py \
    services/tests/test_secret_storage.py \
    services/tests/test_model_load_security.py \
    services/tests/test_tool_sandbox_security.py \
    services/tests/test_dependency_constraints.py \
    services/tests/test_no_stray_print.py \
    services/tests/test_complexity_report_parity.py \
    -q
70 passed, 7 skipped in 3.29s
```

```
$ .venv-ci/bin/python -m pytest -q -k "log or logger or hygiene"
14 passed, 3 skipped in 2.47s
```

```
$ .venv-ci/bin/python -c "import airunner; import airunner_services; from airunner.utils.application.get_logger import get_logger; get_logger('t').info('ok'); print('imports-ok')"
2026-08-29 07:13:05,951 - t - INFO - <string>::<module> - 1 - ok
imports-ok
```

Task 3 build tails: see §5 (Windows + Linux, both `llama-server`/`llama-server.exe` produced).

### New tests
| Test | What it proves |
|---|---|
| `services/tests/test_no_stray_print.py` (11 tests) | AST-based guard: every builtin `print()` under `src/airunner` and `services/src` is in a CLI dir or carries the intentional marker. |
| `services/tests/test_complexity_report_parity.py` (10 tests) | `DEFAULT_EXCLUDES` identical; `_is_generated` identical across 8 representative paths (incl. `foo_ui.py`, `foo_rc.py`, `feather_rc.py`, `x/y/baz_ui.py`). Fails on drift (verified by mutation). |

---

## 7. Issues now closeable

| Issue | Evidence |
|---|---|
| #2052 | `scripts/mypy_shortcut.py` uses project config (grep: no CLI flags); parity guard test added + passing; docs `docs/complexity-and-typing.md` records advisory stance. |
| #2050 | Single `get_logger` in `shared/airunner_common` (grep: no `class Logger`/`def get_logger` outside shared); `print()` census 83→19 (GUI) / ~90→26 (services), all remaining marked or docstring/comment; guard test enforces. |
| #2077 | `runtime_pins.env` bumped to b10000 (mingw-safe, guard verified); `fail-fast: false`; both local builds succeed with mingw-w64; launcher flags all accepted. |

---

## 8. Deferred / follow-ups

- **Task 3 CI hand-off (required):** run
  `gh workflow run "Native Runtime Sidecars" --ref bug/close-audit-issues-round2`
  post-merge; both legs should be green. This is the definitive check.
- Whisper.cpp pins were not touched — its Windows build passes unchanged.
- Full-tree mypy strictness remains out of scope (advisory stance documented).

---

## 9. Risk notes (reviewer focus)

- **Logging is load-bearing.** Part 2A is a behaviour-preserving refactor: the
  shared `Logger` keeps the exact formatter string, `LogHygieneFilter` on every
  handler, console-always/file-conditional behaviour, `_airunner_configured`
  cache semantics, and `stacklevel=3` call-site reporting. The only semantic
  difference: the services file-log base path resolver is now registered by the
  services shim (import-time) rather than a guarded import inside shared — same
  effective result, verified by `imports-ok` and the logging test subset.
- The `# intentional CLI output` marker is on 45 lines; the guard test whitelists
  `bin/`/`scripts/` dirs and the marker (same line or line above). The marker
  wording is load-bearing — changing it breaks the guard.
- Task 3 bump (b8688 → b10000) crosses ~2.5 months of upstream commits. The
  only mingw-relevant CMake changes in that range are MSVC-policy fixes
  (#21934/#21630); the Windows sidecar build verified locally. The maintainer
  should still run the CI workflow as the definitive check.
- No new `install_requires` entry was added anywhere (`git diff master..HEAD`
  touches no dependency declarations). Radon was installed only into the local
  `.venv-ci` (it is already declared in the root package's `[analysis]` extra),
  not into any package metadata.

---

## 10. Post-report follow-up (maintainer request)

After the round-2 implementation was handed back, the maintainer asked for a
badge refresh on the README header. Commit `41b3d3b50` replaced the single
badge line with a full row: build status (Hybrid Runtime CI), Native Runtime
Sidecars, Docker Release, PyPI, Python 3.13, GPL-3.0 license (retained),
last-commit, and a **Discord** badge linking to
`https://discord.gg/7254Hkzc4T`. The Discord badge uses a static shields.io
label (the `/discord/<id>` endpoint requires a numeric guild ID, not an
invite code) so it always renders, and links to the invite.

### Reviewer nits (non-blocking, addressed)

- `shared/airunner_common/get_logger.py` now exposes the shared log base path
  resolver as the **public** `resolve_log_base_path`; `logging_utils.py`
  imports the public name instead of the private `_resolve_log_base_path`
  (commit `65adffb4c`). The private `_resolve_log_base_path` wrapper inside
  `logging_utils.py` is module-internal and intentionally stays private.
- The `debug_print(` call-line markers in the feather CLI scripts are
  harmless marker noise; the AST-based guard test handles them correctly.
  No change made.

---

## 11. Definition-of-done checklist

- [x] Tasks 1–3 each `DONE` with evidence.
- [x] `.venv-ci` §9.3 test list — all pass (70 passed, 7 skipped); new guard tests pass.
- [x] `import airunner` + `import airunner_services` + `get_logger(...)` succeed; `shared` imports neither app package.
- [x] `grep -rn "print(" src/airunner --include=*.py | grep -v /tests/` — only `# intentional CLI output` lines remain (0 unmarked).
- [x] Exactly one `class Logger`/`def get_logger` body (in `shared/airunner_common`); the two `get_logger.py` are shims.
- [x] `runtime_pins.env` bumped; both local sidecar builds succeed; `fail-fast: false` present.
- [x] `git diff master..HEAD` touches only files implied by the plan (+ new tests + this report).
- [x] No new `install_requires` entry anywhere.
- [x] Report complete per §9 of the plan.
