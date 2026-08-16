# AIRunner Architecture Refactor Plan (headlesscode orchestrated)

Based on: docs/architecture/architecture-complexity-audit.md

## Strategy
Three sequential orchestration rounds. Round 1 = safe consolidations (all mostly independent, high value). Round 2 = invasive restructuring (depends on round 1). Round 3 = settings-store cleanup (depends on round 1). Each group is a single coherent deliverable, worked in its own git worktree by a headlesscode worker, then reviewed and QA'd by the harness.

## Baseline (capture BEFORE round 1, run in repo root with the venv)
- ./venv/bin/python scripts/gui_complexity_report.py
- ./venv/bin/python scripts/services_complexity_report.py
- ./venv/bin/python scripts/gui_dead_code_scanner.py
- ./venv/bin/python scripts/services_dead_code_scanner.py
These write reports under build/gui_complexity and build/services_complexity. Keep them; round close-out diffs against them.

## Rounds

### Round 1 — safe consolidations (issues 101-105)
- 101: create one shared package as single source of truth for settings, startup env, dev tokens, bundle layout, and contract enums; delete per-package copies.
- 102: unify the daemon HTTP client into one canonical implementation.
- 103: sunset the legacy API surface (legacy_server.py + legacy_* modules) after verifying versioned route coverage.
- 104: align docs with the real package layout (remove api/ and model/ references).
- 105: add GUI crash capture (sys.excepthook, faulthandler, unraisablehook) to the launchers.

Gate for round 2: issues 101 and 102 must be merged and green (unit tests + service bootstrap + offscreen GUI functional tests).

### Round 2 — invasive restructuring (issues 201-202)
- 201: narrow the string-typed signal bus at the hottest seams (depends on 101 for the single contract_enums source).
- 202: flatten the Settings*Mixin hierarchy and split main_window.py (3244 lines) so no class exceeds the repo's 250-line target (depends on 101).

Gate for round 3: 201 and 202 merged and green.

### Round 3 — cleanup (issue 301)
- 301: resolve the settings-store ambiguity: move client-local preferences out of service SQLite into QSettings, keep service-owned fields in the DB.

## Global validation gates for every group
- Unit suite: ./venv/bin/python scripts/run_tests.py --unit
- Service bootstrap: ./venv/bin/python -m pytest services/tests/test_service_bootstrap.py -v
- Offscreen GUI functional: ./venv/bin/python -m pytest services/tests/test_gui_llm_tts_functional.py -v --timeout=1200
- Complexity targets: no new hotspots beyond baseline (Radon rank <= B, files <= 250 SLOC, functions <= 20 lines, classes <= 250 lines, MI >= 65).

## Monitoring and control commands (run from repo root)
- Round status: headlesscode orchestrate status --repo /home/joe/Projects/airunnerdesktop --wait --json
- Stop a runaway group: headlesscode orchestrate stop --repo /home/joe/Projects/airunnerdesktop --group <name>
- Live dashboard: headlesscode dashboard --port 4390 --repo /home/joe/Projects/airunnerdesktop

## Canonical settings store (issue 301 resolution)

The settings-store ambiguity is resolved as follows; new settings must follow
this split:

- **QSettings (client-local)**: theme and appearance (`dark_mode_enabled`,
  `override_system_theme`), window and tab state (`is_maximized`), canvas-tool
  and layer defaults (`current_tool`, `current_layer_index`,
  `generator_section`), setup-wizard and agreement completion flags
  (`run_setup_wizard`, `download_wizard_completed`, the four agreement
  checks), `FontSetting`, and `gui_language`. The GUI reads/writes these via
  `src/airunner/utils/settings/client_settings.py`, which is backed by
  `AIRUNNER_BASE_PATH/config/settings.ini` (see `get_qsettings`). The alembic
  migration `move_client_local_application_settings_to_qsettings` owns the
  database-side move; the field list in `CLIENT_LOCAL_SETTINGS` mirrors it.
- **Service database (daemon-owned)**: runtime paths (`PathSettings`), LLM
  generation settings, RAG settings, service enablement and daemon bind
  settings (`sd_enabled`, `llm_enabled`, `tts_enabled`, `stt_enabled`,
  `http_server_enabled`, `http_server_host`, `http_server_port`),
  conversations, chatbots, summaries, and user data.
- **Environment constants**: process-level knobs only (ports, toggles that
  must be fixed at process start), never user preferences.

GUI code must not read client-local fields from the daemon `ApplicationSettings`
resource; `BasicSettingsUpdateMixin.update_application_settings` routes
client-local keys to QSettings automatically.

## File ownership (avoid cross-group merge conflicts)
- 101: settings.py, startup_env, dev_build_token, linux_bundle_layout, contract_enums, package_metadata across src/, services/, native/, plus setup.py wiring and all importers of those modules.
- 102: src/airunner/daemon_client/* and services/src/airunner_services/daemon_client/* plus their importers (app.py, launcher.py, main_window.py, worker_manager.py).
- 103: services/src/airunner_services/api/legacy_*.py, legacy_server.py, and any route that imports them.
- 104: README.md, docs/architecture/*.md, native/README.md, services/README.md, src/README.md.
- 105: src/airunner/launcher.py, src/airunner/main.py, native/src/airunner_native/launcher.py.
- 201: src/airunner/utils/application/signal_mediator.py, mediator_mixin.py, and consumers of SignalCode in src/ and services/.
- 202: src/airunner/components/application/gui/windows/main/** (main_window.py, settings_mixin.py, mixins/, worker_manager.py, model_load_balancer.py), app.py.
- 301: src/airunner/components/**/data/*.py settings models, utils/settings/get_qsettings.py, services persistence routes that read those tables.
