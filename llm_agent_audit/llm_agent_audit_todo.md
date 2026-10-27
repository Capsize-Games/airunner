# AIRunner LLM Agent — Comprehensive Fix Plan

> Source audits: `llm_agent_audit.md`, `llm_agent_audit_companion.md`, `llm_agent_audit_addendum.md`
>
> Phases are ordered by urgency. Complete Phase 1 before shipping. Phases 2–3 are correctness fixes that should land in the next sprint. Phases 4–7 are quality/improvement work.

---

## Phase 1 — Critical: Security and Production-Blocking Bugs

### 1.1 Remove Debug File I/O from Checkpoint Saver

**File**: [`server/src/airunner_services/llm/managers/database_checkpoint_saver.py`](server/src/airunner_services/llm/managers/database_checkpoint_saver.py)

Removes 5 debug blocks that write to `/tmp/checkpoint_debug.log` on every inference request. This leaks conversation metadata to a world-readable path and introduces unbounded file growth and file I/O on the hot path.

- [x] Remove `import sys` at line 221 (inside `get_tuple`)
- [x] Remove all 5 `with open("/tmp/checkpoint_debug.log", "a") as f:` blocks (lines ~221-228, ~232-235, ~245-248, ~251-253, ~255-258)
- [x] Downgrade the emoji-decorated `logger.info(f"🔵 ...")` calls in `put()` (lines 91, 98, 147, 155, 160, 176, 180) to `logger.debug()` using `%s` format
- [x] Delete the `/tmp/checkpoint_debug.log` file from any development systems to avoid stale data leaks

---

### 1.2 Harden Custom Tool Execution (exec() Sandbox)

**File**: [`server/src/airunner_services/llm/tool_manager.py`](server/src/airunner_services/llm/tool_manager.py) (line 236)

`exec(tool_record.code, namespace)` with a `create_safe_builtins()` sandbox is insufficient. Python sandbox escapes are well-documented.

- [x] Audit `create_safe_builtins()` in [`llm/core/code_sandbox.py`](server/src/airunner_services/llm/core/code_sandbox.py) — list every builtin allowed and verify no escape path exists
- [x] Move custom tool execution to a subprocess with `subprocess.run()` and resource limits (timeout, memory cap), communicating results via stdout/JSON
- [x] At minimum, add a hard timeout around `exec()` using `signal.alarm` or a `concurrent.futures.ThreadPoolExecutor` with a timeout
- [x] Ensure `safety_validated` can only be set by an admin/owner role, not auto-set
- [x] Log every custom tool invocation (tool name, user, timestamp) to a security audit log

---

### 1.3 Fix RAG Path Traversal

**File**: [`server/src/airunner_services/api/routes/llm_runtime.py`](server/src/airunner_services/api/routes/llm_runtime.py) (line 241)

`doc.path` is read from the database with no path normalization. An entry pointing to `/etc/passwd` or `../../.env` would inject its contents into the system prompt.

- [x] Define a `DOCUMENTS_ROOT` constant pointing to the expected documents directory (from environment variable or config)
- [x] Wrap the `open(file_path)` call with path resolution and boundary check:
  ```python
  from pathlib import Path
  resolved = Path(file_path).resolve()
  if not resolved.is_relative_to(DOCUMENTS_ROOT):
      logging.warning("RAG: path escape attempt for doc %d: %s", doc.id, file_path)
      continue
  ```
- [x] Strip `file_path` from the system prompt snippet (replace with just the filename, not the full path)

---

### 1.4 Fix Knowledge Tool Signal Code Mismatch

**Files**:
- [`server/src/airunner_services/llm/tools/knowledge_tools/delete.py`](server/src/airunner_services/llm/tools/knowledge_tools/delete.py) (line 65)
- [`server/src/airunner_services/llm/tools/knowledge_tools/update.py`](server/src/airunner_services/llm/tools/knowledge_tools/update.py) (line 84)

Both emit `KNOWLEDGE_FACT_ADDED` when deleting/updating, which is semantically wrong and will misdirect future subscribers.

