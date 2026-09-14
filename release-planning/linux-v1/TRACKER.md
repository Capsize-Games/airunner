# Linux desktop release specification

Owner: Capsize LLC, Colorado. Sales intent: worldwide. Status: implementation handoff, not a release-readiness declaration. Date: 2026-09-13.

## Product requirements

- Linux first; Windows deferred. NVIDIA GPUs with 16 GB or more VRAM initially. Retain PySide6/Qt. No Electron conversion. Ubuntu 24.04 LTS x86_64 is the proposed first validation baseline, not a claim that testing has passed. Resolve exact GPU generations, drivers, RAM, disk, and distribution support from measured packaging/hardware evidence.
- Paid official installer, free source and free released desktop updates. No mandatory account, subscription, activation server, or periodic online lease. Suggested USD 39 launch / USD 59 regular price remains a recommendation, not an owner-approved published price. Optional OpenRouter and future hosted search are separate services/costs.
- All existing Desktop functionality remains in scope: art/canvas/editing/filters/LoRA and supported generation modes; LLM/chatbot; speech synthesis/recognition and voice interaction; local embeddings and RAG; downloads; settings; persistence; tool use; supported remote operation. Inventory must enumerate the actual features and expose omissions as linked work. No silently disabling features to pass release checks.
- Core capabilities work offline after explicit model downloads. Network-only tools can correctly report that they require a connection. No silent cloud fallback, cloud embeddings, remote classifiers, background telemetry, or account dependency in offline mode. Explicit remote mode and optional online providers retain clear consent and authentication.
- Bring UwUchat conversation quality, memory, session behavior, mood, background cognition, and tool capabilities to the Desktop backend. Preserve existing Desktop workflows and data. Do not transplant billing/social web UI, PostgreSQL/Redis/Celery services, production credentials, or the conflicting web airunner_services package.
- Mandatory child-protection safeguards and adult-content preferences are separate. The private policy vocabulary must never appear in public source, issues, logs, tests, or artifacts. Production policy data and selected local detection models are release prerequisites. Synthetic neutral fixtures are for testing only. Do not obtain, generate, or put abusive imagery into a test corpus. A qualified owner/specialist controls any sensitive evaluation.
- Preserve local-only privacy and source-license obligations. No promise of perfect detection, tamper prevention, guaranteed legal coverage, unlimited future support, or untested hardware compatibility.

## Architecture decisions

1. Desktop owns the installed application, local SQLAlchemy/SQLite data, service daemon, runtime registry, art/voice execution, and Qt frontend. No Docker required for customers. Existing network-serving features remain optional, authenticated modes.
2. Port characterized UwUchat behavior into a bounded desktop service module under services/src/airunner_services/llm/companion/. Keep provider, memory repository, scheduler, and tool interfaces explicit. Reuse existing Desktop inference and registered tools. Do not import the web package at runtime or install both implementations in one environment. Record upstream provenance and verify licensing before moving source.
3. Reference behavior is captured from the actual web code and neutral deterministic fixtures. The preliminary web guide contains stale cloud-only claims. Live deployments and local uncommitted work are not interchangeable with a fixed upstream commit. Freeze the reference before porting.
4. Conversation-turn events have stable request/turn/chatbot/session identifiers. Store completed turns before background memory work. Persist background jobs with idempotency keys and bounded concurrency; GPU-dependent background work uses the same model resource arbitration as interactive generation. No independent model loading by every background task.
5. Use additive, idempotent database migrations and transactional repository operations. Facts and recall are chatbot-scoped. Local embeddings record model identifier/revision/dimension; changing models requires a rebuilt index, not mixed vector spaces. User data is outside the installation.
6. Central offline policy gates all application-controlled egress; explicit loopback IPC remains allowed. Tool capabilities declare network/filesystem/execution needs. Arbitrary code needs a real process/OS isolation boundary or explicit trusted-code behavior; restricted Python builtins are not a sandbox.
7. Policy artifacts are versioned data, authenticated with a public-key signature. Compile in a private controlled process and package the finished artifact in trusted release CI. Public PR tests have no production policy/key access. Missing, corrupt, incompatible or unverifiable mandatory components deny affected generation. A separate specialist gate chooses viable offline contextual/image detection and thresholds. Do not implement an unvalidated age-estimation rule as proof of safety.
8. Check inputs before inference; check outputs before any preview, signal, API response, automatic export, thumbnail, or TTS publication. Where complete output is required for classification, buffer until allowed and expose progress without leaking unchecked content. Define checks for image input/editing as well as text-to-image.
9. Start with a self-contained directory bundle and a user-level Linux installer. Run a representative PyInstaller-vs-pyside6-deploy experiment, choose once on evidence, then freeze the tool recipe. Native runtimes, Qt plugins, legal resources, translations, Python environment, policy and detector artifacts all have verified manifests. Do not build from the user's working directory or write into the installed application.
10. Candidate releases are assembled and tested before production publication. Transactional upgrades preserve data and retain a recoverable previous installation; data migrations have backups and tested recovery. Uninstall retains user data by default and offers explicit separate deletion. Downloaded updates are verified before activation; offline operation does not require updates to run.

