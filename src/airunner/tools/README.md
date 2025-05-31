# Tools Module

This directory contains utility tools for the AI Runner application. Each tool is designed to provide a focused, reusable function or class that can be leveraged by other modules.

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

## `web_content_extractor.py`

**Purpose:**

Extracts and processes main content from web pages for use in downstream tasks such as summarization, RAG (Retrieval-Augmented Generation), or data ingestion.

**Key Components:**
- Functions/classes for fetching, parsing, and cleaning web page content.
- Handles extraction of readable text, removal of boilerplate, and optional metadata extraction.
- Designed for integration with LLM pipelines and other content ingestion workflows.
- **Caching:** Extracted content is cached to avoid redundant network requests. The cache directory is now located at `{base_path}/cache/.webcache`, where `base_path` is obtained from `PathSettings.objects.first().base_path`. If this directory does not exist, it is created automatically.

**Trafilatura & Scrapy Integration:**
- [Trafilatura](https://trafilatura.readthedocs.io/) is used for robust extraction of main text content from web pages, handling boilerplate removal, readability, and metadata extraction.
- Trafilatura can be used as a standalone extractor or in conjunction with [Scrapy](https://scrapy.org/) for advanced crawling and scraping workflows.
- When used with Scrapy, Scrapy handles crawling and HTTP requests, while Trafilatura processes the HTML content of each page to extract the main text. This allows for scalable, high-quality web content extraction pipelines.

**Usage Example:**

```python
from airunner.tools.web_content_extractor import extract_main_content

url = "https://example.com/article"
main_text = extract_main_content(url)
print(main_text)
```

**Notes:**
- Handles common web content edge cases (ads, navigation, etc.).
- May use third-party libraries for HTML parsing and content extraction.
- See function/class docstrings in `web_content_extractor.py` for details.

---

See the source code for more details and docstrings.

Add new tools to this directory as needed. Update this README to document their purpose and usage.