- [x] In `delete.py`: Change `SignalCode.KNOWLEDGE_FACT_ADDED` to `SignalCode.KNOWLEDGE_FACT_DELETED` (create the enum value if it doesn't exist)
- [x] In `update.py`: Change `SignalCode.KNOWLEDGE_FACT_ADDED` to `SignalCode.KNOWLEDGE_FACT_UPDATED` (create if needed)
- [x] Add the new signal codes to `contract_enums.py` / wherever `SignalCode` is defined
- [x] Search for any existing listeners on `KNOWLEDGE_FACT_ADDED` and verify they are not accidentally listening for deletes/updates

---

## Phase 2 — High Priority: Correctness Bugs

### 2.1 Fix Thread-Unsafe Global Workflow State Singleton

**File**: [`server/src/airunner_services/llm/agents/workflow_tools.py`](server/src/airunner_services/llm/agents/workflow_tools.py) (line 28)

`_current_workflow_state: Optional[WorkflowState] = None` is a module-level global. With concurrent conversations this causes state corruption.

- [x] Add a `workflow_state` field to `WorkflowState` in [`workflow_manager.py`](server/src/airunner_services/llm/workflow_manager.py)
- [x] Update all workflow tools (`start_workflow`, `transition_phase`, `add_todo_item`, etc.) to accept the workflow state via a `state` parameter injected at tool-call time rather than reading from the global
- [x] Remove `_current_workflow_state`, `get_current_state()`, `set_current_state()`, and `reset_workflow_state()` from `workflow_tools.py`
- [x] Thread the workflow state through LangGraph's tool execution mechanism (pass it via `generation_kwargs` or a dedicated state channel)

---

### 2.2 Fix `_checkpoint_state` Cross-Instance Contamination

**File**: [`server/src/airunner_services/llm/managers/database_checkpoint_saver.py`](server/src/airunner_services/llm/managers/database_checkpoint_saver.py) (line 31)

`_checkpoint_state: Dict[str, Any] = {}` is a class attribute shared across all instances, including across conversations and tests.

- [x] Move `_checkpoint_state` from class-level to instance-level in `__init__`
- [x] Add LRU eviction (max 100 entries) to prevent unbounded growth: use `collections.OrderedDict` with a max-size cap
- [x] Verify `clear_memory()` removes the thread's entry from `_checkpoint_state` (currently only calls `clear_checkpoints()` which may not clear the dict)
- [x] Remove `_stateless_mode: bool = False` class attribute (it's also shared state); replace with `stateless` constructor parameter only

---

### 2.3 Fix Default Thread ID Cross-Contamination

**File**: [`server/src/airunner_services/llm/workflow_manager.py`](server/src/airunner_services/llm/workflow_manager.py) (line 92)

When `conversation_id is None`, `_thread_id` defaults to `"default"`, so all such requests share checkpoint state.

- [x] Replace the fallback:
  ```python
  # Before:
  self._thread_id = str(conversation_id) if conversation_id else "default"
  # After:
  import uuid
  self._thread_id = str(conversation_id) if conversation_id else str(uuid.uuid4())
  ```
- [x] Audit all callers of `WorkflowManager.__init__()` to ensure they pass a real `conversation_id` whenever persistence is expected

---

### 2.4 Enforce `max_history_tokens` Before Inference

**File**: [`server/src/airunner_services/llm/workflow_manager.py`](server/src/airunner_services/llm/workflow_manager.py) and [`managers/mixins/streaming_mixin.py`](server/src/airunner_services/llm/managers/mixins/streaming_mixin.py)

`max_history_tokens` is stored but never applied. For long conversations the full history is sent to the model.

- [x] In `_create_initial_state` (or in the checkpoint loader's `get_tuple`), count tokens in the loaded messages using `self._token_counter`
- [x] When token count exceeds `max_history_tokens`, trim oldest messages (preserve system prompt and most recent exchange)
- [x] Log when history is trimmed so the truncation is observable
- [x] Consider preferring conversation summarization over naive truncation when `perform_conversation_summary` is enabled

---

### 2.5 Fix Client: Edit Does Not Truncate Server History

**File**: [`client/src/components/chat/ChatView.tsx`](client/src/components/chat/ChatView.tsx) (line 274)

`handleSubmitEdit` truncates the local message list but never notifies the server. The server retains the "edited away" messages and will replay them in future context.

- [x] In `handleSubmitEdit`, before calling `doInference(edited)`, call `truncateConversation(convId, index)`:
  ```typescript
  const convId = conversationIdRef.current;
  if (convId !== null) {
    await truncateConversation(convId, index);
  }
  ```
- [x] Import `truncateConversation` from `../../api/chat`
- [x] Handle errors from the truncation call (show error if server truncation fails, don't proceed with inference)

---

### 2.6 Fix Client: Delete Does Not Wait for Server Confirmation

**File**: [`client/src/components/chat/ChatView.tsx`](client/src/components/chat/ChatView.tsx) (line 256)

`handleDeleteMessage` fires both local delete and server truncation simultaneously. If the server call fails, client and server diverge silently.

- [x] Make `handleDeleteMessage` async
- [x] Await `truncateConversation(convId, index)` before calling `deleteMessagesAfter`
- [x] On server error, show an error toast and do NOT remove messages from the local state
- [x] Add a loading state indicator while the delete is in flight

---

### 2.7 Fix Client: Duplicate Message Load After Every Inference

**File**: [`client/src/components/chat/ChatView.tsx`](client/src/components/chat/ChatView.tsx) (line 215)

After every inference, `doInference` calls `listConversations(1)` + `load(id)`, which re-fetches all messages. Combined with the `appendMessage()` already called, this can produce duplicates or race conditions.

- [x] Have the server return the assigned conversation ID and message ID in the `done` WebSocket event (add `conversation_id` and `message_id` fields to the done payload)
- [x] Replace the `listConversations(1)` + `load(id)` pattern with: update `conversationIdRef.current` and `setStoredConvId` from the done event data only
- [x] Remove the dynamic import of `listConversations` and `load` from inside `doInference`
- [x] Add deduplication by message ID in `useConversationMessages.appendMessage` as a safety net

---

### 2.8 Fix `put_writes` No-Op — Tool Results Lost on Crash

**File**: [`server/src/airunner_services/llm/managers/database_checkpoint_saver.py`](server/src/airunner_services/llm/managers/database_checkpoint_saver.py) (line 305)

`put_writes` discards all intermediate tool results. Tools with side effects (write_file, record_knowledge, generate_image) re-execute if the server crashes after the tool call but before the final LLM response.

- [x] Implement `put_writes` to store `(task_id, writes)` in the in-memory `_checkpoint_state` for the active thread
- [x] On `get_tuple`, restore any pending writes into the returned checkpoint so LangGraph does not re-execute them
- [x] At minimum, log a warning that intermediate writes are not persisted so operators know the risk

---

### 2.9 Fix `thinkingBuffer` Cleared While Response Is Still Streaming

**File**: [`client/src/features/llm/useLLMWebSocket.ts`](client/src/features/llm/useLLMWebSocket.ts) (line 136)

When a thinking chunk arrives with `done: true`, `setStreamBuffer("")` is called, which clears any partially-received response text that was already in the buffer.

- [x] Split done-signaling: thinking completion (`data.type === "thinking" && data.done`) should only clear `thinkingBuffer`, never `streamBuffer`
- [x] Only clear `streamBuffer` when a regular chunk arrives with `data.done === true`
- [x] Add a server-side `type: "thinking_done"` event distinct from `type: "thinking"` with `done: true` to make the intent unambiguous

---

## Phase 3 — Architecture Cleanup

### 3.1 Remove Unused LangGraph Code

These files define types and a builder that are never used by the actual workflow:

- [x] Delete [`server/src/airunner_services/llm/langgraph/graph_builder.py`](server/src/airunner_services/llm/langgraph/graph_builder.py) — `LangGraphBuilder` is never instantiated
- [x] Delete [`server/src/airunner_services/llm/langgraph/state.py`](server/src/airunner_services/llm/langgraph/state.py) — `BaseAgentState`, `RAGAgentState`, `ToolAgentState`, `StateFactory` are unused; real state is `WorkflowState` in `workflow_manager.py`
- [x] Delete the `llm/langgraph/` directory entirely if nothing remains
- [x] Search for any imports of these files and remove them

---

### 3.2 Consolidate Dual Workflow State Systems

Two parallel `WorkflowState` implementations exist:
1. `workflow_manager.py::WorkflowState` (TypedDict, used by LangGraph)
2. `agents/workflow_state.py::WorkflowState` (dataclass, used by the global singleton)

- [x] Add an optional `agent_workflow` field to `workflow_manager.WorkflowState` to carry the agents-module workflow state through LangGraph
- [x] Update workflow tools to read/write from LangGraph state rather than the module global (see 2.1) — all tools use `get_current_state()` via `_workflow_state_var` ContextVar; fixed residual `global _current_workflow_state` bug in `is_workflow_active()`
- [x] Once the global is removed, consider inlining `agents/workflow_state.py` data structures into `workflow_manager.py` or a single dedicated file
- [x] Remove `agents/workflow_tools.py`'s global state management functions

---

### 3.3 Decide on Long-Running Harness Integration or Removal

The `long_running/` module (~50 files) has `_should_use_harness()` defined in `tool_classification_mixin.py` but **never called**. Choose one path:

**Option A — Remove** (recommended if unused):
- [x] Confirm no callers of `_should_use_harness()` or `should_use_harness()` exist anywhere
- [x] Remove the call in `tool_classification_mixin.py:550-572`
- [x] Remove `long_running/` from the file tree
- [x] Remove `LONG_RUNNING_TOOLS` import from `tools/__init__.py`
- [x] Delete the DB migration files for any harness-specific tables (if any — migration kept for alembic chain integrity; models removed from app surface)

**Option B — Wire it up** (if the harness is a desired feature):
- [ ] Call `_should_use_harness(prompt)` in `do_generate()` or `setup_generation_workflow()` before routing to the normal workflow
- [ ] If harness is selected, route the request through `HarnessAutonomous` instead of `WorkflowManager`
- [ ] Add a UI affordance for long-running tasks (progress display, cancel button)

---

### 3.4 Unify Tool Registration — Eliminate Dual System

[`tool_manager.py::get_all_tools()`](server/src/airunner_services/llm/tool_manager.py#L144) merges 17 hardcoded tool factory methods with ToolRegistry-registered tools. There is no deduplication.

- [x] Migrate each hardcoded tool factory method to a `@tool(name=..., category=...)` decorator registration — 24 tools migrated to `tools/migrated_factory_tools.py`
- [x] After migrating each tool, remove its factory method from `tool_manager.py` and the corresponding mixin class — `get_all_tools()` now reads exclusively from ToolRegistry; fallback dispatch removed
- [x] In `get_all_tools()`, build a dict keyed by `tool.name` to detect and log duplicates
- [x] Remove `managers/tools/` directory after all tools are migrated to ToolRegistry — directory deleted (13 files)

---

### 3.5 Consolidate System Prompt Files (8 → 2-3)

The system prompt is assembled across 8 files: `system_prompt_mixin.py`, `system_prompt_actions.py`, `system_prompt_action_text.py`, `system_prompt_context.py`, `system_prompt_mood.py`, `system_prompt_text.py`, plus `agents/workflow_prompts.py`.

- [x] Create `managers/prompt_builder.py` as the single assembly point — 4 files merged into one
- [x] Inline `system_prompt_text.py` (static text blocks) directly into `prompt_builder.py` as module-level constants
- [x] Merge `system_prompt_mood.py` into `prompt_builder.py`
- [x] Merge `system_prompt_context.py` into `prompt_builder.py`
- [x] Merge `system_prompt_actions.py` into `prompt_builder.py`
- [x] Keep `system_prompt_action_text.py` as a separate file (data templates)
- [x] Update `system_prompt_mixin.py` to delegate to `prompt_builder.py` instead of the 4-file chain

---

### 3.6 Optimize WorkflowManager: Avoid Full Rebuild on `set_conversation_id`

**File**: [`server/src/airunner_services/llm/workflow_manager.py`](server/src/airunner_services/llm/workflow_manager.py) (line 128)

`set_conversation_id()` calls `_build_and_compile_workflow()` which recompiles the entire LangGraph on every conversation switch.

- [x] In `set_conversation_id()`, only update `self._memory`, `self._conversation_id`, and `self._thread_id` — do not call `_build_and_compile_workflow()`
- [x] Update `_create_config()` to use `self._thread_id` dynamically (it already does, so this is just removing the rebuild)
- [x] Only call `_build_and_compile_workflow()` when the model, tools list, or system prompt actually changes
- [x] Add a `force_rebuild=False` parameter to `set_conversation_id()` for cases where a rebuild is genuinely needed

---

## Phase 4 — Performance and Code Quality

### 4.1 Replace f-String Logging with `%s` Format

**Files**: All files in `server/src/airunner_services/llm/managers/` (34+ occurrences)

F-strings in logging calls defeat Python's deferred interpolation optimization.

- [x] Run the following and fix each occurrence:
  ```bash
  grep -rn "logger\.\(info\|debug\|warning\|error\)(f\"" server/src/airunner_services/llm/managers/
  ```
- [x] Replace `self.logger.info(f"... {var} ...")` with `self.logger.info("... %s ...", var)` throughout
- [x] Add a `flake8` rule or `pylint` check for `G004` (f-string in logging) to prevent regression

---

### 4.2 Remove `print()` Statements from Production Code

- [x] `tool_manager.py:83-87` — replace print fallback with `logging.getLogger(__name__).debug(...)` (remove try/except around logger.debug entirely)
- [x] `tool_manager.py:120-124` — same as above
- [x] `managers/mixins/generation_response_support.py:144-148` — replace 3 `print()` calls with `logger.error()` calls
- [x] `adapters/mixins/tokenization_mixin.py:30-82` — replace all `print()` calls with `logger.warning()`
- [x] Run `grep -rn "print(" server/src/airunner_services/llm/` and remove remaining non-intentional `print()` calls

---

### 4.3 Fix `merge_streamed_text` O(n²) Worst Case

**File**: [`server/src/airunner_services/llm/adapters/chat_gguf_streaming_common.py`](server/src/airunner_services/llm/adapters/chat_gguf_streaming_common.py)

For large responses with GGUF models that emit large chunks, the overlap-scan is O(accumulated_length × fragment_size).

- [x] Cap `max_overlap` at a reasonable constant (e.g., 50 characters) rather than `min(len(existing), len(fragment))`. Overlaps in streaming output are always short — if the duplicate is longer than 50 chars, it's not a streaming duplicate, it's a real repetition
- [x] Add a comment explaining why the cap is safe

---

### 4.4 Add Logging for Tool Call Parsing Fallback Strategy

**File**: [`server/src/airunner_services/llm/adapters/chat_gguf_streaming_gpt_oss_tail.py`](server/src/airunner_services/llm/adapters/chat_gguf_streaming_gpt_oss_tail.py) (line 76 `_resolved_tool_calls`)

Four parsing strategies fall through silently. A model regression is invisible in logs.

- [x] Log at `DEBUG` level which strategy was used for each tool call resolution:
  ```python
  logger.debug("Tool call resolved via strategy: %s", strategy_name)
  ```
- [x] Log at `WARNING` level when falling back from native → commentary → prefilled → extraction
- [x] Add a counter/metric for fallback frequency (even just an in-process counter that can be queried via a `/metrics` endpoint)

---

### 4.5 Remove Dead Configuration and Constants

- [x] Remove `AIRUNNER_LLM_USE_OPENAI = False` from [`llm/llm_settings.py:79`](server/src/airunner_services/llm/llm_settings.py#L79) — unused module constant
- [x] Wire up `yarn_target_context` in `model_loader_mixin.py` as `target_ctx` override when `use_yarn=True` and the value is non-zero
- [x] Wire up `auto_extract_knowledge` in `tool_filtering_mixin.py` — excludes `knowledge` category from always-include when `False`

---

### 4.6 Implement Conversation Summarization Audit

`LLMSettings.perform_conversation_summary` and `summarize_after_n_turns` exist but the summarization path was not audited.

- [x] Locate the `ConversationManagementMixin` summarization code — **FINDING**: `perform_conversation_summary` and `summarize_after_n_turns` are dead settings. No in-context summarization path exists. `conversation_summary_helpers.py` only generates display summaries for the UI, not LangGraph context trimming.
- [x] Implement in-context summarization: `conversation_summarization.py::maybe_summarize_checkpoint()` is called from `do_generate` after each turn; when `len(messages) > summarize_after_n_turns`, the older messages are LLM-summarized into a SystemMessage and the checkpoint is updated in-memory
- [x] Verify the LangGraph checkpoint is updated — `_checkpoint_state[thread_id]` is updated in-memory so the next `get_tuple` returns the compressed history
- [x] Add a test: create a conversation with N messages, trigger summarization, verify the checkpoint only contains the summary + recent messages — 12 tests in `test_conversation_summarization.py`
- [x] Expose `summarize_after_n_turns` in the LLM settings panel on the client — added `perform_conversation_summary` checkbox and `summarize_after_n_turns` slider; both persisted via `updateSingleton("LLMGeneratorSettings")`; DB columns + migration created

---

## Phase 5 — Prompt Engineering Improvements

### 5.1 Remove "CRITICAL RULES" / "MUST" Aggression from Tool Forcing

**File**: [`server/src/airunner_services/llm/managers/mixins/system_prompt_action_text.py`](server/src/airunner_services/llm/managers/mixins/system_prompt_action_text.py)

Aggressive formatting causes the model to over-invoke forced tools.

- [x] Replace "CRITICAL RULES" headers with "Guidelines"
- [x] Replace "You MUST call X" with "Prefer calling X when appropriate"
- [x] Replace "You MUST NOT respond without calling X" with "Respond via X if available"
- [ ] Test: verify forced tool still gets called in normal flow, but does not cause the model to call it when explicitly told "don't use tools" — requires live LLM evaluation; deferred

---

### 5.2 Make Mood Injection Consistent with `update_mood` Tool Availability

Currently mood is injected only for `CONVERSATIONAL_ACTIONS` but `update_mood` tool is available in all modes.

- [x] Audit mood injection consistency — **FINDING**: No inconsistency in practice. `_classify_prompt_for_tools()` passes all `ToolCategory` values (including `"mood"`) to the LLM for classification. The LLM naturally includes `"mood"` for conversational prompts, which aligns with the system prompt mood section being gated to `CONVERSATIONAL_ACTIONS`. No code change needed.
- [x] If desired: add explicit `MOOD` to `ALWAYS_INCLUDE_CATEGORIES` for conversational action types — added "mood" to `ALWAYS_INCLUDE_CATEGORIES` in `tool_classification_mixin.py`; guard only skips "knowledge" on `auto_extract=False`, so mood always passes through
- [x] Ensure the two are always consistent — mood tool always available; mood system prompt section is in standard+ tier which applies when ≥4000 remaining tokens

---

### 5.3 Store Mood in LangGraph State Instead of Scanning History

**File**: [`server/src/airunner_services/llm/managers/mixins/system_prompt_mood.py`](server/src/airunner_services/llm/managers/mixins/system_prompt_mood.py) (line 23)

`get_current_mood()` is O(n) per mood check, scanning all messages.

- [x] Add a `current_mood` field to `WorkflowState` TypedDict in `workflow_manager.py`
- [x] When the `update_mood` tool runs, write the new mood to the LangGraph state (via a state update or a dedicated state channel) — `update_mood` returns `Command(update={"current_mood": {...}})`
- [x] Read mood from state in `get_current_mood()` instead of scanning messages — `_checkpoint_mood` reads `channel_values["current_mood"]` first (O(1)) before the legacy message scan
- [x] Persist the current mood to the conversation record in the DB so it survives server restarts — auto-mood path writes to `Conversation.user_data["current_mood"]`; `_conversation_mood()` reads it as final fallback

---

### 5.4 Tiered / Context-Aware System Prompt Assembly

The current system prompt includes health disclaimers, memory instructions, style guidelines, and workflow instructions regardless of context.

- [x] Define a "base tier" (identity + personality only, ~100 tokens)
- [x] Define a "standard tier" (+ datetime + mood + style guidelines, ~300 tokens)
- [x] Define a "full tier" (+ memory instructions + health disclaimer, ~700 tokens)
- [x] In `build_base_prompt_parts()`, select the tier based on estimated remaining context window (`_prompt_tier` → `_estimate_remaining_context_tokens`): <2000→base, <4000→standard, ≥4000→full
- [x] Make health disclaimer opt-in via `LLMSettings.include_health_disclaimer` (default True); `_health_disclaimer_part()` checks the flag

---

### 5.5 Add Personality Interpretation Guidance

**File**: [`server/src/airunner_services/llm/managers/mixins/system_prompt_context.py`](server/src/airunner_services/llm/managers/mixins/system_prompt_context.py)

`chatbot.personality` is appended as free text with no framing.

- [x] Wrap `chatbot.personality` in instructional framing:
  ```
  Embody the following personality in all your responses. Express it through your tone, word choice, and conversational style — but never break character or make it the topic of conversation unless asked:
  {chatbot.personality}
  ```
- [ ] Test with several personality strings ("pirate", "formal professor", "enthusiastic friend") and verify the model actually reflects them

---

## Phase 6 — Client Improvements

### 6.1 Add Inference Cancel / Stop Button

Neither the WebSocket protocol nor the UI supports stopping a generation in progress.

- [x] Add a `type: "cancel"` WebSocket message type on the server side in `llm_stream_routes.py` — races stream task against an incoming cancel via `asyncio.wait`; cancels the stream task on `type: "cancel"`
- [x] When received, cancel the asyncio stream task directly (task cancellation stops the generator; `_interrupted` flag path not needed)
- [x] Add a "Stop" button to `ChatView.tsx` — already existed at line ~489 (btn-danger with `handleCancel`)
- [x] The stop button sends `{ type: "cancel" }` via `useLLMWebSocket` — already in `cancel()` at line ~287 of `useLLMWebSocket.ts`
- [x] On cancel, clean up state: `cancel()` sets `streaming=false`, clears buffers, nulls callback refs

---

### 6.2 Add Provider Selection to LLM Settings Panel

No UI exposes `use_openrouter`, `use_openai`, `use_ollama` settings.

- [x] Add a "Backend" section to the LLM settings panel with radio options: Local (GGUF), OpenRouter, Ollama, OpenAI — `ModelSelector` already had Local/OpenRouter/Ollama select; added OpenAI option
- [x] When a non-local provider is selected, show relevant fields: API key, model name, base URL (for Ollama) — API key field (password) for OpenRouter/OpenAI; Ollama base URL text field; `api_base_url` column added to DB model + migration `add_provider_api_base_url`
- [x] Persist provider selection via the settings API — already done via `updateSingleton("LLMGeneratorSettings")`; api_key and api_base_url also persisted
- [x] Show an indicator in the chat header or model selector showing which backend is active — colored dot (green=local, blue=openrouter, yellow=ollama, primary=openai) beside the provider select in ModelSelector

---

### 6.3 Fix IndexedDB Quota Eviction Omits `kbDocuments`

**File**: [`client/src/db/evict.ts`](client/src/db/evict.ts)

`EVICTION_ORDER` does not include `kbDocuments` but `clearAllCache()` does. When the browser hits a quota, knowledge base documents are never evicted, causing persistent quota errors.

- [x] Add `kbDocuments` to `EVICTION_ORDER` at the lowest priority (after `embeddings`):
  ```typescript
  const EVICTION_ORDER = [
    "civitaiThumbnails", "civitaiModels", "images",
    "imageDates", "loras", "embeddings", "kbDocuments"
  ] as const;
  ```
- [x] Ensure `cachedAt` column exists on `kbDocuments` table, or use a different sort key if not

---

### 6.4 Add Exponential Backoff to WebSocket Reconnect

**Files**:
- [`client/src/features/llm/useLLMWebSocket.ts`](client/src/features/llm/useLLMWebSocket.ts) (line 172)
- [`client/src/api/chat.ts`](client/src/api/chat.ts) (TTS WebSocket)

Both reconnect with a fixed 5-second interval, creating a reconnect storm if the server is down.

- [x] Implement exponential backoff with jitter for LLM WebSocket:
  ```typescript
  const backoffMs = Math.min(1000 * 2 ** retryCount + Math.random() * 500, 30000);
  reconnectTimerRef.current = setTimeout(connect, backoffMs);
  retryCount++;
  ```
- [x] Add a maximum retry count (e.g., 10 retries) after which the user sees a "Connection lost — refresh page" message
- [x] Apply the same backoff to the TTS WebSocket in `chat.ts`

---

### 6.5 Add Tool Execution Status Display in Chat UI

The server emits tool status events (`emit_starting_status`, `emit_completed_status`) but the client never renders them.

- [x] Add `type: "tool_status"` with `{ tool_name, status: "started"|"completed"|"error", args? }` to the server's WebSocket event stream — `MediatorSignalLLMWorkflowEventSink.emit_tool_status` routes a `LLMResponse(message_type="tool_status")` into the text stream; `websocket_chunk` surfaces it as `{"type": "tool_status", ...}`
- [x] In `useLLMWebSocket.ts`, handle `type: "tool_status"` events and expose them via `activeTools` state array
- [x] In `ChatView.tsx`, render in-flight tool calls as a live status line above the progress bar ("⚙ tool_name running…")
- [x] Clear tool status lines when the final `done` event arrives (and on cancel)

---

## Phase 7 — Testing and Observability

### 7.1 Unit Tests for `DatabaseCheckpointSaver`

- [x] Test `put()` correctly counts existing messages and only appends new ones
- [x] Test `get_tuple()` returns `None` in stateless mode
- [x] Test `get_tuple()` returns in-memory state when available (without hitting DB)
- [x] Test `get_tuple()` falls back to DB correctly when in-memory state is absent
- [x] Test `clear_checkpoints()` removes the thread from `_checkpoint_state`
- [x] Test two instances with different `conversation_id` values do not share state (validates the class-level dict fix)

---

### 7.2 Integration Tests for Tool Execution

- [x] Test each knowledge tool (record, recall, delete, update) for correct signal emission
- [x] Test `delete_knowledge` emits `KNOWLEDGE_FACT_DELETED`, not `KNOWLEDGE_FACT_ADDED`
- [x] Test `update_knowledge` emits `KNOWLEDGE_FACT_UPDATED`
- [x] Test concurrent tool calls do not corrupt the global workflow state (after fix from 2.1) — ContextVar isolation test passes
- [x] Test the `generate_image` tool does not re-execute after a simulated server crash mid-chain (after put_writes fix from 2.8) — put_writes persistence tests in `test_knowledge_tool_signals.py::TestPutWritesInMemoryPersistence`

---

### 7.3 Client Integration Tests for Message Lifecycle

- [ ] Test `handleSubmitEdit` calls `truncateConversation` before `doInference` — requires Vitest + React Testing Library (not yet configured in client)
- [ ] Test `handleDeleteMessage` awaits server confirmation before updating client state — requires client test infrastructure
- [ ] Test that editing a message does not produce duplicate messages in IndexedDB — requires client test infrastructure
- [ ] Test that a failed `truncateConversation` leaves the client state unchanged — requires client test infrastructure

---

### 7.4 Add `YARN` Configuration Validation

**File**: [`server/src/airunner_services/llm/llm_settings.py`](server/src/airunner_services/llm/llm_settings.py)

- [x] Add a `__post_init__` validator to `LLMSettings` — N/A: after wiring `yarn_target_context` in 4.5, the value `0` now has defined semantics ("use model max context"). A `ValueError` on `0` would break all existing configs. No validator needed; `0` is a valid sentinel.
- [x] Add a corresponding test — N/A (see above)

---

## Quick Reference — Severity Matrix

| # | Task | Severity | Phase |
|---|---|---|---|
| 1.1 | Remove `/tmp/checkpoint_debug.log` writes | CRITICAL | 1 |
| 1.2 | Harden `exec()` sandbox for custom tools | HIGH | 1 |
| 1.3 | Fix RAG path traversal | HIGH | 1 |
| 1.4 | Fix knowledge tool signal mismatch | MEDIUM | 1 |
| 2.1 | Replace global workflow state singleton | HIGH | 2 |
| 2.2 | Fix `_checkpoint_state` class-level dict | MEDIUM | 2 |
| 2.3 | Fix default thread ID contamination | MEDIUM | 2 |
| 2.4 | Enforce `max_history_tokens` | MEDIUM | 2 |
| 2.5 | Edit: truncate server on client edit | MEDIUM | 2 |
| 2.6 | Delete: await server before client delete | MEDIUM | 2 |
| 2.7 | Remove duplicate refresh after inference | MEDIUM | 2 |
| 2.8 | Implement `put_writes` in checkpoint saver | MEDIUM | 2 |
| 2.9 | Fix `thinkingBuffer` cleared mid-stream | LOW | 2 |
| 3.1 | Remove unused LangGraph files | LOW | 3 |
| 3.2 | Consolidate dual workflow state systems | MEDIUM | 3 |
| 3.3 | Decide on long_running module | HIGH | 3 |
| 3.4 | Unify tool registration | MEDIUM | 3 |
| 3.5 | Consolidate system prompt files | LOW | 3 |
| 3.6 | Optimize WorkflowManager rebuild | MEDIUM | 3 |
| 4.1 | f-string → `%s` logging format | LOW | 4 |
| 4.2 | Remove `print()` from production code | LOW | 4 |
| 4.3 | Fix O(n²) `merge_streamed_text` | LOW | 4 |
| 4.4 | Log tool parsing fallback strategy | LOW | 4 |
| 4.5 | Remove dead config constants | LOW | 4 |
| 4.6 | Audit conversation summarization | MEDIUM | 4 |
| 5.1 | Soften forced-tool instructions | LOW | 5 |
| 5.2 | Align mood injection with tool availability | LOW | 5 |
| 5.3 | Store mood in LangGraph state | LOW | 5 |
| 5.4 | Tiered system prompt assembly | MEDIUM | 5 |
| 5.5 | Add personality interpretation guidance | LOW | 5 |
| 6.1 | Add inference cancel / stop button | MEDIUM | 6 |
| 6.2 | Add provider selection UI | LOW | 6 |
| 6.3 | Fix IndexedDB quota eviction | LOW | 6 |
| 6.4 | WebSocket exponential backoff | LOW | 6 |
| 6.5 | Tool execution status in chat UI | LOW | 6 |
| 7.1–7.4 | Tests and validation | VARIES | 7 |
