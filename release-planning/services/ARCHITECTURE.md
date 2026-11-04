# AI Runner service completion architecture

Owner direction: 2026-11-01. AI Runner provides model workers, runtimes,
and authenticated HTTP/WebSocket APIs for other applications. The retired
Qt interface and paid desktop storefront are outside this release.

## Incremental release policy

Owner direction, 2026-11-03: deliver through CI/CD in small MVP releases instead
of holding the first release for the entire completion project. The release
slices and their bounded exit criteria are defined in
[INCREMENTAL_RELEASES.md](INCREMENTAL_RELEASES.md). That policy supersedes any
statement below that makes all subsystem phases, the full ML dependency closure,
all model evaluations, PostgreSQL, or Docker prerequisites of every release.
Those requirements remain tracked for the release that ships the capability;
deferral is not completion or evidence of a passing check.

Authentication, isolation, preservation of existing data, bounded owned workers,
reviewed inputs, licenses, artifact identity and immutable publication remain
required for each shipped path. A release claims only capabilities exercised
through its installed artifact. Full-profile historical observations below
remain scoped to those profiles and sources.

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

The active V6 release lock contains 244 reviewed inputs, including pure
Psycopg 3.3.7 for the full Linux profile. A fresh offline installation,
dependency check, all 80 direct requirement checks, and notice verification
(244 distributions, 1,735 files) passed. See
[the V6 input record](input-reviews/linux-release-v6-input-validation.md).
A separate 2026-11-03 source-service acceptance on commit `57bebf4a8` passed
using the reviewed Ubuntu 24.04 system libpq and pure Psycopg. It verified `verify-full`
TLS, rejection of an invalid password and unrelated CA, migrations and isolation
for two tenant schemas, and cleanup. Frozen PostgreSQL acceptance remains open;
CORE remains SQLite-only. The old desktop lock is historical evidence. The preceding
V5
diagnostic graph installed all 243 exact reviewed wheels in a separate project
environment with kernel network denial, hash enforcement and no builds;
`uv pip check` passed. All 77 direct service requirements match the installed
metadata in the recorded V5 check. That check predates the two explicit direct
metadata declarations for `soundfile==0.14.0` and `Twisted==26.10.0`; the
selected lock already contains both reviewed wheels. A rebuilt services wheel
was installed offline with no dependency resolution into the isolated V5
candidate environment; all 79 current base and `linux-release` requirements
matched installed metadata. The import check run in that V5 environment was a
full-graph result, not CORE-only evidence. A separate fresh CORE51 environment
was built from the exact hashed CORE lock, then given the rebuilt services and
native wheels with no dependency resolution. It had no Torch, torchvision or
Transformers. Its base import gate scanned 46 module-scope imports: 19 were
satisfied, 27 were declared only under inactive extras, and none were
undeclared or missing. This does not validate Linux-release or optional-extra
imports.
Five CPU ABI/local-fixture probes and full production notice verification
(243 distributions, 1,734 files) passed. These results do not
establish full model, GPU, API or frozen-artifact acceptance. The visible
exact-pin inventory is in `DEPENDENCY_DECISIONS.md`.

Full Linux bundle assembly now requires the reviewed Ubuntu 24.04 amd64
PostgreSQL OS package inputs and stages their exact archives, locks, receipts,
offline installer and standard-library prerequisite checker. Frozen PostgreSQL
selection checks the target OS and installed package versions before importing
its DBAPI. CORE declares PostgreSQL disabled; SQLite does not need those
packages. Disposable pinned-image validation installed the 24 runtime packages
and two conditional development compatibility packages from the assembled
local repository, preserved CUDA/compiler package identities, and passed a
second invocation without package changes. Missing input, checksum drift,
wrong architecture and downgrade cases rejected before installation. The
integrated local bundle/upgrade regression selection passed 163 tests. This
establishes staging, package installation and metadata checks. The later source
PostgreSQL acceptance described above covers connections and migrations; frozen
PostgreSQL and full-release acceptance remain required.

