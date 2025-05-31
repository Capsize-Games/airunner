# Tools Module

## AggregatedSearchTool

`AggregatedSearchTool` provides a static, cache-enabled interface for performing aggregated searches across multiple online services (web, academic, news, code, books, Q&A).

### Usage

```
from airunner.tools.search_tool import AggregatedSearchTool

results = await AggregatedSearchTool.aggregated_search("python asyncio", category="web")
```

- All methods are static.
- Results are cached for efficiency.
- Intended for use in NodeGraphQt nodes, LLM tool integrations, and other AI Runner components.

### Dependencies

Install search dependencies with:

```
pip install .[search]
```

### Services Supported
- DuckDuckGo
- Google Custom Search
- Bing
- Wikipedia
- arXiv
- NewsAPI
- StackExchange
- GitHub Repositories
- OpenLibrary

### Integration Points
- NodeGraphQt node: Use this tool for search operations.
- ToolsMixin: Expose as a tool callable by the LLM.

---

See the source code for more details and docstrings.
