# Content Safety: Input Gate + Output Fail-Closed — Work Order / Plan

**Audience:** the coding agents (Code mode) that will implement the subtasks, and the reviewer
who verifies them.
**Repo:** `Capsize-Games/airunner` (this checkout). Python desktop app; GUI in `src/airunner/`,
daemon/service runtime in `services/src/airunner_services/`, shared code in
`shared/airunner_common/`.
**Status:** plan only — no `.py` files are to be touched by authoring this document.

---

## 0. Repository constraint — read before anything else

This feature exists to block the most severe prohibited-content category in text-to-image prompts.
**No term in that category may appear anywhere in this repository** — not in code, comments,
docstrings, tests, fixtures, data files, commit messages, PR text, or this document. GitHub's
automated scanners flag such strings and can suspend the account.

Therefore, throughout this plan and in all implementation:

- Refer to the mechanism as **"content safety"**, the blocklist entries as **"policy terms"**, and
  the blocked subject as **"prohibited content"**. Never name or enumerate the category or any
  example term — not even an obviously fake sample.
- The design stores **only SHA-256 hashes** of normalized tokens. The repository ships an **empty**
  hash set; a real set is generated **out of band** by an operator using the script described in
  §5.2 and is never committed.
- All tests use **synthetic, neutral tokens** (e.g. invented words) and compute their hashes inside
  the test. Never use a real term in a fixture, docstring, or commit message.
- The generator, matcher, and all log lines must **never echo the matched input** — only counts,
  lengths, booleans, and reason codes.

A subtask that introduces a raw term anywhere is a **hard failure**, regardless of test results.

---

## 1. Context (verified current state)

### 1.1 What exists — output-side NSFW image filter only (post-generation)

- [`check_and_mark_nsfw_images()`](services/src/airunner_services/art/utils/nsfw_checker.py:12) —
  if either model is `None` (line 31) it returns `images, [False] * len(images)`; on any exception
  (line 58) it logs and returns the same. **Fails open in both cases.**
- [`_mark_image_as_nsfw()`](services/src/airunner_services/art/utils/nsfw_checker.py:64) — blackout
  + text overlay for a detected image.
- [`_check_and_mark_nsfw_images()`](services/src/airunner_services/art/managers/stablediffusion/base_diffusers_model_manager.py:196)
  — wrapper. Returns unchanged + `[False]*n` when `use_safety_checker` is `False` (line 212), when
  `_safety_checker`/`_feature_extractor` is `None` (line 216), or on exception (line 229).
  **Fails open in all three cases.**
- Called from
  [`SDImageGenerationMixin._generate()`](services/src/airunner_services/art/managers/stablediffusion/mixins/sd_image_generation_mixin.py:101)
  at lines 132–134; results exported at line 175 (`image_export_worker.add_to_queue`) and handed to
  the canvas / `ImageResponse` at lines 189–205.
- [`ZImageGenerationMixin._generate()`](services/src/airunner_services/art/managers/zimage/mixins/zimage_generation_mixin.py:279)
  calls `super()._generate()` (line 295). [`ZImageModelManager`](services/src/airunner_services/model_management/zimage_model_manager.py:37)
  derives from `BaseDiffusersModelManager` and composes `ZImageGenerationMixin`, so the base
  `_generate()` / `_check_and_mark_nsfw_images()` paths apply to Z-Image too.
- Checker model loaded in
  [`_load_safety_checker()`](services/src/airunner_services/art/managers/stablediffusion/mixins/sd_model_loading_mixin.py:162)
  (`CompVis/stable-diffusion-safety-checker` + `CLIPImageProcessor`); gating in
  [`_ensure_safety_checker_ready()`](services/src/airunner_services/art/managers/stablediffusion/base_diffusers_model_manager.py:304).
- Toggle setting [`ApplicationSettings.nsfw_filter`](services/src/airunner_services/database/models/application_settings.py:63)
  (default `True`); read by [`use_safety_checker`](services/src/airunner_services/art/managers/stablediffusion/base_diffusers_model_manager.py:168).
  GUI disable-confirmation dialog: [`on_actionSafety_Checker_toggled()`](src/airunner/components/application/gui/windows/main/controllers/action_controller.py:177).

### 1.2 What does not exist — no input-side filtering

- Daemon route [`generate_image()`](services/src/airunner_services/api/routes/art_generation_start_routes.py:60)
  logs `len(request.prompt)` only (line 64) and calls
  [`create_generation_job()`](services/src/airunner_services/api/routes/art_generation_start_routes.py:39).
  Request contract [`GenerationRequest`](services/src/airunner_services/api/routes/art_contracts.py:8)
  carries `prompt` and `negative_prompt` only.
