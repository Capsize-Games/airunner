# AIRunner Desktop and AIRunner: release-readiness audit

Date: 2026-09-13. Purpose: findings and decisions for discussion, before solution architecture or GitHub issue creation.

**Recommendation:** retain the Desktop product and Qt interface for the first paid release. Establish a reproducible, supported desktop distribution and repair the release blockers below. Reuse UwUchat's conversation capabilities through an explicit integration boundary. Do not begin with a UI rewrite or install the two service implementations into one Python environment.

## Scope and evidence

Desktop checkout: `cc4d0453a` (6.1.0), initially clean. Web checkout: `707b75e4f`, with existing modified and untracked files, including dialogue routing changes. Findings concern these working trees, not a deployed production build. Existing edits were preserved. No application source was changed, no model inference was invoked, no app was launched, and no issues were created.

Inspected packaging metadata, release and test workflows, launcher/first-run behavior, API authentication, content-policy loading and generation gates, image result handling, model downloads, runtime boundaries, chatbot configuration, embedding dependencies, frontend coupling, and test isolation. Historical plans were treated as leads, not proof of implementation.

Validation performed:

- Desktop: 86 selected tests passed in 10.53 seconds: content matcher, application gate, semantic layer, output-filter failures, dependency constraints, and native package isolation. These validate mechanics, not policy effectiveness or a fresh installation.
- Desktop: an in-memory FastAPI TestClient reproduction accepted an unauthenticated `/api/v1/llm/stream` connection with an unrelated Origin while `AIRUNNER_API_KEY` was set. Runtime construction/client resolution were replaced with test doubles; an empty request returned `No message provided`. No network listener or inference was involved.
- Web: 8 authentication/rate-limiter unit tests passed in 0.48 seconds inside the existing server container, with database URL variables cleared for the test process. This narrow suite does not certify the whole WebSocket implementation.
- No complete test run, fresh dependency installation, native installer build, GPU matrix, vulnerability-database audit, or visual/manual workflow audit was performed. GUI usability, real model quality, cancellation under load, upgrades of customer data, and offline behavior remain unverified.

## Findings

### F1 — Release blocker: Desktop WebSocket authentication differs from HTTP authentication

Evidence: [HTTP middleware](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/api/server.py:219), [WebSocket handler](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/api/routes/llm_stream_routes.py:24), [runtime lookup](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/api/routes/llm_runtime.py:37).

The HTTP middleware enforces an API key or loopback token. The WebSocket handler accepts the socket immediately; its runtime lookup only obtains app state. There is no equivalent authentication or Origin validation in the inspected route/router chain. Confirmed by the in-memory reproduction described above.

Impact: a reachable daemon's LLM streaming endpoint does not receive the access controls that operators may assume the API key provides. Remote reachability depends on the bind/proxy configuration. Desktop's HTTP loopback-token tests do not exercise this transport.

Direction: authenticate WebSockets explicitly, validate browser origins, apply appropriate limits, and require transport-specific regression tests. The web repository's authentication code is useful reference material, though its account/tenant scheme should not be copied wholesale into a single-user desktop product.

### F2 — Release blocker for the stated safety requirement: missing policy data allows generation

Evidence: [policy loader](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/content_safety/policy_data.py:105), [matcher](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/content_safety/matcher.py:165), [application gate](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/content_safety_gate.py:40), [release workflow](/home/joe/Projects/airunnerdesktop/.github/workflows/pypi-dispatch.yml:31).

The checked-in policy file is comments only. Missing, empty, or entirely malformed policy data produces an empty set and successful checks. The release workflow has no policy-data provisioning or nonempty-policy verification step. Passing safety tests is compatible with shipping an ineffective policy gate because this behavior is intentional and tested.

The `.dat` artifact is UTF-8 hexadecimal SHA-256 digests, not an opaque binary classifier. It keeps raw terms out of the repository; hashing does not authenticate the data, prove completeness, or make the policy tamper-resistant.

