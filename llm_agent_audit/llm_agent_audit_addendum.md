# AIRunner LLM Agent Audit — Addendum

> Third installment. Covers findings not present in `llm_agent_audit.md` or `llm_agent_audit_companion.md`. Does not repeat prior findings.

---

## 1. Security Issues

### 1.1 `exec()` Used to Run Database-Stored Tool Code — HIGH

[`tool_manager.py:236`](server/src/airunner_services/llm/tool_manager.py#L236) compiles and executes custom tools stored in the database using `exec()`:

```python
exec(tool_record.code, namespace)
```

A `create_safe_builtins()` sandbox is applied, but Python sandbox escapes via builtins are well-known (e.g., `().__class__.__bases__[0].__subclasses__()` chains). The `safety_validated` flag on the tool record is the only gate — if the database is compromised or the flag is set incorrectly, arbitrary code runs in the server process.

**Fix**: Replace `exec()` with a proper sandboxed execution environment (subprocess isolation, RestrictedPython, or a separate process with resource limits). At minimum, validate `safety_validated` is set and audited by a human, not auto-set.

### 1.2 RAG Path Traversal — No Boundary Enforcement

Confirmed from companion audit but more specific: [`llm_runtime.py:241-243`](server/src/airunner_services/api/routes/llm_runtime.py#L241) reads `doc.path` from the database with no path normalization:

```python
file_path = doc.path
with open(file_path, "r", errors="replace") as f:
    text = f.read(4096)
```

The document path also leaks into the system prompt verbatim (`f"--- Document: {file_path} ---\n{text}"`), so even a relative path like `../../server/.env` would expose its contents to the LLM context and potentially to the user.

**Fix**:
```python
from pathlib import Path
DOCS_ROOT = Path("/path/to/docs").resolve()
resolved = Path(file_path).resolve()
assert resolved.is_relative_to(DOCS_ROOT), f"Path escape attempt: {file_path}"
```

---

## 2. Dead / Misleading Configuration

### 2.1 `auto_extract_knowledge` — Defined But Never Read

`LLMSettings.auto_extract_knowledge: bool = True` (and the matching DB column `llm_generator_settings.auto_extract_knowledge`) exist but are **never read anywhere in the LLM codebase**. The comment in `streaming_mixin.py` says auto-extraction is "disabled — LLM uses tools to record knowledge," but the setting remains, misleading operators who might toggle it expecting an effect.

**Fix**: Either wire up the setting to conditionally include/exclude `record_knowledge` from the tool set, or remove the setting and the DB column with a migration.

### 2.2 `yarn_target_context` Setting Is Unused and Misleading

`LLMSettings.yarn_target_context: int = 0` exists but is never read. YARN context scaling in [`model_loader_mixin.py:75-117`](server/src/airunner_services/llm/managers/mixins/model_loader_mixin.py#L75) uses `yarn_max_ctx` from model metadata, not this setting. The `0` default is therefore harmless but creates false expectation that operators can control the YARN target context via this field.

**Fix**: Remove the field or wire it up. If keeping it, add validation that `yarn_target_context > 0` when `use_yarn = True`.

### 2.3 Stale Module-Level Constant in `llm_settings.py`

[`llm_settings.py:79`](server/src/airunner_services/llm/llm_settings.py#L79) defines:
```python
AIRUNNER_LLM_USE_OPENAI = False
```

This is a module-level constant that duplicates the `LLMSettings.use_openai` field and is never imported anywhere. Dead code.

---

## 3. Code Quality Issues

### 3.1 `print()` Fallbacks in Production Inference Path — MEDIUM

[`tool_manager.py:83-87`](server/src/airunner_services/llm/tool_manager.py#L83) has a `print()` fallback inside `_wrap_tool_with_dependencies` when `self.logger.debug` raises an exception:

```python
try:
    self.logger.debug(...)
except Exception:
    print(f"[TOOL WRAPPER] Invoking tool: ...", flush=True)
```

This pattern appears twice in `tool_manager.py` (lines 83 and 120). Additionally:
- [`generation_response_support.py:144-148`](server/src/airunner_services/llm/managers/mixins/generation_response_support.py#L144) uses `print()` directly in the error handler.
- [`adapters/mixins/tokenization_mixin.py:30-82`](server/src/airunner_services/llm/adapters/mixins/tokenization_mixin.py#L30) uses `print()` for Mistral tokenizer warnings.

**Impact**: These bypass the logging system, making it impossible to suppress, route, or capture this output in production. Structured log aggregators (ELK, Datadog) will miss them.

**Fix**: Replace all `print()` calls with `self.logger.*()` calls. Remove the try/except around logger.debug — if the logger itself raises, the correct behavior is to let it propagate.

### 3.2 f-String Logging Antipattern — 34+ Occurrences

The LLM managers use f-strings inside `logger.info()`, `logger.debug()`, etc.:

```python
self.logger.info(f"🔵 Checkpoint has {len(messages)} messages")
```

Python's logging module defers string interpolation to avoid cost when the log level is disabled. F-strings defeat this — the string is always formatted even if `INFO` logging is off. With 34+ such calls in just the managers directory, this adds unnecessary CPU cost to every inference request.

**Fix**: Use `%s` formatting:
```python
self.logger.info("Checkpoint has %d messages", len(messages))
```

### 3.3 Emoji-Decorated Logging in Production Code — LOW

[`database_checkpoint_saver.py:91`](server/src/airunner_services/llm/managers/database_checkpoint_saver.py#L91) uses emoji-decorated log messages:

```python
self.logger.info(f"🔵 DatabaseCheckpointSaver.put() called ...")
self.logger.info(f"💾 Stored full checkpoint state ...")
self.logger.warning(f"⚠️ Skipping checkpoint save ...")
```

These are debug-grade messages logged at `INFO` level. They'll appear in production logs on every request. The emoji decoration suggests this was debugging code that was never cleaned up.

**Fix**: Drop to `DEBUG` level and remove emoji decoration. Better: remove most of these entirely once the checkpoint system is verified stable.

---

## 4. Architecture Issues Not Previously Documented

### 4.1 `WorkflowManager` Recompiles the LangGraph on Every `set_conversation_id` Call

[`workflow_manager.py:115-128`](server/src/airunner_services/llm/workflow_manager.py#L115):

```python
def set_conversation_id(self, conversation_id: int, ephemeral: bool = False):
    self._conversation_id = conversation_id
    self._thread_id = str(conversation_id)
    self._memory = DatabaseCheckpointSaver(conversation_id, ephemeral=ephemeral)
    self._build_and_compile_workflow()  # ← full LangGraph recompile
```

`_build_and_compile_workflow()` re-creates and re-compiles the entire LangGraph state machine. LangGraph compilation is non-trivial (it builds the graph, validates edges, and JIT-compiles the checkpointer). This is called every time the conversation switches, which happens on every API request.

**Impact**: Unnecessary overhead on every message. The graph structure doesn't change between conversations — only the checkpoint saver's target conversation ID changes.

**Fix**: Update only `self._memory` and `self._thread_id` without recompiling. Inject the checkpoint saver into the compiled graph's config at invocation time instead of rebuild time.

### 4.2 `_checkpoint_state` Class-Level Dict Enables Cross-Instance State Contamination

From companion audit (3.2): `_checkpoint_state` is a class attribute. Adding to it:

Two `WorkflowManager` instances for different conversations share the same `_checkpoint_state` dict. In tests or in any scenario where multiple `WorkflowManager` instances exist (e.g., unit tests, multi-tenant scenarios), state from one conversation can pollute another.

Additionally, there is no `_checkpoint_state.pop(thread_id)` when `clear_memory()` is called — `clear_memory()` calls `clear_checkpoints()` on the saver but the class-level dict's entry for that thread may remain.

**Fix**: Move `_checkpoint_state` to instance level. Pass the in-memory checkpoint cache into the saver at construction time, not as a shared class dict.

### 4.3 `ThreadID = "default"` for Requests Without a Conversation ID

[`workflow_manager.py:92-94`](server/src/airunner_services/llm/workflow_manager.py#L92):
```python
self._thread_id = (
    str(conversation_id) if conversation_id else "default"
)
```

When no `conversation_id` is provided, all such requests share the same `"default"` thread ID in the class-level `_checkpoint_state`. Multiple concurrent requests without conversation IDs (e.g., health checks, initialization calls, tests) will share and potentially corrupt each other's checkpoint state.

**Fix**: Default to `str(uuid.uuid4())` when `conversation_id` is `None`, or enforce that a conversation ID is always required.

### 4.4 Tool Manager Merges Hardcoded Tools and Registry Tools Without Deduplication

[`tool_manager.py:144-184`](server/src/airunner_services/llm/tool_manager.py#L144): `get_all_tools()` builds a list of hardcoded tools then extends it with ToolRegistry tools. There is no check for name collisions. If a tool named `list_files` exists in both the hardcoded list and the ToolRegistry, it will appear twice in the bound tools list.

LangChain handles duplicate tool names by using the last occurrence, but this is silent. A model might invoke the wrong implementation of a tool with the same name.

**Fix**: Build a dict keyed by `tool.name` during assembly, letting ToolRegistry tools override hardcoded ones (or the reverse, explicitly). Log a warning when a collision is detected.

### 4.5 No Maximum Conversation History Enforcement Before Inference

`WorkflowManager` has a `max_history_tokens` parameter (default `8000`) and a `_token_counter`, but there is no code that actually truncates the message history when it exceeds this limit before sending to the LLM. The `count_tokens_approximately` function is assigned but grep shows no call site that enforces the limit.

**Impact**: For long conversations, the full history is sent to the model. For GGUF models with fixed context windows, this silently truncates at the model level (worst case: the model doesn't see recent messages).

**Fix**: In `_create_initial_state` or the checkpoint loader, trim history to `max_history_tokens` by removing oldest messages first, preserving the system prompt and most recent exchange.

---

## 5. Client-Side Issues Not Previously Documented

### 5.1 `thinkingBuffer` Set Not Appended — Confirmed Partial Bug

The companion audit flagged this. Confirming: [`useLLMWebSocket.ts:129`](client/src/features/llm/useLLMWebSocket.ts#L129):
```typescript
setThinkingBuffer(data.content ?? "");
```

Each `thinking` chunk arrives with the **full accumulated thinking content** (not an incremental delta), so `setThinkingBuffer` replacing the previous value is actually correct for this design. However, there is **no deduplication guard** — if two thinking chunks arrive with the same accumulated content before React re-renders, the buffer is set redundantly. More critically, line 136-141 clears `streamBuffer` and `thinkingBuffer` when `data.done === true` for thinking chunks. If a `thinking` chunk with `done: true` arrives while a regular response is still streaming, the `streamBuffer` is incorrectly cleared mid-stream.

**Fix**: Separate the `done` signal for thinking vs. response streams. Don't clear `streamBuffer` when a thinking sequence completes.

### 5.2 No Abort/Cancel Mechanism for In-Flight Inference

Neither `useLLMWebSocket.ts` nor `ChatView.tsx` exposes a "cancel generation" button or mechanism. The WebSocket connection can be closed to abort the stream, but:
1. There is no UI affordance for this.
2. Closing the WebSocket does not signal the server to stop the LangGraph execution — the server continues generating and the output is discarded client-side.
3. The `_interrupted` flag on `WorkflowManager` exists but there is no WebSocket message type that triggers it.

**Fix**: Add a `type: "cancel"` WebSocket message that the server handles by setting `_interrupted = True` on the active workflow. Add a stop button to the chat UI that sends this message.

### 5.3 LLM Settings Panel Does Not Expose Provider Selection

The client has `LLMSettings.use_openrouter`, `use_openai`, `use_ollama` on the server, but the client's settings panel ([`components/panels/llm-settings/`](client/src/components/panels/llm-settings/)) only shows generation parameters (temperature, top_p, etc.) via slider/checkbox fields. There is no UI for switching between GGUF, OpenRouter, Ollama, or OpenAI backends. Users must edit environment variables or the database directly.

---

## 6. Summary Table

| # | Finding | Type | Severity |
|---|---|---|---|
| 1 | `exec()` for database-stored custom tool code | Security | HIGH |
| 2 | RAG path traversal — `doc.path` read without boundary check (more detail) | Security | HIGH |
| 3 | `auto_extract_knowledge` defined but never consumed | Dead Config | MEDIUM |
| 4 | `yarn_target_context` setting unused / misleading | Dead Config | LOW |
| 5 | Stale `AIRUNNER_LLM_USE_OPENAI` module constant | Dead Code | LOW |
| 6 | `print()` fallbacks in production inference path | Code Quality | MEDIUM |
| 7 | 34+ f-string logging antipatterns in managers | Performance | LOW |
| 8 | Emoji-decorated `INFO`-level debug logs in checkpoint saver | Code Quality | LOW |
| 9 | `WorkflowManager` recompiles LangGraph on every `set_conversation_id` | Performance | MEDIUM |
| 10 | Class-level `_checkpoint_state` enables cross-instance contamination | Bug | MEDIUM |
| 11 | `_thread_id = "default"` for no-conversation requests | Bug | MEDIUM |
| 12 | Hardcoded + registry tools merged without deduplication check | Bug | LOW |
| 13 | No `max_history_tokens` enforcement before inference | Bug | MEDIUM |
| 14 | `thinkingBuffer` cleared on thinking-done while response still streaming | Bug | LOW |
| 15 | No abort/cancel mechanism for in-flight inference | UX | MEDIUM |
| 16 | Provider selection (GGUF/API) not exposed in client settings UI | UX | LOW |
