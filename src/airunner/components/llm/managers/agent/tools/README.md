# LLM Agent Tools

This directory contains all LLM agent tool wrappers for the AI Runner project. Each tool exposes a specific capability (search, chat, RAG, etc.) to the agent framework, following a consistent interface and registration pattern.

## Tool Inventory

| Tool Name                | Class Name                  | Purpose                                 | Returns         | Typical Usage         |
|--------------------------|-----------------------------|-----------------------------------------|-----------------|----------------------|
| `search_tool`            | `SearchTool`                | Raw search results                      | dict            | Direct search        |
| `search_engine_tool`     | `SearchEngineTool`          | Search + answer synthesis               | str             | Conversational agent |
| `respond_to_search_query`| `RespondToSearchQueryTool`  | Synthesize answer from search results   | str             | Multi-step workflow  |
| `rag_engine_tool`        | `RAGEngineTool`             | Retrieval-augmented generation          | str             | Knowledge retrieval  |
| `chat_engine_tool`       | `ChatEngineTool`            | Conversational Q&A                      | str             | Chat agent           |
| `react_agent_tool`       | `ReActAgentTool`            | Reasoning + acting (multi-tool)         | varies          | ReAct agent          |
| `weather_tool`           | `WeatherTool`               | Current weather info for a location     | str             | Weather queries      |

## Tool Descriptions

### 1. ChatEngineTool
- **Purpose:** Conversational agent tool; leverages chat engine for context-aware answers.
- **Usage:** Used by agents for general Q&A with memory/history.

### 2. ReActAgentTool
- **Purpose:** Implements the ReAct pattern (reasoning + acting); supports multi-step tool use.
- **Usage:** Used for agents that need to chain reasoning and tool calls.

### 3. RespondToSearchQueryTool
- **Purpose:** Takes search results + original query, synthesizes a natural language answer.
- **Usage:** Used when search and answer synthesis are decoupled (multi-step workflows).

### 4. SearchTool
- **Purpose:** Thin wrapper for AggregatedSearchTool; exposes raw search as a tool.
- **Usage:** Used for direct search queries, returns raw results.

### 5. SearchEngineTool
- **Purpose:** High-level tool: performs search and synthesizes a conversational answer.
- **Usage:** Main tool for "search and answer" workflows.

### 6. RAGEngineTool
- **Purpose:** Retrieval-Augmented Generation; fetches docs from a knowledge base, then answers.
- **Usage:** Used for knowledge retrieval from internal/external corpora.

### 7. WeatherTool
- **Purpose:** Provides current weather information for a given location.
- **Usage:** Used for weather queries via slash command or agent workflow.

## How to Add a New Tool

1. Implement backend logic (e.g., in `src/airunner/tools/`).
2. Create a wrapper tool in this directory.
3. Register with `ToolRegistry`.
4. (Optional) Expose via a mixin for agent access.
5. Update this README.

## See Also
- [AggregatedSearchTool](../../../tools/search_tool.py) for the core search backend.
