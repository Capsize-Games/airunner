# Error-handling policy for `airunner_services` (issue #2485)

## Measurement (2026-11-28 tree)

Counted with `rg '^\s*except\s+Exception\b'` plus an AST pass over
`services/src/airunner_services` (`ast.ExceptHandler` nodes):

- `except Exception` lines: **854** (issue says ~861; drift is tree churn).
  888 handler nodes including `except (Exception, ...)` tuple forms.
- Bare `except:`: **0**.
- Handlers with no logging call and no `raise`: **379**.
- Of those, single-statement `pass` / `return` / `continue` / `break`
  swallows: **288** (issue says ~203; the gap is definitional — see below).

"Silent" here means the handler body contains no logging call
(`log*`, `print`, `emit*`, `traceback`, telemetry) and no `raise`,
counting nested calls. "Log-and-swallow" (405 sites) is usually fine;
"silent" (379) is the burn-down list, starting with the 288 trivial ones.

Reproduce: `rg -c` the pattern above, or re-run the AST classifier used
for this doc (no AI-model, GPU, network, or daemon dependencies).

## Per-layer policy

| Layer | Rule |
|---|---|
| API routes (`api/routes/*`, `api/server.py`) | Never swallow. Convert to an HTTP error response; log with context. A `return None`/`pass` fallback lies to the client. |
| Migrations (`database/alembic/*`, `database/db/*`) | Must propagate. A skipped schema change (e.g. reporting "missing" when inspection actually failed) leaves every install quietly un-migrated. Log, then re-raise. |
| Settings persistence (`daemon_client/*`, `database/models/*`) | Writes are not best-effort: a dropped write must at least log. Reads may return documented defaults, but only swallow `ImportError` (Qt absent); anything else propagates. |
| Startup probes (`get_version`, provider/catalog loaders, runtime flags) | Swallow only the "not present" signal (`PackageNotFoundError`, missing-module `ModuleNotFoundError`). A broken-but-present module must raise so the registry/model list visibly fails instead of silently emptying. |
| Best-effort status reads (lifecycle `_read_*`, `_loaded_model_names`, telemetry samplers) | Swallow-with-log is legitimate: the fallback (`None`/`[]`) means "unknown", and the read must never break the operation it observes. Keep the `except` narrow and keep a comment saying why. |
| Background/telemetry threads (`video/telemetry.py`) | Swallow-with-`pass` is legitimate (`# telemetry must never break generation`), but prefer debug logging when a logger exists. |
| Fallback chains (decrypt-with-each-key, format sniffing, QSettings reads) | Returning the documented fallback (`None`/default/next-key) is the contract, not a swallow — but log at debug/warning when the failure is unexpected (DB error, not "row absent"). |

Narrow-est-exception wins everywhere: `except PackageNotFoundError`,
`except ImportError`, `except InvalidToken`, `except (OSError, ...)`.
`except Exception` survives only at documented trust boundaries
(worker loops, route handlers, migration guards) and must log.

## Fixed in this slice (5 sites)

1. `utils/application/get_version.py` — dropped `except Exception:
   continue`; only `PackageNotFoundError` skips to the next package name.
   Unexpected `importlib.metadata` failures now propagate instead of
   silently reporting the checkout fallback.
2. `model_management/model_registry.py::_load_provider_config` — returns
   `None` only when the provider-config module itself is missing
   (`ModuleNotFoundError` naming it or its parents). Real import bugs and
   a missing `LLMProviderConfig` attribute now raise instead of silently
   registering zero LLM models.
3. `database/db/column.py::_table_has_column` — inspection failure is
   logged and re-raised instead of reported as "column missing", which
   used to make `drop_column_by_name` skip with a misleading warning.
4. `preload_settings_store.py::_first_enabled_llm_model` — DB errors now
   log a warning (new `_log_warning` helper, same pattern as
   `_log_info`/`_log_debug`) instead of silently resolving to "no model".
5. `daemon_client/resource_store.py::_set_qsettings_value` — split the
   optional-dependency guard (`except ImportError: return`, mirroring
   `database/models/application_settings.py`) from write failures, which
   now log a warning instead of vanishing. Per-key best-effort behavior
   of `_write_local_values` is unchanged.

Regression tests: `services/tests/test_error_handling_2485.py`.

## Fixed in the next slice (3 sites)

6. `api/routes/art_model_base.py::query_first` — database failures now
   propagate instead of returning `None` ("no settings"). Callers that
   must tolerate a broken settings store (`service_base_path`) catch and
   warning-log the failure, then use the documented default base path.
   `generator_settings_record()` callers now surface DB errors (a 500)
   instead of silently falling back to default version settings.
7. `api/routes/art_model_base.py::service_base_path` — the existing
   fallback for unreadable settings now emits a warning log with
   traceback instead of a bare `pass`.
8. `api/routes/art_generation_job_routes.py::cancel_job` — a failed
   best-effort runtime cancel now warning-logs with traceback; the
   tracker state remains authoritative and the response is unchanged.

Regression tests: the same `test_error_handling_2485.py` (slice-2
section). The global counts above are from the 2026-11-28 measurement;
this slice removes three trivial swallows from the burn-down list.

## Enumerated follow-ups (not fixed here)

Remainder of the 285 trivial swallows, grouped for later slices. All
verified by reading only — each needs the same verify-before-change
(read implementation + tests + callers) before fixing:

- `api/routes/*` (~22 trivial sites: `art_schedulers`,
  `legacy_llm_compat`, `legacy_llm_helpers`, `legacy_llm_stream_helpers`,
  `legacy_status_routes`, `stt_helpers`, `vram`).
  Highest value: these lie to API clients. Convert to HTTP error responses.
- `art/*`, `llm/*`, `workers/*`, `runtimes/*` (majority of the 379).
  Excluded from this slice per the no-GPU/no-network/no-daemon rule;
  many are worker-loop guards that need per-site review against live
  behavior. Do not bulk-fix.
- `service_manager.py:785` (`is_installed` returns `False` when `nssm`
  is missing — acceptable on non-Windows, but should debug-log).
- `utils/application/api_reference.py:19`,
  `daemon_client/gui_bridge_mixin.py:52`, `lifecycle_service.py:221/299/352`,
  `model_management/hardware_profiler.py`, `database/session.py:239/246`
  (cleanup paths — legitimate, add debug logs).
- `database/setup_database.py:51/127/205`, `_database_is_at_head:205`
  (`return False`/`()` on error — migration control flow; review each
  caller before narrowing).
- Migration scripts with inline `except Exception: pass`
  (`6b36790f3292`, `31194f554323`, `column.safe_alter_column`) — log the
  skipped DDL.
