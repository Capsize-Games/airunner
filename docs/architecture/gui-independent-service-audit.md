# GUI-Independent Service Audit

## Direct Answer

No. AIRunner does not currently match the target architecture where the
PySide6 GUI is only a shell over a fully GUI-independent orchestration
service.

Today the codebase already has meaningful daemon and runtime foundations,
but the higher-level orchestration layer is split:

- LLM, art, TTS, and STT inference can run headless through the daemon,
  runtime registry, and sidecar or local-fallback clients.
- LLM orchestration, tool execution, and conversation loading still depend
  on the GUI-era worker and signal graph.
- Some settings are already correctly stored in QSettings, but several
  GUI-specific or client-specific preferences still live in SQLite.

## What Exists Today

### Headless and service-capable foundations

- The runtime registry and sidecar clients are explicit in
  [src/airunner/runtimes/bootstrap.py](src/airunner/runtimes/bootstrap.py),
  [src/airunner/runtimes/sidecar_llm_client.py](src/airunner/runtimes/sidecar_llm_client.py),
  [src/airunner/runtimes/sidecar_stt_client.py](src/airunner/runtimes/sidecar_stt_client.py),
  [src/airunner/runtimes/sidecar_tts_client.py](src/airunner/runtimes/sidecar_tts_client.py),
  and
  [src/airunner/runtimes/sidecar_art_client.py](src/airunner/runtimes/sidecar_art_client.py).
- Headless bootstrap exists in
  [src/airunner/app_mixins/headless_runtime_mixin.py](src/airunner/app_mixins/headless_runtime_mixin.py).
