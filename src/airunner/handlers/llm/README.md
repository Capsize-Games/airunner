# LLM Handler: Agent and Memory Management

## Overview

This module provides the core logic for managing Large Language Model (LLM) agents and their memory within AI Runner. The `agent` submodule implements the conversational agent logic, while the `storage/chat_store` submodule provides persistent storage for chat histories and conversation state.

## Memory Management and Conversation Structure

### Agent Memory Architecture

- **Agent (`agent/`)**: The agent is responsible for orchestrating LLM interactions, managing conversation state, and integrating with various engines (e.g., chat, RAG, mood, summary).
- **Memory Management**: The agent uses a `ChatMemoryBuffer` to maintain a rolling window of conversation history, which is critical for context-aware LLM responses. This buffer is backed by a `chat_store` implementation.
- **Chat Store (`storage/chat_store/`)**: This directory contains implementations for persistent chat history storage. The default is `SimpleChatStore` (in-memory), but `DatabaseChatStore` (SQL-backed) is used when `AIRUNNER_LLM_CHAT_STORE` is set to `db`.
- **Conversation Structure**: Each conversation is a list of message dicts, each with fields like `role`, `name`, `content`, and `timestamp`. The agent appends new user/assistant messages to this list and synchronizes it with the chat memory and store.

### How Memory Works

- On each user/assistant turn, the agent:
  1. Appends the message to the conversation object (see `BaseAgent._append_conversation_messages`).
  2. Updates the chat memory buffer with the latest conversation state.
  3. Persists the conversation to the chat store (database or in-memory).
  4. Ensures all engines (chat, mood, summary, etc.) share the same memory instance for consistent context.
- When loading a conversation, the agent restores the chat memory buffer from the chat store, ensuring the LLM has access to the full conversation context.

### Conversation Format

- **Current Format:**
  ```json
  [
    {"role": "user", "name": "User", "content": "...", "timestamp": "..."},
    {"role": "assistant", "name": "Computer", "content": "...", "timestamp": "...", "bot_mood": "...", "bot_mood_emoji": "..."},
    ...
  ]
  ```
- **Old Format:**
  ```json
  [
    {"role": "user", "blocks": [{"block_type": "text", "text": "..."}]},
    {"role": "assistant", "blocks": [{"block_type": "text", "text": "..."}]},
    ...
  ]
  ```
- The agent and chat memory buffer are designed to work with the current format, but legacy support may exist for migration.

### Key Classes

- `BaseAgent` (in `agent/agents/base.py`): Orchestrates conversation, memory, and engine logic.
- `ChatMemoryBuffer` (in `agent/memory/`): Manages the in-memory window of chat history.
- `DatabaseChatStore`/`SimpleChatStore` (in `storage/chat_store/`): Provide persistent or ephemeral storage for chat histories.

## Usage

- The agent automatically manages memory and conversation state. No manual intervention is required for most use cases.
- To enable persistent chat history, set `AIRUNNER_LLM_CHAT_STORE=db` in your environment.
- For more details, see the docstrings in `agent/agents/base.py` and `storage/chat_store/database.py`.

---

## Agent and Chat Store Workflow

### How the Agent and Chat Store Work Together

- **Message Flow:**
  1. User/assistant messages are appended to the conversation (a list of dicts) by the agent.
  2. The agent updates the `ChatMemoryBuffer` with the latest conversation state.
  3. The `ChatMemoryBuffer` is backed by a chat store (in-memory or database), which persists the conversation history.
  4. When a conversation is loaded, the agent restores the memory buffer from the chat store, ensuring all engines (chat, mood, summary, etc.) have access to the full context.

- **Synchronization:**
  - The agent ensures all engines share the same memory instance for consistent context.
  - The chat memory buffer is re-initialized with the correct chat store key (conversation ID) when switching conversations.

### Memory Pipeline

- **On message send:**
  - The agent appends the message to the conversation and updates the memory buffer.
  - The buffer persists the updated history to the chat store.
  - All engines are synchronized to use the updated memory.
- **On conversation load:**
  - The agent loads messages from the chat store and sets them in the memory buffer.
  - The memory buffer is responsible for providing the correct window of context to the LLM.

## Conversation Structure and Format

- The agent and memory buffer expect each message to be a dict with at least `role`, `name`, `content`, and `timestamp` fields.
- **Important:** The memory buffer and engines may expect messages to be in a format compatible with `ChatMessage` (possibly with a `blocks` field for legacy support).
- If the conversation format changes (e.g., from `blocks` to flat `content`), ensure that the agent or memory buffer converts messages as needed when syncing memory. Otherwise, the LLM may not receive the full conversation context.

---

## Troubleshooting: Conversation History Not Retained

If the LLM does not seem to remember previous messages:
- Ensure the conversation format in the chat store matches what the agent and memory buffer expect (see above).
- Check that the agent's `chat_memory` is being properly initialized and synchronized with the chat store on each turn and when loading conversations.
- See the next section for a detailed analysis of possible causes.

## Troubleshooting: Conversation History Not Retained (Root Cause)

If the LLM does not remember previous messages:
- **Likely Cause:** The conversation format in the chat store changed from the old `blocks` structure to a flat `content` field, but the memory buffer and engines still expect the old format (with `blocks`).
- **Effect:** When the agent syncs memory, it may not reconstruct the full chat history, causing the LLM to see only the latest message or an empty context.
- **Solution:** Ensure that when loading or syncing memory, the agent converts messages from the new format into the expected `ChatMessage`/`blocks` structure for the memory buffer and engines. Update the memory sync logic if needed.

See `agent/agents/base.py` and `agent/memory/chat_memory_buffer.py` for details on how messages are processed and memory is synchronized.
