# Test Cleanup Plan for `src/airunner`

## DELETE — Tests for Deleted Workers/Features (13 files)

| File | Reason |
|------|--------|
| `components/application/tests/test_worker_manager_daemon_runtime.py` | Tests deleted WorkerManager prewarm/SD features |
| `components/application/tests/test_daemon_model_load_balancer.py` | Tests deleted worker refs in model_load_balancer |
| `components/application/tests/test_main_window_model_status.py` | Tests deleted `_llm_generate_worker` checks |
| `components/application/tests/test_worker_manager_tts_reference_refresh.py` | Tests deleted TTS generator worker |
| `components/application/tests/test_preload_llm_model.py` | Tests deleted LLM preload/local worker |
| `components/server/tests/test_server_llm_loaded_state.py` | Tests `_llm_generate_worker` |
| `components/server/tests/test_server_art_loaded_state.py` | Tests `_sd_worker` |
| `components/llm/api/tests/test_llm_services_daemon_bridge.py` | Tests deleted prewarm/local fallback |
| `components/tts/tests/test_tts_generator_worker_daemon_runtime.py` | Tests deleted TTS generator worker |
| `components/tts/tests/test_tts_generator_worker_openvoice_settings.py` | Tests deleted TTS generator |
| `components/stt/tests/test_audio_processor_worker_executor_boundary.py` | Tests deleted STT processor |
| `services/tests/test_lifecycle_service.py` | Tests `llm_generate_worker` |
| `components/art/tests/test_sd_worker_daemon_runtime.py` | Already deleted |

## DELETE — Tests for Deleted Workers (already gone)

| File | Note |
|------|------|
| `components/llm/workers/tests/test_llm_generate_worker_pending_request.py` | Already deleted |
| `components/llm/workers/tests/test_rag_indexing_mixin_worker.py` | Already deleted |
| `components/art/tests/test_sd_worker_daemon_runtime.py` | Already deleted |

## DELETE — Tests for Deleted art/LLM managers

| File | Reason |
|------|--------|
| `components/art/managers/stablediffusion/tests/` | Tests deleted SD manager |
| `components/llm/managers/tests/` | Tests deleted LLM managers |
| `components/llm/agents/tests/` | Tests deleted agents |

## KEEP — Pure GUI tests (canvas, widgets, positioning)

These test the GUI which still exists:
- `components/art/gui/widgets/canvas/**/test_*.py` (20+ files)
- `components/art/gui/tests/test_*.py` (3 files)
- `components/application/gui/widgets/slider/tests/test_slider_widget.py`
- `components/application/gui/windows/main/tests/test_main_window_art_tools_sidebar.py`

## KEEP — Utility/Infrastructure tests

- `components/tools/tests/test_url_safety.py`
- `utils/tests/test_path_policy.py`
- `utils/tests/test_zip_utils.py`
- `utils/tests/test_export_image.py`
- `utils/tests/test_download_temp_cleanup.py`
- `utils/memory/tests/test_*.py` (3 files)
- `utils/application/tests/test_signal_mediator.py`
- `utils/application/tests/test_request_correlation.py`
- `utils/application/tests/test_headless_logging.py`
- `ipc/tests/test_messages.py`
- `distribution/tests/test_*.py` (2 files)
- `daemon_client/tests/test_daemon_launcher.py`
- `daemon_client/tests/test_gui_daemon_client.py`

## KEEP — Runtime/Sidecar tests (candidate for move to services later)

- `runtimes/tests/test_*.py` (10 files)
- `services/tests/test_daemon.py`
- `services/tests/test_runtime_layout.py`

## KEEP — Bootstrap/Settings tests

- `components/application/tests/test_fresh_database_bootstrap.py`
- `components/application/tests/test_headless_mode.py`
- `components/application/tests/test_settings_mixin.py`
- `components/application/tests/test_settings_property_mixin_voice_settings.py`
- `bin/tests/test_airunner_headless.py`
- `tests/test_qt_bootstrap.py`
- `tests/test_torch_bootstrap.py`
- `tests/test_linux_bundle_layout.py`