Direction: define release policy provisioning and validity requirements, verify the installed artifact, and block affected generation when a mandatory safety component is unavailable. Keep synthetic neutral terms in public tests. Audit all entry points and output paths against the same explicit policy.

### F3 — Product requirement gap: NSFW filtering and prohibited-content filtering are different controls

Evidence: [semantic layer](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/content_safety/semantic.py:1), [output checker](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/art/utils/nsfw_checker.py:30), [output toggle](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/art/managers/stablediffusion/base_diffusers_model_manager.py:196).

The semantic layer is disabled by default, requires an injected judge, and allows requests on absence, timeout, error, or ambiguous results. The image checker now withholds output when enabled but unable to evaluate it, which is good. However, it is a general NSFW checker with an off switch; it is not a classifier of everything that might be prohibited by the intended product policy. A prompt matcher also cannot classify the contents of an input image or reliably interpret every generated image.

Direction: separate the optional adult-content preference from mandatory prohibited-content controls. Define the categories, supported modalities, error behavior, and measurable false-positive/false-negative targets. An absolute guarantee that an owner-controlled offline application cannot be modified to produce illegal material is not a technically supportable product promise. Aim for strong enforcement in the supported distribution with tested limits, without claiming perfect detection or tamper prevention.

### F4 — Release blocker: there is no complete consumer installer pipeline in the inspected tree

Evidence: [distribution workflow](/home/joe/Projects/airunnerdesktop/.github/workflows/pypi-dispatch.yml:1), [sidecar workflow](/home/joe/Projects/airunnerdesktop/.github/workflows/native-runtime-sidecars.yml:1), [native pins](/home/joe/Projects/airunnerdesktop/native/runtime_sidecars/runtime_pins.env:1).

The release workflow builds four Python distributions and native sidecars. Release assets depend only on the Python-package job and attach those distributions; sidecars are workflow artifacts, not assembled with a desktop installer. A second workflow duplicates sidecar construction. These workflows do not establish an install/launch/upgrade/uninstall gate or depend on successful release tests. The shown build matrix covers Linux and Windows sidecars, not a tested full application on either OS. CUDA is not enabled by these workflow commands.

Direction: one reproducible release manifest covering application, Python environment, Qt plugins, native binaries, policy artifact, and supported model/runtime combinations. Build and validate the final product on each supported OS. Add signing, update/recovery behavior, and artifact checks as applicable to the chosen channels.

### F5 — First-run packaging defect: startup still expects development tooling

Evidence: [launcher](/home/joe/Projects/airunnerdesktop/src/airunner/launcher.py:67), [startup call](/home/joe/Projects/airunnerdesktop/src/airunner/launcher.py:473), [package definition](/home/joe/Projects/airunnerdesktop/setup.py:118).

If the UI marker is absent, startup executes `scripts/build_ui.py` relative to the current working directory and tries to write the marker inside the installed package. The setup definition deliberately excludes developer tooling. This makes the startup action invalid in a normal installed layout and fragile in a read-only bundle. Exceptions are swallowed into warnings, so this is not proof that every GUI launch fails; it is a confirmed invalid first-run dependency.

Direction: compile resources during the build and verify their presence in the installed artifact. Runtime should not require the repository, build tools, or writable application files.

### F6 — Dependency profiles do not establish a portable installation contract

Evidence: [GUI dependencies](/home/joe/Projects/airunnerdesktop/setup.py:28), [optional CUDA pins](/home/joe/Projects/airunnerdesktop/setup.py:60), [torch startup import](/home/joe/Projects/airunnerdesktop/src/airunner/main.py:234), [startup invocation](/home/joe/Projects/airunnerdesktop/src/airunner/main.py:258), [services metadata](/home/joe/Projects/airunnerdesktop/services/setup.py:103).

The base GUI package omits torch, but normal startup calls a helper that imports it. A base installation therefore has an undeclared operational prerequisite even though heavyweight ML dependencies are advertised as optional. The documented CPU fallback does not change requirements explicitly pinned to `+cu129` wheels: changing the index alone cannot satisfy a different wheel version identifier.

