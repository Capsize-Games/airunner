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
not planned because their target product changed. This does not establish
acceptance, legal review, or release readiness.

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
acceptance.

The active release lock is pending generation. The old desktop lock is retained
only as historical evidence. Binary-only resolution stopped at
`llama-cpp-python==0.3.21`, which requires a reviewed source-built wheel for the
target. Source review, a pinned isolated CUDA build and hardware validation are
separate work units. CI preflight deliberately fails while the lock or required
sibling input reviews are pending; a skipped or unavailable check is not a pass.

The service Kanban project tracks these inputs, companion retirement, eSpeak
acceptance and CUDA wheel preparation as bounded follow-ups. The inherited
signed content-policy mechanism has not been confirmed as a service requirement.
Its existing code blocks packaged operation without provisioned data;
that behavior is an implementation fact, not a verified owner requirement.
Resolve its place in the service before treating provisioning or specialist
content-policy acceptance as release prerequisites.

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
6. Preserve existing checks while the content-policy requirement is reviewed.
   Private policy contents, credentials, customer data and sensitive
   evaluation evidence never enter public source, issues or artifacts.
   Deterministic coverage cannot substitute for specialist efficacy review.
7. Builds consume reviewed dependencies and exact sibling/runtime pins.
   The tested source revision, artifact manifest and tag must agree. Build
   and verify candidates before promotion. GitHub publication is authorized
   by the current request; unrelated live service changes are separate.

## Phases and acceptance

| Phase | Work and existing issues | Exit evidence |
|---|---|---|
| 0: Reconcile scope | Retire obsolete plans; align contributor/service docs (#2201), preserve companion boundaries (#2144); integrate mainline; make optional static app hosting explicitly configured | Tracker reconciliation; service contract and accurate commands; no machine-specific implicit UI mount; focused merge checks |
| 1: API correctness | HTTP admission and setup terminal status (#2408); Ollama show/pull (#2415); real embedding responses; bounded TTS HTTP requests and voice listing (#2254); accurate STT loaded state | Authenticated contract tests with fake runtime boundaries, bounded request/concurrency tests, no false success or synthetic model output |
| 2: Data integrity | Safe downgrade policy (#2358), existing NULL preservation (#2363), schema drift checks (#2364), list boundaries (#2365), bootstrap/backup/document batching (#2409) | Temporary SQLite upgrade/recovery tests, preserved user values, bounded public reads and streaming ingestion |
| 3: Runtime and companion | Reconcile confirmed LLM/art/voice findings (#2405/#2406/#2407); characterize retained compatibility (#2147/#2149); retire duplicate cognitive policy in stages; diagnose CPU/CUDA scenario (#2242/#2416) | Focused security/lifecycle regressions; preserved data and compatibility; explicit caller inventory before deletion; no real-model parity claim from doubles |
| 4: Distribution | Resolve unavailable TTS distribution (#2413); service dependency/version orchestration (#2200); apt release artifact (#2251); dependency refresh evidence (#2274); optional-ML gate (#2399); ops cleanup (#2410); isolated crash regression (#2276) | Supported profiles resolve; pinned reviewed inputs; artifact-level daemon checks; CI uses the same source/check list; excluded tests recorded |
| 5: Code quality | Repair analyzer path and unavailable-tool handling; analyze all service/native modules; review dead imports and ranked complexity by subsystem | JSON reports with exact scope/exclusions; confirmed defects fixed; reviewed dispositions for residual advisory findings; focused tests/import checks |
| 6: Service acceptance | Installation/restart/recovery (#2139), art API (#2122), voice API (#2148), embeddings/RAG (#2136), offline/auth (#2128), GPU handoffs (#2146), safety efficacy/publication (#2123) | Candidate/model/runtime hashes; exact commands and results on isolated targets; pending/skipped is never pass |
| 7: Release | Service tracker (#2237/#2238), candidate promotion (#2151) | Required CI green for exact source; clean artifacts and notices; immutable tag/release; downloaded bytes match manifest |

Parallel Luna implementation uses disjoint file groups: API/runtime, data,
and quality/distribution. The coordinator reviews diffs, integrates changes,
runs combined checks and owns publication. Shared workflow/metadata edits
are serialized. Workers do not install new third-party dependencies or
start real models without the applicable provenance and capacity checks.

## Audit evidence and quality treatment

The repository's legacy AST analyzer, invoked with a relative services
path, inspected 771 files / 128,965 lines and reported 1,147 findings:
778 warnings and 369 informational notes. The identical absolute path
incorrectly excludes the whole tree. Correct path handling and make
zero-file scans explicit failures for a requested existing source tree.

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

Review quality findings in API, persistence, workers/runtimes, LLM and
companion, art/voice, utilities and build tooling as separate work units.
Prioritize correctness and boundaries, then simplify confirmed hotspots
and public types. Preserve optional import behavior and upstream notices.
Do not impose a bulk formatting rewrite or silently mark legacy debt as
passed. Residual advisory findings need recorded dispositions and linked
work; new or changed code receives focused checks.

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
Unavailable distribution credentials, safety specialist review, or hardware
capacity are explicit gates; no worker may invent their completion.

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
the exact common source revision and its dependencies still need release-input
validation. These excluded components remain quarantined. The previous
desktop-profile lock is retained as historical evidence only; a validated
`linux-release` hash lock has not been generated. The release preflight blocks
before dependency installation until that lock and the required common input
review are complete.
