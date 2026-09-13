# Desktop companion contracts and port mapping (B01)

Issue: https://github.com/Capsize-Games/airunner/issues/2118 (B01). Parent: https://github.com/Capsize-Games/airunner/issues/2083. Built on the frozen upstream inventory from [W01](https://github.com/Capsize-Games/airunnerweb/pull/221) (`airunnerweb` commit `8157628abfd99f8305db754ca640e4a870d046ed`).

**Work type note**: B01 is explicitly "a bounded design/mapping gate; reviewer must resolve the interface before dependent code starts." Everything in `services/src/airunner_services/llm/companion/` is interfaces only (`typing.Protocol` + pydantic request/response shapes) — zero business logic. This document, and the code it describes, is a proposal for owner/reviewer sign-off before any B02-B16 implementation begins, not a declaration that the design is final.

## 1. What was built

| File | Contents |
|---|---|
| `services/src/airunner_services/llm/companion/contracts.py` | Stable IDs (`ChatbotId`, `SessionId`, `TurnId`, `CallChainId`), `CompanionTurnRequest`/`CompanionTurnResult`, `CompanionStreamEvent`, `CancellationRequest`, `CompanionError`/`CompanionErrorCode` + 6 named error codes, `ContextBudget`. |
| `services/src/airunner_services/llm/companion/memory_repository.py` | `CompanionMemoryRepository` protocol + `TurnRecord`/`SessionRecord`/`FactRecord`, scoped by `ChatbotId`/`SessionId`. |
| `services/src/airunner_services/llm/companion/scheduler.py` | `CompanionScheduler` protocol + `CompanionJobType` (one member per confirmed background capability) + `CompanionJobRequest`/`CompanionJobHandle`, idempotency-key-bearing. |
| `services/src/airunner_services/llm/companion/tool_dispatch.py` | `CompanionToolDispatcher` protocol + `ToolDispatchRequest`/`ToolDispatchResult`, explicitly bridging to Desktop's existing `llm.core.tool_registry.ToolRegistry` rather than a new tool system. |
| `services/src/airunner_services/llm/companion/inference.py` | `CompanionInferenceClient` protocol + `CompanionInferenceRequest`, explicitly bridging to Desktop's existing `runtimes.registry`/`runtimes.contracts.LLMInvocationRequest` rather than a new model-invocation path. |

All four Protocols are `@runtime_checkable` so a fake/test implementation can be asserted against them directly (`isinstance(fake, CompanionMemoryRepository)`), not just type-checked statically.

**Reuse over invention** — every contract above deliberately reuses an existing Desktop convention instead of inventing a parallel one:
- `CompanionStreamEvent` is shaped like the existing `ipc.messages.StreamDelta` (same `EnvelopeStatus` vocabulary) so a companion turn could be relayed over the existing `/api/v1/llm/stream`-style surface (with its S01/S02 auth and rate-limiting already in place) rather than needing a second wire format and a second security review.
- `CancellationRequest` mirrors the existing `RuntimeAction.CANCEL`.
- `CompanionInferenceClient` explicitly delegates to the existing `RuntimeRegistry`/`LLMInvocationRequest` — no new model-calling code path.
- `CompanionToolDispatcher` explicitly delegates to the existing `ToolRegistry` (`@tool` decorator system) — no new tool-registration system. Desktop's registry already has `ToolCategory.MOOD` and `ToolCategory.KNOWLEDGE` categories, which is a good sign the companion port has a real landing spot rather than needing new taxonomy.
- `TurnRecord`/`SessionRecord` field names match upstream `ConversationTurn`/`ChatSession` field-for-field (minus `user_id` — Desktop is single-user — and minus `conversation_id`/`embedding_enc`, since neither UwUchat nor Desktop has a multi-conversation concept, and B04 owns embeddings separately).

## 2. Worked example: one turn, a tool call, persistence, and a background follow-up

This traces the acceptance criterion's required example end to end using the actual types defined above (illustrative call sequence, not real implementation code — B02/B10/B11/B12 write the real thing):

