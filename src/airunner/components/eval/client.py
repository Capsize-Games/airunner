"""
AIRunnerClient - Python client library for AI Runner eval testing.

Provides a simple interface to interact with the headless AI Runner server
for evaluation testing purposes. Supports both streaming and non-streaming
LLM generation, model listing, and health checks.

Example:
    >>> client = AIRunnerClient(base_url="http://localhost:8188")
    >>> response = client.generate("What is 2+2?")
    >>> print(response["text"])

    >>> for chunk in client.generate_stream("Tell me a story"):
    ...     print(chunk["text"], end="", flush=True)
"""

import json
import logging
import requests
from typing import Dict, Any, Optional, Iterator, List


class AIRunnerClientError(Exception):
    """Base exception for AIRunnerClient errors."""


class AIRunnerClient:
    """Client library for interacting with AI Runner headless server.

    This client provides methods to:
    - Generate LLM completions (streaming and non-streaming)
    - List available models
    - Check server health

    Args:
        base_url: Base URL of the AI Runner server (default: http://localhost:8188)
        timeout: Request timeout in seconds (default: 300)

    Attributes:
        base_url: The base URL of the server
        timeout: Request timeout in seconds
        logger: Logger instance for client operations
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8188",
        timeout: int = 300,
    ):
        """Initialize the AI Runner client.

        Args:
            base_url: Base URL of the AI Runner server
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def health_check(self) -> Dict[str, Any]:
        """Check if the server is running and healthy.

        Returns:
            Dict with server status information

        Raises:
            AIRunnerClientError: If server is not reachable or unhealthy
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise AIRunnerClientError(f"Health check failed: {e}")

    def list_models(self) -> List[str]:
        """Get list of available LLM models.

        Returns:
            List of model names

        Raises:
            AIRunnerClientError: If request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/llm/models",
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except requests.RequestException as e:
            raise AIRunnerClientError(f"Failed to list models: {e}")

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate LLM completion (non-streaming).

        Args:
            prompt: The prompt text to generate from
            model: Model name to use (optional, uses server default)
            max_tokens: Maximum tokens to generate (optional)
            temperature: Sampling temperature (optional)
            stream: Whether to stream (must be False for this method)
            **kwargs: Additional LLM parameters to pass to server

        Returns:
            Dict with response data including 'text' field

        Raises:
            AIRunnerClientError: If request fails
            ValueError: If stream=True (use generate_stream instead)
        """
        if stream:
            raise ValueError(
                "stream=True not allowed in generate(). "
                "Use generate_stream() instead."
            )

        request_data = self._build_request_data(
            prompt, model, max_tokens, temperature, False, **kwargs
        )

        try:
            response = requests.post(
                f"{self.base_url}/llm/generate",
                json=request_data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self._process_response(response.json())
        except requests.RequestException as e:
            raise AIRunnerClientError(f"Generate request failed: {e}")

    def _build_request_data(
        self,
        prompt: str,
        model: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        stream: bool,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Build request data dict for generate endpoint."""
        request_data = {"prompt": prompt, "stream": stream}

        if model is not None:
            request_data["model"] = model
        if max_tokens is not None:
            request_data["max_tokens"] = max_tokens
        if temperature is not None:
            request_data["temperature"] = temperature

        request_data.update(kwargs)
        return request_data

    def _process_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process API response and map fields."""
        if "message" in data and "text" not in data:
            data["text"] = data["message"]
        return data

    def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> Iterator[Dict[str, Any]]:
        """Generate LLM completion with streaming.

        Yields NDJSON-formatted response chunks as they arrive.

        Args:
            prompt: The prompt text to generate from
            model: Model name to use (optional, uses server default)
            max_tokens: Maximum tokens to generate (optional)
            temperature: Sampling temperature (optional)
            **kwargs: Additional LLM parameters to pass to server

        Yields:
            Dict chunks with 'text' and 'done' fields

        Raises:
            AIRunnerClientError: If request fails

        Example:
            >>> for chunk in client.generate_stream("Hello"):
            ...     print(chunk["text"], end="", flush=True)
            ...     if chunk.get("done"):
            ...         break
        """
        request_data = self._build_request_data(
            prompt, model, max_tokens, temperature, True, **kwargs
        )

        try:
            response = requests.post(
                f"{self.base_url}/llm/generate",
                json=request_data,
                stream=True,
                timeout=self.timeout,
            )
            response.raise_for_status()
            yield from self._parse_ndjson_stream(response)

        except requests.RequestException as e:
            raise AIRunnerClientError(f"Streaming request failed: {e}")

    def _parse_ndjson_stream(
        self, response: requests.Response
    ) -> Iterator[Dict[str, Any]]:
        """Parse NDJSON stream from response."""
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    yield chunk
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse NDJSON chunk: {e}")
                    continue
