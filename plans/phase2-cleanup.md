# Phase 2 Cleanup Plan: `src/airunner` Directory Audit (Updated)

## DELETE — Obsolete (no active purpose in GUI-only architecture)

### Alembic migrations
| Path | Reason |
|------|--------|
| `alembic/versions/` (empty) | Database migrations now handled in `model/src/airunner_model/alembic/` |

### Headless/Server code
| Path | Reason |
|------|--------|
| `bin/airunner_headless.py` | Replaced by daemon API (`services/src/airunner_services/daemon.py`) |
| `bin/tests/test_airunner_headless.py` | Tests for deleted headless |
| `bin/eval/server.py` | Legacy eval server, replaced by daemon |
| `bin/eval/` (directory) | Obsolete eval scripts |
| `app_mixins/headless_runtime_mixin.py` | Headless mode no longer needed in GUI |
| `components/server/` | Local HTTP server for static assets — KEEP (serves MathJax, etc.) |

### Duplicate DB utilities
| Path | Reason |
|------|--------|
| `utils/db/` (5 files + `__init__`) | Duplicate of `model/src/airunner_model/db/` |

### Duplicate data utilities
| Path | Reason |
|------|--------|
| `utils/data/model_to_dataclass.py` | Duplicate of `model/src/airunner_model/model_to_dataclass.py` |

### Dev utilities
| Path | Reason |
|------|--------|
| `dev/autorestart.py` | Unused dev utility |

### LLM non-GUI (moved to services)
| Path |
|------|
| `components/llm/managers/` (keep `llm_request.py`, `llm_response.py`, `llm_settings.py`) |
| `components/llm/config/` |
| `components/llm/agents/` |
| `components/llm/core/` |
| `components/llm/langgraph/` |
| `components/llm/long_running/` |
| `components/llm/adapters/` |
| `components/llm/utils/` |
| `components/llm/data/` |

### Art non-GUI (moved to services)
| Path |
|------|
| `components/art/managers/stablediffusion/` (keep `image_request.py`, `image_response.py`, `rect.py`) |
| `components/art/managers/rmbg/` |
| `components/art/utils/` |
| `components/art/config/` |
| `components/art/data/` |
| `components/art/trainers/` |
| `components/art/services/` |
| `components/art/tests/` |

---

## MIGRATE — Belongs in services/model

### `src/airunner/runtimes/` → `services/src/airunner_services/`
- **Currently**: Sidecar process management (launching, IPC, health checks) lives in the GUI
- **Why wrong**: `src/airunner` should only be a GUI — it should not launch/manage sidecar processes
- **Plan**: Move all runtime/sidecar logic to services. The GUI should communicate with sidecars via the daemon API, not launch them directly. `app.py`'s `build_runtime_registry()` call should be replaced with daemon API calls.

### `src/airunner/services/` → `services/src/airunner_services/`
- **Currently**: `daemon_config.py`, `lifecycle_service.py`, `service_manager.py` live in GUI
- **Plan**: These are infrastructure services. `daemon_config.py` is used by the daemon client. After migration, the GUI daemon client should read config from the daemon API.

### TTS: Full Migration Plan
- **Currently**: Melo/OpenVoice vendor code, TTS model managers, and inference all live in `src/airunner`
- **Target**: Only audio **playback** (tts_vocalizer_worker) stays in GUI. All inference (model loading, synthesis) moves to services.
- **Vendor code**: `src/airunner/vendor/melo/` and `src/airunner/vendor/openvoice/` → `services/src/airunner_services/vendor/`
- **Managers**: `components/tts/managers/` → `services/src/airunner_services/tts/`
- **Tests**: `components/tts/tests/` → `services/tests/tts/`

---

## KEEP — GUI-Only

| Directory | Why |
|-----------|-----|
| `components/llm/gui/` | Chat widgets |
| `components/llm/api/` | API bridge |
| `components/art/gui/` | Canvas, drawing tools |
| `components/art/api/` | API bridge (canvas_services, art_services) |
| `components/art/filters/` | Image filters |
| `components/application/gui/` | Main window, dialogs, WorkerManager |
| `components/application/workers/` | Download workers (with progress UI) |
| `components/chat/`, `components/document/`, `components/downloader/` | UI |
| `components/knowledge/`, `components/model_management/`, `components/settings/` | UI |
| `components/server/` | Local HTTP server (static assets) |
| `components/splash_screen/` | Splash |
| `components/tts/workers/tts_vocalizer_worker.py` | Audio playback only |
| `components/stt/workers/audio_capture_worker.py` | Microphone capture only |
| `daemon_client/` | Daemon HTTP client |
| `utils/application/` | Signal mediator, logging |

---

## Execution Order

1. Delete `alembic/`, `dev/`, `bin/airunner_headless.py`, `bin/eval/`, `bin/tests/test_airunner_headless.py`
2. Delete `utils/db/`, `utils/data/`
3. Delete `headless_runtime_mixin.py` (update `app.py` imports)
4. Delete LLM non-GUI dirs
5. Delete Art non-GUI dirs
6. **Migrate** `runtimes/` → services (update all importers)
7. **Migrate** `services/` (daemon_config, lifecycle, service_manager) → services package
8. **Migrate** TTS vendor + managers → services (full TTS migration)
