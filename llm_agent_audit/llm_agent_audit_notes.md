# LLM Agent Audit — Implementation Notes

Progress log for working through `llm_agent_audit_todo.md`.

---

## Phase 1 — Critical: Security and Production-Blocking Bugs

### 1.1 Remove Debug File I/O from Checkpoint Saver ✅

**File**: `server/src/airunner_services/llm/managers/database_checkpoint_saver.py`

**Changes made:**
- Removed `import sys` inside `get_tuple`
- Removed all 5 `with open("/tmp/checkpoint_debug.log", "a") as f:` blocks (in `get_tuple`: lines ~221-228, ~232-235, ~245-248, ~251-253, ~255-258)
- Downgraded all 7 emoji-decorated `logger.info(f"🔵 ...")` calls to `logger.debug()` using `%s` format
- Fixed remaining f-string `logger.error()` calls to `%s` format

**Notes:**
- The `clear_checkpoints` method already used `f"Cleared checkpoint state..."` style — those were also converted to `%s` format
- No `/tmp/checkpoint_debug.log` file was found to delete on this system (likely only exists on dev machines that ran the server)

---

### 1.2 Harden Custom Tool Execution (exec() Sandbox) ✅

**Files**:
- `server/src/airunner_services/llm/tool_manager.py`
- `server/src/airunner_services/llm/core/code_sandbox.py`

**Changes made:**
- Added `import logging`, `import time`, `ThreadPoolExecutor`, `TimeoutError as FuturesTimeoutError` to `tool_manager.py`
- Added `_security_audit_logger = logging.getLogger("airunner.security.custom_tools")` module-level
- Added `CUSTOM_TOOL_EXEC_TIMEOUT_SECONDS = 10` constant
- `_compile_custom_tool`: wrapped `exec()` in a `ThreadPoolExecutor` with 10s timeout — times out compilation if code hangs
- `tracked_tool`: now logs every invocation to the security audit logger (tool name + timestamp), and wraps execution in a `ThreadPoolExecutor` with 10s timeout
- Fixed closure bug in original `tracked_tool`: added `_tool_record=tool_record, _func=original_func` default args to prevent late-binding capture
- Fixed `logger.error(f"...")` → `logger.error("...", ...)` in the `except` block
- Added docstring warning about sandbox escape risk and subprocess TODO
- `code_sandbox.py`: Added module-level docstring warning about the `__subclasses__` escape path and that this is best-effort mitigation only

**Limitations not fully addressed (for future sprint):**
- `exec()` sandbox is still bypassable via `().__class__.__mro__[-1].__subclasses__()` attribute traversal — full subprocess isolation is the correct fix
- `safety_validated` can still be set directly on the DB record — no admin/owner role gate in the codebase yet (requires DB schema + API changes beyond code scope)

---

### 1.3 Fix RAG Path Traversal ✅

**File**: `server/src/airunner_services/api/routes/llm_runtime.py`

**Changes made:**
- Added `import os` and `from pathlib import Path`
- Added `_DOCUMENTS_ROOT` module-level constant, resolved from `AIRUNNER_DOCUMENTS_ROOT` env var (falls back to `AIRUNNER_BASE_PATH`, then `/tmp`)
- In `_inject_rag_context`: call `Path(file_path).resolve()` for each doc, then check that the resolved path starts with `_DOCUMENTS_ROOT` string; skip + `logging.warning` if outside boundary
- Changed `open(file_path, ...)` to `open(resolved, ...)`
- Changed snippet header from `f"--- Document: {file_path} ---"` (full path) to `f"--- Document: {resolved.name} ---"` (filename only)
- Changed empty-file warning to use `resolved.name` instead of `file_path`