- LLM tool [`generate_image()`](services/src/airunner_services/llm/tools/image_tools.py:143) calls
  `api.art.llm_image_generated(...)` (line 193), which emits
  [`LLM_IMAGE_PROMPT_GENERATED_SIGNAL`](services/src/airunner_services/api/services/art_services.py:145)
  and converges on the same daemon generation path.
- Existing local-LLM guardrails **prompt-prefix** mechanism (not a term filter):
  [`prompt_template.use_guardrails / guardrails`](services/src/airunner_services/database/models/prompt_template.py:15)
  and [`chatbot.use_guardrails / guardrails_prompt`](services/src/airunner_services/database/models/chatbot.py:33).
- Policy is stated but not enforced: [`user_agreement_text.md`](src/airunner/components/downloader/gui/windows/setup_wizard/user_agreement/user_agreement_text.md:33);
  an age gate exists.

### 1.3 The generation dispatch paths (why the choke-point decision below is "both")

Both the GUI button and the LLM tool emit a signal that lands on the daemon
[`SDWorker`](services/src/airunner_services/workers/sd_worker.py:1):

- GUI `send_request()` emits `DO_GENERATE_SIGNAL` → handled by
  [`on_do_generate_signal()`](services/src/airunner_services/workers/sd_worker.py:486) → queued as
  `ModelAction.GENERATE` → [`handle_request` dispatch](services/src/airunner_services/workers/sd_worker.py:593)
  → [`_generate_image()`](services/src/airunner_services/workers/sd_worker.py:597).
- LLM tool → `LLM_IMAGE_PROMPT_GENERATED_SIGNAL` → the art generator form builds an `ImageRequest`
  → `DO_GENERATE_SIGNAL` → same `SDWorker` path.
- `_generate_image()` has two continuations: with a daemon client it forwards via
  [`_generate_image_via_daemon()`](services/src/airunner_services/workers/sd_worker.py:638) → HTTP
  `POST /generate`; without one it runs locally via
  [`load_model_manager()`](services/src/airunner_services/workers/sd_worker.py:318) →
  [`_process_image_request()`](services/src/airunner_services/workers/sd_worker.py:267) (which
  finalizes the `ImageRequest`, building it from [`generator_settings`](services/src/airunner_services/database/models/generator_settings.py:37)
  when the message has none).
- `ImageRequest` (rich contract: `prompt`, `negative_prompt`, `second_prompt`,
  `second_negative_prompt`) is defined in
  [`image_request.py`](services/src/airunner_services/art/managers/stablediffusion/image_request.py:16).

So a single enforcement point inside `SDWorker._generate_image()` sees every signal-driven request
in its final form, and the HTTP route is the public boundary for direct API clients and for the
daemon-forward continuation. Both must call **one** validator (no duplicated logic) — see §3.

---

## 2. Goals / Non-goals

### Goals

1. **Input gate** on all four text fields (`prompt`, `negative_prompt`, `second_prompt`,
   `second_negative_prompt`) before generation begins, at a choke point that covers the GUI path and
   the LLM tool path. Reject with a **generic** error and **fail closed**.
2. **Hash-based matcher**: SHA-256 over normalized token n-grams; source contains only generic
   identifiers; the real term list is never in the repo.
3. **Out-of-band generator** under `scripts/` that reads a plaintext list from a gitignored /
   out-of-repo path and emits the hash data file deterministically. The script contains no terms.
4. **Output filter hardened to fail closed**: when the output filter is enabled but its checker
   model is unavailable or errors, refuse to return/export, rather than emitting unflagged images.
5. **Docs**: a "Content Safety" section in `SECURITY.md` framing the feature as **best-effort, not a
   guarantee**.
6. **No content logging** anywhere in the new paths.

### Non-goals (v1)

- No semantic/LLM second signal (see §3.8 — reuse the existing guardrails mechanism later, if ever).
- No per-user policy editing UI; no remote policy updates.
- No change to the existing NSFW image model, its download flow, or `nsfw_filter` semantics.
- No GUI toggle for the new setting in v1 (DB/API only) — deferred deliberately, see §3.7.
- No new runtime dependency (the matcher is stdlib-only).

---

## 3. Architecture

### 3.1 Layered model

```
text fields ──► [ A. input gate (matcher, hash lookup) ] ──► generation ──► [ B. output filter (image classifier, fail-closed) ]
                        │                                                            │
              reject (generic) / block                              block if enabled but checker unavailable
```

Layer A throws on prohibited input or unavailable policy. Layer B throws when it is enabled but
cannot run. Neither layer ever logs the input.

### 3.2 New module layout (generic naming)

