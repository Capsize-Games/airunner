# RAG extraction audit

Status: audit and recommendation for the repository-split work tracked in
[#2185](https://github.com/Capsize-Games/airunner/issues/2185). No code
changes are required by this document alone. Written 2026-09-19 against
`5d5a5685d`.

## Question

The repository is being split into smaller repositories by functionality.
Does it make sense to split RAG (retrieval-augmented generation) capability
into its own repository, and is RAG already inside the LLM daemon
repository?

## Answer

**RAG is already inside the LLM daemon package, and that is the right place
for it. Do not extract RAG into its own repository now.**

RAG has no separate package or repository. It lives inside
`services/src/airunner_services/llm/` — the daemon's LLM subsystem — and is
composed directly into the daemon's central `LLMModelManager`. It is not a
leaf, not a vendored library, and not dev-only, so it does not match the
shape that justified the extractions already completed under #2185.

The real problem a RAG split is trying to solve (duplication and blur inside
the RAG code) is better fixed in place. The concrete follow-ups are in
[Recommended next steps](#recommended-next-steps).

## Topology

The split tracker #2185 targets a strictly downward dependency graph,
enforced by [`scripts/check_import_boundaries.py`](../scripts/check_import_boundaries.py:1):

```text
airunner            -> airunner_services, airunner_native
airunner_services   -> (nothing in this project)
airunner_native     -> airunner, airunner_services
```

`airunner_common` is no longer tracked by the checker: it was extracted to
its own repository and is now an ordinary installed dependency
(`github.com/Capsize-Games/airunner-common`, #2197). Extractions already done
under #2185 are all leaves or vendor/tooling: `airunner-common` (#2197),
`airunner-eval` (#2194), `airunner-tts-vendor` (#2195), and the native
sidecar build tooling (#2196). `airunnerweb` is a separate repository too.

RAG is none of those things: it is a first-class product feature that the
daemon's most central object owns.

## Where RAG actually lives

RAG is not a standalone subsystem; it is a mixin on the daemon's LLM manager.

- [`services/src/airunner_services/llm/rag_mixin.py`](../services/src/airunner_services/llm/rag_mixin.py:13)
  composes six mixins (`RAGPropertiesMixin`, `RAGDocumentMixin`,
  `RAGIndexManagementMixin`, `RAGIndexingMixin`, `RAGSearchMixin`,
  `RAGLifecycleMixin`).
- [`LLMModelManager`](../services/src/airunner_services/model_management/llm_model_manager.py:47)
  inherits `RAGMixin` alongside ~19 other LLM mixins, so the daemon's LLM
  manager **is** the RAG manager — the tool manager is constructed with
  `rag_manager=self`
  ([`component_loader_mixin.py`](../services/src/airunner_services/llm/managers/mixins/component_loader_mixin.py:139)).

### Footprint

Daemon side (`services/src/airunner_services/`), ~7,700 LOC / 37 RAG-named
files:

| Area | LOC |
|---|---|
| `llm/managers/agent/` (engine: `vector_index`, `retriever`, `document_loader`, 6 mixins) | 2,292 |
| `llm/tools/rag_tools_helpers/` | 2,889 |
| `llm/tools/rag_tools.py` | 669 |
| `llm/tools/knowledge_tools.py` | 377 |
| `knowledge.py` | 451 |
| `llm/workers/mixins/rag_indexing_mixin.py` | 383 |
| `llm/tools/research_rag_tools.py` | 252 |
| `llm/managers/request_rag_preparation.py` | 100 |
| `llm/workers/rag_index_status.py` | 101 |
| `llm/rag_mixin.py` | 23 |
| `api/routes/llm_rag_routes.py` | 46 |
| DB models (`rag_settings`, `embedding`, `target_files`, `target_directories`) | 77 |
| `zimreader.py` (knowledge-base ZIM reader) | 101 |

Client side (`src/airunner/`), ~4,300 LOC / 20 GUI files: the document and
knowledge-base UI (`components/documents/` 3,306, `components/knowledge/`
727, `llm/utils/document_extraction.py` 302), plus attachment handling in
`chat_prompt_widget.py`, the model-status RAG unload, and the daemon-client
bridge.

## Coupling that a split would have to cut

1. **Lifecycle coupling.** RAG is invoked inline by non-RAG daemon code:
   the LLM worker
   ([`llm_generate_worker.py`](../services/src/airunner_services/workers/llm_generate_worker.py:178)),
   request preparation
   ([`request_rag_preparation.py`](../services/src/airunner_services/llm/managers/request_rag_preparation.py:15)),
   system-prompt memory context via `kb.search_rag`
   ([`system_prompt_context.py`](../services/src/airunner_services/llm/managers/mixins/system_prompt_context.py:37)),
   and workflow routing. `clear_rag_documents`, `load_file_into_rag`,
   `load_bytes_into_rag`, `load_html_into_rag`, `ensure_indexed_files`,
   `reload_rag`, and `unload_rag` are called on the shared `LLMModelManager`.
2. **Tool-registry coupling.** RAG is an LLM tool category. The daemon's
   tool registry loads `rag_tools`, `knowledge_tools`, `research_rag_tools`,
   and `qa_tools`
   ([`tool_registry.py`](../services/src/airunner_services/llm/core/tool_registry.py:291));
   `ToolCategory.RAG` tools receive the LLM manager as their API. Extracting
   RAG would force a new `airunner_services -> airunner-rag` edge (the
   opposite of the intended downward graph) unless the RAG tools stayed
   behind.
3. **Persistence coupling.** RAG owns SQLAlchemy models and their Alembic
   migrations (`RAGSettings`, `TargetFiles`, `TargetDirectories`,
   `Embedding`), the `rag_index_path` setting, and the `text/rag/db` base
   directory. The daemon's migration chain and persistence registry reference
   them.
4. **No dependency boundary yet.** RAG's distinctive dependencies
   (`langchain-core`, `langchain-huggingface`, `langchain-text-splitters`,
   `sentence-transformers`, `libzim`, `pypdf`, `EbookLib`, `mobi`, `bs4`,
   `rank-bm25`) all live in the single `LLM_NATIVE_REQUIREMENTS` extra
   ([`services/setup.py`](../services/setup.py:127)) — the same extra as
   `llama-cpp-python`, `bitsandbytes`, and `langgraph`. RAG is not even
   isolatable at the install-extra level today, and extracting it would not
   shrink the daemon's dependency graph because LangChain/torch/transformers
   are already shared with the rest of the LLM stack.
5. **The UI cannot move with it.** The client never imports RAG internals —
   it already talks to RAG over the daemon HTTP API
   (`/api/v1/llm/rag/index[/cancel|/status]` via
   [`gui_bridge_mixin.py`](../services/src/airunner_services/daemon_client/gui_bridge_mixin.py:359)
   and `SignalCode.RAG_INDEX_*`). So the engine could move, but 3,300+ LOC of
   document UI plus the desktop-side knowledge store would be stranded in the
   desktop repository, splitting one user-facing workflow across two repos.
6. **Duplication would get worse.** There are already two
   `get_knowledge_base()` implementations — desktop
   [`src/airunner/components/knowledge/knowledge_base.py`](../src/airunner/components/knowledge/knowledge_base.py:84)
   (702 LOC) and daemon
   [`services/src/airunner_services/knowledge.py`](../services/src/airunner_services/knowledge.py:1)
   (451 LOC) — and the RAG signal enums are duplicated between
   [`src/airunner/enums.py`](../src/airunner/enums.py:337) and the installed
   `airunner_common`. A repository split adds a third place for these to
   drift; it does not resolve them.

## Fit against the #2185 extraction criteria

| Criterion | `airunner-common` | `airunner-tts-vendor` | `airunner-eval` | RAG |
|---|---|---|---|---|
| Dependency direction | Foundation leaf, depended on by all | Vendor leaf with a tiny resolver surface | Nothing depends on it | Daemon depends **on** it (not a leaf) |
| Public surface | Stable shared types | Small, deliberately stable | Dev-only | A mixin on the daemon's LLM manager |
| Change cadence | Rare | Upstream syncs | Independent | Lockstep with LLM/agent work (B03/B04, tools, prompts) |
| Unique dependency weight | n/a | Yes (isolated fork) | n/a | No (shares LangChain/torch/transformers) |
| Second consumer | Desktop, daemon, native | Daemon | Developers | None today |

RAG fails every column that mattered for the extractions that were done.

## Recommendation

**Keep RAG in `airunner_services` (the daemon repository).** A repository
split would add cross-repo release-train cost for a subsystem that changes
in lockstep with the LLM, would not isolate any dependency weight, and would
still leave RAG's UI in the desktop repository.

### Recommended next steps

These deliver the benefits a split is usually meant to buy, at a fraction of
the cost, and are the prerequisites that would make any future extraction
mechanical:

1. **Consolidate the duplication.** Collapse the two `get_knowledge_base()`
   implementations and the duplicated RAG signal enums into one owner
   (candidate: `airunner_common`, matching #2188/#2224, or delete the dead
   copy) before considering any new boundary.
2. **Carve a `rag` install extra** in `services/setup.py` out of
   `LLM_NATIVE_REQUIREMENTS` so RAG's third-party deps become install- and
   dependency-isolatable. This is what makes a future package/repo split
   cheap.
3. **Introduce a `RAGService` interface** (protocol + default daemon
   implementation) so RAG is addressable as an internal service instead of a
   mixin on `LLMModelManager`. This decouples RAG from the LLM manager and is
   independently valuable for testability and the B04 embedding-runtime work.
4. **Revisit extraction only on a second consumer.** The same test that
   justified `airunner-common` applies: extract RAG only when something
   outside `airunner_services` needs to consume it — a standalone RAG daemon,
   `airunnerweb`, or another product.

### If extraction happens later, draw the line here

`airunner-rag` would own ingestion, indexing, retrieval, the RAG/QA/research
tools, and the RAG database models. The daemon would keep LLM orchestration
and call into it through the `RAGService` interface; the desktop repository
would keep all UI and continue to reach RAG only over the daemon HTTP API.

## Execution log (2026-09-19)

### Step 2 — `rag` install extra: DONE

`services/setup.py` now carries `RAG_REQUIREMENTS` (`sentence_transformers`,
`libzim`, `langchain-huggingface`, `langchain-text-splitters`, `EbookLib`,
`mobi`, `pypdf`) and a standalone `rag` extra. The `llm-native` and `llm`
extras still include `RAG_REQUIREMENTS`, so **every existing extra resolves
the same dependency set** — the change is additive isolation, not a removal.
`beautifulsoup4`, `rank-bm25`, `sumy`, and `langchain-core` were deliberately
left in the LLM core list because non-RAG code imports them.

Verified by:
- `services/tests/test_rag_dependency_isolation.py` (new, 4 tests).
- `services/tests/test_dependency_constraints.py` + `test_import_boundaries.py`.

A true reduction (dropping RAG deps from `llm-native` so a bare `llm-native`
install no longer pulls them) is a deliberate follow-up: `llm-native` is
consumed directly by Docker profiles, CI, and the README, so those consumers
must add `rag` in the same change.

### Step 3 — `RAGService` port: first slice DONE

`services/src/airunner_services/llm/rag_service.py` defines a
dependency-light `typing.Protocol` naming the RAG operations the daemon
calls (search/index/load/unload). It is additive — nothing is rewired yet —
and `services/tests/test_rag_service_interface.py` pins `RAGMixin` (and
therefore `LLMModelManager`) to it, including parameter names, so the port
and implementation cannot drift.

Remaining (the actual decoupling): make `LLMModelManager` hold a
`RAGService` instance instead of inheriting `RAGMixin`, and route the
worker/request/tool call sites through it. That is a multi-file change to
the daemon's core manager and is deliberately not bundled into this pass.

### Step 1 — duplication consolidation: NOT landed (blocked on decisions)

Investigation found the two knowledge bases are **not** mechanical copies;
consolidating them needs decisions, not a blind edit:

1. **Divergent persistence.** Services' `_register_knowledge_documents` uses
   a direct SQLAlchemy session
   ([`airunner_services/database/session.py`](services/src/airunner_services/knowledge.py:395)),
   while the desktop copy uses `ensure_document_record`
   ([`components/documents/data/document_records.py`](src/airunner/components/knowledge/knowledge_base.py:630)).
   Choosing one path for both runtimes is a design decision about the
   desktop/documents DB boundary.
2. **Separate tenancy.** The two `get_knowledge_base()` accessors read
   different `ContextVar`s — desktop
   [`airunner.components.data.tenant`](src/airunner/components/data/tenant.py:31)
   vs services
   [`airunner_services.data.tenant`](services/src/airunner_services/data/tenant.py:31)
   — so unifying the accessors before unifying tenancy would break tenant
   isolation. This is the security-sensitive part.
3. **Latent bug in both copies.** `_is_duplicate_fact` extracts entities
   from the *wrong* string (services: the lowercased normalized text;
   desktop: a stale loop variable), so the >80% entity-overlap duplicate
   check can never fire as intended. A correct consolidation must pair each
   normalized fact with its raw line.
4. **The enum half is cross-repo.** RAG signal codes live in the now-external
   [`airunner-common`](https://github.com/Capsize-Games/airunner-common)
   package (`airunner_common.contract_enums.SignalCode`), while the desktop
   keeps its own `SignalCode` in
   [`src/airunner/enums.py`](src/airunner/enums.py:337). The two have drifted:
   the desktop's `RAG_UNLOAD_SIGNAL` has no counterpart in `airunner-common`
   and no daemon handler, so the desktop's "unload RAG" emit is not acted on.
   Fixing this requires a change to the `airunner-common` repository, not
   this one.

Proposed bounded work order (each its own change, with tests first):

1. Add characterization tests for the desktop `KnowledgeBase` (none exist),
   including the entity-overlap dedup path.
2. Fix `_is_duplicate_fact` to extract entities from each raw line in
   services, then port the same fix through the consolidation.
3. Unify the two `data.tenant` modules (or have the desktop re-export the
   services one) while proving tenant isolation with tests.
4. Decide the single `_register_knowledge_documents` path.
5. Reduce the desktop module to the accessor + tenant helper, delegating the
   class to the services implementation.
6. Separately, add `RAG_UNLOAD_SIGNAL` to `airunner-common.contract_enums`
   and a daemon handler, in that repository.

### Step 1 — duplicate-check correctness fix: DONE

The latent `_is_duplicate_fact` bug from point 3 above is fixed in both
copies. Each normalized fact is now paired with its own raw line before
entity extraction, so the >80%-entity-overlap strategy actually fires:

- services: [`airunner_services/knowledge.py`](../services/src/airunner_services/knowledge.py:142)
- desktop: [`components/knowledge/knowledge_base.py`](../src/airunner/components/knowledge/knowledge_base.py:219),
  which also gained a shared `_extract_entities` helper mirroring the
  services one so the two copies stop drifting on this check.

Covered by [`services/tests/test_knowledge_dedup.py`](../services/tests/test_knowledge_dedup.py:1)
and [`src/airunner/components/knowledge/tests/test_knowledge_dedup.py`](../src/airunner/components/knowledge/tests/test_knowledge_dedup.py:1).

Still open from the Step 1 work order (deliberately not done unsupervised,
because it changes live daemon/memory behavior and needs the decisions
above): the full class consolidation (tenant unification + single
document-registration path), and — in the `airunner-common` repository —
the RAG signal enum consolidation and the `RAG_UNLOAD_SIGNAL` daemon handler.

### Incidental fix

`scripts/import_boundary_allowlist.py` recorded the
`airunner_headless.py` → `airunner_native.launcher` import at line 463; the
import is at line 473, so the boundary check and
`services/tests/test_import_boundaries.py` were failing on `master`
independent of this work. The line number was corrected to 473.