## Completion and gates

- Feature inventory maps every capability to code, deterministic checks, manual scenarios and linked defects. Unknown, skipped, or untested is not pass. Feature omissions create separate small issues before the release tracker closes.
- Each issue targets one behavior or one evidence artifact. Normally 2–5 production files plus directly relevant tests; generated resources are exceptions. If implementation exceeds that boundary, stop with a proposed split rather than rewriting the subsystem.
- Run focused existing/static checks. Ticket-specific deterministic regression tests are intended deliverables, but reconcile repository test-creation instructions in the instruction-alignment task first. No running the GUI, loading a real model, contacting paid APIs, altering a live database, or deploying from an ordinary small-model task. Hardware/manual verification is a separate operator task.
- Review security, destructive migration, legal, and policy changes before release. A coding agent can prepare evidence but cannot stand in for counsel or approve its own safety efficacy.
- Final acceptance requires the same signed candidate's installation, offline capabilities, all modalities, cancellation, restart, cross-modality GPU arbitration, save/reopen, upgrades/recovery, consent/egress behavior, policy failures, and supported remote authentication to pass on the selected NVIDIA/Linux matrix.
- Worldwide sales require accurate data-flow and retention disclosures, mandatory consumer-rights treatment, license/model redistribution clearance, and payment-channel eligibility. Do not claim territorial legal clearance without review.

## Working order and usage control

Start with documentation alignment, feature/reference inventory, WebSocket auth, missing-policy rejection, launcher resource fixes, download integrity and isolated tests. Bot slices follow reference/contracts; bundling follows dependency/resource stabilization. Hardware, legal, policy efficacy and publication gates are last.

One issue per fresh small-model session. Read only its body, applicable instructions and named files. Keep one implementation active per shared file group; do not spawn subagents or run autonomous issue loops. Stop after the scoped diff and required checks, with a concise result and unresolved facts. Follow-up defect/split issues may be filed when the assigned ticket explicitly requires them; never automatically implement those follow-ups. A failed requirement is not authorization to weaken a test or expand scope.

OpenAI documentation and the account inspection show finite Codex limits. GPT-5.3-Codex-Spark has a separate allowance. GPT-5.6 Luna is another lower-consumption option using ordinary allowance; neither is promised unlimited. No API billing, credit purchase, reset redemption, or model escalation is authorized by this handoff. Sources: https://learn.chatgpt.com/docs/pricing and https://learn.chatgpt.com/docs/agent-configuration/speed . Do not include this full specification or audit in every coding prompt; the issue bodies contain the relevant slice.


## Execution checklist

