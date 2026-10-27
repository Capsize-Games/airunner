# AIRunner LLM Agent Audit — Companion Report

> Companion to `llm_agent_audit.md`. This report covers systems, bugs, and issues that the original audit missed or only partially described. It does not repeat findings already documented in the original.

---

## 1. Corrections to the Original Audit

### 1.1 Long-Running Harness Is Wired In — But the Trigger Is Dead

The original audit states the long-running module "appears to be a separate, massive subsystem… Most of it seems unused or partially integrated." This is partially incorrect.

The harness **is** connected in two ways:
- [`tools/__init__.py:27`](server/src/airunner_services/llm/tools/__init__.py#L27): `LONG_RUNNING_TOOLS` is imported and presumably merged into the tool set.
- [`tool_classification_mixin.py:550-572`](server/src/airunner_services/llm/managers/mixins/tool_classification_mixin.py#L550): `_should_use_harness()` is implemented, imports `should_use_harness` from the module, and returns whether the harness should be used.

**However**: `_should_use_harness()` is **never called anywhere** in the codebase. The method is defined but has no callers — the hook exists but is never invoked. The harness tools are imported, but the decision logic that would route a prompt to the harness is disconnected. This is more precisely described as "the routing trigger is dead" than "the module is disconnected."

### 1.2 Mixin Count

The original audit lists 18 then later says "19 mixins" for `LLMModelManager`. The inconsistency is in the original; the table has 19 rows while the text says 18. The companion table in section 4.1 of the original counts 19 (including `QuantizationMixin` and `QuantizationConfigMixin` as separate). Confirmed: 19 mixins.

---

## 2. Uncovered System: The GGUF Adapter Layer (30+ files)

The original audit describes `WorkflowManager` as the LangGraph runner but does not cover the **GGUF adapter system**, which is the actual local inference backend. This is a substantial subsystem.

### 2.1 Architecture

The GGUF path (via llama.cpp) is the **primary local inference path**. Transformers-based loading is explicitly disabled. Entry point is [`chat_model_factory.py`](server/src/airunner_services/llm/adapters/chat_model_factory.py), which delegates to one of four provider builders:

| Provider | Factory Method |
|---|---|
| Local GGUF (llama.cpp) | `create_gguf_model` |
| OpenRouter (API) | `create_openrouter_model` |
| Ollama (local API) | `create_ollama_model` |
| OpenAI (API) | `create_openai_model` |

**The original audit never mentions the multi-provider model factory.** `LLMSettings` exposes `use_openrouter`, `use_openai`, and `use_ollama` flags, and `ChatModelFactory` has implementations for all four. This is a real feature, not stubs.

### 2.2 The GPT-OSS Harmony Format

Some models emit output in a custom "Harmony" channel format:

```
<|start|>assistant<|channel|>analysis<|message|>...thinking...<|end|>
<|start|>assistant<|channel|>final<|message|>...response...<|end|>
```

[`GPTOSSStreamParser`](server/src/airunner_services/llm/gpt_oss_parser.py#L159) is a full streaming state machine that parses this format incrementally. The parser routes `analysis` channel content to `reasoning_content` and `final` channel content to the visible response.

This is entirely invisible in the original audit. The `thinking_content` the client displays comes from this parser (for GPT-OSS models), not from a simple `<think>` tag.

**Issue**: The parser's `finish()` method flushes trailing content that didn't arrive before a control token. If a stream terminates mid-token (e.g., connection drop), the buffer is partially flushed but the parse state is left ambiguous — there is no `reset()` or error recovery mechanism.

### 2.3 Multiple Tool Call Parsing Strategies

For GGUF models, tool call parsing is attempted in **four different strategies** in priority order:

1. **Native llama.cpp tool calling** — structured JSON from the model API
2. **GPT-OSS commentary parsing** — tool calls embedded in the Harmony `analysis` channel
3. **Prefilled completion** — tool call prefix is injected; model completes the payload
4. **Extraction (fallback)** — regex/heuristic extraction from raw text

The [`_resolved_tool_calls`](server/src/airunner_services/llm/adapters/chat_gguf_streaming_gpt_oss_tail.py#L76) function tries strategies 2–4 in sequence. Failure at one level silently falls through to the next. There is no logging when a fallback is used.

**Issue**: Silent fallthrough makes it impossible to know in production which parsing strategy was used for a given tool call. A model regression (e.g., switching from native to commentary format) would be invisible in logs.

### 2.4 Streaming Overlap Merge — O(n²) Worst Case

[`merge_streamed_text`](server/src/airunner_services/llm/adapters/chat_gguf_streaming_common.py#L10) deduplicates streaming fragments using an overlap scan:

```python
for overlap in range(max_overlap, 0, -1):
    if existing.endswith(fragment[:overlap]):
        return existing + fragment[overlap:]
```

`max_overlap` is `min(len(existing), len(fragment))`. For a 10,000-character accumulated response with a 200-character fragment, this is up to 200 string comparisons each involving up to 200-character slices. In the common case (no overlap) all comparisons fail. This is O(n²) in accumulated content length × fragment size.

In practice, streaming chunks are small (10–50 chars), making this unlikely to matter. But for models that emit larger chunks (some GGUF quantizations do), this could cause noticeable latency spikes late in a response.

---

## 3. Bugs Not Covered in Original Audit

### 3.1 Debug File I/O Left in Production Code — HIGH

[`database_checkpoint_saver.py`](server/src/airunner_services/llm/managers/database_checkpoint_saver.py) contains debug code that writes to `/tmp/checkpoint_debug.log` on every call to `get_tuple()`:

```python
# Lines 221-228
import sys
with open("/tmp/checkpoint_debug.log", "a") as f:
    f.write(
        f"[GET] thread_id={thread_id}, conv_id={self.conversation_id}, "
        f"checkpoint_keys={list(self._checkpoint_state.keys())}\n"
    )
    sys.stdout.flush()
```

This same pattern repeats at **five locations** within `get_tuple()` (lines 221, 232, 245, 251, 255). `get_tuple()` is called on every LangGraph invocation — once per message exchange.

**Impact**:
- File I/O on the hot inference path (every request opens, writes, and closes a file).
- Leaks conversation metadata (thread IDs, conversation IDs) to a world-readable `/tmp` path.
- The log file grows without bound.

**Fix**: Remove all five `with open("/tmp/checkpoint_debug.log")` blocks and the `import sys` at line 221.

### 3.2 Checkpoint State Memory Leak — MEDIUM

`DatabaseCheckpointSaver._checkpoint_state` is a class-level dict that accumulates one entry per conversation, keyed by `thread_id` (the conversation ID as a string). Entries are removed only when `clear_checkpoints()` or `clear_thread()` is explicitly called.

In a long-lived server serving many conversations, this dict grows indefinitely. Each entry holds a full `Checkpoint` object containing all messages for that conversation.

**Impact**: Memory growth proportional to total number of conversations served since last restart, not concurrent conversations.

**Fix**: Add a maximum size with LRU eviction, or clear thread state when the WebSocket connection for that conversation closes.

### 3.3 `put_writes` No-Op — MEDIUM

```python
def put_writes(self, config, writes, task_id, task_path="") -> None:
    del config, writes, task_id, task_path
    # For our simple implementation, we don't need to store intermediate writes
```

LangGraph calls `put_writes` to persist intermediate tool results during a graph execution step. By discarding these, if the server crashes mid-tool-chain (e.g., after a tool call but before the final LLM response), the tool results are lost. On restart, the graph would re-execute all tool calls.

For tools with side effects (`record_knowledge`, `generate_image`, `write_file`), this means the action runs twice after a crash. For expensive tools (`search_web`, `numpy_compute`), this wastes resources.

### 3.4 Knowledge Tool Signal Code Mismatch — LOW

[`delete.py:65-66`](server/src/airunner_services/llm/tools/knowledge_tools/delete.py#L65) emits `SignalCode.KNOWLEDGE_FACT_ADDED` when deleting a fact:

```python
api.emit_signal(
    SignalCode.KNOWLEDGE_FACT_ADDED,
    {"deleted": True, "count": count},
)
```

The same wrong signal code is used in `update.py`. Any UI listener subscribed to `KNOWLEDGE_FACT_ADDED` would receive delete/update events, and a hypothetical `KNOWLEDGE_FACT_DELETED` listener would never fire. Whether any listener consumes this signal matters for impact, but the semantic mismatch is a latent bug for any future subscriber.

### 3.5 RAG File Read Without Path Boundary Check — LOW

[`llm_runtime.py:241-243`](server/src/airunner_services/api/routes/llm_runtime.py#L241) reads document content for RAG context injection:

```python
file_path = doc.path
with open(file_path, "r", errors="replace") as f:
    text = f.read(4096)
```

`doc.path` comes from the database. If a document record is modified to contain an absolute path outside the expected document directory (e.g., `/etc/passwd`), the server would read and inject that file's content into the system prompt. This is not exploitable from the LLM itself, but it is a concern if the database is accessible to multiple users or services.

**Fix**: `pathlib.Path(file_path).resolve()` and assert the resolved path starts with the expected documents directory.

---

## 4. Architectural Gaps Not Documented

### 4.1 The `LLMSettings` Provider Matrix

The original audit describes the system as GGUF-only. In reality, `LLMSettings` exposes a full provider matrix:

```python
use_local_llm: bool = True      # llama.cpp (GGUF)
use_openrouter: bool = False    # OpenRouter API
use_ollama: bool = False        # Ollama local API
use_openai: bool = False        # OpenAI API
```

`ChatModelFactory` has distinct implementations for each. The implications for the architecture:

- The GGUF adapter layer (30+ files) only applies when `use_local_llm=True`.
- For API backends, the `WorkflowManager` would use a LangChain chat model directly, bypassing all of the GGUF streaming/parsing code.
- The GPT-OSS Harmony format parser is entirely GGUF-specific.

**The original audit's flow diagrams implicitly assume the GGUF path.** For API-backed models, the flow is significantly simpler.

### 4.2 YARN Context Extension

`LLMSettings` exposes:
```python
use_yarn: bool = False
yarn_target_context: int = 0
```

YARN (Yet Another RoPE extensioN) allows GGUF models to operate beyond their trained context window. The default `yarn_target_context = 0` is a misconfiguration: when `use_yarn` is enabled, a target context of 0 would either crash llama.cpp or produce undefined behavior. There is no validation that `yarn_target_context > 0` when `use_yarn = True`.

### 4.3 Conversation Summarization Is Configured But Not Audited

`LLMSettings` has:
```python
perform_conversation_summary: bool = ...
summarize_after_n_turns: int = ...
```

The original audit does not mention automatic summarization. This is a separate code path (likely in `ConversationManagementMixin`) that periodically summarizes old messages to stay within context. If summarization is lossy or occurs at the wrong time, it could silently discard conversation history that the user expects the model to remember.

### 4.4 The `auto_extract_knowledge` Default

```python
auto_extract_knowledge: bool = True
```

This is enabled by default with no mention in the original audit. It implies the system automatically calls `record_knowledge` during normal conversation — every exchange potentially writes to the knowledge base. The conditions under which this fires, and whether the user is informed, are undocumented here (they may be in the system prompt instructions, but the setting itself is surprising).

---

## 5. Client-Side Gaps

### 5.1 IndexedDB Quota Eviction Inconsistency

[`evict.ts`](client/src/db/evict.ts) defines two separate behaviors that don't agree on what to evict:

- `EVICTION_ORDER` (used for quota pressure): `civitaiThumbnails`, `civitaiModels`, `images`, `imageDates`, `loras`, `embeddings` — **does not include `kbDocuments`**.
- `clearAllCache()` (manual clear): clears all of the above **plus `kbDocuments`**.

When the browser hits a storage quota, knowledge base documents will never be automatically evicted. In a knowledge-heavy use case, this means quota errors will persist even after the eviction sweep, since the largest table is excluded.

**Recommendation**: Either add `kbDocuments` to `EVICTION_ORDER` at a lower priority than messages (which are never evicted), or document why it's intentionally excluded.

### 5.2 No Reconnect Backoff on TTS WebSocket

[`chat.ts`](client/src/api/chat.ts) reconnects the TTS WebSocket with a fixed 5-second delay:

```typescript
setTimeout(() => connectTTSWS(), 5000);
```

If the server is down for an extended period, this creates a reconnect loop at exactly 5s intervals indefinitely. There is no exponential backoff, no maximum retry count, and no user feedback that TTS is unavailable. The LLM chat WebSocket (`useLLMWebSocket.ts`) has the same pattern.

**Risk**: In a server restart scenario, both WebSockets will hammer reconnection at fixed intervals rather than backing off.

### 5.3 `useLLMWebSocket` Message Queue Silently Drops on Overflow

```typescript
// Messages queued while connecting are replayed on open.
```

The hook queues messages sent while the WebSocket is connecting. If the connection takes longer than expected (e.g., cold start), and the user clicks send multiple times, all queued messages would be sent in sequence on connect. There is no max queue size or user feedback that messages are queued.

---

## 6. File Inventory Additions

The original audit's file inventory covers `llm/` on the server and 6 client files. These systems were not listed:

### Server — Not Inventoried

| Path | Purpose |
|---|---|
| `llm/adapters/` (30+ files) | Full GGUF inference path, streaming, tool parsing, Harmony format |
| `llm/gpt_oss_parser.py` | GPT-OSS Harmony streaming parser (state machine) |
| `llm/managers/database_checkpoint_saver.py` | Custom LangGraph checkpoint persistence |
| `llm/llm_settings.py` | Provider configuration dataclass |
| `llm/config/provider_config.py` | Provider connection settings |
| `api/routes/llm_runtime.py` | WebSocket handler + RAG context injection |

### Client — Not Inventoried

| Path | Purpose |
|---|---|
| `api/chat.ts` | REST + TTS WebSocket (TTS covered only by mention) |
| `db/db.ts` | IndexedDB schema definition |
| `db/evict.ts` | Storage quota eviction strategy |
| `hooks/useConversations.ts` | Conversation list state |
| `hooks/useLlmPrefs.ts` | LLM preference settings |

---

## 7. Summary Table

| # | Finding | Type | Severity |
|---|---|---|---|
| 1 | Debug file I/O in `get_tuple()` writing to `/tmp/checkpoint_debug.log` | Bug | HIGH |
| 2 | `_should_use_harness()` is defined but never called (harness trigger dead) | Architecture | HIGH |
| 3 | Checkpoint `_checkpoint_state` dict grows unbounded (memory leak) | Bug | MEDIUM |
| 4 | `put_writes()` is a no-op — tool call results not persisted mid-chain | Bug | MEDIUM |
| 5 | Multi-provider support (OpenRouter, OpenAI, Ollama) not documented | Architecture | INFO |
| 6 | GPT-OSS Harmony format parser not covered in original audit | Architecture | INFO |
| 7 | Four tool call parsing strategies with silent fallthrough — no logging | Architecture | MEDIUM |
| 8 | `merge_streamed_text` has O(n²) worst case for long responses | Performance | LOW |
| 9 | YARN `target_context=0` default is a misconfiguration when YARN is enabled | Bug | LOW |
| 10 | Knowledge tool signal code mismatch (`KNOWLEDGE_FACT_ADDED` for delete/update) | Bug | LOW |
| 11 | RAG file read without path boundary check | Security | LOW |
| 12 | `kbDocuments` excluded from IndexedDB quota eviction | Client Bug | LOW |
| 13 | No exponential backoff on LLM/TTS WebSocket reconnect | Client | LOW |
| 14 | `auto_extract_knowledge` enabled by default (silent side effect) | Architecture | INFO |
| 15 | Conversation summarization path exists but is unaudited | Architecture | INFO |