```python
# 1. A turn request arrives (e.g. from the Qt chat widget via the daemon API).
request = CompanionTurnRequest(
    chatbot_id=ChatbotId(7),
    session_id=None,  # let the repository resolve/start one
    call_chain_id=CallChainId(str(uuid4())),
    message="what's the weather looking like, and remind me what I told you about my trip?",
)

# 2. B02's repository resolves or starts the session (upstream's 4h-gap
#    rotation rule, or a Desktop-chosen threshold -- B02's call).
session = memory_repo.get_or_start_session(request.chatbot_id)

# 3. B10 composes the prompt: recent turns + facts + mood context,
#    trimmed to request.context_budget.
recent_turns = memory_repo.get_recent_turns(
    request.chatbot_id, session.session_id, limit=request.context_budget.max_recent_turns
)
facts = memory_repo.get_facts(request.chatbot_id, limit=request.context_budget.max_facts)
messages = compose_prompt(recent_turns, facts, request.message)  # B10

# 4. B11's classifier (upstream-derived or Desktop-native -- unresolved,
#    see W01 gap) decides a tool call is warranted, then B11's dispatcher
#    executes it through the existing ToolRegistry.
tool_result = tool_dispatcher.dispatch(
    ToolDispatchRequest(tool_name="get_weather", arguments={}, chatbot_id=request.chatbot_id)
)
if tool_result.succeeded:
    messages.append(ChatMessage(role=MessageRole.TOOL, content=tool_result.content))

# 5. B12's inference client streams the actual reply from the *local*
#    Desktop LLM runtime (never a cloud provider by default -- O01/B12).
inference_request = CompanionInferenceRequest(
    call_chain_id=request.call_chain_id, messages=messages,
)
reply_text = ""
async for event in inference_client.stream(inference_request):
    reply_text += event.delta_text
    if event.final:
        break

# 6. B02 persists the completed turn *before* any background follow-up
#    starts (parent spec architecture decision #4: "Store completed
#    turns before background memory work").
turn = memory_repo.append_turn(TurnRecord(
    chatbot_id=request.chatbot_id, session_id=session.session_id,
    role="assistant", content=reply_text, turn_index=len(recent_turns),
    call_chain_id=request.call_chain_id,
))

# 7. B06's scheduler fires bounded, idempotent background work -- fact
#    extraction now; mood/episodic/rolling-compression/curiosity later,
#    at session-rotation, exactly as upstream schedules them (W01 §2/§3).
scheduler.schedule(CompanionJobRequest(
    job_type=CompanionJobType.FACT_EXTRACTION,
    chatbot_id=request.chatbot_id, session_id=session.session_id,
    idempotency_key=f"fact-extract:{turn.turn_id}",
))
```

Cancellation: a caller sends `CancellationRequest(call_chain_id=request.call_chain_id)`; B12's inference client implementation is responsible for mapping that to the same `RuntimeAction.CANCEL` path any other in-flight runtime invocation already uses.

Errors: any step may raise `CompanionError(CompanionErrorCode(code=ERROR_..., detail=..., retryable=...))`. `detail` is caller-safe text (no turn/prompt content embedded), matching the S02 precedent of deterministic, content-free error codes on the existing LLM WebSocket.

## 3. Capability -> contract -> issue mapping

