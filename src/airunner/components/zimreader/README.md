# Zimreader Component

This component provides utilities for reading and searching ZIM files (offline web archives) using the `libzim` library. It includes:

- `ZIMReader`: A Python class for direct ZIM archive access and search.
- `LlamaIndexZIMReader`: A LlamaIndex-compatible reader that allows ZIM files to be indexed and queried by the AI Runner RAG pipeline.

## Usage

- Use `ZIMReader` for direct programmatic access to ZIM articles and search.
- Use `LlamaIndexZIMReader` to enable LlamaIndex (and thus the LLM agent) to ingest and retrieve content from ZIM files as part of document RAG.

This enables offline, high-performance access to large knowledge bases (e.g., Wikipedia) for LLM-powered applications.
