# AI Runner service completion architecture

Owner direction: 2026-11-01. AI Runner provides model workers, runtimes,
and authenticated HTTP/WebSocket APIs for other applications. The retired
Qt interface and paid desktop storefront are outside this release.

## Baseline and scope

The service branch was inspected at `f953d5496`, then reconciled with
`origin/master` at `5898dad49` in merge `d9fb0c1e3`. Preserve the existing
service APIs, data, optional companion contracts, licenses and extracted
packages. Do not reintroduce the root GUI distribution or move the service
to a new repository. Consuming applications own interface flows and cognitive
policy, including mood, curiosity and proactive conversation. The service owns
model execution and generic runtime contracts. Retain existing companion
interfaces, schema history and stored data during staged retirement; see
`COMPANION.md` for the dependency and preservation boundaries.

The initial inventory contained 41 open GitHub issues.
Issues #2083, #2185, #2198, #2199, #2132, #2135 and #2150 were retired as
not planned because their target product changed. Issue #2123 was retired
after the owner made application content policy optional and removed manual
release gates. Optional-policy integration is tracked by SRV-22. These
dispositions do not establish acceptance or release readiness.

## Current release decisions

The owner deferred OpenVoice on 2026-11-01. The `linux-release` extra excludes
the TTS vendor; runtime and API guards reject OpenVoice before import, loading,
synthesis or automatic download. Historical vendor-bearing extras remain
described as unavailable profiles. Docker and installer defaults use the new
profile and reject those historical selections.

The headless eSpeak path returns WAV bytes without local playback. It uses a
bounded plain-text renderer and an explicit voice catalogue operation; see
`services/README.md` for the API selector and supported speed range. Isolated
engine and contract checks do not establish packaged installation or voice
acceptance. The `tts-python-core` release extra no longer installs pyttsx3:
only the retained legacy playback manager uses it. Legacy `llm` and
`tts-python` extras preserve that separate dependency and compatibility path.

The active release lock is ready for candidate builds; portable staging
verified all 243 inputs. Target validation remains open. The old desktop lock
is historical evidence. The selected V5
diagnostic graph installed all 243 exact reviewed wheels in a separate project
environment with kernel network denial, hash enforcement and no builds;
`uv pip check` passed. All 77 direct service requirements match the installed
metadata. Five CPU ABI/local-fixture probes and full production notice
verification (243 distributions, 1,734 files) passed. These results do not
establish full model, GPU, API or frozen-artifact acceptance. The visible
exact-pin inventory is in `DEPENDENCY_DECISIONS.md`.

The reviewed CUDA wrapper `0.3.21+capsize.3` corrects the Qwen MTP loader and
ctypes context-layout defects found in earlier candidates. Disk caching is an
explicit extra. Compiled candidate run `41545665728` and notice-completion run
`41554942120` passed. The final wheel retains all 94 original runtime payloads
and includes the wrapper, backend and JSON notices. Actual Qwen3.5-9B Q8
inference at context 32768 returned HTTP 200 on RTX 5080, with full configured
offload and 9,474 MiB process GPU memory. The exact-output assertion failed:
the offline embedded chat template did not receive the disabled-thinking
preference. Physical unload released GPU memory while `/api/ps` still reported
a loaded model. These confirmed source defects and reload acceptance remain
open. A default 300-second cold-load request timed out on model storage; the
successful inference used the validated finite 900-second setting.
Input readiness no longer blocks candidate CI. Required checks and target
acceptance must still pass; a skipped or unavailable check is not a pass.

The service Kanban project tracks these inputs, companion retirement, eSpeak
acceptance and CUDA wheel preparation as bounded follow-ups. On 2026-11-01 the
owner chose optional application content policy. It is disabled by default;
consuming applications can select `AIRUNNER_CONTENT_POLICY_MODE=enforce`.
Invalid mode values are configuration errors, and enabled policy retains its
deny/unavailable behavior. Signed policy-data verification is a separate
explicit option. Standard service artifacts require no private corpus, signing
keys, semantic judge, or image evaluator. Authentication, URL restrictions,
sandboxing, admission controls and artifact integrity remain service controls.

The next candidate versions are services 6.1.9 and native launcher 6.1.4.
The latest existing GitHub application tag is v6.1.8; older tags retained a
stale services version. New promotion checks require the annotated tag,
services metadata, event commit and candidate source SHA to agree and reject
existing asset-name collisions before upload. These versions are prepared
metadata, not published releases.