Numerous dependencies have open version ranges and there is no full resolved Python lock/constraints artifact for a target product bundle. Several metadata definitions are mirrored across package surfaces. Existing tests check declarations, not a complete resolver/install/launch exercise.

Direction: choose supported hardware profiles and resolve/test complete environments for them. Distinguish the Python-facing developer package from the supported consumer installation. Do not promise AMD, Apple Silicon, CPU art, or arbitrary NVIDIA generations before measured validation.

### F7 — Integration blocker: both repositories own the same Python distribution and namespace

Evidence: [Desktop service metadata](/home/joe/Projects/airunnerdesktop/services/setup.py:1), [web service metadata](/home/joe/Projects/airunner/server/package_metadata.py:455).

Both define `airunner-services` and install `airunner_services`. Desktop is version 6.1.0; web is 6.0.0 in the inspected metadata. They have divergent runtime layouts and dependency constraints. Pip cannot treat them as two independent implementations in one environment; installing one can replace files/metadata belonging to the other.

Direction: preserve separate environments/processes for any initial integration, or extract and rename genuinely shared packages under one owner. Decide ownership of inference, conversation orchestration, persistence, and API contracts before moving code. A subprocess integration still needs its own complete dependency and lifecycle solution.

### F8 — UwUchat is partly locally routable, but is not currently a self-contained offline chatbot

Evidence: [pipeline configuration](/home/joe/Projects/airunner/projects/uwuchat/server/ai_pipeline.py:66), [dialogue override](/home/joe/Projects/airunner/projects/uwuchat/server/dialogue_routing.py:102), [embedding provider](/home/joe/Projects/airunner/projects/uwuchat/server/embedding_provider.py:32), [database session](/home/joe/Projects/airunner/server/src/airunner_services/database/session.py:1).

Current dialogue code routes to a local Ollama-compatible daemon by default unless opted into OpenRouter; environment configuration can override other text pipelines. This contradicts the cloud-only agent guide. Embeddings still explicitly call OpenRouter and use a Redis-backed limiter. The persistence implementation is PostgreSQL-oriented; the surrounding project uses Redis/Celery and account-specific encryption and tenancy.

Direction: reuse conversation behavior, memory, streaming, and tests, with deliberate choices about local storage, embeddings, background work, model capacity, and cloud consent. Changing the main dialogue model is insufficient to establish offline behavior or equal chatbot quality. Measure local-model memory extraction and tool use as well as response quality and latency.

### F9 — UwUchat's UI is coupled to the full application

Evidence: [ChatView](/home/joe/Projects/airunner/projects/uwuchat/client/components/chat/ChatView.tsx:1), [framework route registration](/home/joe/Projects/airunner/server/src/airunner_services/api/server_routes_specs.py:152).

The 1,244-line chat view imports auth, quotas, administrative panels, code-mode behavior, conversation inspection, and global event hooks. It registers window listeners at module scope. Server route declarations likewise know about multiple UwUchat-specific integrations. A mature user experience exists, but a drop-in chatbot library does not follow from that.

Direction: decide whether the goal is UwUchat's behavior, its visual interface, or the full product. Those have very different costs. A chat-only UI boundary or a backend conversation service would be a bounded extraction; transplanting the entire web stack brings SaaS responsibilities into Desktop.

### F10 — Quality gate gap: tests exist, but do not certify a release

Evidence: [Desktop CI](/home/joe/Projects/airunnerdesktop/.github/workflows/eval-tests.yml:21), [web CI](/home/joe/Projects/airunner/.github/workflows/eval-tests.yml:87), [client test configuration](/home/joe/Projects/airunner/client/vitest.config.ts:1).

Desktop's mandatory contract job selects a small set of files and does not include the new safety suites run in this audit. Web CI explicitly excludes four tests and documents additional historical full-suite failures; those comments are evidence of exclusions and recorded debt, not a fresh count of current failures. Client CI runs tests but does not itself execute the production TypeScript/Vite build. Neither the sampled tests nor the workflows establish an end-to-end offline installed-product guarantee.