**Notes:**
- `AIRUNNER_DOCUMENTS_ROOT` is the preferred env var; if unset, falls back to `AIRUNNER_BASE_PATH`. Operators should set `AIRUNNER_DOCUMENTS_ROOT` explicitly to a dedicated documents directory rather than the whole base path.
- Used `str(resolved).startswith(str(_DOCUMENTS_ROOT))` for compatibility with Python 3.8 (`.is_relative_to()` requires 3.9+)

---

### 1.4 Fix Knowledge Tool Signal Code Mismatch ✅

**Files**:
- `server/src/airunner_services/contract_enums.py`
- `server/src/airunner_services/llm/tools/knowledge_tools/delete.py`
- `server/src/airunner_services/llm/tools/knowledge_tools/update.py`

**Changes made:**
- Added `KNOWLEDGE_FACT_DELETED = "knowledge_fact_deleted_signal"` to `SignalCode` enum
- Added `KNOWLEDGE_FACT_UPDATED = "knowledge_fact_updated_signal"` to `SignalCode` enum
- `delete.py`: Changed `SignalCode.KNOWLEDGE_FACT_ADDED` → `SignalCode.KNOWLEDGE_FACT_DELETED`
- `update.py`: Changed `SignalCode.KNOWLEDGE_FACT_ADDED` → `SignalCode.KNOWLEDGE_FACT_UPDATED`

**Listener audit:**
- `record.py` correctly uses `KNOWLEDGE_FACT_ADDED` — unchanged
- `utils/application/enum_resolver.py` has a `"KNOWLEDGE_FACT_ADDED"` string entry — this is a string lookup map and does not need new entries for the new signals unless callers need to look up by string (not the case currently)
- No other listeners subscribe to `KNOWLEDGE_FACT_ADDED` in either the Python or TypeScript codebase — the signal fix is safe

---

## Phase 2 — High Priority: Correctness Bugs

### 2.1 Fix Thread-Unsafe Global Workflow State Singleton ✅

**Files**:
- `server/src/airunner_services/llm/agents/workflow_tools.py`
- `server/src/airunner_services/llm/workflow_manager.py`
- `server/src/airunner_services/llm/managers/mixins/streaming_mixin.py`

**Changes made:**
- Replaced module-level `_current_workflow_state: Optional[WorkflowState] = None` with `ContextVar[Optional[WorkflowState]]` named `_workflow_state_var`
- `get_current_state()` / `set_current_state()` / `reset_workflow_state()` now operate on the `ContextVar` instead of the global
- `WorkflowState` TypedDict in `workflow_manager.py`: added `agent_workflow: Optional[Any]` field
- `WorkflowManager.__init__`: added `self._agent_workflow_state = None` instance attribute
- `StreamingMixin._prepare_workflow_run`: before each workflow invocation, creates a `WorkflowState()` if needed and calls `set_current_state(self._agent_workflow_state)` — binding this conversation's state to the current asyncio task context

**Why this works**: `ContextVar` is asyncio-task-safe. Each `stream()` call is an asyncio coroutine with its own context copy. Concurrent conversations cannot share each other's workflow state.

**Not done (future)**: Remove `get_current_state()` / `set_current_state()` / `reset_workflow_state()` in favor of pure `InjectedState` in each tool (requires restructuring all tools to return `Command` objects — deferred).

---

### 2.2 Fix `_checkpoint_state` Cross-Instance Contamination ✅

**File**: `server/src/airunner_services/llm/managers/database_checkpoint_saver.py`

**Changes made:**
- Removed class-level `_checkpoint_state: Dict[str, Any] = {}` and `_stateless_mode: bool = False`
- Added `self._checkpoint_state: OrderedDict[str, Any] = OrderedDict()` in `__init__`
- Added LRU eviction: after writing to `_checkpoint_state`, call `move_to_end()` and pop oldest if `len > _CHECKPOINT_STATE_MAX_SIZE` (100)
- Updated `clear_checkpoints()` and `clear_thread()` to use `self._checkpoint_state` (instance-level) instead of `DatabaseCheckpointSaver._checkpoint_state`
- Removed `clear_all_checkpoint_state()` classmethod (no callers found)
- Removed `set_stateless_mode()` classmethod (no callers found)
- Fixed all remaining f-string `logger.info(f"...")` calls in these methods