```
services/src/airunner_services/content_safety/
├── __init__.py          # public API re-exports
├── decision.py          # ContentDecision dataclass
├── errors.py            # ProhibitedContentError, ContentSafetyUnavailableError
├── normalization.py     # normalize_tokens(), candidate_strings(), hash_candidate()
├── policy_data.py       # path resolution + load/validate policy hash file
├── matcher.py           # check_text_fields(), enforce_content_safety(), cache/status
└── data/
    └── policy_terms.sha256.json   # committed; SHIPS EMPTY
```

Everything is **stdlib-only** (`json`, `hashlib`, `unicodedata`, `importlib.resources`, `os`,
`re`, `logging`) so it imports cleanly in the torch-less CI venv.

### 3.3 The choke point (decision)

**Decision: both — one validator, two thin call sites.**

- **Primary (signal boundary):** at the very top of
  [`SDWorker._generate_image()`](services/src/airunner_services/workers/sd_worker.py:597),
  before the daemon-forward / local branches. Rationale: both the GUI path and the LLM tool path
  reach this before any generation work; validating here means neither continuation can start on a
  prohibited request. Fields are taken from the message's `ImageRequest` when present, otherwise
  from `generator_settings` (the same source `_process_image_request()` uses to build one), so a
  single call covers both construction paths without touching `_process_image_request()`.
- **Secondary (public API boundary):** in
  [`create_generation_job()`](services/src/airunner_services/api/routes/art_generation_start_routes.py:39)
  (or at the top of [`generate_image()`](services/src/airunner_services/api/routes/art_generation_start_routes.py:60)),
  validating `GenerationRequest.prompt` / `negative_prompt` before `unload_llm_before_art` and job
  creation. Rationale: external HTTP clients bypass the worker; the route also gives a clean
  `4xx`/`503` and is traversed by the daemon-forward continuation.

There is **no duplicated matching logic** — both sites call
`enforce_content_safety(fields, enabled=...)` from the one module in §3.2. The worker call is
exhaustive (it covers the route-forward path too, since that path re-enters the route), so the route
call is a fast-fail convenience and an external-client guard, not a second policy engine.

Additionally (defense-in-depth, **SHOULD**): a pre-check in
[`image_tools.generate_image()`](services/src/airunner_services/llm/tools/image_tools.py:143) before
`api.art.llm_image_generated(...)`, returning
`{"status": "rejected", "message": <generic>}` so the LLM receives a clean tool result instead of an
asynchronous worker error. It calls the same `check_text_fields()`; enforcement still rests on the
worker gate.

### 3.4 Normalization spec (versioned as `"v1"`)

`normalize_tokens(text: str) -> list[str]`, in order:

1. Unicode **NFKC** normalize.
2. `casefold()`.
3. **NFKD** normalize, then drop combining marks (diacritics: `é` → `e`).
4. Fold **homoglyph / leet** characters to letters via a fixed table in code (digits and symbols
   only, e.g. `0→o`, `1→l`, `3→e`, `4→a`, `5→s`, `7→t`, `@→a`, `$→s`, `!→i`). The table contains no
   words and is safe to commit.
5. Remove every character that is not `[a-z0-9]` or whitespace (punctuation, symbols, zero-width
   chars); collapse whitespace runs to a single space; strip.
6. Split on spaces into tokens; drop empties.
7. Within each token, collapse a run of the **same character of length ≥ 3** to a single character
   (defeats elongation while preserving normal double letters such as `ball` → `ball`).

`candidate_strings(tokens, ngram_min=1, ngram_max=3, unigram_min_length=4) -> Iterator[str]`:

- Yield space-joined windows for `n` from `ngram_min`..`ngram_max`.
- Skip unigrams shorter than `unigram_min_length` (keeps short common single words out of the set
  and makes individual stored hashes less trivially reversible).
- Additionally yield the delimiter-free concatenation of each multi-token window (catches split
  tokens).

`hash_candidate(s: str) -> str` returns `hashlib.sha256(s.encode("utf-8")).hexdigest()` (lowercase
hex). Lookup is a single `frozenset` membership test. **The matched candidate is never returned,
logged, or surfaced** — only a boolean/reason.

### 3.5 Policy data format, location, loading

File: `services/src/airunner_services/content_safety/data/policy_terms.sha256.json`, UTF-8 JSON:

```json
{
  "schema_version": 1,
  "algorithm": "sha256",
  "normalization": "v1",
  "ngram_min": 1,
  "ngram_max": 3,
  "unigram_min_length": 4,
  "hashes": ["<64 lowercase hex chars>", "..."]
}
```

Rules:

- `policy_data.load_policy_hashes()` resolves the path as: **`AIRUNNER_CONTENT_SAFETY_DATA`** env
  var if set, else the packaged file via `importlib.resources.files("airunner_services.content_safety")`.
- Unknown `schema_version`, unknown `normalization`, malformed JSON, or any entry not matching
  `^[0-9a-f]{64}$` → raise `ContentSafetyUnavailableError` (**corrupt/tampered = fail closed**).
- Env var set but the path is missing → `ContentSafetyUnavailableError`.
- Packaged file **missing** or `hashes == []` → allow (empty policy set) and emit a **once-only**
  warning with no content (this is the by-design public-repo default; see §3.6).
- Result is cached in a module-level frozen set; expose `reset_cache()` for tests.
- The committed `hashes` list is **`[]`**. `MANIFEST.in` / `setup.py` must ship the file (see §5.5).

### 3.6 Fail-closed semantics (precise)

**Input gate (Layer A):**

| Situation | Behavior |
|---|---|
| Setting disabled | skip (allow) |
| Match | raise `ProhibitedContentError` → block, generic message |
| Env-var data missing / corrupt / unknown schema | raise `ContentSafetyUnavailableError` → block |
| Packaged data corrupt / unknown schema | raise `ContentSafetyUnavailableError` → block |
| Packaged data missing or empty | allow, **warn once** (no content) |

**Output filter (Layer B), governed by `nsfw_filter`:**

- `use_safety_checker` is `False` → unchanged (no filtering), as today.
- Enabled and `_safety_checker` or `_feature_extractor` is `None` → **raise**
  `SafetyCheckUnavailableError` (replaces the fail-open at
  [`base_diffusers_model_manager.py:216`](services/src/airunner_services/art/managers/stablediffusion/base_diffusers_model_manager.py:216)).
- Enabled and the classifier call raises → **raise** `SafetyCheckUnavailableError` (replaces the
  fail-open inside
  [`nsfw_checker.py:31`](services/src/airunner_services/art/utils/nsfw_checker.py:31) and
  [`nsfw_checker.py:58`](services/src/airunner_services/art/utils/nsfw_checker.py:58)).
- `_generate()` catches it and **aborts the batch**: stop progress bar, emit
  `EngineResponseCode.ERROR` with a generic message, call `image_request.callback(message)` if set,
  and `return` **before** `image_export_worker.add_to_queue(...)` and before any `ImageResponse` /
  canvas handoff. No unflagged image leaves the process.
- **Mid-session unload:** the wrapper re-reads `_safety_checker`/`_feature_extractor` on every
  batch, so if the checker unloads mid-session the *next* batch fails closed.
- Because Z-Image's `_generate()` delegates to `super()._generate()`, hardening the base covers both
  SDXL and Z-Image.

### 3.7 Configuration surface (decision)

**Decision: add a new setting; do not overload `nsfw_filter`.**

- New column `content_safety_filter = Column(Boolean, default=True)` in
  [`ApplicationSettings`](services/src/airunner_services/database/models/application_settings.py:50),
  mirroring existing columns such as
  [`trust_remote_code`](services/src/airunner_services/database/models/application_settings.py:66).
- Requires an Alembic migration using the existing helper
  [`add_column`](services/src/airunner_services/database/db/column.py:29) (pattern:
  [`20c05328cd3b_restore_nsfw_filter_setting.py`](services/src/airunner_services/database/alembic/versions/20c05328cd3b_restore_nsfw_filter_setting.py:25)).
- Rationale for a separate flag: the text gate is a legal-compliance control with different
  semantics from the image classifier; turning off the image filter must not silently disable it,
  and vice-versa. Both default to `True` and are independent.
- The worker/route read it via `ApplicationSettings.objects.first()` (see
  [`tokenizer_loader_mixin.py:35`](services/src/airunner_services/llm/managers/mixins/tokenizer_loader_mixin.py:35)),
  defensively: `getattr(settings, "content_safety_filter", True)`.
- **GUI toggle deferred to a later change.** v1 exposes the setting via the DB and the settings API
  only. Document this in `SECURITY.md`.

### 3.8 Optional semantic second layer (decision)

**Decision: defer.** Reusing the local-LLM guardrails mechanism
([`prompt_template.use_guardrails`](services/src/airunner_services/database/models/prompt_template.py:15) /
[`chatbot.guardrails_prompt`](services/src/airunner_services/database/models/chatbot.py:52)) as a
secondary signal is promising but introduces nondeterminism, latency, and a model-specific failure
mode into a safety control. It is **out of v1**. If added later it must be a *secondary* signal
that cannot convert a block into an allow, and it must not log prompt content.