Direction: make release acceptance explicit: clean installation, first model download, generation, cancellation, modality switching, save/reopen, upgrade preserving data, interrupted download, missing policy, and unavailable runtime. Keep hardware/manual checks separate from inexpensive deterministic unit contracts.

### F11 — Test isolation risk: UwUchat tests may use the application's database

Evidence: [database fixture](/home/joe/Projects/airunner/projects/uwuchat/server/tests/conftest.py:14).

The `_db` fixture falls back from `AIRUNNER_TEST_DATABASE_URL` to `AIRUNNER_DATABASE_URL` and invokes schema setup. Database-using tests may consequently touch the configured application database when no dedicated test URL is supplied. Setup failures become skips, which can also conceal missing validation.

Direction: require a distinct test database, reject application/production targets, and fail required CI checks when their database is unavailable. This audit avoided the database-backed suites in the live application container.

### F12 — Download reliability: mutable revisions and size-only acceptance

Evidence: [existing-file acceptance](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/downloads/huggingface_download_worker.py:317), [download/resume implementation](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/downloads/huggingface_download_worker.py:825).

The inspected downloader fetches `/resolve/main/`, trusts existing files based on size heuristics, and can promote an existing temporary file when its size is at least the expected size. When expected size is zero, that condition is especially weak. Resume uses a byte range without the shown code binding it to a pinned revision or checksum. A changed upstream file or corrupted local file can therefore pass these checks and fail later during model loading.

Direction: pin supported model revisions, verify digests, resume only the same artifact, and promote validated files safely. This is likely to improve customer support outcomes more than broad cosmetic refactoring.

### F13 — Art API contract mismatch and input limits

Evidence: [request contract](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/api/routes/art_contracts.py:8), [runtime forwarding](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/api/routes/art_job_requests.py:54), [response handling](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/api/routes/art_job_response.py:42).

The public request accepts and forwards `num_images`, but job result handling selects only `images[0]`. The API result thus loses additional returned images even if the runtime supports the requested batch. This finding does not assert that every backend supports batches or that backend auto-export loses them.

The public request model also lacks explicit bounds on dimensions, steps, batch size, prompt size, and base64 input size. Downstream runtime behavior may impose limits, but the boundary permits invalid or excessive requests to proceed farther than needed.

Direction: align request/result contracts and enforce resource-aware limits at the public boundary, with tests covering all returned images and rejected invalid parameters.

### F14 — Maintenance and trust-boundary debt

Evidence: [Desktop chat widget](/home/joe/Projects/airunnerdesktop/src/airunner/components/chat/gui/widgets/chat_prompt_widget.py:1), [worker manager](/home/joe/Projects/airunnerdesktop/src/airunner/components/application/gui/windows/main/worker_manager.py:1), [custom tool compilation](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/llm/tool_manager.py:224), [sandbox caveat](/home/joe/Projects/airunnerdesktop/services/src/airunner_services/llm/core/code_sandbox.py:1).

Desktop still has large responsibility-heavy files: chat prompt widget 2,802 lines, worker manager 2,245, installer page 1,655, local fallback 1,608. File length alone is not a defect, but these boundaries make small-agent changes harder to constrain and verify. The web project's instructions and wiki also disagree with current routing and Electron removal; native runtime README pins disagree with the authoritative pin file.

Custom tools execute in the application process after a validation flag check. The restricted-builtins module correctly states that it is not a security sandbox. I did not prove an untrusted caller can set that flag, so this is a trust-boundary concern rather than a demonstrated arbitrary-code exploit.

Direction: document current ownership and trust assumptions; constrain agent issues to a named behavior and a small file set. Consider disabling advanced code/computer-control features in a basic consumer profile until their permission/isolation story is deliberately supported. Refactor the high-change boundaries when behavior tests exist, not to achieve an arbitrary line count.

## What is worth preserving

