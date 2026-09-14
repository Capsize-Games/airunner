# Review of the second agent's Linux v1 manifest

**Overall verdict: FAIL — do not approve this batch for merge as a whole.**

Reviewed the [15-item report](https://claude.ai/code/artifact/df67ff60-0af5-4a17-ae7e-e8fa748acbd8), the corresponding GitHub diffs, relevant surrounding code, original issue requirements, and the supplied regression tests. All PR heads were checked again at the end and were unchanged from the reviewed snapshots. Nothing was merged or modified in the application. The older Spark correction automation was paused to prevent overlapping edits.

A PASS below means the scoped change passed this review, not that the complete application is qualified for release. HOLD means the proposal cannot yet be accepted as a completed gate; it does not imply an observed runtime failure.

## Verdicts

| PR | Issue | Verdict | Reason |
|---|---|---|---|
| [2152](https://github.com/Capsize-Games/airunner/pull/2152) | R03 | PASS | Correct replacement paths and the requested test-authorization wording are present. |
| [2153](https://github.com/Capsize-Games/airunner/pull/2153) | S01 | PASS | Shared auth policy applied before WebSocket accept/runtime lookup; focused tests pass. |
| [2154](https://github.com/Capsize-Games/airunner/pull/2154) | R01 | FAIL | Incorrect coverage mappings and at least one nonexistent implementation anchor remain; see F7. |
| [2155](https://github.com/Capsize-Games/airunner/pull/2155) | S02 | FAIL | Omitted/null output limit remains uncapped at this boundary; raw message-size bound is incomplete; F4. |
| [2156](https://github.com/Capsize-Games/airunner/pull/2156) | P01 | FAIL | A source-distribution build fails importing the omitted build helper; F1. |
| [2157](https://github.com/Capsize-Games/airunner/pull/2157) | D01 | FAIL | Digest checking is not connected to ordinary curated downloads; mutable branch names remain; F3. |
| [2158](https://github.com/Capsize-Games/airunner/pull/2158) | D03 | PASS | Batch bytes, indexed retrieval, status count and GUI bridge were updated consistently; 14 focused tests pass. Actual model/GUI acceptance remains outstanding. |
| [2159](https://github.com/Capsize-Games/airunner/pull/2159) | D04 | FAIL | Rejects zero CFG, a supported Z-Image Turbo setting; F5. |
| [2160](https://github.com/Capsize-Games/airunner/pull/2160) | O01 | PASS, scoped | Central fetch gate and non-frozen exceptions pass focused checks. This is explicitly partial egress coverage, not proof of complete offline operation. The report's default-behavior decision remains separate from code review. |
| [2161](https://github.com/Capsize-Games/airunner/pull/2161) | O02 | FAIL | Offline errors direct users to a UI setting that cannot clear the new global offline flag; F6. |
| [2162](https://github.com/Capsize-Games/airunner/pull/2162) | O03 | FAIL | Diagnostics export retains prompt/transcript/secret canaries; F2. |
| [2163](https://github.com/Capsize-Games/airunner/pull/2163) | D02 | FAIL | Missing identity permits mixed bytes; same-sized stale partial is promoted without checking identity; F3. |
| [2164](https://github.com/Capsize-Games/airunner/pull/2164) | R02 | HOLD | Useful proposed matrix, but required driver/compute floor, system RAM, immutable model identities and disk evidence remain incomplete. Pending hardware results are appropriate; they do not substitute for the missing specification evidence. |
| [2165](https://github.com/Capsize-Games/airunner/pull/2165) | B01 | FAIL as design gate | Cancellation has no callable interface; existing Desktop conversations are incorrectly assumed absent; worked example drops the user turn; F9. |
| [web 221](https://github.com/Capsize-Games/airunnerweb/pull/221) | W01 | FAIL | Frozen source contradicts cloud-only claim; tests are classified without inspection and capability characterization is incomplete; F8. |

## Findings and required corrections

### F1 — P1: P01 breaks builds from the source distribution

At `b4349859cd86edac6f74073d62cda552cf8eff75`, `setup.py:117` imports `build_ui` from a sibling `scripts` directory during `build_py`. The source archive contains neither `scripts/build_ui.py` nor `scripts/process_qss.py`.

Reproduced in an isolated checkout: `python setup.py sdist --dist-dir ...` succeeds; extract that archive, then run `python setup.py build_py`: exit 1, `ModuleNotFoundError: No module named 'build_ui'`. This is an actual build regression, not merely a missing test.

Additionally, importing the verifier transitively imports PySide6 through `process_qss`, while isolated build requirements list only setuptools/wheel. The new check verifies existence, not freshness, and does not itself compile resources.

Required: make the generation/verification tooling available in the sdist, define build dependencies and generation ordering, and exercise the sdist-to-wheel path. Keep pure verification independent of GUI imports where possible. Do not count synthetic placeholder-file tests as build-artifact validation.

### F2 — P1: O03 exports sensitive exception content

At `26cc59be7473ae1955fa901f29c7ece6c273321d`, `src/airunner/crash_handler.py:218-224` strips indentation, then includes sanitized exception messages in the export. Redacting recognizable URLs/paths/tokens cannot remove arbitrary user content. `line.strip()` also contradicts the claimed exclusion of indented lines. The generic token pattern does not match plain `token=`.

Executed the exact committed parser/sanitizer functions using neutral strings:

| Input | Exported message |
|---|---|
| `ValueError: prompt=NEUTRAL_PRIVATE_PROMPT_CANARY` | `prompt=NEUTRAL_PRIVATE_PROMPT_CANARY` |
| `RuntimeError: transcript=NEUTRAL_PRIVATE_TRANSCRIPT_CANARY` | `transcript=NEUTRAL_PRIVATE_TRANSCRIPT_CANARY` |
| Indented `ValueError: NEUTRAL_SOURCE_CANARY` | `NEUTRAL_SOURCE_CANARY` |
| `ValueError: token=NEUTRAL_SECRET_CANARY_123456` | `token=NEUTRAL_SECRET_CANARY_123456` |

Required: export an allowlisted structured set of failure codes and non-content metadata; do not copy arbitrary exception messages. Add canaries for ordinary user text, indented content and generic secrets. Keep user inspection before sharing. Expanding credential regexes alone cannot satisfy the content-exclusion requirement.

### F3 — P1: D01/D02 do not establish immutable download identity

D01 at `3ca1f86d8f503ea8181e8514ffbf191befea054d`: ordinary calls at worker lines 230-238 and 553-579 pass a revision but never a checksum. `expected_sha256` defaults to `None`; its checking branch is principally exercised by direct helper tests. No curated checksum metadata is added. `main` and `fp16` are mutable branch names, not immutable artifact identities. File discovery also calls `get_model_files(repo_id)` without the resolved revision.

D02 at `a2714120ff1e9652725fbcf408d8539a0658d71b`: the 206 path explicitly accepts either missing stored identity or missing response identity. The pre-request shortcut still promotes any temporary file whose size is at least the expected size. Without a checksum it never checks whether those bytes belong to the requested artifact.

Executed the exact committed download methods against a fake transport and temporary files:

- Four old bytes `OLD!`, no identity sidecar, then a valid-looking 206 carrying `NEW!`: promoted `OLD!NEW!` and marked complete.
- An eight-byte stale temp file `STALE123` with expected size eight: promoted it and marked complete with **zero transport calls**.

Required: propagate an immutable revision and digest from curated metadata through discovery, retry and finalization. Store artifact identity with partial state. Restart/reject unverifiable partials; verify complete-looking temp files too. Validate the complete Content-Range rather than only its starting offset. Preserve explicit custom-model status without calling it verified.

### F4 — P1: S02 leaves output and wire-size gaps

At `e4f6b12ff298ad16ccba196be264a0dedf7f7f1f`, `llm_contracts.py:148` checks the output ceiling only when `max_tokens` is non-null. Both omission and explicit null pass through as `None`; `llm_runtime.websocket_envelope` forwards that value. This endpoint therefore does not enforce its advertised 4096-token ceiling for the default request; downstream configuration decides the eventual limit.

The parser also accepts a 20,037-character JSON request containing a short message plus an ignored 20,000-character field despite the advertised 16,000-character message setting. `receive_json()` parses the full frame before this check. Invalid JSON reaches the generic error path without the deterministic validation code.

Required: resolve omission/null to a bounded output default; enforce wire and prompt limits distinctly before expensive parsing/inference; handle malformed JSON with a fixed code. Add route-level tests covering omitted/null caps and oversized non-prompt fields.

### F5 — P1: D04 rejects a supported model configuration

At `d7a42e4984757707bb15c9331703cadaac32cff7`, `GenerationRequest.cfg_scale` uses `gt=0`. A neutral request with `cfg_scale=0.0` is rejected with a Pydantic `greater_than` error.

The existing `services/src/airunner_services/art/managers/zimage/mixins/zimage_generation_mixin.py:92` explicitly describes Z-Image Turbo's zero-guidance setting; the native pipeline defaults to `guidance_scale=0.0`. The GUI bridge forwards the request's scale into `cfg_scale`.

Required: allow zero where the selected model supports it and use model-aware validation. Add a supported-model request regression test, not only generic boundary tests. Continue rejecting non-finite and excessive values.

### F6 — P2: O02's recovery instruction cannot restore online access

At `c1eca1f2c6e308b62ab6cb9ba2b63fb4f81db503`, `downloads/service.py:53-58` directs users to Preferences > Privacy & Security when global offline mode blocks a download. But `downloads/policy.py:59-60` returns false before consulting those preferences. The global setting is loaded from `AIRUNNER_OFFLINE_MODE`, with no corresponding GUI bridge in this stack.

Required: either wire an explicit user-controlled global online setting consistently across processes, or provide the actual environment/restart instructions until that UI exists. Exercise the real enable-then-download flow. Do not claim the existing provider checkboxes can override global offline mode.

### F7 — P2: R01 still has misleading coverage evidence

At `3dac98c40afd367ac7210f54e057be2948dadd09`:

- RAG-05 cites nonexistent `services/src/airunner_services/llm/managers/mixins/rag_indexing_mixin.py`.
- ART-06 assigns VRAM/budget coverage to `test_loading_watchdog.py`; its tests cover watchdog release/progress/generation interruption, not memory-budget calculation.
- ART-04 says filters are not explicitly named by Q02 and proposes another ticket. Q02's existing outcome explicitly includes filters.
- The matrix omits the separately exposed art text-embedding management workflow while claiming every discoverable feature.

Required: repair source and scenario mappings, include omitted features, and compare proposed gaps with existing issue bodies. A file's existence is not evidence that its tests cover the claimed behavior.

### F8 — P2: W01's frozen-source conclusions are unreliable

At web PR head `95400cb38b`, the document pins source `8157628abfd99f8305db754ca640e4a870d046ed` and claims all stages are cloud-only. That exact source's `projects/uwuchat/server/ai_pipeline.py:65-86` documents and implements `AIRUNNER_LLM_PROVIDER`/`AIRUNNER_LLM_MODEL` overrides for text-generation pipelines. Embeddings are explicitly treated separately. This is a default-cloud configuration, not proof that local text inference is unavailable.

The reference labels tests “confirmed deterministic” or “confirmed real-model-dependent” while acknowledging classification from names without reading bodies. It leaves tool classification, recall and other required capability details uncharacterized. Local dialogue changes explicitly identified in the original audit are not reconciled with the chosen reference.

Required: characterize the selected commit accurately, inspect the relevant tests, identify concrete neutral fixtures/test IDs, finish or explicitly split missing bot behavior, and resolve which local changes belong in the port reference. Do not build downstream contracts on the cloud-only assertion.

### F9 — P1 design gate: B01 cannot yet guide the dependent port safely

At `92df7770b68a5841aa6d5738881d12ed3ff908d3`:

- `CancellationRequest` exists but `CompanionInferenceClient` exposes only `stream()`. The example says cancellation is delegated without specifying a callable contract, ownership or how its ID maps to an in-flight runtime request. Implementations cannot express cancellation through the declared interface.
- `memory_repository.py:41-43` and the design document justify dropping conversation identity by saying Desktop has no multi-conversation concept. Desktop has a persisted `Conversation` model and conversation-history/current-conversation behavior. Compatibility/migration must be decided explicitly rather than erased by that assumption.
- The worked example reads limited recent history, uses its length as a persistent turn index, and persists only the assistant reply. Once history reaches its limit, the proposed index repeats; the current user message is absent from the persisted turn sequence used by later memory work.
- The import-purity test imports the companion package at module scope before taking its before/after module snapshot, so that test cannot prove its stated import-isolation property.

Required before B02-B16: specify cancellation, conversation/session ownership and migration, correct user/assistant persistence and monotonic indexing, and verify import isolation in a fresh process. Resolve the W01 factual errors first. These are design corrections; the inert interfaces have not yet caused a demonstrated production failure.

## Verification and limits

Ran each new regression suite in a separate process at its exact Desktop PR commit, using a dedicated detached review checkout and temporary application/database paths. Existing venv dependencies were reused; no installation, GUI launch, inference, model downloads, live DB access or paid API calls. All **123 tests passed**:

| Suite | Passed |
|---|---:|
| S01 | 9 |
| S02 | 8 |
| P01 | 6 |
| D01 | 7 |
| D03 | 14 |
| D04 | 28 |
| O01 | 10 |
| O02 | 14 |
| O03 | 12 |
| D02 | 6 |
| B01 | 9 |

Command shape: `AIRUNNER_TEST_NO_GUI_LAUNCH=1 AIRUNNER_HEADLESS=1 <existing venv>/python -m pytest services/tests/test_release_<id>.py -o addopts='' -q -p no:cacheprovider`, with temporary data paths and PYTHONPATH pointing exclusively to that Desktop snapshot. W01 is a documentation review; no web test runtime was launched.

Supplemented those tests with the source-archive build and neutral parser/download/configuration reproductions above. Passing the submitted tests does not cover those omitted scenarios. Did not run full repository regressions, the installed Qt application, GPU acceptance, safety-model efficacy or legal review. No claim of release readiness is warranted.

Exact PR metadata/diffs, test logs, runner and build artifacts are retained locally at `/tmp/airunner-manifest-review/`. Reviewed heads are recorded in `manifest-review-heads.json` alongside this report. Ordinary workspaces were preserved.