**Implemented (follow-up 1).** The optional semantic second layer now ships in
[`content_safety/semantic.py`](services/src/airunner_services/content_safety/semantic.py) as a
default-OFF, env-gated secondary signal (`AIRUNNER_CONTENT_SAFETY_SEMANTIC`; `1`/`true`/`yes`
enables). It reuses the existing guardrails prompt and asks the local model for a single explicit
allow/deny token; the response parser is strict, so only an explicit negative answer blocks. It is
wired through
[`content_safety_gate.evaluate_prompt_fields()`](services/src/airunner_services/content_safety_gate.py:44)
after a clean hash check, so the hash matcher fast path still blocks without ever consulting the
model. The layer is **fail-open when unavailable** (disabled, no judge registered, timeout, error,
or ambiguous answer): it logs a content-free status and allows. It can only add a block and can
never convert a hash block into an allow. The judge callable is injected via `set_judge(...)`; the
repository registers no global judge by default, so the layer stays inert until an adapter is
injected. No DB column or migration was added. See the "Optional semantic input layer" subsection
in [`SECURITY.md`](SECURITY.md:38).

### 3.9 Error / UX contract

Generic message constants (no field names, no terms, no lengths):

- Prohibited: `"This request cannot be processed because it appears to violate the content policy."`
- Policy unavailable: `"Content safety is temporarily unavailable; image generation is disabled."`
- Output checker unavailable: `"Image safety verification is unavailable; the image was not returned."`

Surfacing:

- **HTTP route:** `HTTPException(status_code=422, detail=<prohibited msg>)` on a match;
  `HTTPException(status_code=503, detail=<unavailable msg>)` when policy is unavailable.
- **Worker (`SDWorker`):** a helper `_reject_generation(image_request, message)` that calls
  `self.handle_error(message)` (logs the generic string only), stops the progress bar, calls
  `image_request.callback(message)` when present, and emits
  `self.api.worker_response(code=EngineResponseCode.ERROR, message=message)`. It must **not** call
  `send_missing_model_alert` (wrong title/path) and must **not** log the request.
- **LLM tool (optional pre-check):** return
  `json.dumps({"status": "rejected", "message": <prohibited msg>})` without calling
  `api.art.llm_image_generated(...)`.
- **GUI:** no new UI. The existing worker-error surfacing shows the generic message.
- The rejection reason code (`"prohibited"` / `"unavailable"`) may be logged; the input may not.

---

## 4. Interfaces (frozen contracts for the subtasks)

```python
# content_safety/decision.py
@dataclass(frozen=True)
class ContentDecision:
    allowed: bool
    reason: str          # "ok" | "prohibited" | "unavailable" | "disabled" | "empty_policy"

# content_safety/errors.py
class ContentSafetyError(Exception): ...
class ProhibitedContentError(ContentSafetyError): ...       # generic message only
class ContentSafetyUnavailableError(ContentSafetyError): ... # generic message only

# content_safety/matcher.py
def check_text_fields(fields: Sequence[str], *, enabled: bool) -> ContentDecision: ...
def enforce_content_safety(fields: Sequence[str], *, enabled: bool) -> None: ...
    # raises ProhibitedContentError | ContentSafetyUnavailableError; returns None when allowed
def reset_cache() -> None: ...   # test hook

# content_safety/normalization.py
def normalize_tokens(text: str) -> list[str]: ...
def candidate_strings(tokens: Sequence[str], *, ngram_min: int = 1,
                      ngram_max: int = 3, unigram_min_length: int = 4) -> Iterator[str]: ...
def hash_candidate(s: str) -> str: ...
NORMALIZATION_VERSION: str  # "v1"

# content_safety/policy_data.py
POLICY_DATA_ENV_VAR: str     # "AIRUNNER_CONTENT_SAFETY_DATA"
POLICY_DATA_FILENAME: str    # "data/policy_terms.sha256.json"
def load_policy_hashes(*, refresh: bool = False) -> frozenset[str]: ...

# application_exceptions.py (art side)
class SafetyCheckUnavailableError(Exception): ...
```

Generator script contract (`scripts/build_content_safety_hashes.py`):

```
--terms PATH        plaintext list, one entry per line (default: $AIRUNNER_CONTENT_SAFETY_TERMS)
--out PATH          output JSON (default: services/src/airunner_services/content_safety/data/policy_terms.sha256.json)
--emit-empty        write an empty-hash file (used to regenerate the committed default)
--check             verify --out matches what --terms would produce; exit non-zero on drift; write nothing
--force             required if --terms resolves inside the repository tree
```

- Reads each line, skips blanks and `#` comments, runs the **same** `normalization` +
  `candidate_strings` + `hash_candidate` from `content_safety`, unions the hashes.
