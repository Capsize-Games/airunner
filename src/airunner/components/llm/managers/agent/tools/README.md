# LLM Agent Tools

This directory contains all LLM agent tool wrappers for the AI Runner project. Each tool exposes a specific capability (search, chat, browser, RAG, etc.) to the agent framework, following a consistent interface and registration pattern.

## Tool Inventory

| Tool Name                | Class Name                  | Purpose                                 | Returns         | Typical Usage         |
|--------------------------|-----------------------------|-----------------------------------------|-----------------|----------------------|
| `search_tool`            | `SearchTool`                | Raw search results                      | dict            | Direct search        |
| `search_engine_tool`     | `SearchEngineTool`          | Search + answer synthesis               | str             | Conversational agent |
| `respond_to_search_query`| `RespondToSearchQueryTool`  | Synthesize answer from search results   | str             | Multi-step workflow  |
| `browser_tool`           | `BrowserTool`               | Web browsing/scraping                   | varies          | Web navigation       |
| `rag_engine_tool`        | `RAGEngineTool`             | Retrieval-augmented generation          | str             | Knowledge retrieval  |
| `chat_engine_tool`       | `ChatEngineTool`            | Conversational Q&A                      | str             | Chat agent           |
| `react_agent_tool`       | `ReActAgentTool`            | Reasoning + acting (multi-tool)         | varies          | ReAct agent          |
| `weather_tool`           | `WeatherTool`               | Current weather info for a location     | str             | Weather queries      |
| `map_tool`               | `MapTool`                   | Map/geocoding/POI actions (Nominatim)   | dict            | Map agent           |

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

### 5. BrowserTool
- **Purpose:** Allows agents to browse/scrape web pages and trigger browser navigation in the GUI.
- **Usage:** Used for tasks requiring web navigation or scraping. Accepts both `url` and `input` as arguments (e.g., `{"input": "reddit.com"}` or `{"url": "https://reddit.com"}`), and normalizes to a full `https://` URL automatically. Robust to LLM and user input.
- **Integration:** Emits browser navigation signals via the agent API for GUI/browser integration. See `BrowserToolsMixin` for singleton access pattern.

### 6. SearchEngineTool
- **Purpose:** High-level tool: performs search and synthesizes a conversational answer.
- **Usage:** Main tool for "search and answer" workflows.

### 7. RAGEngineTool
- **Purpose:** Retrieval-Augmented Generation; fetches docs from a knowledge base, then answers.
- **Usage:** Used for knowledge retrieval from internal/external corpora.

### 8. WeatherTool
- **Purpose:** Provides current weather information for a given location.
- **Usage:** Used for weather queries via slash command or agent workflow.

### 9. MapTool
- **Purpose:** Provides map/geocoding/POI actions using Nominatim and Leaflet.
- **Usage:** Used for geocoding, POI search, adding markers, and zooming to locations. Directions/routing is not supported by Nominatim. See `components/tools/map_tool.py` for API.

## How to Add a New Tool

1. Implement backend logic (e.g., in `src/airunner/tools/`).
2. Create a wrapper tool in this directory.
3. Register with `ToolRegistry`.
4. (Optional) Expose via a mixin for agent access.
5. Update this README.

## See Also
- [AggregatedSearchTool](../../../tools/search_tool.py) for the core search backend.