- Desktop already has GUI/service/shared/native separation, runtime envelopes and registries, lifecycle clients, and pinned native source revisions. The distribution effort can build on this work.
- The new input-policy implementation centralizes matching, normalizes text, avoids disclosing matched content, and has useful synthetic tests. Enabled output checking has meaningful failure handling.
- The web project has explicit account-aware WebSocket handling, tenant/security regression tests, organized provider configuration, and substantially developed conversation/memory behavior.
- Download resume, job tracking, error states, and model management already exist. The task is to make their contracts reliable and supportable rather than recreate every capability.

## Distribution choices for discussion

| Choice | Fit | Main cost | Recommendation |
|---|---|---|---|
| Keep Qt and distribute a self-contained Python application | Preserves current Desktop experience and traction | Native dependencies, resources, installation/update testing | Preferred first release |
| Replace the desktop UI with web UI in Electron | Useful if one React interface is the long-term product decision | UI migration, browser/IPC security, plus all Python/runtime packaging | Evaluate only with explicit UI convergence goal |
| Keep Qt and integrate a chat service or chat view | Reuses the strongest chatbot behavior incrementally | Clear API, process lifecycle, storage and offline boundaries | Worth a bounded feasibility study after scope decisions |

Python can be bundled with its interpreter so customers need not install Python. PyInstaller supports this and requires platform-specific builds; its documentation recommends making a directory bundle work before a single-file bundle. Qt also provides `pyside6-deploy`, based on Nuitka, with standalone-directory support. Neither tool has been validated against this application's entire dependency graph here. Sources: [PyInstaller operation and limitations](https://pyinstaller.org/en/stable/operating-mode.html), [Qt deployment tool](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html).