**Limitation**: `set_conversation_id()` still creates a new `DatabaseCheckpointSaver` instance, causing the in-memory cache to be lost. The DB fallback handles recovery. Task 3.6 will address the unnecessary rebuild.

---

### 2.3 Fix Default Thread ID Cross-Contamination ✅

**File**: `server/src/airunner_services/llm/workflow_manager.py`

**Change**: `self._thread_id = str(conversation_id) if conversation_id else str(uuid.uuid4())` — replaced `"default"` fallback with a fresh UUID.

---

### 2.4 Enforce `max_history_tokens` Before Inference ✅

**File**: `server/src/airunner_services/llm/managers/database_checkpoint_saver.py`

**Changes made:**
- Added `max_history_tokens: Optional[int] = None` parameter to `__init__`
- Added `_trim_messages(messages)` helper: uses `count_tokens_approximately()` to check total, then trims from the front (oldest first) until within budget; always preserves the last 2 messages; logs when trimming occurs
- Applied `_trim_messages()` in both the in-memory cache path and the DB fallback path of `get_tuple()`
- `WorkflowManager.__init__`: passes `max_history_tokens=max_history_tokens` to `DatabaseCheckpointSaver`
- `WorkflowManager.set_conversation_id()`: also passes `max_history_tokens=self._max_history_tokens`

---

### 2.5 Fix Client: Edit Does Not Truncate Server History ✅

**File**: `client/src/components/chat/ChatView.tsx`

**Changes made:**
- `handleSubmitEdit` now calls `truncateConversation(convId, index)` before `doInference(edited)`
- If server truncation fails, sets an error and returns early (does not proceed with inference)

---

### 2.6 Fix Client: Delete Does Not Wait for Server Confirmation ✅

**File**: `client/src/components/chat/ChatView.tsx`

**Changes made:**
- Made `handleDeleteMessage` async
- Now awaits `truncateConversation(convId, index)` before calling `deleteMessagesAfter`
- On server error, sets an error message and does NOT modify local state

---

### 2.7 Fix Client: Duplicate Message Load After Every Inference ✅

**File**: `client/src/components/chat/ChatView.tsx`

**Changes made:**
- Removed the `listConversations(1)` + `load(id)` block inside `doInference` that ran after every inference
- Replaced with a comment explaining that `appendMessage` already persisted the result and a full reload risks duplicates

**Note**: The server does not currently return `conversation_id` / `message_id` in the `done` WebSocket event. Tracking the assigned conversation ID via `conversationIdRef.current` (set at conversation creation) is sufficient. If the server starts a new conversation implicitly, that case is not handled — but this is the same as before.

---

### 2.8 Fix `put_writes` No-Op — Tool Results Lost on Crash ✅ (partial)

**File**: `server/src/airunner_services/llm/managers/database_checkpoint_saver.py`

**Changes made:**
- `put_writes` now stores `(task_id, writes)` in `_checkpoint_state[thread_id]["pending_writes"]` when in-memory state exists for the thread
- When no in-memory state exists for the thread, logs a `WARNING` so operators know writes are not persisted
- The in-memory pending writes survive within a single process lifetime but are lost on server restart (full DB persistence is the long-term fix)

---

### 2.9 Fix `thinkingBuffer` Cleared While Response Is Still Streaming ✅

**File**: `client/src/features/llm/useLLMWebSocket.ts`

**Change**: When `data.type === "thinking" && data.done === true`, only `setThinkingBuffer("")` is called — `setStreamBuffer("")` is no longer called in this branch. The `onDoneRef.current?.()` and `setStreaming(false)` calls were also removed from the thinking-done path (they should only fire when the full response is done, not just the thinking phase).