- [x] [R01: Inventory every Desktop launch capability and its acceptance scenario](https://github.com/Capsize-Games/airunner/issues/2084) — docs
- [x] [R02: Record the Linux/NVIDIA model and hardware validation manifest](https://github.com/Capsize-Games/airunner/issues/2086) — docs
- [x] [R03: Correct stale small-agent paths and testing guidance](https://github.com/Capsize-Games/airunner/issues/2085) — docs
- [ ] [W01: Freeze UwUchat bot behavior and provenance for the Desktop port](https://github.com/Capsize-Games/airunnerweb/issues/216) — docs
- [ ] [W02: Require an explicit isolated database for UwUchat tests](https://github.com/Capsize-Games/airunnerweb/issues/217) — webcode
- [ ] [W03: Reconcile web agent documentation with actual dialogue routing](https://github.com/Capsize-Games/airunnerweb/issues/218) — docs
- [x] [S01: Authenticate Desktop LLM WebSocket before accepting it](https://github.com/Capsize-Games/airunner/issues/2087) — code
- [x] [S02: Bound WebSocket message sizes and per-client request rates](https://github.com/Capsize-Games/airunner/issues/2092) — code
- [ ] [S03: Define and compile a versioned private policy-data artifact](https://github.com/Capsize-Games/airunner/issues/2088) — code
- [ ] [S04: Verify policy signatures with a bundled public key](https://github.com/Capsize-Games/airunner/issues/2093) — code
- [ ] [S05: Deny image generation when mandatory policy data is unavailable](https://github.com/Capsize-Games/airunner/issues/2100) — code
- [ ] [S06: Provision signed policy data only in trusted release CI](https://github.com/Capsize-Games/airunner/issues/2101) — code
- [ ] [S07: Select offline contextual and image safety evaluators with evidence](https://github.com/Capsize-Games/airunner/issues/2094) — review
- [ ] [S08: Implement the selected offline contextual safety adapter](https://github.com/Capsize-Games/airunner/issues/2106) — code
- [ ] [S09: Implement the selected offline image-safety adapter](https://github.com/Capsize-Games/airunner/issues/2102) — code
- [ ] [S10: Screen imported image inputs before generation and editing](https://github.com/Capsize-Games/airunner/issues/2109) — code
- [ ] [S11: Withhold art outputs until mandatory checks succeed](https://github.com/Capsize-Games/airunner/issues/2115) — code
- [ ] [S12: Gate chatbot text and derived speech before publication](https://github.com/Capsize-Games/airunner/issues/2110) — code
- [x] [P01: Move Qt resource compilation out of installed-app startup](https://github.com/Capsize-Games/airunner/issues/2089) — code
- [ ] [P02: Resolve and lock the Linux NVIDIA runtime dependency profile](https://github.com/Capsize-Games/airunner/issues/2095) — code
- [ ] [P03: Unify pinned native runtime manifests and release artifacts](https://github.com/Capsize-Games/airunner/issues/2096) — code
- [ ] [P04: Compare representative Qt packaging builds and select one recipe](https://github.com/Capsize-Games/airunner/issues/2103) — experiment
- [ ] [P05: Assemble the complete Linux application directory bundle](https://github.com/Capsize-Games/airunner/issues/2107) — code
- [ ] [P06: Add a user-level Linux installer with safe install paths](https://github.com/Capsize-Games/airunner/issues/2111) — code
- [ ] [P07: Make upgrades transactional with backup and recovery](https://github.com/Capsize-Games/airunner/issues/2116) — code
- [ ] [P08: Implement uninstall with explicit optional user-data removal](https://github.com/Capsize-Games/airunner/issues/2117) — code
- [ ] [P09: Report hardware, disk and runtime prerequisites before model work](https://github.com/Capsize-Games/airunner/issues/2112) — code
- [ ] [P10: Verify downloaded application updates before activation](https://github.com/Capsize-Games/airunner/issues/2119) — code
- [ ] [P11: Produce dependency/model license inventory and source manifest](https://github.com/Capsize-Games/airunner/issues/2113) — review
- [x] [D01: Pin supported model downloads to immutable revisions and digests](https://github.com/Capsize-Games/airunner/issues/2097) — code
- [x] [D02: Resume only the same model artifact and promote it safely](https://github.com/Capsize-Games/airunner/issues/2104) — code
- [x] [D03: Return every image from a requested art batch](https://github.com/Capsize-Games/airunner/issues/2090) — code
- [x] [D04: Validate art request resource limits before job creation](https://github.com/Capsize-Games/airunner/issues/2098) — code
- [x] [O01: Define and enforce explicit offline egress policy](https://github.com/Capsize-Games/airunner/issues/2091) — code
- [x] [O02: Apply offline policy to model downloads and online tools](https://github.com/Capsize-Games/airunner/issues/2108) — code
- [x] [O03: Make diagnostics private and user-controlled](https://github.com/Capsize-Games/airunner/issues/2099) — code
- [x] [B01: Define Desktop companion contracts and port mapping](https://github.com/Capsize-Games/airunner/issues/2118) — design
- [x] [B02: Persist chatbot sessions and completed turn records](https://github.com/Capsize-Games/airunner/issues/2120) — code
- [ ] [B03: Add scoped fact and narrative-memory repositories](https://github.com/Capsize-Games/airunner/issues/2124) — code
- [ ] [B04: Implement local embeddings with explicit index identity](https://github.com/Capsize-Games/airunner/issues/2129) — code
- [ ] [B05: Port scoped fact and conversation recall tools](https://github.com/Capsize-Games/airunner/issues/2133) — code
- [ ] [B06: Add durable bounded background jobs for companion work](https://github.com/Capsize-Games/airunner/issues/2125) — code
- [ ] [B07: Port post-turn fact extraction and deduplication](https://github.com/Capsize-Games/airunner/issues/2137) — code
- [ ] [B08: Port episodic session summaries](https://github.com/Capsize-Games/airunner/issues/2130) — code
- [ ] [B09: Port narrative-memory updates and rolling compression](https://github.com/Capsize-Games/airunner/issues/2134) — code
- [ ] [B10: Port prompt composition and mood context](https://github.com/Capsize-Games/airunner/issues/2138) — code
- [ ] [B11: Adapt companion tool routing to Desktop registered tools](https://github.com/Capsize-Games/airunner/issues/2140) — code
- [ ] [B12: Route every companion pipeline through local inference by default](https://github.com/Capsize-Games/airunner/issues/2141) — code
- [ ] [B13: Connect Qt chat events to the companion service](https://github.com/Capsize-Games/airunner/issues/2143) — code
- [ ] [B14: Migrate existing Desktop knowledge without losing user data](https://github.com/Capsize-Games/airunner/issues/2131) — code
- [ ] [B15: Port remaining mood and proactive cognition as bounded jobs](https://github.com/Capsize-Games/airunner/issues/2144) — design
- [ ] [B16: Define and run the companion regression comparison procedure](https://github.com/Capsize-Games/airunner/issues/2147) — manual
- [ ] [T01: Isolate execution of custom code tools from the application process](https://github.com/Capsize-Games/airunner/issues/2142) — design
- [ ] [T02: Implement the selected custom-tool worker boundary](https://github.com/Capsize-Games/airunner/issues/2145) — code
- [ ] [L01: Inventory actual privacy data flows and retention promises](https://github.com/Capsize-Games/airunner/issues/2121) — docs
- [ ] [L02: Draft a factual Desktop privacy policy for worldwide sales](https://github.com/Capsize-Games/airunner/issues/2126) — legal
- [ ] [L03: Draft GPL-consistent purchase, support and acceptable-use terms](https://github.com/Capsize-Games/airunner/issues/2127) — legal
- [ ] [L04: Verify UwUchat hosted privacy and terms claims against operations](https://github.com/Capsize-Games/airunnerweb/issues/219) — legal
- [ ] [L05: Record owner and legal review decisions for the release documents](https://github.com/Capsize-Games/airunner/issues/2132) — owner
- [ ] [L06: Install approved legal notices and versioned consent records](https://github.com/Capsize-Games/airunner/issues/2135) — code
- [ ] [C01: Gate release candidates on required checks and artifact completeness](https://github.com/Capsize-Games/airunner/issues/2114) — code
- [ ] [C02: Record baseline test failures as small actionable defects](https://github.com/Capsize-Games/airunner/issues/2105) — experiment
- [ ] [W04: Triage currently excluded web regression tests without hiding failures](https://github.com/Capsize-Games/airunnerweb/issues/220) — experiment
- [ ] [Q01: Validate installation, restart, upgrade and uninstall](https://github.com/Capsize-Games/airunner/issues/2139) — manual
- [ ] [Q02: Validate all art and canvas workflows](https://github.com/Capsize-Games/airunner/issues/2122) — manual
- [ ] [Q03: Validate local chatbot, memory and tools on 16 GB NVIDIA](https://github.com/Capsize-Games/airunner/issues/2149) — manual
- [ ] [Q04: Validate TTS, STT and full voice conversations](https://github.com/Capsize-Games/airunner/issues/2148) — manual
- [ ] [Q05: Validate local embeddings, documents and RAG](https://github.com/Capsize-Games/airunner/issues/2136) — manual
- [ ] [Q06: Validate offline privacy and optional remote operation](https://github.com/Capsize-Games/airunner/issues/2128) — manual
- [ ] [Q07: Validate shared GPU lifecycle across all modalities](https://github.com/Capsize-Games/airunner/issues/2146) — manual
- [ ] [Q08: Review mandatory-safety efficacy and publication-path coverage](https://github.com/Capsize-Games/airunner/issues/2123) — manual
- [ ] [C03: Prepare accurate itch.io listing, sales terms and channel clearance](https://github.com/Capsize-Games/airunner/issues/2150) — owner
- [ ] [C04: Promote the reviewed candidate and verify public downloads](https://github.com/Capsize-Games/airunner/issues/2151) — owner

## Existing web issues (linked, not duplicated)

- [Billing provider extraction](https://github.com/Capsize-Games/airunnerweb/issues/210) and [auth storage extraction](https://github.com/Capsize-Games/airunnerweb/issues/212): adjacent work; do not transplant this SaaS infrastructure into Desktop.
- [Hosted output moderation](https://github.com/Capsize-Games/airunnerweb/issues/112): hosted-service work; Desktop publication gates have separate ownership.
- [Existing owner OSS checklist](https://github.com/Capsize-Games/airunnerweb/issues/172): reconcile with hosted legal review.

## First small-model session

Start R03 (documentation guidance repair) only. Owner authorized one GPT-5.3-Codex-Spark session using its finite separate allowance. No autonomous implementation queue was authorized. After it returns, inspect its result and select another ready issue manually.