- Output: UTF-8 JSON exactly per §3.5, `indent=2`, `sort_keys=True`, one trailing newline.
- **Deterministic:** same input → byte-identical output. **No timestamps**, no source path, no
  counts embedded.
- Prints **counts only** (lines read, hashes written). Never prints an entry.
- `--check` prints only `OK` / `DRIFT`.

---

## 5. File-level work breakdown (ordered subtasks for Code mode)

Each subtask is independently reviewable and must honor the interfaces in §4. Commit per subtask.

### S-1 — `content_safety` core package (matcher, normalization, loader, errors) + tests

**New files** under [`services/src/airunner_services/content_safety/`](services/src/airunner_services/content_safety/):
`__init__.py`, `decision.py`, `errors.py`, `normalization.py`, `policy_data.py`, `matcher.py`,
`data/policy_terms.sha256.json` (empty `hashes`), plus
[`services/tests/test_content_safety_matcher.py`](services/tests/test_content_safety_matcher.py)
and [`services/tests/test_content_safety_no_plaintext.py`](services/tests/test_content_safety_no_plaintext.py).

**Deliverable:** §3.4 normalization, §3.5 loading, §3.6 input-gate semantics, and the §4 interface,
with the committed data file shipping **empty**. Stdlib-only.

**Interface it must honor:** the exact function signatures in §4. **Blocks S-2 and S-3.**

**Must not:** echo any field content in messages or logs; contain any non-generic string literal;
add a dependency.

### S-2 — Out-of-band generator script + tests

**New files:** [`scripts/build_content_safety_hashes.py`](scripts/build_content_safety_hashes.py),
[`services/tests/test_build_content_safety_hashes.py`](services/tests/test_build_content_safety_hashes.py);
one entry in [`scripts/README.md`](scripts/README.md).

**Deliverable:** the contract in §4. Imports normalization/hashing from S-1 (no duplicated
algorithm). Default term path is env-driven and expected to live **outside** the repo or under a
gitignored path (`tmp/`), enforced by the `--force` guard.

**Interface it must honor:** §4 generator contract; schema identical to §3.5.

**Depends on S-1** (reuses its normalization + hashing).

**Must not:** contain any term; print entries; embed timestamps; write outside the repo except to the
operator-specified `--out` (which may point outside only via `AIRUNNER_CONTENT_SAFETY_DATA`-style
operator paths).

### S-3 — Wire the input gate into the daemon choke points + LLM tool pre-check + tests

**Files changed:**
[`services/src/airunner_services/workers/sd_worker.py`](services/src/airunner_services/workers/sd_worker.py:597)
(add the gate + `_reject_generation` helper at the top of `_generate_image`),
[`services/src/airunner_services/api/routes/art_generation_start_routes.py`](services/src/airunner_services/api/routes/art_generation_start_routes.py:39)
(gate in `create_generation_job`/`generate_image`),
[`services/src/airunner_services/llm/tools/image_tools.py`](services/src/airunner_services/llm/tools/image_tools.py:143)
(optional pre-check). **New test:**
[`services/tests/test_content_safety_input_gate.py`](services/tests/test_content_safety_input_gate.py).

**Deliverable:** §3.3 call sites and §3.9 surfacing. Read the setting defensively with
`getattr(settings, "content_safety_filter", True)` so S-3 is not blocked by S-5.

**Interface it must honor:** §4 `enforce_content_safety`/`check_text_fields`; generic messages from
§3.9. Catch **only** the two content-safety exceptions (never a broad `except Exception`) so the
block is not swallowed.

**Depends on S-1.**

**Must not:** log the request; restructure the existing dispatch beyond the early-return guard.

### S-4 — Harden the output filter to fail closed (SDXL + Z-Image) + tests

**Files changed:**
[`services/src/airunner_services/application_exceptions.py`](services/src/airunner_services/application_exceptions.py:1)
(add `SafetyCheckUnavailableError`),
[`services/src/airunner_services/art/utils/nsfw_checker.py`](services/src/airunner_services/art/utils/nsfw_checker.py:12)
(raise instead of fail-open when models missing or on error),
[`services/src/airunner_services/art/managers/stablediffusion/base_diffusers_model_manager.py`](services/src/airunner_services/art/managers/stablediffusion/base_diffusers_model_manager.py:196)
(raise when enabled + unavailable),
[`services/src/airunner_services/art/managers/stablediffusion/mixins/sd_image_generation_mixin.py`](services/src/airunner_services/art/managers/stablediffusion/mixins/sd_image_generation_mixin.py:101)
(catch → abort batch before export/canvas). **New test:**
[`services/tests/test_content_safety_output_failclosed.py`](services/tests/test_content_safety_output_failclosed.py).

