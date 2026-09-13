# Desktop feature matrix (Linux v1)

Issue: https://github.com/Capsize-Games/airunner/issues/2084 (R01). Parent: https://github.com/Capsize-Games/airunner/issues/2083.

Scope: every discoverable user-facing capability registered in `src/airunner/components/` (Qt GUI) and `services/src/airunner_services/api/` (local FastAPI daemon), mapped to a stable ID, a real code anchor, a hardware/network classification, and a deterministic-or-manual verification scenario.

All paths below were verified to exist in this checkout at the time of writing (`test -f` / `find`); none are inferred or guessed.

## Architecture note

This is a two-process application, not a single GUI codebase:

- `src/airunner/components/**` — the PySide6/Qt desktop GUI. Talks to the daemon over a local loopback HTTP/WebSocket API (see [S01](https://github.com/Capsize-Games/airunner/issues/2087)/[S02](https://github.com/Capsize-Games/airunner/issues/2092)).
- `services/src/airunner_services/**` — a separate daemon process that owns GPU/model inference, RAG, tool execution and persistence. Most "real" capability logic (and most existing automated coverage) lives here, not in the GUI widgets, which are thin clients.

A feature is only "local" end-to-end if both its GUI entry point and its daemon-side implementation are local; where the two differ, the row states both.

## Classification legend

- **local** — runs fully offline once any required model files are already downloaded; no network access needed for a specific invocation.
- **gpu** — code path performs materially worse, degrades, or does not run at all without an NVIDIA GPU/adequate VRAM. Everything under this label still requires the Linux/NVIDIA ≥16GB baseline defined in [#2083](https://github.com/Capsize-Games/airunner/issues/2083).
- **network** — the feature cannot function without an outbound network call (either always, or once a user opts into a specific provider/source).

## Coverage legend

- **auto** — an existing automated test file is cited.
- **manual** — no automated coverage exists; verification is a named manual scenario, generally satisfied by one of the Q01–Q08 hardware-validation tickets.
- **gap** — no automated coverage and no existing ticket currently covers manual verification of this specific behavior; see "Proposed follow-up tickets" at the end.

---

## 1. Art generation & canvas

| ID | Feature | Code anchor | Class | Coverage | Scenario / linked ticket |
|---|---|---|---|---|---|
| ART-01 | txt2img / img2img / inpaint / outpaint generation modes | `src/airunner/components/art/gui/widgets/stablediffusion/stablediffusion_generator_form.py`; `src/airunner/components/art/managers/stablediffusion/image_request.py` (GUI) → `services/src/airunner_services/art/managers/stablediffusion/*.py` (daemon inference) | gpu | manual | [Q02](https://github.com/Capsize-Games/airunner/issues/2122) validates all four modes on the target GPU |
| ART-02 | Canvas editing (layers, drawing, undo/redo history) | `src/airunner/components/art/gui/widgets/canvas/canvas_widget.py`; `canvas/mixins/canvas_layer_mixin.py`, `canvas_history_mixin.py` | local | auto | `src/airunner/components/art/gui/widgets/canvas/mixins/tests/test_canvas_history_fresh_canvas.py` |
| ART-03 | Canvas-triggered generation (draw → generate) | `canvas/mixins/canvas_generation_mixin.py` | gpu | manual | [Q02](https://github.com/Capsize-Games/airunner/issues/2122) |
| ART-04 | Image filters (blur, dither, halftone, pixel art, color balance, etc.) | `src/airunner/components/art/filters/*.py` (11 filter implementations); UI: `gui/widgets/filter_parameter_widget.py`, `gui/windows/filter_window/filter_window.py` | local | gap | No filter-specific test found; not explicitly named by any Q0x ticket. Proposed: FOLLOWUP-1. |
| ART-05 | LoRA loading and application | `src/airunner/components/art/api/lora_services.py` (`LORA_UPDATE_SIGNAL`/`LORA_DELETE_SIGNAL`) | gpu | manual | [Q02](https://github.com/Capsize-Games/airunner/issues/2122) |
| ART-06 | VRAM-aware generation settings / budget calculator | `src/airunner/components/art/gui/widgets/stablediffusion/stable_diffusion_settings_widget.py`, `vram_calculator.py` | gpu | auto | `src/airunner/components/art/gui/widgets/stablediffusion/tests/test_loading_watchdog.py` |
| ART-07 | Background removal (RMBG) | GUI stub: `src/airunner/components/art/managers/rmbg/__init__.py`; real implementation: `services/src/airunner_services/art/managers/rmbg/rmbg_model_manager.py` | gpu | gap | No test found on either side. Proposed: FOLLOWUP-1. |
| ART-08 | Z-Image model bundle generation | `src/airunner/components/art/managers/zimage/zimage_bundle_requirements.py` (bundle validation, direct `torch`/`safetensors` use); `services/src/airunner_services/art/pipelines/z_image/pipeline_z_image.py` | gpu | auto | `services/tests/test_zimage_model_dir_config.py` |
| ART-09 | Daemon-side SD/diffusion inference (backing ART-01/03/05) | `services/src/airunner_services/art/managers/stablediffusion/*.py` | gpu | auto | `services/src/airunner_services/tests/functional/test_art_service_runtime_smoke.py`, `test_art_service_runtime_conditioned.py` |
| ART-10 | NSFW/output safety screening for generated images | `services/src/airunner_services/art/utils/nsfw_checker.py` | local | manual | [S09](https://github.com/Capsize-Games/airunner/issues/2102)/[S11](https://github.com/Capsize-Games/airunner/issues/2115) own gating correctness; [Q08](https://github.com/Capsize-Games/airunner/issues/2123) reviews efficacy |
| ART-11 | Batch image generation returning every requested image | `services/src/airunner_services/api/routes/art*.py`, `art_job_runner.py` | gpu | manual | Known defect, already tracked: [D03](https://github.com/Capsize-Games/airunner/issues/2090) |
| ART-12 | Art request resource-limit validation | `services/src/airunner_services/api/routes/art*.py` | local | manual | Already tracked: [D04](https://github.com/Capsize-Games/airunner/issues/2098) |

## 2. Chat / LLM

| ID | Feature | Code anchor | Class | Coverage | Scenario / linked ticket |
|---|---|---|---|---|---|
| CHAT-01 | Chat prompt input & attachments | `src/airunner/components/chat/gui/widgets/chat_prompt_widget.py`, `chat_attachment_pill_widget.py`, `image_attachment_widget.py` | local | gap | No GUI-level test found. Proposed: FOLLOWUP-2. |
| CHAT-02 | Conversation rendering & history (daemon-backed) | `src/airunner/components/chat/gui/widgets/conversation_widget.py`; `src/airunner/components/conversations/conversation_history_manager.py`, `conversation_record.py` | local | gap | No GUI-level test found. Proposed: FOLLOWUP-2. |
| CHAT-03 | Local GGUF/llama.cpp chat inference | `services/src/airunner_services/llm/adapters/chat_gguf*.py` | local | auto | `services/tests/test_llm_functional.py` |
| CHAT-04 | Remote LLM providers (e.g. OpenRouter) | `src/airunner/components/settings/gui/widgets/openrouter_settings/openrouter_settings_widget.py`; daemon routes to provider only if configured | network | manual | [Q06](https://github.com/Capsize-Games/airunner/issues/2128) validates offline-vs-remote behavior and consent |
| CHAT-05 | Tool-calling orchestration | `services/src/airunner_services/llm/managers/mixins/tool_execution_mixin.py`, `tool_classification_mixin.py`, `tool_management_mixin.py` | local | auto | `services/tests/eval/test_agent_tool_eval.py`, `test_agent_tool_selection_eval.py` |
| CHAT-06 | Streaming chat responses (WebSocket) | `services/src/airunner_services/api/routes/llm_stream_routes.py` | local | auto | `services/tests/test_release_s01.py` (auth); no functional streaming-content test found — gap for content correctness, proposed FOLLOWUP-3 |
| CHAT-07 | Chatbot persona / prompt-template settings | `src/airunner/components/llm/gui/widgets/bot_preferences.py`, `prompt_templates_widget.py`, `llm_settings_widget.py` | local | gap | No test found. Proposed: FOLLOWUP-2. |
| CHAT-08 | Custom LLM tool authoring (GUI CRUD) | `src/airunner/components/llm/gui/widgets/llm_tool_editor_widget.py`, `llm_tool_manager_widget.py` | local | gap | No test found. Proposed: FOLLOWUP-2. |
| CHAT-09 | Output text/derived-speech safety gate before publication | daemon routes above + safety adapters (see [S12](https://github.com/Capsize-Games/airunner/issues/2110)) | local | manual | [S12](https://github.com/Capsize-Games/airunner/issues/2110) implements; [Q08](https://github.com/Capsize-Games/airunner/issues/2123) reviews efficacy |
| CHAT-10 | Manual end-to-end chatbot/memory/tool validation on target GPU | all of the above together | gpu | manual | Already tracked: [Q03](https://github.com/Capsize-Games/airunner/issues/2149) |

## 3. Voice (STT / TTS)

| ID | Feature | Code anchor | Class | Coverage | Scenario / linked ticket |
|---|---|---|---|---|---|
| VOICE-01 | Microphone capture | `src/airunner/components/stt/workers/audio_capture_worker.py` | local (needs mic hardware) | gap | No automated coverage possible without hardware; not explicitly named by a Q0x ticket beyond general voice validation. Covered by [Q04](https://github.com/Capsize-Games/airunner/issues/2148). |
| VOICE-02 | Speech-to-text (whisper.cpp sidecar) | `services/src/airunner_services/runtimes/sidecar_stt_client.py`, `sidecar_stt_launcher.py`, `whisper_cpp_runtime_settings.py`; API: `services/src/airunner_services/api/routes/stt.py` | local | auto | `services/tests/test_stt_transcribe_functional.py` |
| VOICE-03 | Text-to-speech: eSpeak engine | `services/src/airunner_services/runtimes/espeak_model_manager.py` | local | auto | `services/tests/test_tts_synthesize_functional.py`, `test_tts_runtime_load.py` |
| VOICE-04 | Text-to-speech: OpenVoice engine | `services/src/airunner_services/runtimes/openvoice_model_manager.py` (uses `torch.cuda.is_available()`, GPU when present) | gpu (CPU fallback exists) | auto | `services/tests/test_tts_runtime_load.py` |
| VOICE-05 | Voice/engine preference UI | `src/airunner/components/tts/gui/widgets/voice_settings_widget.py`, `espeak_preferences_widget.py`, `open_voice_preferences_widget.py` | local | gap | No test found. Proposed: FOLLOWUP-2. |
| VOICE-06 | Full voice conversation loop (STT → LLM → TTS) | `services/tests/test_llm_tts_functional.py`, `test_gui_llm_tts_functional.py`, `test_gui_stt_llm_tts_functional.py` (these ARE the existing tests, confirming this composed path already has coverage) | gpu | auto | Also manually validated end-to-end by [Q04](https://github.com/Capsize-Games/airunner/issues/2148) |

## 4. Documents / embeddings / RAG

| ID | Feature | Code anchor | Class | Coverage | Scenario / linked ticket |
|---|---|---|---|---|---|
| RAG-01 | Document import | `src/airunner/components/documents/document_import.py`, `workers/document_worker.py` | local | gap | No test found. Proposed: FOLLOWUP-2. |
| RAG-02 | Kiwix ZIM library browsing | `src/airunner/components/documents/kiwix_api.py` (calls `https://browse.library.kiwix.org/...`); `gui/widgets/kiwix_widget.py`; local scan: `data/scan_zimfiles.py` | network (browsing catalog only; downloaded ZIM files are read locally) | gap | No test found. Proposed: FOLLOWUP-1. |
| RAG-03 | Local knowledge base (daily markdown facts) | `src/airunner/components/knowledge/knowledge_base.py` (`~/.local/share/airunner/text/knowledge/YYYY-MM-DD.md`) | local | gap | No test found. Proposed: FOLLOWUP-2. |
| RAG-04 | Vector index / embeddings | `services/src/airunner_services/llm/managers/agent/vector_index.py`, `retriever.py` | local (unless a remote embedding provider is explicitly configured) | auto | `services/tests/eval/test_agent_document_eval.py` |
| RAG-05 | RAG indexing / search / tool integration | `services/src/airunner_services/llm/managers/mixins/rag_indexing_mixin.py`, `rag_document_mixin.py`, `rag_search_mixin.py`; `services/src/airunner_services/llm/tools/rag_tools.py` | local | auto | `services/tests/eval/test_agent_document_eval.py` |
| RAG-06 | Embedding index identity (model/revision/dimension pinning) | see [B04](https://github.com/Capsize-Games/airunner/issues/2129) (not yet implemented) | local | manual | Already tracked: [B04](https://github.com/Capsize-Games/airunner/issues/2129); [Q05](https://github.com/Capsize-Games/airunner/issues/2136) validates |

## 5. Downloads / model management

| ID | Feature | Code anchor | Class | Coverage | Scenario / linked ticket |
|---|---|---|---|---|---|
| DL-01 | HuggingFace model downloads | `services/src/airunner_services/downloads/huggingface_download_worker.py`; GUI: `src/airunner/components/downloader/gui/windows/download_wizard/*.py` | network | auto | `services/tests/test_download_security.py`, `test_model_load_security.py` |
| DL-02 | CivitAI model search/download | `services/src/airunner_services/downloads/service.py` (`fetch_civitai_model_info`, `search_civitai_models`); API: `services/src/airunner_services/api/routes/downloads.py` | network | auto | `services/tests/test_download_security.py` |
| DL-03 | First-run setup wizard (model selection) | `src/airunner/components/downloader/gui/windows/setup_wizard/**` | network | gap | No test found. Proposed: FOLLOWUP-2. |
| DL-04 | Hardware/VRAM profiling | `src/airunner/components/model_management/hardware_profiler.py` (queries daemon, no local `torch` dependency); `memory_allocator.py` (`device="cuda:0"` default) | gpu | auto | `src/airunner/components/model_management/tests/test_model_state_parity.py`, `test_model_status_widget.py` |
| DL-05 | Model lifecycle / quantization / memory tracking | `src/airunner/components/model_management/{canvas_memory_tracker,model_registry,model_resource_manager,quantization_strategy}.py` | gpu | auto | `test_model_state_parity.py`, `test_model_status_widget.py` |
| DL-06 | Pinning downloads to immutable revisions/digests | see [D01](https://github.com/Capsize-Games/airunner/issues/2097) (not yet implemented) | network | manual | Already tracked: [D01](https://github.com/Capsize-Games/airunner/issues/2097) |
| DL-07 | Resuming interrupted downloads to the same artifact | see [D02](https://github.com/Capsize-Games/airunner/issues/2104) (not yet implemented) | network | manual | Already tracked: [D02](https://github.com/Capsize-Games/airunner/issues/2104) |

## 6. Settings / data persistence

| ID | Feature | Code anchor | Class | Coverage | Scenario / linked ticket |
|---|---|---|---|---|---|
| SET-01 | Daemon connection / service settings | `src/airunner/components/settings/gui/widgets/service_settings_widget.py` | local | auto | `src/airunner/components/settings/gui/widgets/tests/test_service_settings_lna_warning.py` |
| SET-02 | HuggingFace / OpenRouter credential settings | `huggingface_settings/huggingface_settings_widget.py`, `openrouter_settings/openrouter_settings_widget.py` | network | gap | No test found. Proposed: FOLLOWUP-2. |
| SET-03 | Privacy / memory / export / sound / theme preference panels | `privacy_settings/`, `memory_preferences/`, `export_preferences/`, `sound_settings/`, `theme_settings/` widgets | local | gap | No test found; privacy-specific behavior also covered by [Q06](https://github.com/Capsize-Games/airunner/issues/2128) |
| SET-04 | Model selection/management dialogs | `model_manager_dialog.py`, `model_selector_widget.py` | local (network only if triggering a download) | gap | No test found. Proposed: FOLLOWUP-2. |
| SET-05 | Local SQLite/DB persistence (conversations, settings, jobs) | `services/src/airunner_services/api/routes/persistence*.py` | local | gap | No dedicated test file found under `services/tests/`. Proposed: FOLLOWUP-3. |
| SET-06 | Bootstrap/seed data (models, fonts, voices) | `src/airunner/components/data/bootstrap_service.py`, `settings/data/bootstrap/font_settings_bootstrap_data.py` | local | gap | No test found. Proposed: FOLLOWUP-2. |
| SET-07 | Multi-tenant DB schema selection | `src/airunner/components/data/tenant.py`; `services/src/airunner_services/data/tenant.py` | local | auto | Exercised indirectly by `services/tests/test_loopback_auth.py` (tenant-key header gating) |

## 7. Server / remote / API modes

| ID | Feature | Code anchor | Class | Coverage | Scenario / linked ticket |
|---|---|---|---|---|---|
| SRV-01 | Local embedded HTTP server (static/Jinja2 web UI) | `src/airunner/components/server/local_http_server.py` (`MultiDirectoryCORSRequestHandler`; explicitly restricts CORS to loopback origins) | local | auto | `src/airunner/components/server/tests/test_local_http_server_cors.py` |
| SRV-02 | Daemon FastAPI app (HTTP API-key/loopback-token auth) | `services/src/airunner_services/api/server.py`, `loopback_token.py` | local | auto | `services/tests/test_loopback_auth.py` |
| SRV-03 | Daemon LLM WebSocket auth | `services/src/airunner_services/api/routes/llm_stream_routes.py` | local | auto | Fixed and tested by [S01](https://github.com/Capsize-Games/airunner/issues/2087) (`services/tests/test_release_s01.py`) |
| SRV-04 | WebSocket message-size/rate bounding | see [S02](https://github.com/Capsize-Games/airunner/issues/2092) (not yet implemented) | local | manual | Already tracked: [S02](https://github.com/Capsize-Games/airunner/issues/2092) |
| SRV-05 | Daemon lifecycle / health / VRAM reporting | `services/src/airunner_services/api/routes/daemon*.py` | local | auto | `services/tests/test_gui_daemon_client_runtime_actions.py` |
| SRV-06 | OpenAI/Ollama-compatible legacy API surface | `services/src/airunner_services/api/routes/legacy_openai_compat.py`, `legacy_ollama_compat.py`, `legacy_native_compat.py` | local (compat shim; network only if a remote provider is configured behind it) | auto | `services/tests/test_legacy_api_surface.py` |
| SRV-07 | Geolocation endpoint | `services/src/airunner_services/api/routes/geolocation.py` | network (unverified beyond file existence — low confidence) | gap | No test found; behavior not independently confirmed. Proposed: FOLLOWUP-1 (verify whether this is reachable/used at all before writing a scenario for it). |
| SRV-08 | Offline egress policy enforcement | see [O01](https://github.com/Capsize-Games/airunner/issues/2091)/[O02](https://github.com/Capsize-Games/airunner/issues/2108) (not yet implemented) | local | manual | Already tracked: O01/O02; [Q06](https://github.com/Capsize-Games/airunner/issues/2128) validates |

## 8. Tools (LLM/user-invokable)

| ID | Feature | Code anchor | Class | Coverage | Scenario / linked ticket |
|---|---|---|---|---|---|
| TOOL-01 | Tool registration system | `services/src/airunner_services/llm/core/tool_registry.py`, `tool_schema.py` | local | auto | `services/tests/eval/test_agent_tool_eval.py`, `test_agent_tool_selection_eval.py` |
| TOOL-02 | Sandboxed code execution tool | `services/src/airunner_services/llm/core/code_sandbox.py` | local | auto | `services/tests/test_tool_sandbox_security.py`; process/OS isolation itself is tracked separately: [T01](https://github.com/Capsize-Games/airunner/issues/2142)/[T02](https://github.com/Capsize-Games/airunner/issues/2145) |
| TOOL-03 | Web search tool (DuckDuckGo) | `services/src/airunner_services/tools/web_tools.py`, `search_providers/duckduckgo_provider.py` | network | gap | No dedicated test found (only indirect eval coverage, not confirmed). Proposed: FOLLOWUP-1. |
| TOOL-04 | arXiv search tool | `services/src/airunner_services/tools/search_providers/arxiv_provider.py` | network | gap | No test found. Proposed: FOLLOWUP-1. |
| TOOL-05 | Web crawling tool (Scrapy) | `services/src/airunner_services/tools/scrapy/llm_crawler_controller.py`; `tools/web_content_extractor.py` | network | gap | No test found. Proposed: FOLLOWUP-1. |
| TOOL-06 | Local filesystem access tool | `services/src/airunner_services/llm/managers/tools/file_tools.py` | local | gap | Security-sensitive (arbitrary local file access from an LLM tool) with no dedicated test found. Proposed: FOLLOWUP-1 (higher priority — recommend triage before release). |
| TOOL-07 | Author / QA / math / mood / reasoning / RAG / system tool sets | `services/src/airunner_services/llm/tools/{author,qa,math,mood,reasoning,research_*,system}_tools.py` | local (mixed; a few sub-tools call network providers) | auto | `services/tests/eval/test_agent_tool_eval.py`, `test_agent_mood_eval.py` |
| TOOL-08 | Custom-tool process isolation | not yet implemented | local | manual | Already tracked: [T01](https://github.com/Capsize-Games/airunner/issues/2142)/[T02](https://github.com/Capsize-Games/airunner/issues/2145) |

## Companion module (B01–B16) status

Confirmed **absent** in this checkout: no `companion/` directory exists anywhere in the repo, and `services/src/airunner_services/llm/` has no such subdirectory (its actual children are `adapters`, `agents`, `api`, `config`, `core`, `data`, `langgraph`, `long_running`, `managers`, `tools`, `utils`, `workers`). This matches the parent spec: the companion module is a planned deliverable of [B01](https://github.com/Capsize-Games/airunner/issues/2118), not existing code, so it is intentionally absent from this matrix rather than a coverage gap.

## Proposed follow-up tickets

These are **proposals only** — no GitHub issues have been filed for them in this session, per the one-issue-per-session/no-automatic-follow-on-implementation constraint. Filing them is a small owner decision, not an implementation task.

1. **FOLLOWUP-1 (recommend before release): triage untested network/security-sensitive tool and data-source paths.** Covers ART-04/ART-07 (filters, RMBG — no test, but low risk), RAG-02 (Kiwix), SRV-07 (geolocation — confirm it's even reachable), TOOL-03/04/05 (web search, arXiv, crawler), and especially **TOOL-06 (local filesystem access tool)**, which has no dedicated regression test despite being a direct arbitrary-local-file-access surface exposed to an LLM. Recommend scoping TOOL-06 as its own higher-priority ticket rather than bundling it with the lower-risk items above.
2. **FOLLOWUP-2 (docs/manual, lower urgency): GUI-widget test gap.** A large fraction of `src/airunner/components/{chat,llm,tts,documents,knowledge,downloader,settings}/**` widgets have zero automated coverage (chat input/attachments, persona/prompt-template settings, tool-authoring UI, voice preference UI, document import, knowledge base, setup wizard, credential settings, model dialogs, bootstrap data). Existing Q0x manual-validation tickets (Q02–Q06) exercise many of these indirectly through end-to-end scenarios, but none names GUI-widget-level regression coverage explicitly as an acceptance condition. Recommend either accepting Q0x manual coverage as sufficient for v1, or filing one tracking ticket for GUI test-coverage debt post-v1.
3. **FOLLOWUP-3 (small, concrete): no dedicated persistence-layer test file** under `services/tests/` for `services/src/airunner_services/api/routes/persistence*.py`, and no functional test asserting *content* correctness of the LLM WebSocket stream (only its auth, per S01/`test_release_s01.py`). Recommend a single small ticket once B02 (session/turn persistence) lands, since that will need equivalent coverage anyway.

## Validation

This document was produced by reading and cross-referencing source under `src/airunner/components/` and `services/src/airunner_services/api/` in this checkout; every cited path was confirmed with `test -f` (or `find` for directories) before being listed. No runtime launch, model load, or source/test changes were made as part of this ticket.
