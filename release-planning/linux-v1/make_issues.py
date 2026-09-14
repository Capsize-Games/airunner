"""Generate bounded, owner-requested issue specifications; no remote writes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
items = []
D = 'Capsize-Games/airunner'
W = 'Capsize-Games/airunnerweb'

def add(key, title, files, change, acceptance, deps='', kind='code', repo=D):
    items.append(dict(key=key, title=f'[Linux v1][{key}] {title}', repo=repo,
                      files=files.split('|'), change=change,
                      acceptance=acceptance.split('|'), deps=deps.split(), kind=kind))

add('R01','Inventory every Desktop launch capability and its acceptance scenario',
    'src/airunner/components/|services/src/airunner_services/api/|release-planning/linux-v1/feature-matrix.md (new)',
    'Produce a feature matrix from registered UI actions, routes and tools. Cover art modes/canvas/filters/LoRA, chat, voice, embeddings/RAG, downloads/settings, tools and remote modes. Map each to code and a deterministic or manual scenario. Record missing issue coverage; do not remove or silently defer any feature.',
    'Each discoverable feature has a stable ID and code anchor.|Distinguish local, network-optional and unsupported hardware paths.|Unmapped defects receive proposed one-behavior follow-up tickets; no runtime/source edits.',kind='docs')
add('R02','Record the Linux/NVIDIA model and hardware validation manifest',
    'native/runtime_sidecars/runtime_pins.env|shared/airunner_common/package_metadata.py|release-planning/linux-v1/hardware-models.md (new)',
    'Specify the proposed Ubuntu 24.04 x86_64 baseline, NVIDIA 16 GB minimum, actual model revisions/formats, required GPU compute capabilities, driver/runtime versions, RAM/disk and memory scheduling assumptions. Use upstream model/license evidence; do not download models or claim measured compatibility.',
    'Manifest includes all modalities and policy models, marking undecided choices explicitly.|Separate VRAM capacity from GPU-generation compatibility and shared-memory scheduling.|Provide manual 16 GB and higher-VRAM test matrix with pending result fields.', 'R01',kind='docs')
add('R03','Correct stale small-agent paths and testing guidance',
    '.github/copilot-instructions.md|scripts/build_ui.py|scripts/run_tests.py|release-planning/linux-v1/AGENT-HANDOFF.md',
    'Correct documented paths that no longer exist (UI builder, quality/coverage helpers, URL/path hygiene helpers). Preserve existing privacy, generated-UI and manual-runtime boundaries. Clarify that tests specifically requested by an assigned release issue are in its scope; do not give blanket authority to launch the app or run real inference. Document one issue per session and preserve unrelated edits.',
    'Every concrete command/path in the revised guidance exists or is explicitly an example/new deliverable.|No invented path replacement: locate it or remove the obsolete command with a factual explanation.|Docs-only diff; no app launch, model load, dependency installation, or test changes.',kind='docs')
add('W01','Freeze UwUchat bot behavior and provenance for the Desktop port',
    'projects/uwuchat/server/ai_pipeline.py|server/src/airunner_services/llm/|projects/uwuchat/server/tests/|wiki/Desktop-Bot-Port-Reference.md (new)',
    'Create a commit-pinned inventory of bot capabilities and reusable functions/tests: dialogue, context compression, facts, narrative/session/turn recall, mood, background cognition, routing and all bot tools. Identify cloud/DB/Celery/auth dependencies and local modifications separately. Map each capability to a Desktop port issue or proposed follow-up. Do not copy private prompts or production conversations.',
    'Neutral reference fixtures/test IDs cover each behavior, with deterministic vs real-model evaluation distinguished.|Document copyright/license provenance and uncommitted-source decisions for owner review.|No web behavior changes or live/cloud inference; do not revive stale llm_routing.py.',kind='docs',repo=W)
add('W02','Require an explicit isolated database for UwUchat tests',
    'projects/uwuchat/server/tests/conftest.py|projects/uwuchat/server/tests/test_test_database_guard.py (new)',
    'Remove the fallback from test database configuration to the application database. Require an explicit disposable test target before schema setup; reject a target equivalent to the original application URL, including normalized aliases where detectable. Missing required CI test DB must fail rather than silently skip.',
    'Fake setup function is never called for missing, malformed or same-as-application targets.|An explicitly distinct test target reaches setup.|No connection to the live DB; test URL parsing and guard behavior with doubles.',kind='webcode',repo=W)
add('W03','Reconcile web agent documentation with actual dialogue routing',
    'AGENTS.md|wiki/Architecture.md|projects/uwuchat/server/dialogue_routing.py|projects/uwuchat/server/ai_pipeline.py|projects/uwuchat/server/embedding_provider.py',
    'Correct cloud-only and Electron-present claims from inspected code. Explain deployment-specific dialogue overrides, cloud embedding dependency, and absence of the current Electron shell. Preserve production defaults; describe local routing without testing it. Avoid publishing infrastructure identifiers or secrets.',
    'Guide names the real routing authority and project/framework boundary.|No runtime/config changes and no claim of full offline support.|References resolve and match the pinned reference inventory.', 'W01',kind='docs',repo=W)
add('S01','Authenticate Desktop LLM WebSocket before accepting it',
    'services/src/airunner_services/api/server.py|services/src/airunner_services/api/routes/llm_stream_routes.py|services/src/airunner_services/api/loopback_token.py',
    'Apply the existing HTTP API-key/loopback-token policy explicitly to the LLM WebSocket before accept or runtime resolution. Reject unapproved browser Origins using an explicit allowlist (not wildcard substring matching); permit authenticated native clients without Origin. Trace Desktop socket callers and update authentication if required; if more than five production files are needed, propose a split.',
    'An API key configured for HTTP also blocks unauthenticated sockets.|Missing/wrong loopback credentials and unrelated Origins never resolve the runtime.|Valid native and configured browser clients work with doubles; health remains unchanged.', 'R03')
add('S02','Bound WebSocket message sizes and per-client request rates',
    'services/src/airunner_services/api/routes/llm_stream_routes.py|services/src/airunner_services/api/routes/llm_contracts.py',
    'Add bounded message/prompt/output-token validation and per-authenticated-principal request admission before model work. Rate state must not reset merely on socket reconnect. Provide deterministic error codes without user content; document chosen conservative configurable bounds.',
    'Oversized and malformed payloads are rejected before inference.|Reconnect cannot reset the limiter; one client cannot exhaust unbounded queue state.|Allowed traffic and disconnect cleanup remain correct under fake clock/runtime.', 'S01')
add('S03','Define and compile a versioned private policy-data artifact',
    'scripts/build_policy_terms.py|services/src/airunner_services/content_safety/policy_data.py|services/tests/test_build_policy_terms.py',
    'Define a documented non-executable artifact schema with normalization/schema versions, sorted fixed-size digests, length/count bounds and integrity metadata. Extend the private-input compiler deterministically. Keep production plaintext/digests out of commits and logs; public fixtures use neutral invented tokens only. Signature verification is a separate issue.',
    'Identical neutral input yields identical bytes; malformed schema/counts are rejected.|Compiler never echoes source lines and rejects an empty release artifact.|Artifact has a declared compatibility version and bounded parser.', 'R03')
add('S04','Verify policy signatures with a bundled public key',
    'services/src/airunner_services/content_safety/policy_data.py|services/src/airunner_services/content_safety/policy_signature.py (new)',
    'Verify a detached signature over exact policy artifact bytes using an established cryptographic library and a pinned public-key/key-ID trust store. Private signing keys never ship. Reject wrong key, truncation, schema mismatch and modified metadata before loading hashes. Do not implement custom cryptography or online key lookup.',
    'Synthetic signed fixture loads fully offline.|Tampered body/metadata, wrong key and missing signature fail verification.|No private key or production data in code/test assets.', 'S03')
add('S05','Deny image generation when mandatory policy data is unavailable',
    'services/src/airunner_services/content_safety/matcher.py|services/src/airunner_services/content_safety_gate.py|services/tests/test_content_safety.py|services/tests/test_content_safety_gate.py',
    'Replace the current allow-on-empty behavior with explicit unavailable/invalid policy denial for affected generation. Keep adult-content preference independent. Surface a generic actionable installation/policy error, without logging input. Do not use a production environment override to bypass mandatory checks.',
    'Missing, empty and invalid data produce denial before jobs/model load.|Valid neutral policy allows safe fixtures and rejects matching fixtures.|Existing tests asserting fail-open are updated to the requirement; non-generation app use still works.', 'S04')
add('S06','Provision signed policy data only in trusted release CI',
    '.github/workflows/pypi-dispatch.yml|scripts/build_policy_terms.py|release-planning/linux-v1/policy-provisioning.md (new)',
    'Add a trusted release-stage recipe to retrieve an already compiled/signed private policy artifact, verify its expected digest/signature, and stage it into the bundle. Use protected release credentials, pinned actions and a clean job; never execute untrusted PR code with those credentials. Public CI uses synthetic data only. Production policy/key provisioning is owner-operated.',
    'Release mode fails for absent, invalid or synthetic-only policy data.|Source list/key cannot enter logs, caches, debug dumps or uploaded general artifacts.|A secret-free fixture workflow validates the wiring; no real secrets requested in issue comments.', 'S04')
add('S07','Select offline contextual and image safety evaluators with evidence',
    'services/src/airunner_services/content_safety/semantic.py|services/src/airunner_services/art/utils/nsfw_checker.py|release-planning/linux-v1/safety-evaluation.md (new)',
    'Prepare a bounded evaluator comparison with model/license availability, local performance, input/output coverage, uncertainty semantics and documented limitations. Define owner/specialist-approved effectiveness and latency thresholds. Adult NSFW detection or age estimation alone is not sufficient. No abusive imagery may be obtained, generated or published; sensitive evaluation stays with qualified authorized parties.',
    'Select or explicitly mark unavailable each required evaluator; unsupported efficacy remains a release blocker.|Document safe neutral test fixtures plus specialist evaluation procedure/results needed.|No model efficacy claim based only on synthetic unit tests; no implementation in this issue.', 'R02',kind='review')
add('S08','Implement the selected offline contextual safety adapter',
    'services/src/airunner_services/content_safety/semantic.py|services/src/airunner_services/content_safety_gate.py',
    'Implement the evaluator and thresholds selected in S07 behind allow/deny/unavailable results. Make the required contextual check local-only, bounded and fail-closed on timeout/error/ambiguity. Use cancellable/isolated work rather than unbounded abandoned daemon threads. Preserve matcher denials.',
    'Doubles cover allowed/blocked/unavailable/timeout and bounded worker count.|No remote provider or implicit model download on inference.|Private evaluation is still a separate gate, not satisfied by these adapter tests.', 'S05 S07')
add('S09','Implement the selected offline image-safety adapter',
    'services/src/airunner_services/art/utils/nsfw_checker.py|services/src/airunner_services/content_safety/image_verdict.py (new)',
    'Add the selected mandatory image evaluator independently of optional adult-content filtering. Validate batch cardinality and map missing models/errors/uncertainty to withheld results. Preserve originals privately in memory only until verdict; no automatic export here.',
    'Synthetic images/doubles cover all verdicts and mismatched batch lengths.|Disabling optional adult filtering never disables mandatory evaluator.|No remote calls, unchecked fallback or production/sensitive fixtures.', 'S07 S04')
add('S10','Screen imported image inputs before generation and editing',
    'services/src/airunner_services/api/routes/art_generation_start_routes.py|services/src/airunner_services/workers/sd_worker.py|services/src/airunner_services/api/routes/art_contracts.py',
    'Invoke mandatory input-image checking on final resolved img2img/inpaint/outpaint/reference-image requests before model dispatch. Validate size/type and use shared path policy. Trace GUI and API paths so a text-only gate is not mistaken for input-image coverage.',
    'Blocked/unavailable verdict prevents inference for each image-bearing entry point.|No unchecked preview/export is introduced by decoding.|Synthetic files and runtime doubles only; record uncovered paths as split follow-ups.', 'S08 S09')
add('S11','Withhold art outputs until mandatory checks succeed',
    'services/src/airunner_services/art/managers/stablediffusion/mixins/sd_image_generation_mixin.py|services/src/airunner_services/api/routes/art_job_response.py|services/src/airunner_services/workers/sd_worker.py',
    'Apply the mandatory image verdict before GUI signals, previews, auto-export, thumbnails or API results in both direct and sidecar paths. Trace each result sink and ensure all batch members have verdicts. Keep optional NSFW preferences independent; never surface unchecked pixels on error.',
    'Blocked/unavailable batches never reach fake export/signal/API sinks.|Allowed batches preserve ordering, metadata and all images.|Include cancellation and backend-error paths; oversized scope must split by sink rather than omit coverage.', 'S09 S10')
add('S12','Gate chatbot text and derived speech before publication',
    'services/src/airunner_services/llm/managers/mixins/generation_stream_support.py|services/src/airunner_services/workers/tts_generator_worker.py|services/src/airunner_services/content_safety_gate.py',
    'Define and implement a local publication gate for chatbot output and text handed to speech. Buffer any material requiring whole-output review; emit status separately until allowed. Apply mandatory policy to tool-originated generation too. Preserve cancellation and distinguish final denied response from a model failure.',
    'No unreviewed text/audio reaches fake stream or TTS sinks.|Timeout/unavailable evaluator denies affected publication without killing unrelated UI.|Allowed response and voice paths preserve ordering; ordinary adult material is not blanket-blocked.', 'S08')
add('P01','Move Qt resource compilation out of installed-app startup',
    'src/airunner/launcher.py|scripts/build_ui.py|setup.py|MANIFEST.in',
    'Remove the installed runtime dependency on scripts/build_ui.py and the in-package UI marker. Compile required Qt resources during build and verify them before packaging. Runtime must work from an unrelated current directory and read-only installation without writing into site-packages.',
    'A build/resource inspection demonstrates generated resources are present.|A launcher test double observes no build subprocess or package write.|Missing resources produce an actionable error, not a swallowed build attempt.', 'R03')
add('P02','Resolve and lock the Linux NVIDIA runtime dependency profile',
    'setup.py|services/setup.py|native/setup.py|shared/airunner_common/package_metadata.py|package/',
    'Define a coherent complete NVIDIA desktop profile, including torch needed by GUI startup. Resolve exact mutually compatible wheels in an isolated build environment and save a reproducible constraints/lock artifact with provenance/hashes. Correct the CUDA-index/CPU-fallback documentation mismatch; CPU support is not a release target.',
    'Fresh isolated installation resolves and pip check passes with captured evidence.|All imported base-startup requirements are declared.|No updates to the developer venv and no blanket upgrade of unrelated packages.', 'R02 R03')
add('P03','Unify pinned native runtime manifests and release artifacts',
    'scripts/build_runtime_sidecars.sh|native/runtime_sidecars/runtime_pins.env|native/runtime_sidecars/README.md|.github/workflows/native-runtime-sidecars.yml',
    'Use one authoritative native-source manifest and synchronize documentation. Build the selected Linux NVIDIA profile and include required shared libraries and origin/license information. Remove duplicate release responsibility without dropping developer workflows; Windows artifacts are deferred for this release.',
    'Bundle manifest records exact upstream commits, target architecture and CUDA options.|CI artifact contents match paths used by runtime discovery.|No reliance on developer absolute paths or undocumented system binaries.', 'R02')
add('P04','Compare representative Qt packaging builds and select one recipe',
    'packaging/|setup.py|native/runtime_sidecars/README.md|release-planning/linux-v1/packaging-decision.md (new)',
    'In an isolated build environment, compare directory-mode PyInstaller and pyside6-deploy/Nuitka for this app entry point, resources and one runtime with doubles. Record build result, missing imports/plugins, size and startup constraints. Select one supported recipe; do not convert to Electron or run real models.',
    'A reproducible command and manifest exist for the chosen candidate.|Choice is based on actual artifact inspection, with GUI/hardware launch pending owner verification.|Failure is reported with a bounded next issue, not an unsupported working-installer claim.', 'P01 P02 P03',kind='experiment')
add('P05','Assemble the complete Linux application directory bundle',
    'packaging/|scripts/|setup.py|services/setup.py',
    'Extend the selected P04 recipe to include all runtime profiles, required Qt plugins/WebEngine helpers if used, translations, legal files, migrations, shared resources and synthetic test policy. Keep models outside the application unless explicitly selected for distribution. Add artifact inspection instead of relying on editable imports.',
    'Bundle import/resource inspection succeeds without repository PYTHONPATH.|Manifest covers every feature dependency from R01.|No secrets, developer tooling, caches or customer data are included.', 'P04 R01')
add('P06','Add a user-level Linux installer with safe install paths',
    'packaging/linux/|packaging/linux/airunner.desktop',
    'Package P05 into a versioned user-level installation with launcher/menu entry, no customer Python/Docker requirement and no root by default. Support paths with spaces and an unrelated working directory. Separate installation from user data; validate free disk space before extraction.',
    'Filesystem fixture install is repeatable and cannot overwrite unrelated paths.|Launcher resolves the installed interpreter/resources and desktop icon.|Owner manual install scenario is documented; no system install performed by agent.', 'P05')
add('P07','Make upgrades transactional with backup and recovery',
    'packaging/linux/|services/src/airunner_services/database/setup_database.py|services/src/airunner_services/database/',
    'Stage and verify a new version before atomic activation. Back up local database before migration and retain the previous installation. Define compatibility-aware recovery; never blindly downgrade a migrated database. Use synthetic historical fixtures only.',
    'Interrupted extraction/activation and failed migration leave a recoverable installation/data state.|Successful upgrade preserves settings, conversations, media/model paths and policy.|Focused fixture tests demonstrate recovery; no real customer database touched.', 'P06')
add('P08','Implement uninstall with explicit optional user-data removal',
    'packaging/linux/',
    'Remove the installed app/menu entries while retaining user data by default. A separate explicit deletion action must list data scope and validate ownership/path boundaries, including custom paths. Never recursively delete an arbitrary user-selected model/media directory.',
    'Default uninstall preserves models/media/database.|Explicit managed-data deletion removes only owned fixture files.|Document backup/custom-path exclusions and align later privacy wording.', 'P06')
add('P09','Report hardware, disk and runtime prerequisites before model work',
    'src/airunner/components/downloader/gui/windows/setup_wizard/|services/src/airunner_services/model_management/hardware_profiler.py',
    'Add actionable capability diagnostics for the R02 Linux/NVIDIA profile: GPU generation/VRAM, driver compatibility, system RAM, free disk, missing runtime/policy/model artifacts. Do not hide unsupported requirements behind generic tracebacks or start downloads automatically.',
    'Fixture profiles produce precise supported/unsupported/unknown results.|Missing dependencies are reported before generation, without GPU loading in tests.|User can still inspect settings/help and repair installation.', 'R02 P05')
add('P10','Verify downloaded application updates before activation',
    'packaging/linux/|services/src/airunner_services/downloads/',
    'Provide an explicit opt-in update check and verified download/install handoff using signed manifests and artifact digests. No update check is required for offline startup. Handle network failure/cancel without altering the current install; apply P07 activation only after verification.',
    'Wrong signatures/digests and incomplete downloads cannot activate.|Network denied/failed/cancelled leaves the current version usable.|Synthetic transport and installer fixtures only.', 'P07 S04')
add('P11','Produce dependency/model license inventory and source manifest',
    'THIRD_PARTY_NOTICES.md|LICENSE|packaging/|release-planning/linux-v1/licenses.md (new)',
    'Generate an inventory of application dependencies, vendored code, native binaries, models, detector/policy data and redistributed assets. Record version/revision, license, attribution/source obligations and whether bundled or downloaded. Flag unresolved provenance including Desktop GPL and web MIT ancestry for counsel/owner decision.',
    'Every selected bundle/model artifact has a license/provenance row.|Required notices/source offer material is present; unresolved rights remain explicit release blockers.|No claim that commercial use or private policy data is automatically permitted.', 'R02 P05 W01',kind='review')
add('D01','Pin supported model downloads to immutable revisions and digests',
    'services/src/airunner_services/downloads/huggingface_download_worker.py|services/src/airunner_services/downloads/',
    'Extend supported-model metadata with revision and checksum identity; stop using resolve/main for those curated downloads. Verify the digest before declaring completion, even if file size matches. Preserve explicit custom-model behavior without falsely calling it a verified curated model.',
    'Same-sized corrupt files fail verification and are not loaded.|Pinned URL and identity survive restart and retry.|Use small neutral HTTP/file fixtures, not model downloads.', 'R02 R03')
add('D02','Resume only the same model artifact and promote it safely',
    'services/src/airunner_services/downloads/huggingface_download_worker.py',
    'Associate temporary downloads with immutable artifact identity. Validate Range/Content-Range and restart when server identity differs or 200 ignores Range. Unknown expected size must never make an arbitrary temp file complete. Verify then atomically promote without deleting a valid prior file first.',
    'Interrupted/restarted downloads reconstruct exact fixture bytes.|Changed identity, zero-size metadata, invalid 206 and 416 are handled safely.|Cancellation retains only resumable partial state and existing valid destination.', 'D01')
add('D03','Return every image from a requested art batch',
    'services/src/airunner_services/api/routes/art_job_response.py|services/src/airunner_services/api/routes/art_generation_job_routes.py|src/airunner/daemon_client/art_mixin.py',
    'Replace first-image-only API job handling with a versioned/list result containing every checked batch image. Preserve compatibility for existing single-image callers while updating the Desktop consumer. Avoid duplicating auto-export or regenerating images.',
    'Three fake returned images reach the caller in order.|Single-image callers retain documented compatibility.|Batch/error/cancellation metadata are preserved.', 'R03')
add('D04','Validate art request resource limits before job creation',
    'services/src/airunner_services/api/routes/art_contracts.py|services/src/airunner_services/api/routes/art_generation_start_routes.py',
    'Bound dimensions/pixel count, steps, batch size, prompt length, strength and decoded input-image size before tracker/model side effects. Derive configurable limits from the supported model profile; reject nonfinite/invalid values. Do not silently shrink user requests.',
    'Negative, zero, excessive, nonfinite and malformed values are rejected early.|Valid boundary cases pass and downstream runtime errors remain separate.|No GPU/network used.', 'R02 R03')
add('O01','Define and enforce explicit offline egress policy',
    'shared/airunner_common/settings.py|services/src/airunner_services/|src/airunner/url_safety.py',
    'Create one offline/online policy interface with loopback IPC allowed and external network denied by default. Inventory outbound clients and add a first integration at the central fetch/provider boundary. Break additional call-site wiring into follow-up tickets if more than five production files; enumerate every uncovered egress path rather than declaring full coverage.',
    'Core policy tests deny external requests in offline mode and allow authenticated local IPC.|Explicit online consent is required to change mode; no silent cloud fallback.|An egress coverage ledger links each caller to a completed/follow-up issue.', 'R01 R03')
add('O02','Apply offline policy to model downloads and online tools',
    'services/src/airunner_services/downloads/|services/src/airunner_services/llm/tools/|src/airunner/url_safety.py',
    'Use O01 to gate user-triggered downloads, search/weather/research and other network tools. Represent network-required tool capability honestly while leaving local tools available. Coordinate an explicit download mode for first-run models; switching back offline must stop further external requests.',
    'Fake transports show zero external attempts when offline.|Online tool invocation gives an actionable unavailable result instead of hanging or falling back.|Per-caller coverage ledger updated; split by caller family if needed.', 'O01 D02')
add('O03','Make diagnostics private and user-controlled',
    'services/src/airunner_services/database/secret_store.py|src/airunner/crash_handler.py|shared/airunner_common/logging_utils.py',
    'Audit the diagnostics path and add a local-only sanitized support export for IDs, versions, capabilities and failure codes. Exclude prompts, files, paths, transcripts, tokens, raw tool results and policy material. Verify credential file permissions and no implicit upload.',
    'Neutral sensitive canaries are absent from exported diagnostics.|User can inspect the export before sharing; offline export makes no network attempt.|Tests use a temporary data directory and never inspect real credentials.', 'R03 O01')
add('B01','Define Desktop companion contracts and port mapping',
    'services/src/airunner_services/llm/companion/ (new)|services/src/airunner_services/runtimes/contracts.py|release-planning/linux-v1/companion-contracts.md (new)',
    'Define typed interfaces for inference, scoped memory repository, bounded scheduler and tool dispatch. Define stable turn/session/chatbot IDs, streaming events, cancellations, errors and context budgets. Map every W01 capability to a narrow implementation slice. Keep Desktop runtime/SQLite ownership; no web package import or SaaS dependency.',
    'Contract example traces one turn, tool call, persistence and background follow-up.|Every upstream capability has a mapped issue or explicit proposed split.|Contracts import without Qt, torch, web package, Postgres or Redis; reviewer confirms boundaries before downstream implementation.', 'W01 R01 P11',kind='design')
add('B02','Persist chatbot sessions and completed turn records',
    'services/src/airunner_services/database/models/|services/src/airunner_services/database/alembic/versions/|services/src/airunner_services/llm/companion/',
    'Add local session/turn records and a repository following B01, scoped by chatbot. Implement the characterized inactivity-gap rotation and transactional completed-turn persistence. Preserve existing Conversation IDs/transcripts; no destructive migration.',
    'Fake-clock boundary cases create the expected sessions.|Repeated completion event is idempotent and different bots never share turns.|Fresh and historical SQLite fixtures migrate without losing existing records.', 'B01')
add('B03','Add scoped fact and narrative-memory repositories',
    'services/src/airunner_services/database/models/|services/src/airunner_services/database/alembic/versions/|services/src/airunner_services/llm/companion/',
    'Add structured facts with subject/source/timestamps/retraction and one evolving narrative per chatbot. Implement repository CRUD with provenance and transaction boundaries. Keep vector indexing out of this issue and retain old file-based knowledge until migrated.',
    'Create/update/retract/reopen maintains provenance and bot isolation.|Duplicate event IDs do not duplicate facts.|Additive migration works on a populated synthetic old database.', 'B02')
add('B04','Implement local embeddings with explicit index identity',
    'services/src/airunner_services/llm/companion/|services/src/airunner_services/runtimes/',
    'Adapt the selected local embedding runtime to B01. Persist embedding model revision/dimensions and index identity. Reject mixed embedding spaces; schedule explicit rebuild on change. No OpenRouter call, Redis dependency, or implicit download.',
    'Deterministic fake embeddings support query/index round trip.|Dimension/revision mismatch is detected and cannot yield misleading search.|Offline tests verify no external transport call.', 'B03 R02 O01')
add('B05','Port scoped fact and conversation recall tools',
    'services/src/airunner_services/llm/companion/|services/src/airunner_services/llm/tools/',
    'Implement characterized record/recall/update/retract and past-turn recall through B01 repositories and B04 retrieval. Keep tool schemas stable and attach source IDs. Enforce chatbot scope in the repository, not only in the prompt.',
    'Neutral fixtures retrieve expected facts/turns and preserve citations.|Cross-bot queries cannot return another bot data.|Existing tools remain available through a documented compatibility adapter.', 'B04')
add('B06','Add durable bounded background jobs for companion work',
    'services/src/airunner_services/llm/companion/|services/src/airunner_services/database/models/',
    'Implement local persisted job records with idempotency keys, bounded queue/concurrency, leases/retries and restart recovery for post-turn work. No Celery/Redis. Inject clock/executor; GPU work must be requested through runtime arbitration rather than loading models here.',
    'Duplicate enqueue and process restart do not duplicate effects.|Queue limits and cancellation are deterministic.|A crashed leased job can recover with capped retries.', 'B02 B01')
add('B07','Port post-turn fact extraction and deduplication',
    'services/src/airunner_services/llm/companion/|services/src/airunner_services/llm/tools/',
    'Port W01 extraction behavior using B06 jobs, B03 facts and B05 lookup/dedup tools. Validate model output schemas and reject unsupported invented facts according to the reference rules. Use synthetic conversations and fake inference responses.',
    'Neutral fixtures cover new facts, duplicate facts, corrections and retractions.|Malformed response or job retry cannot corrupt/duplicate memory.|Every inference task routes through the local provider interface with a bounded budget.', 'B05 B06')
add('B08','Port episodic session summaries',
    'services/src/airunner_services/llm/companion/',
    'Schedule a characterized summary when a session becomes inactive. Use completed turns only, preserve source session IDs and mood snapshot where applicable, and write atomically. Handle unavailable inference as retryable work without blocking active chat.',
    'Fake-clock session closure yields one summary with correct source scope.|Retry/restart does not duplicate or overwrite newer session data.|Incomplete turns and another bot history never enter the prompt.', 'B06 B02')
add('B09','Port narrative-memory updates and rolling compression',
    'services/src/airunner_services/llm/companion/',
    'Apply characterized narrative blending to reviewed episodic summaries, with strict size/token bounds, source tracking and memory-injection sanitation. Keep recent dialogue and durable memories distinct; include rolling context compression without deleting original history.',
    'Neutral reference fixtures preserve established facts and reject instruction-like memory payloads.|Concurrent/stale jobs cannot overwrite a newer narrative.|Context remains within explicit budgets and original turns remain retrievable.', 'B08 B03')
add('B10','Port prompt composition and mood context',
    'services/src/airunner_services/llm/companion/|services/src/airunner_services/llm/managers/mixins/system_prompt_mood.py',
    'Compose character identity, user context, scoped facts, recent episodes, narrative, time and mood in the reference order through B01. Apply context budgets deterministically and treat retrieved/tool text as untrusted data. Do not copy cloud cache controls or account/economy behavior.',
    'Neutral fixtures match intended section ordering and optional omissions.|Changing one chatbot cannot affect another prompt.|Oversized memory truncates by a documented policy without dropping mandatory safety instructions.', 'B09 B05')
add('B11','Adapt companion tool routing to Desktop registered tools',
    'services/src/airunner_services/llm/companion/|services/src/airunner_services/llm/tool_manager.py|services/src/airunner_services/llm/managers/mixins/tool_execution_mixin.py',
    'Port characterized tool classification/execution behavior using existing Desktop registration and B01 contracts. Validate schemas, bound tool-call rounds/time, propagate cancellation, preserve tool result provenance, and honor offline/capability policy. Do not create an independent tool runtime.',
    'Fake tool scenarios cover selection, invalid args, retry, failure, loop limit and cancellation.|Network tools cannot execute offline; local tools remain available.|Tool output cannot become a system instruction or bypass mandatory generation checks.', 'B10 O02 S12')
add('B12','Route every companion pipeline through local inference by default',
    'services/src/airunner_services/llm/companion/|services/src/airunner_services/runtimes/registry.py',
    'Wire dialogue, extraction, summaries, mood and other inventoried background tasks to Desktop runtime providers. Explicit online OpenRouter is optional; denied/unavailable local inference never silently becomes cloud inference. Coordinate model load/unload priorities with other modalities.',
    'Fake routing matrix covers every pipeline from W01.|Offline has zero external inference/embedding requests.|Cancellation and exhausted VRAM/resource admission yield actionable results instead of loading duplicate models.', 'B11 B07 B09 O01')
add('B13','Connect Qt chat events to the companion service',
    'src/airunner/daemon_client/llm_mixin.py|src/airunner/components/chat/gui/widgets/chat_prompt_widget.py|src/airunner/components/chat/gui/widgets/conversation_widget.py',
    'Adapt existing Qt chat send/stream/cancel/reopen behavior to B01 events and B12 service. Keep the UI, conversation selection, tools and voice integration. Extract only the small event adapter needed; do not rewrite the 2800-line widget.',
    'Adapter contract tests preserve message ordering, IDs and cancellation.|Switching/reopening conversations restores correct bot/session state.|Provide manual Qt steps; do not launch GUI in ordinary agent validation.', 'B12 S01')
add('B14','Migrate existing Desktop knowledge without losing user data',
    'services/src/airunner_services/knowledge.py|services/src/airunner_services/database/alembic/versions/|services/src/airunner_services/llm/companion/',
    'Import existing file knowledge/conversations into the new scoped repositories using stable source identities and a migration ledger. Preserve original files and IDs, back up before changes, and support interrupted/resumed migration. Do not infer another bot ownership silently.',
    'Historical neutral fixtures migrate idempotently and retain original files.|Unknown ownership creates an explicit resolution item, not cross-bot assignment.|Failure/recovery leaves the old data usable.', 'B03 P07')
add('B15','Port remaining mood and proactive cognition as bounded jobs',
    'services/src/airunner_services/llm/companion/',
    'From W01, map mood updates, curiosity/journal and other remaining bot cognition to B06 jobs and B12 providers. This ticket is a mapping/design slice: file separate bounded per-behavior implementation issues for anything not already covered, with exact upstream anchors and fixtures. Do not equate completing the mapping with implementing these capabilities.',
    'Every inventoried bot capability has an executable issue or recorded acceptance evidence.|No capability is silently dropped because it was absent from the initial port list.|New issues use the same bounded template and do not include private content.', 'W01 B12',kind='design')
add('B16','Define and run the companion regression comparison procedure',
    'services/tests/eval/|release-planning/linux-v1/companion-evaluation.md (new)',
    'Assemble neutral reference scenarios for conversation quality, fact correction, delayed recall, mood, tools, long context and local-vs-optional-cloud behavior. Separate deterministic fixture checks from owner-operated 16 GB real-model trials. Record model revisions, thresholds, latency and factuality; do not invent passing scores.',
    'Scenario IDs map back to W01 capabilities and R01 matrix.|Deterministic checks pass; real-model results remain pending until actually performed.|Any deficit creates one-behavior issues and blocks claimed quality parity.', 'B13 B14 B15 R02',kind='manual')
add('T01','Isolate execution of custom code tools from the application process',
    'services/src/airunner_services/llm/tool_manager.py|services/src/airunner_services/llm/core/code_sandbox.py|release-planning/linux-v1/tool-isolation.md (new)',
    'Design the Linux custom-tool execution boundary: worker process, explicit filesystem/network capabilities, resource limits, cancellation and failure protocol. Restricted builtins and safety_validated alone are not isolation. Inventory existing execution/computer-control paths; split implementation by boundary. Do not disable launch features to avoid the problem.',
    'Threat model distinguishes trusted operator code from model/untrusted code.|Proposed worker contract has neutral abuse/failure tests and exact implementation tickets.|No claims of sandbox security or working implementation from this design artifact.', 'R01 B11',kind='design')
add('T02','Implement the selected custom-tool worker boundary',
    'services/src/airunner_services/llm/core/|services/src/airunner_services/llm/tool_manager.py',
    'Implement the reviewed T01 worker and the single ToolManager dispatch adapter. Enforce documented capabilities and process lifetime with structured IPC and bounded outputs. Preserve tools through the adapter; separate additional execution paths into linked tickets if required.',
    'Neutral fixture worker cannot access resources outside its granted boundary.|Timeout/cancel terminates work and returns a bounded result.|No parent-process exec for untrusted code; independent security review remains required.', 'T01')
add('L01','Inventory actual privacy data flows and retention promises',
    'src/airunner/components/downloader/gui/windows/setup_wizard/user_agreement/privacy_policy.md|shared/airunner_common/|release-planning/linux-v1/privacy-facts.md (new)',
    'Map local data, model downloads, optional providers/search, remote mode, updates, diagnostics, purchases/support and any hosted services to recipients, purpose, settings, storage, deletion and retention evidence. Distinguish code facts from business facts needing owner input. Do not claim all data is local for online features.',
    'Every existing policy promise maps to evidence or an unresolved question.|Identify data not deleted by uninstall, custom paths/backups and sensitive voice/memory data.|No logs/secrets/customer records inspected or published.', 'R01 O01 P08',kind='docs')
add('L02','Draft a factual Desktop privacy policy for worldwide sales',
    'release-planning/linux-v1/legal/privacy-policy-draft.md (new)|src/airunner/components/downloader/gui/windows/setup_wizard/user_agreement/privacy_policy.md',
    'Write a replacement draft grounded in L01 for Capsize LLC, Colorado: offline core, optional external processing/recipients, purchase/support data, retention/deletion, user choices, contacts and territory-specific rights where applicable. Separate unverified facts with an owner checklist. Do not invent legal bases, provider retention, encryption guarantees or compliance certification.',
    'Draft corrects the unsupported no-server and uninstall-deletes-all assertions.|Network-only tools are not promised offline; optional consent matches implementation.|Marked draft and qualified legal review required before replacing live notices.', 'L01',kind='legal')
add('L03','Draft GPL-consistent purchase, support and acceptable-use terms',
    'release-planning/linux-v1/legal/desktop-terms-draft.md (new)|src/airunner/components/downloader/gui/windows/setup_wizard/user_agreement/user_agreement_text.md|LICENSE',
    'Separate GPL software rights from official installer purchase, free released updates, support scope, trademarks and optional hosted services. Draft age/content notices, mandatory prohibited-content policy, AI/model limitations, consumer-rights and refunds treatment for worldwide sales. Review private policy-data/source obligations. Remove contradictory revocable/nontransferable GPL license grant language.',
    'Draft does not impose additional restrictions on GPL rights or promise perpetual support.|No blanket no-refunds/waiver of mandatory local rights or unsupported automatic reporting claim.|Unresolved legal/business decisions listed for counsel/owner; not published as effective terms.', 'P11 L01',kind='legal')
add('L04','Verify UwUchat hosted privacy and terms claims against operations',
    'projects/uwuchat/client/components/legal/PrivacyPolicy.tsx|projects/uwuchat/client/components/legal/TermsOfService.tsx|wiki/Hosted-Legal-Claims-Audit.md (new)',
    'Audit provider-retention statements, deletion windows/backups, analytics/cookies, encryption, billing data, integrations, moderation and territorial claims against code and operator evidence. Produce correction drafts separately from Desktop; do not modify production-facing text without reviewed facts. Reference existing web moderation issue #112 rather than duplicate it.',
    'Claims ledger distinguishes observed implementation from operator/legal verification.|Unverified retention/compliance assertions are removed or qualified in the proposed draft.|No production data access or legal certification; no changes to billing/auth scope of #210/#212.', 'W01',kind='legal',repo=W)
add('L05','Record owner and legal review decisions for the release documents',
    'release-planning/linux-v1/legal/',
    'Owner/qualified counsel review the prepared drafts and artifact licenses for worldwide sales, sensitive-content handling, consumer remedies, source obligations and policy-data treatment. Confirm contact details, support/refund terms, retention and territories. This is a human acceptance gate, not a request for a coding model to certify legality.',
    'Record document versions, reviewer, decisions and remaining blockers.|No unresolved required business facts or legal blockers are marked approved.|Do not publish notices or sign contracts from this issue.', 'L02 L03 L04',kind='owner')
add('L06','Install approved legal notices and versioned consent records',
    'src/airunner/components/application/gui/dialogs/legal_document_dialog.py|src/airunner/components/application/gui/dialogs/first_run_agreement_dialog.py|src/airunner/components/downloader/gui/windows/setup_wizard/user_agreement/',
    'Install only the approved L05 texts into packaged resources. Align About/setup/age notices and record accepted document versions locally. Distinguish software license acknowledgment from optional data-processing consent; do not require online account acceptance for offline use.',
    'Packaged artifact contains exactly the approved document digests/version.|Updated notices remain readable offline and optional consent can be withdrawn.|Manual Qt scenario provided; no generated UI files edited directly.', 'L05 P05')
add('C01','Gate release candidates on required checks and artifact completeness',
    '.github/workflows/eval-tests.yml|.github/workflows/pypi-dispatch.yml|packaging/',
    'Create one Linux candidate pipeline using the selected recipe and required deterministic checks, including safety/auth/download/data migration tests. Assemble native artifacts and signed policy in the same manifest. Candidate creation must not publish to PyPI/itch by itself. Remove continue-on-error for required release checks only.',
    'Any required failed/skipped/missing check blocks candidate promotion.|All expected bundle components are verified and published as candidate artifacts.|Public PR pipeline remains secret-free; no production deployment performed.', 'P05 P03 S06 R03')
add('C02','Record baseline test failures as small actionable defects',
    '.github/workflows/eval-tests.yml|services/tests/|release-planning/linux-v1/test-baseline.md (new)',
    'Collect the declared Desktop deterministic suite in an isolated environment. Triage existing collection/failure/skip reasons without fixing unrelated issues or changing assertions. File one-behavior follow-ups with minimal reproductions; classify real-model/manual tests explicitly.',
    'Baseline includes exact commands/environment and every exclusion rationale.|No required scenario disappears via blanket skip or test filtering.|Do not claim current full-suite health from the prior 86 selected passing tests.', 'R03 P02',kind='experiment')
add('W04','Triage currently excluded web regression tests without hiding failures',
    '.github/workflows/eval-tests.yml|server/tests/|server/src/airunner_services/tests/',
    'Inspect the explicit excluded tests and recorded baseline debt. Reproduce only deterministic relevant cases in an isolated test environment, then file minimal one-behavior fixes or link existing issues. Preserve production configurations and existing auth/billing extraction work.',
    'Report current evidence rather than copying old failure counts as current.|Every exclusion has an issue and reason; no blanket ignore additions.|No live DB, cloud inference or production deployment.', 'W02',kind='experiment',repo=W)

# Separate owner-operated acceptance slices keep hardware tests from becoming vague coding epics.
manuals = [
('Q01','Validate installation, restart, upgrade and uninstall','P07 P08 P09 L06 C01','Clean supported Linux host; install offline-ready candidate, launch from unrelated directory, restart, upgrade populated fixture data, interrupt an upgrade, recover, and uninstall with/without explicit managed-data removal.'),
('Q02','Validate all art and canvas workflows','S11 D03 D04 P09 C01','Run every inventoried art/canvas mode, LoRA/embeddings, batch, filter, import/export and editing scenario with approved neutral images; cover cancellation, OOM/recovery and save/reopen.'),
('Q03','Validate local chatbot, memory and tools on 16 GB NVIDIA','B16 T02 S12 C01','Run characterized conversation, tool selection/execution, fact correction, delayed recall, narrative/session behavior, long context and all remaining bot capability scenarios; compare quality/latency to recorded thresholds.'),
('Q04','Validate TTS, STT and full voice conversations','B13 S12 C01','Exercise every supported TTS/STT backend, voice selection/cloning with authorized neutral samples, microphone permissions, device switching, interruption and STT-to-chat-to-TTS ordering.'),
('Q05','Validate local embeddings, documents and RAG','B14 B04 C01','Import every supported document format, index/reindex, retrieve grounded answers with source IDs, cancel imports, restart and delete data; verify bot isolation and embedding-model change handling.'),
('Q06','Validate offline privacy and optional remote operation','O02 O03 S02 P10 C01','With external network denied, run core features after downloads and inspect egress attempts. Separately verify explicit online tools/provider consent, authenticated remote HTTP/WebSocket access and return to offline mode.'),
('Q07','Validate shared GPU lifecycle across all modalities','B12 P09 C01','On the approved 16 GB and higher-VRAM NVIDIA matrix switch art/chat/STT/TTS/embedding workloads, schedule memory jobs, cancel, idle-unload and recover from OOM without lost user state or orphan processes.'),
('Q08','Review mandatory-safety efficacy and publication-path coverage','S10 S11 S12 S07 C01','Owner/qualified specialist reviews chosen evaluators against approved private procedure and all GUI/API/tool/preview/export failure paths. Use neutral public fixtures; do not ask coding agents to acquire or generate abusive material.'),
]
for key,title,deps,scenario in manuals:
    add(key,title,'release-planning/linux-v1/feature-matrix.md|release-planning/linux-v1/acceptance/ (new)',
        scenario+' This is an operator/manual acceptance issue. An ordinary small-model agent prepares the script/results template only; real GUI/model work requires the operator to run it.',
        'Record candidate digest, hardware/driver/model revisions and exact scenario IDs/results.|Untested/skipped/failed is not pass; file one-behavior defects with sanitized evidence.|Cover all R01 entries in this family and link any missing capability work before closing.',deps,kind='manual')
add('C03','Prepare accurate itch.io listing, sales terms and channel clearance',
    'release-planning/linux-v1/store-listing-draft.md (new)|release-planning/linux-v1/legal/',
    'Draft the Linux-only listing from measured capabilities and approved legal text: NVIDIA 16 GB hardware matrix, required downloads/storage, offline/optional-network distinction, price proposal, free updates/support scope and existing-buyer treatment. Owner verifies worldwide/payment-provider eligibility for the actual product; do not publish or change prices here.',
    'No old RTX 3060/untested distro claims or unsupported perfect-safety claims.|Links to source/license, approved notices and support/refund process are accurate.|Owner records price and channel decisions; unresolved eligibility is a release blocker.', 'L05 Q01 Q02 Q03 Q04 Q05 Q06 Q07 Q08',kind='owner')
add('C04','Promote the reviewed candidate and verify public downloads',
    '.github/workflows/pypi-dispatch.yml|release-planning/linux-v1/release-checklist.md (new)',
    'Owner-operated publication gate after every required acceptance and legal/channel decision. Promote the exact tested signed candidate, attach checksums/source/notices and release notes, publish the approved listing, verify clean public download and record rollback/withdrawal process. No automatic release merely because coding issues are closed.',
    'All required tracker gates pass with evidence on the same candidate digest.|Download/install is verified without developer environment; rollback contacts/process recorded.|Owner explicitly approves the concrete release before publishing or changing storefront.', 'C03 Q01 Q02 Q03 Q04 Q05 Q06 Q07 Q08 C02 W04',kind='owner')

# Ensure each reference resolves inside this plan and ordering is executable.
keys={i['key'] for i in items}
assert len(keys)==len(items)
for i in items:
    assert set(i['deps']) <= keys, (i['key'],i['deps'])
(ROOT/'issues.json').write_text(json.dumps(items,indent=2)+'\n')
print(f'{len(items)} bounded issue specifications generated')