**Deliverable:** §3.6 output semantics. `use_safety_checker=False` remains a true no-op.

**Independent of S-1/S-2/S-3** (can be worked in parallel).

**Must not:** change the classifier model, its download path, or the `nsfw_filter` setting's
meaning; leave any fail-open branch on the enabled path.

### S-5 — Settings column + migration + `SECURITY.md` docs

**Files changed:**
[`services/src/airunner_services/database/models/application_settings.py`](services/src/airunner_services/database/models/application_settings.py:63)
(add `content_safety_filter`, default `True`), a **new** Alembic revision under
[`services/src/airunner_services/database/alembic/versions/`](services/src/airunner_services/database/alembic/versions/)
using [`add_column`](services/src/airunner_services/database/db/column.py:29),
[`SECURITY.md`](SECURITY.md) (new "Content Safety" section),
[`services/MANIFEST.in`](services/MANIFEST.in) and [`services/setup.py`](services/setup.py) (package
the `data/policy_terms.sha256.json`).

**Deliverable:** §3.7 column + migration; the packaging so the data file ships; a `SECURITY.md`
section that states the feature is **best-effort, not a guarantee**, describes the two layers, the
`content_safety_filter` setting (default on), the out-of-band generation/installation procedure
(`AIRUNNER_CONTENT_SAFETY_DATA`), and that input/prompt content is never logged.

**Independent** of S-1…S-4 for the migration/doc parts; the packaging edit lands after S-1 creates
the data file.

**Must not:** name the prohibited category or any example; include operational term lists.

### S-6 — Verification pass

Run the suites and quality checks (§7) against the merged work and record real output: which paths
are covered, that no fail-open branch remains on the enabled output path, that the matcher is
stdlib-only, and that the committed data file is empty and hash-only.

**Depends on S-1…S-5.**

---

## 6. Test plan (synthetic tokens only — never a real term)

All fixtures are invented neutral tokens (e.g. `alpha`, `widget`, `zorb`). Hashes are computed
inside the test. No fixture, docstring, or commit message contains a real term.

1. **Matcher + normalization (`services/tests/test_content_safety_matcher.py`)**
   - Write a temp policy JSON to `tmp/` (repo-local, gitignored) whose `hashes` are computed in-test
     from neutral tokens; point `AIRUNNER_CONTENT_SAFETY_DATA` at it.
   - Match/no-match for each field independently and as a set.
   - Normalization: case, diacritics, punctuation, leet/digit folding, elongation — each using
     neutral tokens.
   - Schema/edge errors: unknown `schema_version` → `ContentSafetyUnavailableError`; malformed JSON
     → same; env path missing → same; packaged-missing/empty → allow + single warning.
   - **No-disclosure assertion:** the raised exception's `str()` does not contain any matched
     synthetic token.
   - **No-logging assertion:** with a captured logger, assert no log record contains any field
     content (only reason/count).
2. **No-plaintext guard (`services/tests/test_content_safety_no_plaintext.py`)**
   - Load the committed packaged data file; assert every hash matches `^[0-9a-f]{64}$`, that the
     only keys are the schema keys, and that `hashes == []` for the repo default.
3. **Generator (`services/tests/test_build_content_safety_hashes.py`)**
   - Determinism: run twice on one temp input → byte-identical outputs.
   - **No-leak:** reading the output, assert none of the input lines appear as substrings.
   - `--check` returns OK for a matching file and DRIFT for a modified one.
   - In-repo terms path without `--force` is refused.
4. **Input gate integration (`services/tests/test_content_safety_input_gate.py`)**
   - Construct `SDWorker` via `object.__new__` with a fake `api`/`generator_settings` (pattern in
     [`art_service_runtime_probe.py`](services/src/airunner_services/tests/functional/art_service_runtime_probe.py:123)).
     With a temp policy that triggers on a synthetic field, assert: `_generate_image()` returns via
     the reject path, `handle_error` receives the generic message, `worker_response` emits
     `EngineResponseCode.ERROR`, and the model-load / export paths are **not** reached.
   - Route: FastAPI `TestClient` against the art router with the matcher pointed at the temp policy;
     assert `422` with the generic detail and that the body contains no synthetic token.
   - Tool pre-check (if implemented): assert a triggering synthetic prompt yields the
     `{"status": "rejected", ...}` JSON and that `llm_image_generated` is not called.