I would start with a directory-based bundle inside a normal installer and keep large models outside the application installation. Select the packaging tool after a small representative build experiment covering Qt resources, one inference runtime, audio, and model download. Electron adds a separate security/update responsibility; its own guidance emphasizes safe handling of remote content and keeping the bundled framework current. [Electron security guidance](https://www.electronjs.org/docs/latest/tutorial/security).

Commercial packaging should explicitly inventory application, dependency, model, and bundled-asset licenses. Desktop declares GPL-3.0-only; the web project declares MIT. The repositories' shared ancestry warrants a provenance check before code transfer or release-license claims; this audit does not conclude infringement. Existing third-party notices are a useful start but are not a complete bill of materials for a future installer.

The business premise about traffic and willingness to pay comes from the owner, not verified analytics. Preserve that audience while validating demand with a reliable first-run experience. For itch.io, adult-themed pages require appropriate classification and are subject to payment-related policies; this audit does not determine this specific product's payment eligibility. [itch.io creator guidelines](https://itch.io/docs/creators/quality-guidelines).

## Decisions needed before architecture and small-agent issues

1. Which OS and GPU combinations account for the audience, and which are required for the first paid release?
2. Must the core experience work fully offline after downloads, without login or API keys? Which cloud features are intentionally optional?
3. Is retaining the Qt interface a preference, or is replacing it with the web interface an acceptable product change?
4. Which three workflows are non-negotiable at launch, and which advanced capabilities may be hidden or marked experimental?
5. Does “UwUchat integration” mean conversation quality/memory, its visual chat experience, or the full account/social/tooling product? Which existing tests best establish its quality?
6. What explicit prohibited-content policy and release acceptance criteria should be enforced, separately from adult-content preferences? Is the intended goal best-effort enforcement in the official build or resistance to owner modification?
7. What pricing/update/support model and existing-user data compatibility commitments should the installer support?

After these decisions, architect the chosen boundaries, then split work into narrowly scoped issues with prerequisites, allowed files, non-goals, acceptance examples, exact validation commands, and a clear completion condition. Avoid broad tickets such as “clean up architecture,” “port UwUchat,” or “make it secure.”

## Owner decisions following the audit

- Target Windows and Linux.
- Essential features must work offline after model downloads; OpenRouter may be optional.
- Retain Qt.
- All existing functionality is in launch scope and must meet defined release acceptance criteria; no scope reduction was agreed.
- Reuse UwUchat's conversation quality, memory, tool use, and bot capabilities rather than transplanting its account/social UI.
- Mandatory protection targets the specific prohibited-content category identified by the owner; allow adult content separately. Do not publish the plaintext policy list. A private policy artifact supplied during release builds is under discussion, not yet an implemented or approved architecture.
- Paid installer, free source, free updates, no subscription initially. Optional paid services such as FastSearch may follow.
- Target 16 GB VRAM and higher. GPU vendor, architecture, system RAM, and simultaneous-model expectations remain to be specified; VRAM capacity alone is not a compatibility definition.

## Legal-document and commercial follow-up

The owner confirmed NVIDIA-only support initially, at 16 GB VRAM or above. Privacy policies, terms, age notices, sales terms, and related disclosures are now part of release preparation.

Initial document inspection found these issues; these are review findings, not a completed legal compliance opinion:

- Desktop's user agreement, section 2, describes a non-transferable, non-sublicensable, revocable software license while invoking GPLv3. Reconcile the agreement with GPL rights; distinguish software licensing from purchase, support, trademark, and optional hosted-service terms. Review private policy-data distribution against applicable source obligations as well. Reference: https://opensource.org/license/gpl-3.0
- Desktop's privacy policy asserts the company does not operate servers processing personal information. Scope that statement to verified local application behavior, and separately describe purchases, support correspondence, websites, download/update infrastructure, and any optional company-operated services. Do not substitute the hosted UwUchat policy for the offline desktop policy.
- Desktop's privacy policy lists uninstalling as a means to delete all application data. This is not supported by a verified installer/uninstaller contract. Define treatment of user-created media, models, local databases, backups, and custom paths, then document actual deletion behavior.
- The phrase “full functionality” offline must distinguish installed local features from inherently networked search, remote models, and connected tools. Essential offline capabilities remain a product requirement; online services must be visibly optional and must not receive data through silent fallback.
- UwUchat's privacy policy promises provider non-retention, specific retention/deletion periods, and specific payment data receipt. Verify these against actual provider settings/contracts, storage jobs, backups, payment integration, and operating practices before retaining the claims.
- Both sets of documents need review of age declarations, sensitive-data descriptions, legal applicability, consent, limitation of liability, consumer rights, and actual moderation/reporting practices. Do not claim automatic compliance or blanket legal protection. Local-only enforcement should not be described as remote monitoring/reporting that does not occur.
- The live itch.io page still lists earlier Ubuntu versions, an RTX 3060 minimum, and old feature/model descriptions. Update the listing to match the tested release and explicit NVIDIA VRAM requirement, while making treatment of existing purchasers clear. Reference: https://capsizegames.itch.io/ai-runner
- itch.io's payment terms require compliance with its payment processors' acceptable-use policies. Adult-content labeling alone does not establish payment eligibility for this specific application. Reference: https://itch.io/docs/legal/terms#7-acceptable-payment-forms

Required factual inputs for final legal drafts include confirmed seller identity/contact information, intended sales territories, actual purchase/support data handling and retention, selected providers, deletion behavior, update/support commitments, and refund handling. Final drafts should be reviewed by qualified counsel, especially for GPL consistency, consumer sales, privacy, and the sensitive-content policy. No existing user-facing legal document was replaced during this preliminary review.

Pricing hypothesis: USD 39 launch price and USD 59 regular price for Windows and Linux installers, offline core capabilities, and free released desktop updates. Optional hosted services/API costs remain separate. This is a recommendation to validate using conversion, refunds, and support burden, not an estimate of demand or revenue. Current comparison points: LM Studio describes free local use, while TypingMind lists one-time tiers at USD 39/79/99 (the USD 99 tier is promotional), excluding API costs. References: https://lmstudio.ai/blog/free-for-work and https://www.typingmind.com/buy

A same-day fully integrated, validated production release is not supported by the audit evidence. Packaging feasibility, Windows/Linux hardware acceptance, offline bot portability, security fixes, policy provisioning and detection evaluation, upgrades, legal verification, and channel eligibility are still outstanding. A package that merely builds does not meet the owner's all-functionality release standard.