## Service boundaries

1. The transport layer authenticates all non-health HTTP requests and
   WebSockets, validates payloads, bounds admission and returns truthful
   status/error contracts. Keep the shared API-key/loopback-token policy.
   Setup is already covered by global authentication; it needs capacity
   control and accurate results, not a second invented identity system.
   Reuse the existing separate admin credential for installation actions.
2. Runtime contracts select a modality/provider/deployment explicitly.
   Workers own execution, cancellation, resource release and correlated
   terminal results. GPU work shares the existing lifecycle arbitration;
   independent callers must not load competing models without arbitration.
3. Persistence belongs to the service. Public list/query APIs remain
   paginated. Internal full reads must be deliberate and distinguishable
   from public queries. Migrations preserve user values and either support
   recovery or reject an irreversible downgrade before changing data.
4. Embeddings must come from a configured local runtime with an explicit
   model/revision/dimension identity. Random vectors and fabricated timing
   measurements are invalid responses. If a backend cannot serve a request,
   return an explicit unavailable/unsupported error.
5. Consolidate cognitive policy in consuming applications rather than adding
   a second production scheduler to this service. Extract generic embedding,
   capability, error and execution contracts from companion modules first.
   Preserve registered memory-tool compatibility and historical migrations
   until their callers and stored data have an explicit retirement path.
6. Keep application content policy optional. Test the disabled default and
   explicit enforcement separately; a configured denial or unavailable
   evaluator must not silently become an allow. Preserve explicit signature
   validation for applications that select it. Private policy contents,
   credentials, customer data and sensitive evaluation evidence never enter
   public source, issues or standard artifacts. Contract tests establish
   integration behavior, not moderation efficacy.
7. Builds consume reviewed dependencies and exact sibling/runtime pins.
   The tested source revision, artifact manifest and tag must agree. Build
   and verify candidates before promotion. GitHub publication is authorized
   by the current request; unrelated live service changes are separate.

## Phases and acceptance