- The daemon and HTTP API already exist, with explicit runtime-route usage
  for art, TTS, and STT in
  [src/airunner/api/routes/art.py](src/airunner/api/routes/art.py#L156),
  [src/airunner/api/routes/tts.py](src/airunner/api/routes/tts.py#L83),
  and
  [src/airunner/api/routes/stt.py](src/airunner/api/routes/stt.py#L69).
- Conversations, chatbots, user data, and LLM settings are already stored
  in SQLite via SQLAlchemy models such as
  [src/airunner/components/llm/data/conversation.py](src/airunner/components/llm/data/conversation.py),
  [src/airunner/components/llm/data/chatbot.py](src/airunner/components/llm/data/chatbot.py),
  and
  [src/airunner/components/llm/data/llm_generator_settings.py](src/airunner/components/llm/data/llm_generator_settings.py).

### Current packaging direction

- The repo already targets a native launcher plus bundled Python, not a
  pure native application rewrite. That is spelled out in
  [END_USER_DISTRIBUTION.md](END_USER_DISTRIBUTION.md),
  [native/airunner_launcher/CONTRACT.md](native/airunner_launcher/CONTRACT.md),
  and
  [native/airunner_launcher/README.md](native/airunner_launcher/README.md).
- The current launcher boundary is intentionally narrow: native code boots
  Python, while Python still owns runtime clients and sidecar supervision.

## Closest Existing Foundation

These are the strongest pieces already aligned with the desired target:

1. The daemon, runtime registry, and runtime clients already define a real
   service boundary.
2. Conversations and modality configuration already persist outside the GUI.
3. Art, TTS, and STT request routing already resolve runtime clients instead
   of always calling GUI workers directly.
4. The bundle and launcher story already supports a no-system-Python product
   on Linux and Windows.

If AIRunner stops at this layer and keeps building upward, the target is
reachable without another full rewrite.

## Largest Remaining Gaps

### 1. LLM orchestration still depends on GUI-era workers

This is the main architectural blocker.

- `CoreLifecycleService` imports and instantiates `WorkerManager` from the
  GUI package in
  [src/airunner/services/lifecycle_service.py](src/airunner/services/lifecycle_service.py#L11)
  and
  [src/airunner/services/lifecycle_service.py](src/airunner/services/lifecycle_service.py#L40).
- `LLMGenerateWorker` still owns request orchestration and model-manager
  coordination in
  [src/airunner/components/llm/workers/llm_generate_worker.py](src/airunner/components/llm/workers/llm_generate_worker.py).
- `WorkflowManager` still accepts a `signal_emitter` in
  [src/airunner/components/llm/managers/workflow_manager.py](src/airunner/components/llm/managers/workflow_manager.py#L62)
  and uses signal-driven mixins.
- `ToolExecutionMixin` still emits tool-status and related workflow events
  through the global API signal path in
  [src/airunner/components/llm/managers/mixins/tool_execution_mixin.py](src/airunner/components/llm/managers/mixins/tool_execution_mixin.py).

The result is that the LLM sidecar is currently only inference. The higher
level agent, tool routing, workflow execution, and conversation loading are
still Python-side and still bound to the worker graph.

### 2. Legacy daemon LLM endpoints still reach into workers directly

- The compatibility route in
  [src/airunner/api/routes/legacy.py](src/airunner/api/routes/legacy.py#L51)
  grabs `_worker_manager` and the live LLM worker directly.

That is the opposite of the desired target, where the GUI would be a client
of a service and not the owner of the service implementation.

### 3. Conversation loading is still signal-routed into GUI widgets/workers

- `LLMAPIService.load_conversation()` emits
  `QUEUE_LOAD_CONVERSATION` in
  [src/airunner/components/llm/api/llm_services.py](src/airunner/components/llm/api/llm_services.py#L163).
- Conversation tools still call `agent.load_conversation(...)` in
  [src/airunner/components/llm/tools/conversation_tools.py](src/airunner/components/llm/tools/conversation_tools.py#L48).
- GUI conversation widgets consume that signal in
  [src/airunner/components/chat/gui/widgets/conversation_widget.py](src/airunner/components/chat/gui/widgets/conversation_widget.py#L225)
  and
  [src/airunner/components/chat/gui/widgets/chat_prompt_widget.py](src/airunner/components/chat/gui/widgets/chat_prompt_widget.py#L1489).

The persistence is service-capable, but the load-and-activate behavior is
still a GUI interaction pattern rather than a service API.

### 4. STT is still split between local faster-whisper and whisper.cpp

- The local worker path still instantiates `WhisperLocalExecutor` in
  [src/airunner/components/stt/workers/audio_processor_worker.py](src/airunner/components/stt/workers/audio_processor_worker.py#L30).
- That executor still uses `faster-whisper` in
  [src/airunner/components/stt/executors/whisper_local_executor.py](src/airunner/components/stt/executors/whisper_local_executor.py#L125).
- The sidecar runtime path already exists through
  [src/airunner/runtimes/sidecar_stt_client.py](src/airunner/runtimes/sidecar_stt_client.py)
  and
  [src/airunner/runtimes/sidecar_stt_launcher.py](src/airunner/runtimes/sidecar_stt_launcher.py).

So the repo is not yet standardized on a single STT service boundary.

### 5. Art is only partially unified as a service

- Art generation has an explicit sidecar path in
  [src/airunner/api/routes/art.py](src/airunner/api/routes/art.py#L156).
- RMBG and safety checker still exist as in-process workers through
  [src/airunner/components/art/workers/background_removal_worker.py](src/airunner/components/art/workers/background_removal_worker.py)
  and
  [src/airunner/components/art/workers/safety_checker_worker.py](src/airunner/components/art/workers/safety_checker_worker.py).
- GUI worker ownership remains visible in
  [src/airunner/components/application/gui/windows/main/worker_manager.py](src/airunner/components/application/gui/windows/main/worker_manager.py#L120)
  and
  [src/airunner/components/application/gui/windows/main/worker_manager.py](src/airunner/components/application/gui/windows/main/worker_manager.py#L258).

That means AIRunner does not yet have a single art service boundary that
owns diffusion, safety checking, and background removal together.

## Storage Audit

### What is already correctly client-side in QSettings

This boundary is mostly right today.

- Window geometry and fullscreen state are already in QSettings through
  [src/airunner/components/application/gui/windows/main/main_window.py](src/airunner/components/application/gui/windows/main/main_window.py#L1403)
  and
  [src/airunner/components/application/gui/windows/main/mixins/settings_property_mixin.py](src/airunner/components/application/gui/windows/main/mixins/settings_property_mixin.py#L71).
- GUI-only prompt-container and widget state already use QSettings in
  [src/airunner/components/art/gui/widgets/stablediffusion/stablediffusion_generator_form.py](src/airunner/components/art/gui/widgets/stablediffusion/stablediffusion_generator_form.py#L862)
  and related widgets.
- The QSettings backend is already centralized under the AIRunner data root in
  [src/airunner/utils/settings/get_qsettings.py](src/airunner/utils/settings/get_qsettings.py).

### What should stay in the service database

These settings are service-owned and should remain database-backed or move to
an explicit service configuration layer, not to QSettings:

- conversations, chatbots, summaries, user data
- runtime paths in
  [src/airunner/components/settings/data/path_settings.py](src/airunner/components/settings/data/path_settings.py)
- LLM generation settings in
  [src/airunner/components/llm/data/llm_generator_settings.py](src/airunner/components/llm/data/llm_generator_settings.py)
- RAG settings in
  [src/airunner/components/llm/data/rag_settings.py](src/airunner/components/llm/data/rag_settings.py)
- service enablement and daemon bind settings in
  [src/airunner/components/settings/data/application_settings.py](src/airunner/components/settings/data/application_settings.py)
  such as `sd_enabled`, `llm_enabled`, `tts_enabled`, `stt_enabled`,
  `http_server_enabled`, `http_server_host`, and `http_server_port`

### What should move out of SQLite into QSettings or client config

These fields look GUI-specific or client-specific rather than service-owned:

- `dark_mode_enabled`, `override_system_theme`, `is_maximized`,
  `current_tool`, `current_layer_index`, and likely `generator_section` in
  [src/airunner/components/settings/data/application_settings.py](src/airunner/components/settings/data/application_settings.py)
- setup and agreement flow flags such as `run_setup_wizard`,
  `download_wizard_completed`, `stable_diffusion_agreement_checked`,
  `airunner_agreement_checked`, `user_agreement_checked`, and
  `age_agreement_checked` in the same table
- `FontSetting` in
  [src/airunner/components/settings/data/font_setting.py](src/airunner/components/settings/data/font_setting.py)
- GUI language in
  [src/airunner/components/settings/data/language_settings.py](src/airunner/components/settings/data/language_settings.py)
  for `gui_language`

These are poor fits for shared service state because different clients could
reasonably want different values.

### What needs a split rather than a simple move

Some settings are mixed and should be split into service-owned and
client-owned pieces:

- `LanguageSettings`: `gui_language` is client-side, while user-facing or
  chatbot-facing language defaults may remain service-level.
- `SoundSettings` in
  [src/airunner/components/settings/data/sound_settings.py](src/airunner/components/settings/data/sound_settings.py)
  are currently global SQLite rows, but playback and recording device choice
  are often client-local concerns rather than shared modality state.
- `current_image_generator` in
  [src/airunner/components/settings/data/application_settings.py](src/airunner/components/settings/data/application_settings.py)
  currently acts like a global default. In a multi-client architecture that
  should be explicit in the request or stored as client preference.

## Packaging and Installer Audit

### Already aligned with the target

- A native launcher plus bundled Python is already the intended product shape
  in [END_USER_DISTRIBUTION.md](END_USER_DISTRIBUTION.md).
- Windows packaging already creates a standard installer and uninstaller in
  [packaging/windows/airunner.nsi](packaging/windows/airunner.nsi).
- Linux headless deployment already expects a separated bundle root and data
  root in [deployment/systemd/README.md](deployment/systemd/README.md).

### Not yet aligned with the target

- The Linux uninstall flow intentionally leaves the shared data directory in
  place, as shown in [install.sh](install.sh#L515).
- The current Windows uninstaller removes the install tree but does not yet
  explicitly remove a user data root comparable to `~/.local/share/airunner`.
- The native launcher is not yet the owner of sidecar supervision; Python
  still owns that boundary today.

## Pushback on a Full C++ Service Rewrite

The native launcher and bundled-product direction is already correct.
Rewriting the full AIRunner orchestration service in C++ right now is not the
fastest path to the architecture you want.

The current high-level LLM orchestration layer is deeply invested in Python
components such as LangGraph workflows, Python tool modules, SQLAlchemy
models, and runtime clients. Rebuilding that entire layer in C++ now would
turn one migration into two:

1. decouple orchestration from the GUI
2. rewrite the orchestration service in a new language

The better path is:

1. make the orchestration service GUI-independent while it is still Python
2. stabilize the service API and runtime boundaries
3. decide later whether any part of that service should move into native code

That preserves momentum and keeps the native launcher and installer work on
track.

## Recommended Target Architecture

The practical target should be:

- a GUI-independent AIRunner daemon that owns orchestration, storage, routing,
  and modality coordination
- inference runtimes behind explicit clients and service APIs
- PySide6 as a client shell over that service
- a native launcher and native installers that package the service, sidecars,
  GUI, and embedded Python as one product

That target is already compatible with the repo's current launcher and bundle
direction.

## Migration Plan

### Phase 1: decouple orchestration from GUI workers

Create a service-owned orchestration layer for LLM requests that does not
require `WorkerManager`.

Deliverables:

- replace `CoreLifecycleService -> WorkerManager -> LLMGenerateWorker` as the
  only daemon path
- introduce a service-level conversation request handler and tool executor
- make `WorkflowManager` depend on service abstractions instead of a Qt-era
  signal emitter

### Phase 2: make conversation operations service APIs

Add service routes for:

- list conversations
- load one conversation into service context
- stream one conversation request
- clear history, delete history, and summarize history

That should bypass GUI widgets entirely.

### Phase 3: finish STT standardization on whisper.cpp

Remove the local faster-whisper worker fallback after the caller path is fully
ported to the sidecar runtime.

Deliverables:

- worker and daemon paths both resolve the same STT service boundary
- remove `faster-whisper` from the shipping dependency profile
- delete the legacy local executor once tests cover the migrated path

### Phase 4: unify the art service boundary

Move diffusion, safety checking, and background removal behind one art
service contract.

That can still be one service with separate internal worker lanes rather than
three unrelated runtimes.

### Phase 5: split client settings from service settings

Move GUI and client-local preferences out of SQLite and into QSettings or a
future client-config layer.

Initial candidates:

- theme and appearance
- window and tab state
- setup wizard completion flags
- canvas-tool selection and other GUI interaction defaults
- client-local audio device selection

### Phase 6: consolidate public service APIs

Once orchestration is service-owned, expose the four modalities through one
coherent service surface so other clients can reuse the same agent and state.

### Phase 7: finish installer and uninstall behavior

Package goals already align with the repo direction, but the product is not
finished until install and uninstall fully manage the shared runtime tree and
data root on both Linux and Windows.

## Priority Order

If AIRunner wants the architecture described in this audit, the priority order
should be:

1. LLM orchestration decoupling
2. service-level conversation APIs
3. STT sidecar standardization
4. unified art service boundary
5. SQLite versus QSettings cleanup
6. installer and uninstall completion

That order avoids rewriting the launcher or packaging strategy prematurely and
keeps the work anchored to the seams that already exist in the repo.