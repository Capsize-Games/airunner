# LLM API Service

This module provides the API service interface for LLM-related operations, including text generation, conversation management, and map search requests.

## Key Components
- **LLMAPIService**: Main API service for LLM operations. Emits signals to the LLM generate worker for processing requests.

## Usage Example
```python
llm_api = LLMAPIService()
```

## Future Work
- Integrate actual LLM/geocoding logic in the LLM agent for map search.