| Phase | Work and existing issues | Exit evidence |
|---|---|---|
| 0: Reconcile scope | Retire obsolete plans; align contributor/service docs (#2201), preserve companion boundaries (#2144); integrate mainline; make optional static app hosting explicitly configured | Tracker reconciliation; service contract and accurate commands; no machine-specific implicit UI mount; focused merge checks |
| 1: API correctness | HTTP admission and setup terminal status (#2408); Ollama show/pull (#2415); real embedding responses; bounded TTS HTTP requests and voice listing (#2254); accurate STT loaded state; terminal LLM failures and bounded completion observation (SRV-23, #2416) | Authenticated contract tests with fake runtime boundaries, bounded request/concurrency tests, no false success or synthetic model output |
| 2: Data integrity | Safe downgrade policy (#2358), existing NULL preservation (#2363), schema drift checks (#2364), list boundaries (#2365), bootstrap/backup/document batching (#2409) | Temporary SQLite upgrade/recovery tests, preserved user values, bounded public reads and streaming ingestion |
| 3: Runtime and companion | Reconcile confirmed LLM/art/voice findings (#2405/#2406/#2407); characterize retained compatibility (#2147/#2149); retire duplicate cognitive policy in stages; diagnose CPU/CUDA scenario (#2242/#2416) | Focused security/lifecycle regressions; preserved data and compatibility; explicit caller inventory before deletion; no real-model parity claim from doubles |
| 4: Distribution | Resolve unavailable TTS distribution (#2413); service dependency/version orchestration (#2200); apt release artifact (#2251); dependency refresh evidence (#2274); Triton external toolchain and compile opt-in (SRV-24); optional-ML gate (#2399); ops cleanup (#2410); isolated crash regression (#2276) | Supported profiles resolve; pinned reviewed inputs; artifact-level daemon checks; CI uses the same source/check list; excluded tests recorded |
| 5: Code quality | Repair analyzer path and unavailable-tool handling; analyze all service/native modules; review dead imports and ranked complexity by subsystem | JSON reports with exact scope/exclusions; confirmed defects fixed; reviewed dispositions for residual advisory findings; focused tests/import checks |
| 6: Service acceptance | Installation/restart/recovery (#2139), art API (#2122), voice API (#2148), embeddings/RAG (#2136), offline/auth (#2128), GPU handoffs (#2146), optional-policy contracts (SRV-22) | Automated candidate/model/runtime checks with hashes and exact results on isolated targets; disabled-default and opt-in policy tests; pending/skipped is never pass |
| 7: Release | Service tracker (#2237/#2238), candidate promotion (#2151) | Required CI green for exact source; clean artifacts and notices; immutable tag/release; downloaded bytes match manifest |

Parallel Luna implementation uses disjoint file groups: API/runtime, data,
and quality/distribution. The coordinator reviews diffs, integrates changes,
runs combined checks and owns publication. Shared workflow/metadata edits
are serialized. Workers do not install new third-party dependencies or
start real models without the applicable provenance and capacity checks.

## LLM completion observation

SRV-25 / [#2444](https://github.com/Capsize-Games/airunner/issues/2444)
extends phase 1 and phase 6 to accurate Ollama metadata. Actual model testing
found guessed model names, quantization, sizes, digests, dates, VRAM and expiry
in list/process responses. Resolve configured and resident artifact identity
separately, use actual file facts and the active runtime profile, and preserve
the client schema with explicit unknown values. Status requests must not
download assets or synchronously hash multi-gigabyte files. The catalog's
maximum context describes capability; it does not describe the active context.
Regression and actual model/API evidence are required before release closure.

SRV-23 tracks the shared callback boundary used by legacy, Ollama and OpenAI
completion APIs. A terminal manager error must fail the request, including
after partial output. Non-streaming routes return an HTTP error; streams emit
an explicit protocol error because their HTTP headers may already be sent.
Internal loading/status messages are excluded from assistant output. Successful
tool-only completions retain their existing contract. Source change `d93e3c189`
implements this error propagation; 31 isolated API regressions passed, including
HTTP status checks for all three compatibility endpoints. No model was run.

The shared observer owns one request's callback registration, terminal
state and bounded output queue. It uses a monotonic total deadline, retaining the
existing 300-second default with a finite validated configuration override.
Timeouts, buffer exhaustion, backend failures and client disconnects clean
up that request's registration and cancel only its owned runtime operation.
The terminal event is queued before signalling completion; late callbacks are
rejected. Overflow fails explicitly rather than truncating a successful result.
Model-download completion and retries are serialized on the LLM worker, with
FIFO waiting requests and cancellation by request identity. The combined local
observer, ownership, terminal-error, Ollama client and action-parity suite passed
72 tests (four dependency deprecation warnings) in an isolated temporary home,
with model network access and GPU visibility disabled. It covers silence,
partial output then failure, late events, slow consumers and cross-request
isolation using runtime doubles. The existing Radon tool identified the worker
message handler at complexity E (34); focused control/request/result helpers
reduce it to A (3), retaining peer-checked error and waiting-status behavior.
Real Qwen Q8/32k and target lifecycle acceptance remain
in #2416 and #2146; callback doubles cannot satisfy those requirements.

## Triton distribution and optional compilation

SRV-24 preserves JIT functionality without redistributing NVIDIA tools and
headers whose grant is not established. The local Triton subset removes those
members and retains its compiler/backend code and licensed libdevice. Its
external toolchain must be staged privately from exact reviewed vendor inputs;
excluded payloads must not enter public artifacts. The packaged preflight checks
the candidate identity, required external bytes and retained libdevice without
importing Triton or executing tools. Frozen packaging must retain its metadata
and policy resource. These source contracts do not prove JIT execution.

Operators can explicitly stage the inputs with
`airunner-daemon --install-triton-toolchain`. This is the only daemon action
that downloads those inputs. Compile opt-in can discover the existing private,
versioned cache, verify its files and then configure the process environment;
explicit operator path overrides retain precedence. Startup and inference never
download missing toolchain files. Cached installation exercised all six exact
NVIDIA archives and staged 14 selected files with their notices; read-only cache
discovery returned the same paths. No vendor executable or Triton JIT ran in
that check. Focused staging, CLI, preflight, subset and compile regressions
passed 58 tests. Radon reported the preflight validator at complexity 33 before
refactoring; focused helpers reduce its highest function complexity to 12.

The existing `use_torch_compile` setting now has an explicit Stable Diffusion
operation boundary. Default inference and CORE startup do not require the
external compiler. When enabled, compilation requires CUDA and a successful
preflight; an unavailable toolchain leaves eager execution active with an
unapplied status. Lazy compiler failures may restore the same pipeline's eager
UNet; resource/model errors propagate. Pipeline ownership prevents stale wrappers
from restoring a different model. Parent regressions cover these boundaries,
but installed/frozen toolchain staging, actual compilation and model/hardware
acceptance remain open. A compiled driver object checks only the header contract.

## Audit evidence and quality treatment

The initial legacy AST scan with a relative services path inspected 771 files /
128,965 lines and reported 1,147 findings. Its absolute-path handling incorrectly
excluded the whole tree. That analyzer defect and empty-selection reporting
were fixed in `657f0b2dd`; focused quality-tool regressions passed 17 tests.
The corrected baseline reported 783 files / 130,395 lines and 1,215 findings,
with identical relative/absolute-path results. These are dated inventories,
not a claim that the current tree has the same counts or that every finding
is a confirmed defect.

The fleet analyzer inspected 973 services files / 141,108 lines, including
different scope from the legacy analyzer. It reported 4,888 advisory notes:
2,116 long lines, 1,339 long functions, 1,010 missing-hint notes, 166 long
files, 116 long classes, 104 multi-class files, 34 suppressions and three
heuristic stopgap markers. Native code has five files / 441 lines and ten
notes. These are review inputs, not 4,898 independently established bugs.
The unused-import scan produced 157 lines. Its framework/optional-import
false positives require inspection before removal.

The Radon/Xenon reporter failed because Xenon is absent in `.venv-ci`.
Emit Radon results even when Xenon is unavailable, label that state
unambiguously, and preserve actual failed-check results. Vulture is also
absent in the inspected environments; record it as unavailable until a
reviewed pinned tool environment exists. Do not install unreviewed tools
to manufacture a complete audit.

The 2026-11-02 refreshed legacy AST report inspected 802 service files /
135,415 lines and reported 1,263 advisory findings. Its native selection
inspected three files / 407 lines and reported six notes. The refreshed
Radon report inspected 996 files and identified 176 complex blocks and 529
hotspot files under its broader selection. Xenon remains explicitly
unavailable; successful report generation does not mean a Xenon pass. These
counts use different tool selections and are not a before/after defect score.
The new artifact stager's main function initially ranked F (complexity 59);
its refactor splits preflight, routes, streaming and receipts while preserving
security regressions. The current stager has no D/E/F blocks (maximum C, 17).
Remaining advisory findings require the subsystem dispositions below rather
than mechanical deletion of optional imports, migrations or compatibility code.

Review quality findings in API, persistence, workers/runtimes, LLM and
companion, art/voice, utilities and build tooling as separate work units.
Prioritize correctness and boundaries, then simplify confirmed hotspots
and public types. Preserve optional import behavior and upstream notices.
Do not impose a bulk formatting rewrite or silently mark legacy debt as
passed. Residual advisory findings need recorded dispositions and linked
work; new or changed code receives focused checks.

The per-revision data recovery dispositions are recorded in
`MIGRATION_RECOVERY.md`. The historical conversation-pointer migration rejects
non-NULL values before upgrade mutation because converting a conversation ID
to a chatbot ID would lose information. Its NULL and absent-column paths retain
the supported upgrade behavior. Already-discarded values cannot be recovered by
editing a migration that has run.

## Verification and release constraints

The first merge check ran in `.venv-ci` and failed collection because
`airunner_common` was absent. The unchanged selection in the existing
`.venv` passed 19 tests. Art/data and voice regressions failed under the
incomplete CI environment, then passed unchanged in the existing `venv`:
60 and 68 tests respectively. These runs used isolated data paths and no
real model inference. They establish only the checked behavior.

Keep CPU-fast deterministic contracts separate from CUDA/model acceptance.
Do not tune global timeouts to hide an unmeasured 9B CPU capacity failure.
Inspect current GPU/process/service state before requesting shared hardware.
Run private isolated acceptance without taking over the owner's display.

Release outputs include the service source commit, versions and lock
digests, wheel/sdist/bundle or package manifests, required notices, exact
check results and exclusions, and downloadable SHA-256 sums. A successful
source test is insufficient for artifact startup or model quality.
Run the existing automated CI/CD flow through merge and release. Do not add
human review, release approval, sign-off or manual verification gates.
Unavailable credentials, external dependencies or hardware capacity are
specific blockers; finish independent work and report the exact unfinished
step without inventing completion.

On 2026-11-01, the PyPI JSON API showed all published versions of
`airunner-common`, `facehuggershield` and `airunner-tts-vendor` yanked with
the reason "Distribution paused by the project owner." Preserve that
decision. The current task authorizes a GitHub release; it does not require
resuming PyPI publication. Dependency availability must be resolved through
reviewed release inputs rather than silently bypassing the owner's pause.

The Linux candidate profile now uses `services[linux-release]`, which omits
the OpenVoice/Melo `airunner-tts-vendor` dependency and the unused default
FacehuggerShield dependency. Explicit `legacy-shield` compatibility extras
retain its pin without activating it. Common 6.1.8 also makes Shield optional;
its exact source and wheel are recorded in
`input-reviews/airunner-common-6.1.8.md`. The common release is published on
GitHub, its downloaded bytes match the recorded hash, and isolated installed
imports passed with the reviewed python-dotenv dependency. This establishes
that bounded input, not the full service artifact. The excluded components
remain quarantined. The previous
desktop-profile lock is retained as historical evidence only; a validated
`linux-release` hash lock has not been generated. The release preflight blocks
before dependency installation until that lock is generated and validated.

The binary-only dependency probe advanced past an unused Wikipedia requirement
after its removal from the search extra. Sumy remains necessary for conversation
and web-content summarization. Its reviewed docopt 0.6.2 wheel, source identity
and MIT notice are retained in `package/wheelhouse`; an offline build and parser
smoke check passed. Diagnostic probes now include the verified CUDA wheel;
their metadata resolution does not constitute a validated release lock or
authorize installing affected dependencies.

The Debian candidate uses a separate `linux-services-core` frozen profile.
Ubuntu's Python package catalog does not provide the service's exact base pins,
so the package embeds its Python interpreter and CORE dependency closure instead
of substituting older distribution versions. The profile preserves the ten
service console aliases, migrations and notices. It excludes ML libraries and
weights; runtime-backed features remain optional and OpenVoice remains deferred.
The full ML bundle retains its separate dependency and acceptance requirements.

The CORE candidate lock contains 51 distributions. Its readiness record binds
the requirements, lock, exact-pin review inventory and builder review records
by SHA-256. Completed source reviews without a concrete policy flag do not
require an owner exception. Concrete unresolved flags and incomplete source
reviews prevent installation or freezing. As of 2026-11-02, all 51 locked
distributions have recorded static source review and origin disposition. The
readiness record permits isolated candidate installation and build work.
CORE Debian builds, post-packaging inspection and fresh-target installation
passed at source `ac1fc6206a8388e4ce19068209a714296cc21290` in
[workflow run 41502697852](https://github.com/Capsize-Games/airunner/actions/runs/41502697852).
The validation receipt binds Debian SHA-256
`75e747b019d2a2a839fa2109907a1d618c07f754de02859330c6c4031d3c7ea1`
to that source. It covers systemd start, authenticated API health, installed
service version, frozen API executable identity, stop/start/restart and exit
of both the supervisor and API child. The profiles retain imports from all
packaged migrations, with regression and TOC checks. Daemon, art and TTS
launchers execute the frozen image directly and preserve normal Python module
execution. These results apply to this CORE candidate; they exclude real models,
offline denial, prior-package upgrades, apt promotion/signing and the full ML
bundle. The visible input and whitelist inventory is in
`DEPENDENCY_DECISIONS.md`. Remaining Debian exit checks include upgrade preservation,
followed by source-bound apt promotion and downloaded-package verification.

GitHub release promotion runs from the exact annotated version tag through
`workflow_dispatch`. It builds and checks the Python distributions, full Linux
candidate, native sidecars and Debian package before creating or resuming a
draft release. The promoter checks the complete asset set and digests, uploads
only missing matching assets, then publishes once and verifies GitHub's immutable
release state. A published-release event only verifies the existing release;
it does not append assets. The dispatch verifies its own publication because
GitHub can suppress events caused by the workflow token.

The apt publisher accepts only a stable immutable release whose Debian manifest
binds to the exact successful promotion run and job. It stages the existing apt
repository, verifies its signature and package digest, checks an isolated target
install and daemon health, then promotes and checks the public repository again.
Failed validation restores the previous repository. These are automated release
steps, not owner approval or manual review gates. The pipeline source is prepared;
no main service release or apt publication has passed these steps yet.