A subsequent isolated Ubuntu 24.04 source-runtime probe established a
`verify-full` TLS connection, rejection of an invalid password and unrelated
CA, pure Psycopg with the exact system libpq, and private SASL plugin paths.
Tenant startup then exposed a service defect: a configured SQLite backup
directory redirected PostgreSQL into the SQLite-only snapshot helper. The
guard now skips non-SQLite URLs before considering that directory; SQLite
snapshots remain enabled. Unsupported-backup errors omit the database URL.
The integrated backup, recovery and PostgreSQL runtime selection passed 41
tests. A later isolated source-service probe on commit `57bebf4a8` passed
live PostgreSQL migrations and two-schema isolation. This was an integration
probe, not an additional numbered test selection. Frozen PostgreSQL acceptance
remains open.

The reviewed CUDA wrapper `0.3.21+capsize.3` corrects the Qwen MTP loader and
ctypes context-layout defects found in earlier candidates. Disk caching is an
explicit extra. Compiled candidate run `41545665728` and notice-completion run
`41554942120` passed. The final wheel retains all 94 original runtime payloads
and includes the wrapper, backend and JSON notices. Actual Qwen3.5-9B Q8
inference at context 32768 returned HTTP 200 on RTX 5080 with full configured
offload. The first exact-output assertion exposed a missing disabled-thinking
preference in the offline embedded chat template; a separate status defect
reported an unloaded model as loaded. Both source fixes are committed. A later
authenticated run rejected an unauthenticated request with HTTP 401 and returned
exactly `7`, using approximately 9,472 MiB process GPU memory. It released the
model weights on unload, but a harness predicate incorrectly required the
process CUDA context to disappear before reload. The failed receipt is retained.
Independent harness review also found that keepalive frames could be mistaken
for model output during the disconnect test. Cancellation and full reload
acceptance remain open until the corrected checks pass. A 300-second cold-load
request timed out on model storage; the completed inference used the validated
finite 900-second setting. These source/runtime observations do not establish
frozen-artifact acceptance.
The `61c5d12a5` hosted run passed runtime contracts and CORE clean installation,
but failed the LLM dependency installation on disk exhaustion and the CORE
published-package upgrade probe on early frozen startup. The failed upgrade
artifact did not retain the child log, so its underlying exit remains
unexplained. Failure diagnostics now retain bounded, redacted child-log tails
while preserving the failed result. A subsequent source regression reproduced a metadata-head read attempting
`PRAGMA journal_mode=WAL` while a writer held `BEGIN IMMEDIATE`; the dedicated
metadata engine now preserves the journal mode and allows backup/head reads.
The same fixture failed before that fix and passed afterward. At `ef91e36d6`,
CORE candidate run `41718346308` built and clean-installed the package, and its
published-upgrade job passed migration, data/config preservation, package
remove/purge preservation, and the installed frozen interruption/recovery probe.
The interruption probe kills the owned headless entry point after its durable
pre-upgrade backup and before migration writes, then resumes normal startup;
it does not simulate arbitrary power loss or interrupted package unpacking.
Its authenticated API/conversation checks returned 200 and unauthenticated API
returned 401. The exact published baseline is retained as a checksum-pinned
test fixture after the original download endpoint returned HTTP 502. These
results cover the synthetic SQLite CORE scenario, not PostgreSQL or model
backends. All four optional runtime-smoke marker
selections are absent in the inspected source; CI reports that explicitly as
no coverage before dependency setup. Runtime contracts, final full-profile
packaging checks and physical-model acceptance remain separate requirements.

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

The owner delegated quality and latency targets on 2026-11-03.
[EVALUATION_TARGETS.md](EVALUATION_TARGETS.md) defines the reproducible scenarios,
correctness/quality criteria, performance targets and comparison procedure.
These are targets; actual source and final-artifact results remain separate.