---

## Phase 3 — Architecture Cleanup

### 3.1 Remove Unused LangGraph Code ✅

Deleted `server/src/airunner_services/llm/langgraph/` directory (3 files: `graph_builder.py`, `state.py`, `__init__.py`). No external imports of these files were found.

---

### 3.2 Consolidate Dual Workflow State Systems ✅ (partial)

- Added docstring to `WorkflowState` TypedDict in `workflow_manager.py` explaining the two types and why they exist separately
- `agent_workflow: Optional[Any]` field already added in 2.1
- Full inlining of `agents/workflow_state.py` into `workflow_manager.py` is deferred — requires restructuring all workflow tools to use `InjectedState` / `Command` pattern

---

### 3.3 Decide on Long-Running Harness ✅

Chose Option A (remove the dead trigger):
- Removed `_should_use_harness()` method from `tool_classification_mixin.py`
- Added comment with instructions for re-wiring if the feature is needed
- The `long_running/` module itself remains intact (its tools may be used independently)

---

### 3.4 Unify Tool Registration ✅ (partial)

Added deduplication logic to `get_all_tools()` in `tool_manager.py`:
- Builds a `dict[name, tool]` during assembly; factory tools registered first, ToolRegistry tools override on collision
- Logs `WARNING` for any duplicate name in factory list or between factory and registry
- Custom tools override built-ins with a warning

Full migration of 17 hardcoded factory methods to `@tool()` decorator registration is deferred.

---

### 3.5 Consolidate System Prompt Files ✅ (noted, deferred)

Files are relatively small (93-195 lines each). The `system_prompt_mixin.py` already acts as a thin delegation layer. Creating `prompt_builder.py` is a low-risk architectural improvement but adds no correctness value at this time. Deferred to future sprint.

---

### 3.6 Optimize WorkflowManager: Avoid Full Rebuild on `set_conversation_id` ✅

- `set_conversation_id()` now skips `_build_and_compile_workflow()` when the workflow already exists
- Instead, calls `self._workflow.compile(checkpointer=self._memory)` to reattach the new checkpointer only
- Added `force_rebuild: bool = False` parameter for cases that truly need a full rebuild
- Fixed f-string logger calls in `workflow_manager.py`

---

## Phase 4 — Performance and Code Quality

### 4.1 Replace f-String Logging with `%s` Format ✅

Converted all 65 f-string logger calls in `server/src/airunner_services/llm/managers/` using a Python bulk-replace script. All 16 affected files updated. Verified 0 remaining occurrences.

---

### 4.2 Remove `print()` Statements from Production Code ✅

- `tool_manager.py`: Replaced `try/except print(...)` fallback with `self.logger.debug()` + result debug log
- `generation_response_support.py`: Added `_logger = logging.getLogger(__name__)`, converted 4 `print()` calls to `_logger.error()`
- `adapters/mixins/tokenization_mixin.py`: Added `_logger`, converted all 10 `print()` calls to `_logger.warning()` / `_logger.info()` / `_logger.debug()`

---

### 4.3 Fix `merge_streamed_text` O(n²) Worst Case ✅

**File**: `server/src/airunner_services/llm/adapters/chat_gguf_streaming_common.py`

Added `_MAX_OVERLAP = 50` constant. Changed `max_overlap = min(len(existing), len(fragment))` to `min(len(existing), len(fragment), _MAX_OVERLAP)`. Added comment explaining why the cap is safe (streaming duplicates are always short).

---

### 4.4 Add Logging for Tool Call Parsing Fallback Strategy ✅

**File**: `server/src/airunner_services/llm/adapters/chat_gguf_streaming_gpt_oss_tail.py`

- Added module-level `_logger = logging.getLogger(__name__)`
- `_resolved_tool_calls`: logs `DEBUG` for which strategy succeeded
- Logs `WARNING` when falling back from commentary → prefilled → extraction
- Logs `WARNING` when all strategies fail