5. **Output fail-closed (`services/tests/test_content_safety_output_failclosed.py`)**
   - `use_safety_checker=True` + `_safety_checker=None` → `SafetyCheckUnavailableError`.
   - Classifier raising → `SafetyCheckUnavailableError`.
   - `use_safety_checker=False` → unchanged, no raise.
   - `_generate()` abort: on an `object.__new__` manager with no-op `_load_prompt_embeds`,
     `_prepare_data`, a fake `_get_results` yielding one image, and a checker that reports
     unavailable, assert the export queue is not called and `worker_response(ERROR, <generic>)` is
     emitted. Skip with the project's existing torch-skip pattern if torch is unavailable.
   - A symmetry check that the Z-Image manager resolves `_generate()` through the same base path
     (class-hierarchy assertion, no GPU needed).

Sensitive strings never appear in any test artifact. `tmp/` is used for temp files (never `/tmp`).

---

## 7. Verification checklist (S-6)

From the repo root, with the project venv:

- `./venv/bin/python scripts/run_tests.py --unit` — green.
- Services tests: `services/tests/` and `services/src/airunner_services/tests/` — green (or the
  project's documented services target); record the exact command and output.
- Import smoke (stdlib-only, no torch/PySide) of every changed/created module.
- `./scripts/security_audit.sh` (or the repo's documented security check) — no new findings.
- Confirm by inspection + grep that the new paths contain **no** content logging and that only the
  generic messages from §3.9 are emitted.
- Confirm the committed `policy_terms.sha256.json` is hash-only and empty.
- Confirm the output path has **no** fail-open branch when the filter is enabled.
- `git status` clean apart from intended files; one commit per subtask; each commit message
  references the subtask and contains no term.

---

## 8. Acceptance criteria

1. `content_safety` imports and unit-tests run in the lean, torch-less CI venv (stdlib-only).
2. The input gate blocks prohibited input on both the GUI signal path and the LLM tool path via the
   `SDWorker._generate_image()` choke point, and the HTTP route returns `422` (match) / `503`
   (unavailable) with generic detail.
3. No prompt/field content is logged or included in any error string/message on the new paths.
4. The output filter fails closed: enabled + checker missing/erroring → generation aborts with a
   generic error and neither exports nor hands an image to the canvas; applies to SDXL and Z-Image;
   covered by relocation of a mid-session unload.
5. The committed policy data file is hash-only and empty; the generator produces deterministic,
   term-free output from an out-of-repo input and contains no terms itself.
6. `SECURITY.md` has a "Content Safety" section framing the feature as best-effort and documenting
   the setting, the out-of-band installation path, and the no-content-logging guarantee.
7. The `ApplicationSettings.content_safety_filter` column exists (default `True`) with a migration;
   the packaged data file is included in the built wheel/sdist.
8. The repository contains **no** term from the prohibited category anywhere (code, comments, tests,
   fixtures, docs, commits).

---

## 9. Risks and mitigations

- **Empty default policy (no protection out of the box).** Inherent to the constraint that no term
  may be committed. *Mitigation:* documented operator step (generate + install via
  `AIRUNNER_CONTENT_SAFETY_DATA` or a private build) in `SECURITY.md`; a once-only startup warning
  when the policy set is empty.
- **Reversibility of short hashes.** A single common word's SHA-256 can be recovered by dictionary
  attack. *Mitigation:* hash multi-token n-grams and skip short unigrams; document as best-effort.
- **Over-blocking false positives** from homoglyph folding / run collapsing. *Mitigation:* collapse
  only runs ≥ 3; keep the normalization versioned so it can be revised; operators can rebuild the
  set.
- **Per-request cost.** N-gram generation is `O(tokens × ngram_max)`; fine for prompts. *Mitigation:*
  cache the loaded hash set; avoid re-reading the file per request.
- **Output fail-closed could newly block users** whose checker download previously failed silently.
  *Mitigation:* intentional per requirement; the existing `nsfw_filter` disable toggle (with its
  confirmation dialog) remains the documented escape hatch; call this out in the release notes.
- **Migration omission** for the new column. *Mitigation:* S-5 ships the migration via the existing
  `add_column` helper; S-3 reads the setting defensively so it works before the migration lands.
- **Broad exception handlers** in the worker could swallow the rejection. *Mitigation:* place the
  gate before the existing try/except and catch only the two content-safety exceptions.
- **GitHub scanning of prose.** Even without terms, feature descriptions can look suspicious.
  *Mitigation:* generic wording throughout (this document is the template).

---

## 10. What to report back

For the completed work, report: files changed per subtask; the exact test commands and their real
output; confirmation that the matcher is stdlib-only; that the committed data file is empty and
hash-only; that no fail-open branch remains on the enabled output path; that no content is logged on
the new paths; and any residual uncertainty. State explicitly if any gate could not run in the
environment and why.
