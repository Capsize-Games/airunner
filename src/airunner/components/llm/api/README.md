# LLM API Service

This module provides the API service interface for LLM-related operations, including text generation, conversation management, and map search requests.

## Key Components
- **LLMAPIService**: Main API service for LLM operations. Emits signals to the LLM generate worker for processing requests.

## Map Search Integration
- The `map_search(query: str)` method emits a `MAP_SEARCH_REQUEST_SIGNAL` to the LLM generate worker, which will process map search queries (e.g., geocoding, location lookup) via the LLM agent.

## Usage Example
```python
llm_api = LLMAPIService()
llm_api.map_search("Eiffel Tower")
```

## Signals
- `MAP_SEARCH_REQUEST_SIGNAL`: Used for map search requests from the map widget.

## Future Work
- Integrate actual LLM/geocoding logic in the LLM agent for map search.