| Phase | Work and existing issues | Exit evidence |
|---|---|---|
| 0: Reconcile scope | Retire obsolete plans; align contributor/service docs (#2201), preserve companion boundaries (#2144); integrate mainline; make optional static app hosting explicitly configured | Tracker reconciliation; service contract and accurate commands; no machine-specific implicit UI mount; focused merge checks |
| 1: API correctness | HTTP admission and setup terminal status (#2408); Ollama show/pull (#2415); real embedding responses; bounded TTS HTTP requests and voice listing (#2254); accurate STT loaded state; terminal LLM failures and bounded completion observation (SRV-23, #2416) | Authenticated contract tests with fake runtime boundaries, bounded request/concurrency tests, no false success or synthetic model output |
| 2: Data integrity | Safe downgrade policy (#2358), existing NULL preservation (#2363), schema drift checks (#2364), list boundaries (#2365), bootstrap/backup/document batching (#2409); restore the full-profile PostgreSQL driver and verify migrations/schema isolation (#2446, SRV-27; source acceptance passed, frozen acceptance remains) | Temporary SQLite upgrade/recovery tests, PostgreSQL connection/migration/schema tests, preserved user values, bounded public reads and streaming ingestion |
| 3: Runtime and companion | Reconcile confirmed LLM/art/voice findings (#2405/#2406/#2407); characterize retained compatibility (#2147/#2149); retire duplicate cognitive policy in stages; consolidate native LLM execution and authenticate supervised native children (#2242/#2416) | Shared backend identity and ownership tests, child authentication, native-failure containment, preserved route semantics/data/compatibility; explicit caller inventory before deletion; no real-model parity claim from doubles |
| 4: Distribution | Resolve unavailable TTS distribution (#2413); service dependency/version orchestration (#2200); apt release artifact (#2251); dependency refresh evidence (#2274); Triton external toolchain and compile opt-in (SRV-24); optional-ML gate (#2399); ops cleanup (#2410); isolated crash regression (#2276) | Supported profiles resolve; pinned reviewed inputs; artifact-level daemon checks; CI uses the same source/check list; excluded tests recorded |
| 5: Code quality | Repair analyzer path and unavailable-tool handling; analyze all service/native modules; review dead imports and ranked complexity by subsystem | JSON reports with exact scope/exclusions; confirmed defects fixed; reviewed dispositions for residual advisory findings; focused tests/import checks |
| 6: Service acceptance | Installation/restart/recovery (#2139), art API (#2122), voice API (#2148), embeddings/RAG (#2136), offline/auth (#2128), GPU handoffs (#2146), optional-policy contracts (SRV-22) | Automated candidate/model/runtime checks with hashes and exact results on isolated targets; disabled-default and opt-in policy tests; pending/skipped is never pass |
| 7: Release | Service tracker (#2237/#2238), candidate promotion (#2151) | Required CI green for exact source; clean artifacts and notices; immutable tag/release; downloaded bytes match manifest |

Parallel Luna implementation uses disjoint file groups: API/runtime, data,
and quality/distribution. The coordinator reviews diffs, integrates changes,
runs combined checks and owns publication. Shared workflow/metadata edits
are serialized. Workers do not install new third-party dependencies or
start real models without the applicable provenance and capacity checks.

## Knowledge-base tool boundaries

SRV-28 / [#2447](https://github.com/Capsize-Games/airunner/issues/2447)
extends phases 1 and 2 to catalog search and managed knowledge saves. Catalog
search must honor the same per-request document scope as retrieval, including
an explicitly empty scope. Model tool calls use registered documents; ingestion
is explicit rather than an implicit repository scan. Saves must stay within
managed storage, preserve existing content, and distinguish durable persistence
from registration and indexing. Keep public tool names compatible and pass the
request scope through hidden ToolNode configuration. Concurrent scope and
storage-boundary regressions, followed by packaged-service evidence, are required.

The source implementation preserves standalone unscoped catalog compatibility
while making scoped searches use registered documents only. An empty scope
returns before database access. Saves use bounded input, descriptor-relative
no-follow/exclusive creation, file/directory sync, durable document registration
and a chatbot file assignment for the next request scope. The active request's
scope is not widened. Partial registration/notification failures are reported;
existing files are preserved. A request snapshots its chatbot and restores that
binding even when loading fails. The source regressions cover ToolNode schema
hiding, concurrent scopes, failed writes/syncs, bot switching and actual SQLite
ORM persistence after resetting sessions. Final packaged acceptance remains open.

The catalog search refactor replaces the F/83 implementation with A/3
orchestration and B/9 catalog logic. Save orchestration is A/5; its pure input
validator is C/20 and its durable writer C/17. The separate OS input stager's
validator was reduced from F/52 to A/5; its maximum function complexity is C/15.
These scores support maintenance review, not runtime correctness claims.

## Docker OS and Python inputs

SRV-30 / [#2449](https://github.com/Capsize-Games/airunner/issues/2449)
extends phases 4 and 6 to the remaining Docker OS/Python inputs. Although the
CUDA base and Python wheels are pinned, additional apt packages and the
deadsnakes PPA still resolve mutable versions. Inventory and review the retained
closure, remove retired interface-only dependencies where compatible, and
stage authenticated exact archives before an offline image install. Preserve
the separate PostgreSQL lock and CUDA dependencies. Actual image-build and
isolated service evidence are required; source checks do not close this gap.

## Native execution profiles in delivered artifacts

SRV-29 / [#2448](https://github.com/Capsize-Games/airunner/issues/2448)
extends phases 3, 4 and 6 to native artifact delivery and selection. The pinned
v0.2.3 archives supply CPU sidecars; requesting GPU layers from that binary does
not create CUDA support. The current Docker recipe's GPU reservation also does
not supply a model-server payload. The separate SM 120a candidate must retain
its wrapper and archive-local libraries in a distinct profile tree rather than
replace the CPU executable under the same name.

Resolve native backend selection separately from GGUF context/sampling profiles.
Honor CPU/GPU intent, reject unavailable or unsupported requested GPU profiles,
and keep model identity and 32k context unchanged. Verify profile manifests,
relative entrypoints, hashes, permissions and notices before launch. Distinguish
selected artifact capabilities from observed device/layer offload; unknown
observations remain unknown. Frozen, installer and Docker staging must carry
the same verified native profiles. A versioned sidecar manifest must describe
standalone runtime facts without fictional application Python paths.

The source selector now separates native CPU/CUDA selection from GGUF tuning,
defers optional GPU verification during registry construction, and returns
`native_backend_unavailable` at use when the requested profile is absent or
invalid. It verifies the profile inventory and confines CUDA execution to the
archive-local wrapper, uses PCI-ordered device selection, and disables automatic
model fitting. `CUDA_VISIBLE_DEVICES` remapping is explicitly unsupported by
this initial profile. Public capability metadata includes deferred/unavailable
selection state while actual device/offload observations remain unknown.
The integrated local transport/authentication/model-binding selection passed
143 tests with four dependency deprecation warnings. The new verifier has no
Radon D/E/F blocks; whole-file size/maintainability remains a review hotspot.
These source checks do not establish packaged GPU acceptance.

Explicit CUDA archive staging now requires independent archive, source and
producer pins and a verified profile manifest. A read-only preflight checks
the complete archive before PyInstaller; staging validates it again before
writing. Both reject path escapes, links, special files, unlisted entries,
wrong modes/hashes, malformed manifests and an unsafe wrapper. The profile tree
is installed separately from the CPU executable, with permissions that allow
the service user to traverse it. An integration fixture stages a profile and
passes it through the runtime selector without executing its fake binary.
The combined local staging/selector/bundle selection passed 138 tests. The
stager was refactored from F/51 and E/38 functions to a maximum C/20; no D/E/F
blocks remain. Actual final archive pins, installed/container integration and
GPU acceptance remain open; no candidate is promoted by these fixture tests.

The installer and Docker staging helpers preserve the complete pinned CPU
archive, including its licenses and provenance, alongside an independently
verified CUDA profile. The developer `scripts/install.sh` leaves CUDA opt-in by default; an operator
can request it with `--sidecars-cuda` or `AIRUNNER_DEV_SIDECAR_CUDA=1`. The full
Linux bundle spec currently marks CUDA staging optional. The development
launcher discovers a staged profile through
`AIRUNNER_LLAMA_CUDA_PROFILE_ROOT`, without redirecting application/Python paths.
The full NVIDIA Docker image requires both profiles. The published CUDA pin
remains absent pending native acceptance and publication; no candidate
placeholder is installed. Once an accepted profile is published, the release
installer and frozen-profile defaults still need to require both CPU and CUDA
profiles. The integrated payload, launcher, authentication and compatibility
selection passed 123 tests with three dependency warnings.
New staging helpers have no Radon D/E/F blocks. Source review retains the
88-line staging transaction and the pre-existing D/23 named-file extractor as
advisory findings: the former keeps validation and atomic replacement together;
the latter remains the compatibility extraction path. These dispositions do not
replace runtime or artifact acceptance.

Historical CUDA candidate `41720615159` loaded the required Qwen model and 32k
context in 24.515 seconds, returned health 200, rejected an unauthenticated
completion with 401, and released its owned process. It did not pass acceptance:
the server observed 33/34 layers on GPU and block 0 on CPU. Source review traced
the layer-count discrepancy to the native full-offload branch. The service maps
its negative full-offload setting to the native CLI's explicit `all` value
(`-2`), preserving CPU and positive layer counts. The maintained native source
backport at `7495314` has passed 59 focused tests. Hosted candidate run
[41737512324](https://github.com/Capsize-Games/airunner-native/actions/runs/41737512324)
was building when this status was recorded; no new CUDA profile is accepted.
Observed full placement, authenticated generation, cancellation and cleanup
remain required, and device capability must come from runtime evidence rather
than the compiled CUDA target.

Coordinate the producer's annotated release/tag, complete immutable asset set,
consumer pins and safe profile-tree staging. Preserve existing immutable tags.
Native producer PR [#4](https://github.com/Capsize-Games/airunner-native/pull/4)
retains the reviewed Whisper v1.9.5 source with a version-specific key-file auth
patch and binds CPU/CUDA packaging to committed producer recipes. Local
model-free producer tests and hosted input tests pass. Earlier candidate run
`41712069289` built both Linux and Windows CPU archives and passed their native
OS help/version checks. CUDA run `41712967565` completed compilation but failed
the subsequent runtime-notice/package-list verification; it produced no accepted
CUDA archive. A later source backport and candidate run are tracked above; the
profile remains unaccepted until the current run completes and its runtime
evidence passes. Actual service inference, offload, lifecycle, quality/latency
and final packaged evidence remain required before the service release.

The Linux Whisper candidate from that CPU run was also exercised through the
source `SidecarSTTClient` in an isolated network namespace with the unchanged
large-v3 model. All 20 fixed synthetic utterances completed; aggregate word error
rate was 3/185 (1.62%), within the initial 10% fixture target. Unauthenticated
inference/load returned 401, and both owned daemons exited and were reaped.
Eight threads preserved all 20 transcripts and reduced median clip wall time
from 13.381 to 8.092 seconds, with 13.4% more aggregate process CPU time.
For the 5.962-second clip, real-time factor improved from 2.312 to 1.331;
the eight-thread observation meets the CPU target of at most 2. These
sequential shared-host runs have a contention confound and single short/long
latency observations. They establish neither warm P95 nor real-speaker/noise,
normal API or frozen-application acceptance. Use eight threads only when the
service has that CPU capacity; retain bounded configurations for smaller or
shared budgets. Targets and measurement rules are in `EVALUATION_TARGETS.md`.

## Shared native LLM request lifecycle

Source commits `61c5d12a5`, `b7ccee850`, and `32554f6ee` share the supervised
GGUF process between graph orchestration and stateless routes while preserving
their route semantics. Matching model-file identity and effective settings are
required for reuse; cached graph bindings reconcile after a supervised reload.
Cancellation can interrupt the owning HTTP connection before response headers
arrive without stopping a sibling request or the shared backend. Provider
completion and SSE parsing use one validation module. The modern stateless chat
contract forwards bounded function definitions, assistant calls, tool results
and returned usage. It returns calls to the consuming application; it does not
execute application tools. Unsupported runtime modes fail before invocation,
and HTTP streaming requests point callers to the supported WebSocket route.

The final integrated source selection passed 102 tests in a disposable HOME
and private loopback namespace, including authenticated HTTP and WebSocket
tool-call round trips. That result includes existing migration deprecation
warnings. It does not establish native model quality, physical cancellation,
GPU performance, or final frozen-artifact acceptance.

## LLM completion observation

SRV-26 / [#2445](https://github.com/Capsize-Games/airunner/issues/2445)
extends phase 1 and phase 6 to the lifetime of asynchronous art jobs. Reserve
bounded background capacity before model handoff and retain it until execution
actually exits, including runtime threads that outlive an observer's cancelled
response. Supervise owned tasks at shutdown. Retain cancellation arriving
before a sidecar child ID exists, and correlate local worker interrupts to
their request; an explicitly global administrative interrupt stays separate.
Use deterministic barriers for admission/cancellation/shutdown races. Actual
image generation and LLM/art resource handoffs remain required in #2122;
the inspected cache contains no complete supported art pipeline.

SRV-25 / [#2444](https://github.com/Capsize-Games/airunner/issues/2444)
extends phase 1 and phase 6 to accurate Ollama metadata. Actual model testing
found guessed model names, quantization, sizes, digests, dates, VRAM and expiry
in list/process responses. Resolve configured and resident artifact identity
separately, use actual file facts and the active runtime profile, and preserve
the client schema with explicit unknown values. Status requests must not
download assets or synchronously hash multi-gigabyte files. The catalog's
maximum context describes capability; it does not describe the active context.
Regression and actual model/API evidence are required before release closure.
Generation usage follows the same rule: provider-reported token counts may be
returned; missing counts and unmeasured phase durations use zero rather than
character-based estimates. Total request duration uses the monotonic clock.

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
security regressions. The Linux wheel stager has no D/E/F blocks (maximum C,
17).
Remaining advisory findings require the subsystem dispositions below rather
than mechanical deletion of optional imports, migrations or compatibility code.

A committed-source refresh at `fbea76520` used Python 3.13.5, the existing
`.venv-ci` quality analyzer, and Radon 6.0.1. The legacy AST scan found 804
service files / 136,176 lines and 1,269 advisory notes; its native scan remains
three files / 407 lines and six notes. The Radon service selection found 998
files, 180 complex blocks and 531 hotspot files. The legacy analyzer's source
exclusions and Radon's generated-file, directory and 500 KB size exclusions
remain in force; neither count includes all repository Python files. Six
release-input and notice helper scripts were also scanned separately. The new
Docker input stager's cached-wheelhouse verifier is complexity C/20; its output
path validator is B/9. The runtime notice CLI is A/4. The scan includes older
notice validation code, whose verifier remains F/56 and distribution reader
E/40. Against the previous Radon snapshot, five blocks are newly reported:
`handle_ollama_embedding_async` C/19, `build_ollama_runtime_metadata` D/26,
`_cached_digest` C/11, `ServiceApp.cleanup` C/13 and
`LLMModelManager._load_model_locked` D/25. The manager load block replaces the
previously ranked `LLMModelManager.load` at the same score after extraction;
the E5 directory verifier changed from C/14 to C/17. A bounded read-through
found no discrete correctness defect attributable to these scores. The scores
remain review prompts, not acceptance gates or confirmed defects.
Xenon is still unavailable in `.venv-ci`; its result is unavailable, not a pass.

A committed-source refresh at `32554f6ee` used the existing `.venv-ci`
interpreter and repository AST analyzer against an isolated source archive.
It inspected 810 service files / 140,962 lines and emitted 1,312 advisory notes:
378 missing-docstring, 173 long-function, 392 missing-hint, 355 inline-import,
and 14 long-class notes. Its permanent migration, database-model, data, vendor,
CLI and GUI exclusions remain in force. The native selection inspected three
files / 407 lines and emitted six notes. These are inventories, not confirmed
bug counts. The Radon selection includes code excluded by that AST scan and
returns blocks for 879 files; the counts are not interchangeable.

The extracted HTTP transport has maximum complexity B/9; provider parsing C/20;
function-tool validation C/15; chat route B/6; WebSocket envelope handling B/9;
and the shared proxy B/7. The manager's model-load coordinator remains D/29,
with reviewed state transitions and dedicated stale-binding regressions. The
RAG catalog search ranks F/83 and its boundary review led to SRV-28, rather than
a cosmetic split that would preserve the underlying behavior. Remaining
hotspots and unavailable tools retain their earlier explicit dispositions.

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
remain quarantined. The previous desktop-profile lock is retained as historical
evidence only. The V6 `linux-release` hash lock now contains 244 reviewed inputs
and passed offline installation, direct-requirement and notice checks; see the
[V6 input validation record](input-reviews/linux-release-v6-input-validation.md).
That lock result does not establish frozen PostgreSQL or full artifact acceptance.
Temporary Actions inputs still need durable release mirrors before final
publication.

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
`DEPENDENCY_DECISIONS.md`. A later published-package upgrade run
(`41718346308`) passed upgrade preservation and installed frozen interruption
recovery for its synthetic SQLite scenario. Remaining Debian exit checks include
source-bound apt promotion and downloaded-package verification.

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

## Unused geospatial helper

The service geospatial helper `services/src/airunner_services/utils/location/map.py`
was removed after a caller search of desktop `services/src`, `native/src`,
`scripts`, and service release documentation found no imports or calls to
`extract_geojson_from_pbf`, `download_and_extract`, or
`list_available_regions`. The sibling web checkout contains its own
`airunner_engine` map module and unit tests; those are outside this service
package and were left unchanged. The service no longer imports `pyrosm`
through this unused module.

## Art generation job bounds

The art API admits one background generation job per service process. Admission
is atomic and occurs before the LLM unload handoff; a full slot returns HTTP 503
with `Retry-After: 1`. The slot remains held until runtime invocation and result
handling finish, even after the public job status becomes cancelled. API shutdown
requests cancellation and waits for active runners up to its bounded timeout;
an unfinished runner remains tracked and keeps its reservation.

Cancellation uses the parent request ID through the sidecar submission window.
The sidecar sends a pending cancellation as soon as it learns the child job ID.
The local callback runtime and SD worker match cancellation to the queued or
active API request. The ID-less administrative interrupt retains its existing
process-wide behavior. Deterministic tests cover admission, reservation lifetime,
shutdown timeout, sidecar ID handoff, local fallback timeout acknowledgement and
SD worker request matching. An independent isolated selection passed 213 tests
with three dependency warnings, including API, cancellation, shutdown and release
contracts. These tests use no model inference; authenticated real-model generation, output inspection and GPU handoff remain
separate acceptance work.

## Durable custom runtime inputs

The final application release must include the five exact custom runtime wheels
for llama-cpp-python, NVSHMEM, torchaudio, torchvision and Triton. Each release
asset remains bound to its reviewed hash, original Actions artifact, run and
source revision. The stager tries the public immutable versioned release asset
without credentials. Only HTTP 404 permits fallback to the original authenticated
Actions artifact; other HTTP errors, invalid redirects and size/hash mismatches
fail. Promotion verifies the complete wheel asset group before publishing.

The five final URLs are absent before publication. A bounded smoke verified
live 404 responses and original artifact metadata, then exercised the production
stager with a cached, hash-verified archive containing three of the wheels.
It did not fetch a live Actions ZIP or re-download the full runtime graph.
Published asset downloads and hashes remain a required release check. Root's
focused transport/promotion regressions passed 47 tests locally.

## Remaining document and resource boundaries

Phase 2 and phase 6 / [#2136](https://github.com/Capsize-Games/airunner/issues/2136)
include three confirmed document gaps. Keep one supported-format inventory for
the loader, indexing worker and tools; reject Office containers when no parser
exists. Carry immutable document IDs from the selected chatbot and explicit
request documents through generation and tool execution into retrieval. An
explicit empty selection must return no passages; a per-request filter must
never widen an existing retriever restriction. Preserve standalone compatibility
when no request scope exists.

Document deletion must share indexing admission and the runtime activity lock.
Stage only deterministic generated index directories, update registry and database
with rollback on pre-commit failure, invalidate caches, and retain a cleanup
manifest for post-commit removal retries. Original document files remain intact.
Both singular and bulk resource deletion must use this boundary. These changes
and actual E5 document lifecycle acceptance are in progress; earlier synthetic
retrieval proof does not establish this full scope.

Phase 3 / [#2406](https://github.com/Capsize-Games/airunner/issues/2406) also
includes ART memory admission. Inspection found that path-valued ART identities
were accepted as unregistered by the resource coordinator. The pretrained loader
used total VRAM, a 4 GiB floor and a fixed 32 GiB CPU allowance, which can exceed
live capacity. Register the declared ART resource demand and quantization intent,
use fresh available resources, and account for transformer, text encoder, VAE and
activation headroom under a shared budget. Reject an unsupported load before
starting it; estimated budgets remain distinct from measured peaks.

The pinned Z-Image intake contains all 19 selected files. Seven safetensors
payloads total 32,832,339,790 bytes; source/LFS identities and tensor header/layout
checks passed. This is data intake evidence, not model loading or generation.

Phase 6 / [#2139](https://github.com/Capsize-Games/airunner/issues/2139) has
two distinct interruption probes. The source probe kills only its own setup
subprocess after one observed schema DDL. Its published-baseline local run
interrupted post-migration schema repair, retained the verified pre-upgrade backup
and synthetic conversation, correctly rejected restoring an already-migrated
database, and resumed to the authoritative candidate graph heads. Fifteen
independent regressions passed locally. Separately, hosted installed-package run
`41718346308` tested interruption after the durable pre-upgrade backup and before
migration writes, then resumed the frozen daemon and verified the synthetic
conversation. Neither probe establishes arbitrary power-loss or interrupted
dpkg-unpack recovery.