---

### 4.5 Remove Dead Configuration and Constants ✅

- Removed `AIRUNNER_LLM_USE_OPENAI = False` from `llm_settings.py` (no callers found)
- Removed from `__all__`
- `yarn_target_context` and `auto_extract_knowledge` have DB backing — kept as-is

---

## Phase 5 — Prompt Engineering Improvements

### 5.1 Remove "CRITICAL RULES" / "MUST" Aggression ✅

**File**: `server/src/airunner_services/llm/managers/mixins/system_prompt_action_text.py`

- Replaced "CRITICAL INSTRUCTION" / "CRITICAL RULES" / "CRITICAL CONVERSATION RULES" headers with "Guidelines" / "**Guidelines:**"
- Replaced "You MUST use..." with "Prefer using..."
- Replaced "Do NOT respond without..." with softer guidance
- Replaced "NEVER" / "ALWAYS" with plain language
- Softened `START_WORKFLOW_FORCE_PROMPT` and `SEARCH_WEB_FORCE_PROMPT`

---

### 5.5 Add Personality Interpretation Guidance ✅

**File**: `server/src/airunner_services/llm/managers/mixins/system_prompt_context.py`

Changed bare `f"Personality: {chatbot.personality}"` to a full framing sentence:
```
Embody the following personality in all your responses. Express it through your tone,
word choice, and conversational style — but never break character or make it the topic
of conversation unless asked:
{chatbot.personality}
```

---

## Phase 6 — Client Improvements

### 6.3 Fix IndexedDB Quota Eviction Omits `kbDocuments` ✅

**File**: `client/src/db/evict.ts`

Added `"kbDocuments"` to `EVICTION_ORDER` as the last entry (lowest priority). `kbDocuments` has a `cachedAt` column so `orderBy("cachedAt").limit(EVICT_BATCH)` works correctly.

---

### 6.4 Add Exponential Backoff to WebSocket Reconnect ✅

**File**: `client/src/features/llm/useLLMWebSocket.ts`

- Added `retryCountRef = useRef(0)` and `MAX_RETRIES = 10`
- Both `socket.onclose` and the `catch` block now compute `backoffMs = Math.min(1000 * 2^retryCount + jitter, 30000)` and increment `retryCountRef`
- After `MAX_RETRIES`, sets error "Connection lost — please refresh the page" instead of retrying
- `socket.onopen` resets `retryCountRef.current = 0` on successful connection

**TTS WebSocket** (`client/src/api/chat.ts`) ✅ (session 2):
- Added `_ttsRetryCount = 0` and `_TTS_MAX_RETRIES = 10` module-level variables
- Both `socket.onclose` (non-clean) and the `catch` block apply the same exponential backoff formula
- `socket.onopen` resets `_ttsRetryCount = 0`; `_ttsDisconnect()` also resets it

---

## Session 2 — Continuation (2026-06-08)

### 3.3 Option A — Remove long_running/ Module ✅

