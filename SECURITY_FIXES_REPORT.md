# SECURITY_FIXES_REPORT

Security & bug close-out for the open 2026-08 audit issues (#2031, #2032,
#2034, #2035, #2057, #2048) plus the security-test CI coverage gap (Task 5).

---

## 1. Branch & commits

**Branch:** `security/close-audit-issues-2026-08` (off `master`)

```
$ git log --oneline master..HEAD
b01f4c097 fix(gui): replace duplicated url_safety with re-export shim
e22432779 fix(packaging): keep setuptools below 82 while torch is pinned <2.14
f6f2c3813 ci: run security regression tests in Hybrid Runtime CI
fc2778c28 feat(gui): persistent LNA warning in service settings widget
60513887f fix(services): replace substring deny-list with AST tool-code validator
3d518dd04 fix(services): gate tokenizer trust_remote_code fallbacks on explicit opt-in
```

Lean CI venv `.venv-ci` built exactly as specified in the plan
(`python3 -m venv .venv-ci`; `pip install -U pip setuptools wheel`;
`pip install -e ./shared`; `pip install -e "./services[development]"`;
`pip install -e ".[development]"`). No `torch`/`transformers`/`langgraph`.

---

## 2. Per-task status

### Task 1 — #2031: gate the tokenizer `trust_remote_code` fallbacks

**Status: DONE**

**Files changed**

| Path | What |
|------|------|
| `services/src/airunner_services/llm/managers/mixins/tokenizer_loader_mixin.py` | Added module-level `_remote_code_allowed()` (L20); gated all three `trust_remote_code=True` sites |
| `src/airunner/components/llm/gui/widgets/llm_settings_widget.py` | Visible opt-in checkbox (L107–121) + `on_trust_remote_code_toggled` (L124) |
| `services/tests/test_model_load_security.py` | Split into lean-env-runnable + torch-only; new gating tests |

**Changes**

1. `_remote_code_allowed()` (L20) reads `ApplicationSettings.trust_remote_code`
   via `ApplicationSettings.objects.first()` / `get_or_create()`, wrapped in
   try/except → `return False` (fail closed on missing row / no DB / error).
   No raw sqlite connection.
2. `_load_model_config` (L175): tries `trust_remote_code=False` first; only on
   exception **and** `_remote_code_allowed()` retries with `True` (L194). When
   the flag is off, the `False` attempt's exception propagates to the caller's
   `_handle_tokenizer_error`.
3. `_load_tokenizer_with_trust_remote_code` (L79/L101) and `_load_slow_tokenizer`
   (L125/L139): `if not _remote_code_allowed(): raise RuntimeError("Model
   requires remote code; enable 'Trust remote code' in settings to load it.")`.
   `from_pretrained(..., trust_remote_code=True)` never runs when the flag is
   off.
4. Justification comments retained above every remaining literal (required by
   `test_trust_remote_code_disabled_by_default`).
5. UI: no existing checkbox surfaced `ApplicationSettings.trust_remote_code`
   (grep of `src/airunner` found no reference). Added a `QCheckBox` in
   `llm_settings_widget.py` L107 labeled *"Trust remote code from model repos
   (unsafe — runs arbitrary Python)"*, wired via the existing
   `update_application_settings(trust_remote_code=val)` pattern
   (`BasicSettingsUpdateMixin`), reading the current value from
   `self.application_settings`.

**Acceptance criteria**

- ✅ `grep -rn "trust_remote_code=True" services/src/airunner_services` — all
  7 hits are in `tokenizer_loader_mixin.py`; the 3 code hits (L115, L153,
  L200) are each inside a method whose function body calls
  `_remote_code_allowed()` (proved structurally by
  `test_tokenizer_mixin_has_no_unconditional_remote_code`), the other 4 are
  comments/docstrings. **No unconditional `True`.**
- ✅ With `trust_remote_code=False` (default), loads that need remote code
  raise `RuntimeError` instead of executing remote code
  (`test_tokenizer_fallback_methods_raise_without_opt_in`,
  `test_load_model_config_passes_false_first`).
- ✅ New tests in `services/tests/test_model_load_security.py`:
  `test_remote_code_allowed_false_by_default` (False when setting off / DB
  unavailable / True when opted in),
  `test_load_model_config_passes_false_first` (spy on
  `AutoConfig.from_pretrained`, asserts kwargs `trust_remote_code=False` and
  call count 1),
  `test_tokenizer_fallback_methods_raise_without_opt_in` (both fallbacks raise
  and never call `from_pretrained` with `True` when flag off),
  `test_tokenizer_fallback_methods_run_when_opted_in` (opt-in on → both run
  with `trust_remote_code=True`),
  `test_load_model_config_retries_true_only_when_opted_in`.
- ✅ These tests **run** (not skip) in the lean venv (13/13 pass, see §3).
- ✅ `test_model_load_security.py` passes in `.venv-ci` (13 passed).

### Task 2 — #2032: real validation for custom tool code

**Status: DONE**

**Files changed**

| Path | What |
|------|------|
| `services/src/airunner_services/database/models/llm_tool.py` | `validate_code_safety` rewritten as an AST analyzer (L110); module constants `_DENYLISTED_CALLS` (L13), `_DENYLISTED_MODULE_ROOTS` (L36), `_dotted_attribute_chain` (L50) |
| `services/tests/test_tool_sandbox_security.py` | 12 new lean-runnable AST tests; ToolManager tests scoped to the agent stack |

**Changes**

`validate_code_safety()` (L110) now:
- `ast.parse`; `SyntaxError`/`ValueError` → `(False, "Code contains syntax errors: …")`.
- Rejects `ast.Import` / `ast.ImportFrom` → `"import statements are not allowed"`.
- Rejects `ast.Call` to a `Name` in `_DENYLISTED_CALLS` (`exec, eval, compile,
  __import__, getattr, setattr, delattr, globals, locals, vars, open, input,
  breakpoint, help, memoryview`) → `"call to '<name>' is not allowed"`.
- Rejects dunder `ast.Attribute` (`__class__`, `__subclasses__`, …) →
  `"attribute access to '<attr>' is not allowed"`.
- Rejects attribute chains rooted at `os/sys/subprocess/shutil/socket/ctypes/
  pathlib/importlib` → `"access to '<dotted>' is not allowed"` (defence in
  depth; imports already blocked).
- Rejects `ast.Name` with id `__builtins__` / `__loader__`.
- Keeps the `@tool` decorator requirement; specific messages.
- Signature `-> tuple[bool, str]` and module-level `validate_tool_code(code)`
  unchanged; all call sites unchanged.

**Acceptance criteria**

- ✅ AST-based; `grep -c "\.lower()" llm_tool.py` → **0** (no substring
  matching remains).
- ✅ New tests reject each listed payload with a specific message:
  `().__class__.__mro__[1].__subclasses__()` (`test_validate_ast_rejects_dunder_mro_chain`),
  `getattr(x, "__globals__")` (`..._rejects_getattr_globals`),
  `import os` (`..._rejects_import_statement`),
  `from sys import modules` (`..._rejects_from_import`),
  `__builtins__["ev"+"al"]("1")` (`..._rejects_builtins_concat_eval`),
  `breakpoint()` (`..._rejects_breakpoint`).
- ✅ Benign `@tool` fixture passes (`test_validate_ast_accepts_benign_tool`;
  the decorator is injected by `ToolManager`'s exec namespace — matching
  existing fixtures, so no import in the payload).
- ✅ A literal string `"open(the file)"` in a docstring/return value is **not**
  rejected (`test_validate_ast_accepts_literal_open_string`).
- ✅ All previously-passing assertions still pass (ToolManager-level tests kept
  verbatim).
- ✅ These tests run in the lean venv (12 passed, see §3); the 7 ToolManager
  tests are explicitly `_NEEDS_TOOL_MANAGER`-skipped only when the agent stack
  is absent.

### Task 3 — #2034: LNA CORS — UI warning + regression test

**Status: DONE**

**Files changed**

| Path | What |
|------|------|
| `src/airunner/components/settings/gui/widgets/service_settings_widget.py` | Persistent inline warning `QLabel` (L129–139), show/hide on toggle (L181–187), sync on load (L275–276) |
| `src/airunner/components/settings/gui/widgets/tests/test_service_settings_lna_warning.py` | New GUI regression test |

**Changes**

- Persistent inline warning label (styled with the existing
  `setStyleSheet("color: #b45309; font-weight: bold;")` pattern used by other
  settings widgets; no new styling infra). Text: *"Local Network Access is
  enabled. Other devices on your network can reach AI Runner's local server.
  Only enable this on trusted networks."*
- `_on_lna_toggled` now shows/hides the label (the one-shot `QMessageBox` was
  replaced — the plan asked for a persistent inline warning, not a popup).
- `set_settings` also syncs the label so an already-enabled LNA shows it on
  load without a toggle.

**Acceptance criteria**

- ✅ Foreign origin gets no permissive CORS — already proven by
  `test_lna_cors_rejects_non_loopback_origin` /
  `test_lna_cors_rejects_https_scheme` /
  `test_lna_cors_never_sends_wildcard` in
  `src/airunner/components/server/tests/test_local_http_server_cors.py`
  (existing file; the required assertions — evil origin → no `ACAO`, loopback
  → exact echo, `Access-Control-Allow-Private-Network: true` present — were
  all already present, so no parallel file was created; the plan says "do not
  create a parallel file").
- ✅ Loopback origin still works — `test_lna_cors_echoes_loopback_origin`,
  `test_lna_cors_accepts_localhost_origin`.
- ✅ Toggling LNA shows/hides a visible warning label — warning widget at
  `service_settings_widget.py:129` (created), toggle handler at `:181`,
  load sync at `:275`. Proven by `test_service_settings_lna_warning.py`.
- ✅ New test passes in `.venv-ci` (4/4).

### Task 4 — #2035: verify keyring migration is complete

**Status: NO CHANGE NEEDED** — all four verification points pass; evidence:

**1. Every read path goes through the serialization layer or a non-DB source.**

Consumer table (grep over `src/` + `services/`):

| Field | Consumers | Secret source |
|-------|-----------|----------------|
| `hf_api_key_read_key` | `api_token_widget.py:19,25` (GUI display), write-back `:32,35` | GUI reads come from daemon `ApplicationSettings` hydrated by `serialize_record` → `retrieve_secret` (`persistence_serialization.py:58`). Writes go through `update_application_settings` → daemon `normalized_values` → `store_secret` (`persistence_serialization.py:114`). |
| `hf_api_key_write_key` | only `secret_store.py`/model/migration | No GUI/service read of a live secret; column stores the keyring reference. |
| `civit_ai_api_key` | `civitai_preferences_widget.py:20,24` (GUI), `download_model_dialog.py:795` (`_api_key` property) | Both read `self.application_settings.civit_ai_api_key` — hydrated via `serialize_record`/`retrieve_secret` (daemon-backed), never a raw DB column read. Download path (`job_service.py:156`) uses `get_setting("civitai/api_key", …)` (QSettings), not the DB column. |
| `api_key` (LLM generator) | `chat_model_factory_provider_creation.py:39,68` (`provider_runtime.api_key`) | `ProviderRuntimeConfig` is built from `os.getenv("OPENROUTER_API_KEY")`/`OPENAI_API_KEY` (`chat_model_factory_helpers.py:191,221`) or local. `grep` finds **no** runtime read of `db_settings.api_key` expecting a live secret (only `secret_store.py:35` references the column key). |

No consumer reads a raw DB column expecting a live secret.

**2. The migration clears the plaintext column.** Quoted from
`a7c93f2e1b4d_move_api_keys_to_os_keyring.py` L66–73:

```python
store_secret(column_name, str(value))
bind.execute(
    sa.text(
        f"UPDATE {table_name} SET {column_name}=:empty "
        f"WHERE id=:id"
    ),
    {"empty": "", "id": row_id},
)
```

It **clears** the column (`= ""`) after moving the secret.

**3. `keyring` is optional everywhere.** `grep -rn "keyring" setup.py
services/setup.py native/setup.py shared/airunner_common/package_metadata.py`
→ no matches (exit 1). The only import is the guarded
`try: import keyring except Exception` in `secret_store.py:20-26`.

**4. Headless fallback test passes.** `test_plaintext_fallback_when_keyring_missing`
passes (see §3, `test_secret_storage.py` 8/8).

**Acceptance criteria:** ✅ consumer table above; ✅ `test_secret_storage.py`
passes (8/8); ✅ no gap found → no fix/test needed.

### Task 5 — SEC tests must run in CI (coverage gap)

**Status: DONE**

**Files changed**

| Path | What |
|------|------|
| `services/tests/test_model_load_security.py` | Removed module-level `importorskip("torch")`; source-scan + pure-Python assertions now run in lean env; only `TestTorchOnlySourceScans.test_all_torch_load_calls_use_weights_only` keeps a scoped `importorskip` |
| `services/tests/test_tool_sandbox_security.py` | AST-validator assertions moved above the guard; ToolManager imports wrapped in try/except with per-test `_NEEDS_TOOL_MANAGER` skipif |
| `.github/workflows/eval-tests.yml` | `runtime-contract-tests` pytest list now includes `test_model_load_security.py`, `test_tool_sandbox_security.py`, `test_dependency_constraints.py` (`test_secret_storage.py` was already listed) |

**Before/after (lean `.venv-ci`)**

| File | Before | After |
|------|--------|-------|
| `test_model_load_security.py` | 0 run / whole module skipped | 13 passed, 0 skipped |
| `test_tool_sandbox_security.py` | 0 run / whole module skipped | 12 passed, 7 skipped (ToolManager tests, need langchain stack) |
| `test_secret_storage.py` | 8 passed | 8 passed |

**Acceptance criteria**

- ✅ The three security test files are in the `runtime-contract-tests` list
  (`eval-tests.yml:60-72`).
- ✅ Task 1 / Task 2 / Task 3 tests execute (not skip) in `.venv-ci`.
- ✅ No security assertion deleted or weakened — only re-scoped. The only
  remaining skips are the 7 ToolManager tests (genuinely need
  langgraph/langchain_core) and 1 torch-only source scan; listed in §3.

### Task 6 — #2057: setuptools vs torch constraint

**Status: DONE**

**Files changed**

| Path | What |
|------|------|
| `pyproject.toml:5` | `requires = ["setuptools>=80.9.0,<82", "wheel"]` |
| `services/pyproject.toml:8` | same |
| `native/pyproject.toml:8` | same |
| `services/tests/test_dependency_constraints.py` | new source-scan guard |
| `.github/workflows/eval-tests.yml` | constraint test wired into CI list |

**Changes**

- All three `[build-system]` files now pin `setuptools>=80.9.0,<82` with a
  comment explaining the torch metadata constraint.
- `grep -rn "setuptools" DEVELOPMENT_REQUIREMENTS` → no extra pin to align
  (only the build-system files carry setuptools).
- `services/tests/test_dependency_constraints.py` asserts (a) every
  build-system file's setuptools pin is `<82` with an explicit `<82` bound,
  (b) no `DEVELOPMENT_REQUIREMENTS` entry requests `>=82` — while torch is
  pinned below 2.14 (source scan of `package_metadata.py`).

**Acceptance**

- ✅ `.venv-ci/bin/pip check` → `No broken requirements found.` (exit 0). No
  other `pip check` noise to report in the lean install.
- Report recommendation: **close PR #2022 or rebase it to `<82`** — the
  constraint test will fail the moment it merges a `>=84` setuptools pin.
- The venv install step (`pip install -U setuptools`) installs 84, but the
  build-system pin governs isolated builds; the constraint test guards the
  packaging files.

### Task 7 — #2048: drift guard for duplicated modules

**Status: DONE**

**Files changed**

| Path | What |
|------|------|
| `src/airunner/url_safety.py` | Replaced the stale duplicate with a thin re-export shim of `airunner_services.url_safety` |
| `src/airunner/components/application/tests/test_module_parity.py` | `url_safety` guard is now a re-export identity check; added `runtime_layout` bind-host-normalized parity test |

**Approach:** preferred (services copy canonical; GUI re-export shim) for
`url_safety`; drift-guard tests for the remaining pairs.

**Reconciliation of the three drifted pairs**

| Pair | What differed | Winner | Why |
|------|---------------|--------|-----|
| `url_safety` (GUI vs services) | GUI was missing the NAT64 embedded-IPv4 prefixes (`64:ff9b::/96`, `64:ff9b:1::/48`), the 6to4 relay anycast block (`192.88.99.0/24`), multicast handling, and the `AIRUNNER_SSRF_ALLOWED_HOSTS` allow-list (`_allowed_host_set`/`_host_is_allowed` + 2 call sites) | **services** | Services has the more complete SSRF blocklist (commit `23bc2e114` hardening, issue #2029). GUI copy was stale → replaced with a re-export shim, so the GUI inherits the stricter behaviour. Never loosened. |
| `daemon_config` (GUI vs services) | Only the `runtime_layout` import path (`airunner.runtimes.runtime_layout` vs `airunner_services.config.runtime_layout`) | both (identical otherwise) | Pre-existing parity test `test_daemon_config_identical_after_import_normalization` normalizes the documented import-path difference and guards the rest; verified identical apart from that line. |
| `runtime_layout` (GUI `runtimes/` vs services `config/`) | Only the `runtime_bind_host` import path (`airunner.runtimes.runtime_bind_host` vs `airunner_services.runtimes.runtime_bind_host`) | both (identical otherwise) | New parity test `test_runtime_layout_identical_after_bind_host_normalization` normalizes the documented import path and guards the rest. `file_policy` is byte-identical (existing guard). |

**Acceptance criteria**

- ✅ Either re-export shims OR drift-guard tests exist for every pair:
  `file_policy` byte-identical guard; `daemon_config` import-normalized guard;
  `runtime_layout` import-normalized guard; `url_safety` re-export identity
  check (cannot drift).
- ✅ The three drifted pairs are reconciled (table above).
- ✅ `url_safety` behaviour unchanged-or-safer: `test_download_security.py`
  (47 tests) and all parity tests green.
- ✅ No import cycles: `.venv-ci/bin/python -c "import airunner; import
  airunner_services; print('ok')"` → `ok`.

---

## 3. Test evidence (run in `.venv-ci`)

```
$ .venv-ci/bin/python -m pytest \
    services/tests/test_model_load_security.py \
    services/tests/test_tool_sandbox_security.py \
    services/tests/test_secret_storage.py \
    services/tests/test_download_security.py \
    services/tests/test_dependency_constraints.py \
    src/airunner/components/server/tests/test_local_http_server_cors.py \
    -q
=================== 88 passed, 7 skipped, 1 warning in 1.27s ===================
```

Additional (Task 3 + Task 7 GUI tests):

```
$ .venv-ci/bin/python -m pytest \
    src/airunner/components/settings/gui/widgets/tests/test_service_settings_lna_warning.py \
    src/airunner/components/application/tests/test_module_parity.py -q
============================== 11 passed in 0.17s ==============================
```

The 7 skipped tests are the `ToolManager`-level tests in
`test_tool_sandbox_security.py` (`_NEEDS_TOOL_MANAGER`), which require the
langchain/langgraph agent stack that is deliberately absent from the lean
`[development]` install. They are listed explicitly; **no security-critical
assertion is skipped.** The single torch-only test
(`TestTorchOnlySourceScans.test_all_torch_load_calls_use_weights_only`) is
scoped `importorskip` and skips in the lean env by design (it needs torch to
be meaningful only in the ML install).

```
$ .venv-ci/bin/pip check
No broken requirements found.
```

```
$ .venv-ci/bin/python -c "import airunner; import airunner_services; print('ok')"
ok
```

---

## 4. Issues now closeable

| # | Evidence (one line) |
|---|---------------------|
| #2031 | No unconditional `trust_remote_code=True` remains; all three sites gated on `_remote_code_allowed()`; UI opt-in checkbox added; 6 new gating tests pass in lean CI. |
| #2032 | `validate_code_safety` is AST-based (no `code.lower()` substring matching, grep = 0); all six listed bypass payloads rejected with specific messages; benign tool + literal-string tests pass. |
| #2034 | Foreign origin gets no `Access-Control-Allow-Origin` (existing CORS tests); persistent inline UI warning added (`service_settings_widget.py:129`) with show/hide + on-load sync and regression test. |
| #2035 | Consumer table complete; migration clears plaintext columns (`UPDATE … SET col=''`); `keyring` optional everywhere; headless fallback test passes (8/8). |
| #2057 | All three `[build-system]` files pin `setuptools>=80.9.0,<82`; `pip check` clean; `test_dependency_constraints.py` guards future bumps (PR #2022 must be rebased to `<82`). |
| #2048 | `url_safety` GUI copy is a re-export shim of the canonical services module; parity guards cover all four duplicated pairs; `import airunner` + `import airunner_services` succeed. |

---

## 5. Deferred / out of scope

- **Subprocess isolation for #2032** — not implemented, per the plan. The AST
  validator makes `safety_validated=True` meaningful (the actual gate), and
  `code_sandbox.py` remains honest that restricted-builtins is not a security
  boundary. A true subprocess sandbox is a larger change tracked separately;
  recommendation: do it as its own issue.
- **#2050, #2052, #2077** and all `enhancement`/language issues — out of scope
  per the plan, untouched.
- **Other `pip check` noise** — none observed in the lean `.venv-ci` install.
  The setuptools/torch conflict only manifests in ML installs; the constraint
  test guards the packaging files.

---

## 6. Risk notes (reviewer should look at hard)

1. **`test_model_load_security.py` stubs `transformers`/`torch`** in
   `_load_language_base_pure()` (restricted-unpickler import isolation). If a
   future change makes `language_base.py` use another heavy import, the stub
   list must be extended. The stub uses `sys.modules.setdefault`, so a real
   torch install is not clobbered.
2. **`test_tool_sandbox_security.py` order matters**: the AST-validator tests
   must stay above the guarded `ToolManager` imports; the try/except wraps
   only the heavy imports.
3. **`_remote_code_allowed()`** performs a DB read on every tokenizer load
   fallback. It is cached only by the ORM's normal query path (the
   `RuntimeContextMixin` settings cache is not used here). Performance is a
   single indexed singleton-row query per fallback; acceptable, but a reviewer
   may want the cache reused if the fallback path is hot.
4. **`llm_settings_widget.py` checkbox** is added to `quantization_layout`
   (mirroring `_runtime_precision_dropdown`); it does not touch the generated
   `.ui` file, so regeneration won't drop it.
5. **`url_safety` shim** depends on `airunner_services` being importable from
   the GUI. The GUI already hard-depends on `airunner-services` (declared in
   `setup.py` GUI_REQUIREMENTS, issue #2037), and `import airunner` +
   `airunner_services` both succeed. If a future packaging change makes the
   GUI importable without services, the shim would need a fallback — currently
   not the case.
6. **PR #2022** (`setuptools>=84`) will now fail `test_dependency_constraints.py`
   and must be rebased to `<82` or closed.