Every capability confirmed in [W01](https://github.com/Capsize-Games/airunnerweb/pull/221)'s inventory (§3 of that document), mapped here to which of the contracts above it uses and which B0x issue implements it. No upstream capability from that inventory is missing from this table — where W01 itself flagged a gap (implementation not located), that gap is carried forward here rather than silently dropped.

| Capability (W01 §3) | Contract(s) used | Desktop issue |
|---|---|---|
| Dialogue turn, complexity-tiered routing | `CompanionTurnRequest`, `CompanionInferenceClient` | [B10](https://github.com/Capsize-Games/airunner/issues/2138), [B12](https://github.com/Capsize-Games/airunner/issues/2141) |
| Tool classification / selection | `CompanionToolDispatcher.available_tools` (filtering step) | [B11](https://github.com/Capsize-Games/airunner/issues/2140) — **W01 flagged the actual upstream classifier implementation as not located**; B11 may need to design this from Desktop's existing tool metadata rather than port an unread implementation |
| Facts: extract / dedupe / retract | `CompanionMemoryRepository.get_facts`/`upsert_fact`, `CompanionJobType.FACT_EXTRACTION` | [B03](https://github.com/Capsize-Games/airunner/issues/2124) (repository), [B07](https://github.com/Capsize-Games/airunner/issues/2137) (extraction/dedup) |
| Session/turn recall | `CompanionMemoryRepository.get_or_start_session`/`append_turn`/`get_recent_turns`, `SessionRecord`/`TurnRecord` | [B02](https://github.com/Capsize-Games/airunner/issues/2120) |
| Narrative memory / episodic summary | `CompanionMemoryRepository.update_session_summary`, `CompanionJobType.EPISODIC_SUMMARY` | [B08](https://github.com/Capsize-Games/airunner/issues/2130) — the upstream `_lexrank_fallback`/`_try_local_runtime` split (W01 §3) is a promising concrete shape for this issue to reuse |
| Rolling compression | `CompanionMemoryRepository.update_session_summary`, `CompanionJobType.ROLLING_COMPRESSION` | [B09](https://github.com/Capsize-Games/airunner/issues/2134) |
| Long-term memory blend | `CompanionJobType.MEMORY_BLEND` | [B09](https://github.com/Capsize-Games/airunner/issues/2134) (cascaded from episodic summary, matching upstream's `MEMORY_UPDATER` trigger) |
| Mood tracking | `CompanionJobType.MOOD_UPDATE`; mood context injected into `compose_prompt` (B10) | [B10](https://github.com/Capsize-Games/airunner/issues/2138) (context injection), [B15](https://github.com/Capsize-Games/airunner/issues/2144) (the update job itself) |
| Curiosity engine | `CompanionJobType.CURIOSITY` | [B15](https://github.com/Capsize-Games/airunner/issues/2144) — **W01 flagged a possible legacy/duplicate `world/curiosity_engine.py`**; resolve which is authoritative before implementing |
| Interjections | Not given a dedicated `CompanionJobType` — **proposed split**: upstream itself disabled this in production (W01 §3: "post-turn interjections... don't make sense at session-end" after the trigger model moved to session-end); recommend B15 treat this as explicitly out of scope for v1 rather than porting a feature upstream turned off, unless the owner decides otherwise | [B15](https://github.com/Capsize-Games/airunner/issues/2144) (decision needed, not implementation) |
| Journal summarizer | Not given a dedicated `CompanionJobType` — **proposed split**: W01 could not locate this capability's implementation (only the pipeline-config entry); recommend a follow-up ticket once/if it's found, rather than guessing at its shape here | [B15](https://github.com/Capsize-Games/airunner/issues/2144) (proposed follow-up) |
| Tool-output validation (`NODE_VALIDATOR`) | Not modeled — **proposed split**: same gap as journal summarizer; `ToolDispatchResult.succeeded=False` already gives a companion turn a way to react to a failed tool call without this, so it may be partially redundant, but that is not confirmed | [B11](https://github.com/Capsize-Games/airunner/issues/2140) (proposed follow-up) |
| Content-risk / safety classification | Deliberately not modeled here at all | Explicitly separate, specialist-gated: [S07](https://github.com/Capsize-Games/airunner/issues/2094)/[S08](https://github.com/Capsize-Games/airunner/issues/2106) |

## 4. Open questions carried forward from W01 (not resolved by this design)

1. Does per-user encryption-at-rest for turns/facts need to carry over to Desktop's local SQLite model? `TurnRecord`/`FactRecord` do not encode an encryption requirement either way — a B02/B03 (and ultimately owner) decision.
2. Does upstream's PII-masking-before-cloud-egress design still apply once local inference is the default? Not modeled in these contracts; would layer in front of `CompanionInferenceClient` for the explicit remote-provider mode only, if the owner decides it's needed.
3. `world/curiosity_engine.py` vs `llm/curiosity_engine.py` — needs resolving before B15 implements `CompanionJobType.CURIOSITY`.
4. Tool classification/selection's real implementation (`route_policy.py`/`tool_selection_plan.py`) was not located in W01 — B11 needs either a deeper upstream read or a Desktop-native design.

## 5. Validation

`services/tests/test_release_b01.py` confirms the `companion` package imports with zero Qt (`PySide6`/`PyQt`), `torch`, SQL driver (`sqlalchemy`/`psycopg`), or `redis` module pulled into `sys.modules`, and that a minimal fake implementation of each Protocol satisfies it via `isinstance()` (the `@runtime_checkable` contracts above). No runtime launch, model load, or database access was used to produce this design.