**Decision**: User confirmed the harness was built for a "deep research" feature (similar to Google Gemini's), but it's not useful in its current form and should be removed to keep the codebase lean.

**Files deleted**: Entire `server/src/airunner_services/llm/long_running/` directory (~60 Python files + `__pycache__`)

**External references cleaned up**:
- `server/src/airunner_services/llm/tools/__init__.py`: Removed `from airunner_services.llm.long_running import tools as project_tools` and `"project_tools"` from `__all__`
- `server/src/airunner_services/database/models/__init__.py`: Removed all `project_state` imports (DecisionMemory, DecisionOutcome, FeatureCategory, FeatureStatus, ProgressEntry, ProjectFeature, ProjectState, ProjectStatus, SessionState) and their `__all__` entries
- `server/src/airunner_services/llm/managers/mixins/tool_classification_mixin.py`: Removed dead comment block about re-wiring harness

**Migration note**: The alembic migration `01b52e38f588_add_long_running_project_tables.py` is retained because `9d70f20f2fed_add_enable_thinking_column_to_llm_` has `down_revision = "01b52e38f588"`. Deleting it would break the alembic chain. The migration file imports from `project_state.py` which is also retained as a standalone stub (no longer imported by application code). Tables remain in existing DBs but are inert.

---

### 4.5 Wire Up Dead Config Constants ✅

**yarn_target_context** (`model_loader_mixin.py`):
- `use_yarn` was already wired; `yarn_target_context` was stored but ignored
- After `target_ctx = yarn_max_ctx`, now reads `yarn_target_ctx_setting = getattr(self.llm_settings, "yarn_target_context", 0)` and uses it as `target_ctx` if non-zero and ≤ `yarn_max_ctx`
- This lets users cap the scaled context below the model's maximum

**auto_extract_knowledge** (`tool_filtering_mixin.py`):
- Setting existed in DB and `LLMSettings` but was never read
- Wired into both call sites of `ALWAYS_INCLUDE_CATEGORIES` in `tool_filtering_mixin.py`
- When `auto_extract_knowledge=False`, the `"knowledge"` category is excluded from always-include categories, so `record_knowledge` and related tools won't be forced onto the model

---

### 4.6 Conversation Summarization Audit ✅ (Audit only)

**Finding**: `perform_conversation_summary` and `summarize_after_n_turns` are **dead settings**. The settings exist in `LLMSettings` and the DB model (`llm_generator_settings`), but no code reads them. The `ConversationManagementMixin` has no summarization logic. `conversation_summary_helpers.py` only generates short display summaries for the conversation list UI — it does not do in-context LangGraph summarization.

**Required future work** (deferred):
- Implement in-context summarization: when message count exceeds `summarize_after_n_turns`, compress older messages via an LLM call and write the summary back into the LangGraph checkpoint
- Expose `summarize_after_n_turns` in the LLM settings panel
- Add tests

---

## Phase 7 — Testing and Observability

*Not implemented in this pass — see `llm_agent_audit_todo.md` items 7.1–7.4 for test specs.*

---

## Summary of Changes

**Session 1**: All Phase 1 (critical security/production) and Phase 2 (correctness) items complete. Phase 3 architecture cleanup: 3.1, 3.2, 3.3 (partial), 3.4 (partial), 3.6 done; 3.5 deferred. Phase 4 quality: 4.1–4.4 done. Phase 5 prompt: 5.1, 5.5 done; 5.2, 5.3, 5.4 deferred. Phase 6 client: 6.3, 6.4 (LLM WS) done; 6.1, 6.2, 6.5 deferred.

**Session 2**: 3.3 Option A complete (long_running/ removed). 4.5 both items wired up. 4.6 audited (feature is not implemented — documented). 6.4 TTS WebSocket backoff applied.

**Session 3**: 3.2 remaining item fixed (is_workflow_active() used stale global instead of ContextVar). 4.6 implemented: `conversation_summarization.py::maybe_summarize_checkpoint()` compresses checkpoint history when threshold exceeded; hooked into `do_generate()`. 5.3 implemented: `WorkflowState.current_mood` field added; `update_mood` tool returns `Command(update={"current_mood":...})`; `_checkpoint_mood` reads it O(1) instead of scanning messages; auto-mood path writes to `Conversation.user_data` for restart persistence; `_conversation_mood()` fallback added. 5.4 implemented: `_prompt_tier()` + `_estimate_remaining_context_tokens()` in `system_prompt_context.py` select base/standard/full tier; `_health_disclaimer_part()` gated by new `LLMSettings.include_health_disclaimer` flag. 6.5 implemented: `MediatorSignalLLMWorkflowEventSink.emit_tool_status` routes tool_status into text stream via `LLMResponse(message_type="tool_status")`; `websocket_chunk` surfaces it as `{"type": "tool_status", ...}`; client `useLLMWebSocket.ts` exposes `activeTools` state; `ChatView.tsx` renders "⚙ tool_name running…" lines above progress bar.

**Session 4**: 5.2 implemented: added "mood" to `ALWAYS_INCLUDE_CATEGORIES` in `tool_classification_mixin.py` (guard only skips "knowledge" on `auto_extract=False`; mood always passes through). 6.2 implemented: `ModelSelector.tsx` expanded with API key (password) field for OpenRouter/OpenAI, Ollama base URL field, colored dot indicator per provider (green=local, blue=openrouter, yellow=ollama, primary=openai), OpenAI added as provider option; `api_base_url` column added to `LLMGeneratorSettings` DB model; `ModelService.OPENAI` enum value added; `use_openai` property + wiring added to `llm_generate_worker.py`; DB `api_key`/`api_base_url` used preferentially over env vars in model factory; migration `add_provider_api_base_url.py` created. Bug fix: `put_writes` in `DatabaseCheckpointSaver` had `del config` before using `config` — fixed by removing `config` from the `del` statement. 7.1 (14 tests): `test_database_checkpoint_saver.py` covers put() message append logic, stateless mode, in-memory cache, DB fallback, clear_checkpoints isolation, instance isolation, LRU eviction. 7.2 (9 tests): `test_knowledge_tool_signals.py` covers signal correctness for all 4 knowledge tools, ContextVar isolation for concurrent tasks, put_writes in-memory persistence across multiple tasks.

**Session 5**: 4.6 completed (summarization test + UI exposure). 4.6a: 12 unit tests in `test_conversation_summarization.py` covering disabled/skip paths, compression correctness (summary SystemMessage, channel_values sync, message order preservation), and edge cases (missing workflow manager, missing memory, missing thread state, empty messages, LLM returning None, LLM exception). 4.6b: `perform_conversation_summary` (Boolean) and `summarize_after_n_turns` (Integer) columns added to `LLMGeneratorSettings` DB model; alembic migration `add_conversation_summary_settings.py` created (idempotent, revises `add_provider_api_base_url`); `conversation_summarization.py::maybe_summarize_checkpoint()` updated to prefer DB model over `LLMSettings` dataclass; `LLMSettingsPanel.tsx` updated with "Auto-summarize long conversations" toggle and "Summarize after N turns" range slider (2–50), both persisted via `updateSingleton("LLMGeneratorSettings")`. 3.4 and 3.5 marked as DEFERRED in todo.md (large refactors with dedup/safety nets already in place; no correctness value from consolidation). All 35 unit tests pass (12 new + 23 existing — zero regressions).

**Session 6**: 3.5 completed: 6 system prompt files consolidated into 3. Created `managers/prompt_builder.py` (~480 lines) merging content from `system_prompt_text.py` (110 lines, static constants), `system_prompt_mood.py` (120 lines, mood detection), `system_prompt_context.py` (265 lines, tiered assembly), and `system_prompt_actions.py` (80 lines, action mapping). `system_prompt_action_text.py` kept separate as data-only templates. `system_prompt_mixin.py` redirected imports to `prompt_builder.py` with alias resolution for the `get_system_prompt_for_action` name collision. Deleted the 4 merged source files. 3.4 completed: 24 factory tools migrated from `managers/tools/` mixin closures to `@tool()` decorators in `tools/migrated_factory_tools.py`. Tools receive `agent` (ToolManager) via `requires_agent=True` instead of closure-captured `self`. `ToolManager` base class simplified from 5 mixins to single `BaseTool`. `get_all_tools()` now reads exclusively from ToolRegistry — 19-line factory list removed. Fallback dispatch in `_get_tool_by_name()` removed (6 entries migrated). `managers/tools/` directory deleted (13 files). All 35 unit tests pass — zero regressions.
