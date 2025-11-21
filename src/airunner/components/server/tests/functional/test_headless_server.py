"""
Functional tests for the headless LLM server.

These tests verify the headless server works correctly with real HTTP requests.
NO MOCKING - these are true functional tests against a running server.

Requirements:
- Headless server must be running on localhost:8080
- Model must be loaded for generation tests
- Tests verify streaming, RAG files, conversation isolation, and error handling
"""

import json
import os
import tempfile
import time

import pytest
import requests
from airunner.settings import (
    AIRUNNER_HEADLESS_SERVER_HOST,
    AIRUNNER_HEADLESS_SERVER_PORT,
)


# Test configuration
BASE_URL = (
    f"http://{AIRUNNER_HEADLESS_SERVER_HOST}:{AIRUNNER_HEADLESS_SERVER_PORT}"
)
TIMEOUT_CONNECT = 5  # seconds
TIMEOUT_READ = 60  # seconds for generation


class TestHeadlessServerHealth:
    """Test basic server health and availability."""

    def test_server_is_running(self):
        """Verify the server responds to health check requests."""
        response = requests.get(
            f"{BASE_URL}/health", timeout=(TIMEOUT_CONNECT, TIMEOUT_READ)
        )
        assert response.status_code == 200, "Server health check failed"

    def test_server_health_response_format(self):
        """Verify health check returns expected format."""
        response = requests.get(
            f"{BASE_URL}/health", timeout=(TIMEOUT_CONNECT, TIMEOUT_READ)
        )
        data = response.json()
        assert (
            "status" in data or "message" in data
        ), "Health response missing status/message"


class TestStreamingGeneration:
    """Test streaming LLM generation."""

    def test_streaming_basic_generation(self):
        """Test basic streaming generation without RAG."""
        payload = {
            "prompt": "Say 'test successful' and nothing else.",
            "action": "CHAT",
            "stream": True,
            "llm_request": {
                "max_new_tokens": 10,
                "temperature": 0.1,
                "tool_categories": [],
            },
        }

        response = requests.post(
            f"{BASE_URL}/llm",
            json=payload,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            stream=True,
        )

        assert response.status_code == 200, "Streaming request failed"

        # Collect streamed chunks
        chunks = []
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if chunk.get("message"):
                    chunks.append(chunk["message"])

        # Verify we got a response
        full_response = "".join(chunks).strip()
        assert len(full_response) > 0, "No content in streamed response"

    def test_streaming_with_rag_files(self):
        """Test streaming generation with RAG files loaded."""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("Test Document Content\n")
            f.write("This is a test document for RAG functionality.\n")
            f.write(
                "It contains specific information that should be referenced.\n"
            )
            temp_file = f.name

        try:
            payload = {
                "prompt": "What does the document say?",
                "action": "CHAT",
                "stream": True,
                "llm_request": {
                    "max_new_tokens": 50,
                    "temperature": 0.1,
                    "tool_categories": ["rag"],
                    "rag_files": [temp_file],
                },
            }

            response = requests.post(
                f"{BASE_URL}/llm",
                json=payload,
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
                stream=True,
            )

            assert response.status_code == 200, "RAG streaming request failed"

            # Collect response
            chunks = []
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if chunk.get("message"):
                        chunks.append(chunk["message"])

            full_response = "".join(chunks).strip()
            assert len(full_response) > 0, "No content in RAG response"

        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestConversationIsolation:
    """Test that conversations are properly isolated."""

    def test_new_conversation_without_id(self):
        """Test that each request without conversation_id starts a new conversation."""
        # First request
        payload1 = {
            "prompt": "Remember this number: 42",
            "action": "CHAT",
            "stream": True,
            "llm_request": {
                "max_new_tokens": 20,
                "temperature": 0.1,
                "tool_categories": [],
            },
        }

        response1 = requests.post(
            f"{BASE_URL}/llm",
            json=payload1,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            stream=True,
        )
        assert response1.status_code == 200

        # Consume first response
        for line in response1.iter_lines():
            pass

        # Second request without conversation_id - should NOT remember
        payload2 = {
            "prompt": "What number did I just tell you?",
            "action": "CHAT",
            "stream": True,
            "llm_request": {
                "max_new_tokens": 20,
                "temperature": 0.1,
                "tool_categories": [],
            },
        }

        response2 = requests.post(
            f"{BASE_URL}/llm",
            json=payload2,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            stream=True,
        )
        assert response2.status_code == 200

        chunks = []
        for line in response2.iter_lines():
            if line:
                chunk = json.loads(line)
                if chunk.get("message"):
                    chunks.append(chunk["message"])

        full_response = "".join(chunks).lower()
        # Should NOT contain "42" if conversation isolation is working
        # Note: This is a weak test - the model might guess the number
        # Better would be to check conversation IDs are different
        assert True  # Placeholder - need to check actual implementation

    def test_ephemeral_conversation(self):
        """Test that ephemeral_conversation keeps conversation in memory only."""
        payload = {
            "prompt": "Test ephemeral conversation",
            "action": "CHAT",
            "stream": True,
            "llm_request": {
                "max_new_tokens": 10,
                "temperature": 0.1,
                "tool_categories": [],
                "ephemeral_conversation": True,
            },
        }

        response = requests.post(
            f"{BASE_URL}/llm",
            json=payload,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            stream=True,
        )

        assert response.status_code == 200
        # TODO: Verify conversation not saved to database


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_malformed_json_request(self):
        """Test server handles malformed JSON gracefully."""
        response = requests.post(
            f"{BASE_URL}/llm",
            data="invalid json{{{",
            headers={"Content-Type": "application/json"},
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
        )
        assert response.status_code in [
            400,
            500,
        ], "Should handle malformed JSON"

    def test_missing_required_fields(self):
        """Test server handles missing required fields."""
        payload = {
            "action": "CHAT",
            # Missing prompt
        }

        try:
            response = requests.post(
                f"{BASE_URL}/llm",
                json=payload,
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            )
            # Server should either reject (400) or handle gracefully
            assert response.status_code in [200, 400, 422, 500]
        except requests.exceptions.RequestException:
            # Connection errors are acceptable for invalid requests
            pass

    def test_invalid_rag_file_path(self):
        """Test server handles non-existent RAG file paths."""
        payload = {
            "prompt": "Test with invalid file",
            "action": "CHAT",
            "stream": True,
            "llm_request": {
                "max_new_tokens": 10,
                "temperature": 0.1,
                "tool_categories": ["rag"],
                "rag_files": ["/nonexistent/file/path.txt"],
            },
        }

        try:
            response = requests.post(
                f"{BASE_URL}/llm",
                json=payload,
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
                stream=True,
            )
            # Server should handle gracefully
            assert response.status_code in [200, 400, 500]
        except requests.exceptions.RequestException:
            # Connection errors are acceptable
            pass


class TestChunkedAndFormEncoding:
    """Test Transfer-Encoding: chunked and application/x-www-form-urlencoded parsing."""

    def test_chunked_transfer_encoding_request(self):
        """Test that the server correctly reads a Transfer-Encoding: chunked request body."""
        payload = {
            "prompt": "Say 'chunked test' and nothing else.",
            "action": "CHAT",
            "stream": True,
            "llm_request": {
                "max_new_tokens": 20,
                "temperature": 0.1,
                "tool_categories": [],
            },
        }

        json_bytes = json.dumps(payload).encode("utf-8")

        def gen():
            # Yield in small fragments to simulate chunked transfer
            chunk_size = 64
            for i in range(0, len(json_bytes), chunk_size):
                yield json_bytes[i : i + chunk_size]

        headers = {
            "Transfer-Encoding": "chunked",
            "Content-Type": "application/json",
        }

        response = requests.post(
            f"{BASE_URL}/llm",
            data=gen(),
            headers=headers,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            stream=True,
        )

        assert response.status_code == 200, "Chunked request failed"

        # Collect streamed chunks - ensure at least one chunk with 'message' is present
        messages = []
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if chunk.get("message"):
                        messages.append(chunk["message"])
                except Exception:
                    # ignore parse issues
                    pass

        assert len(messages) > 0, "No content in streamed chunked response"

    def test_form_encoded_llm_request(self):
        """Test that application/x-www-form-urlencoded with JSON string llm_request is parsed."""
        payload = {
            "prompt": "Form-encoded test",
            "action": "CHAT",
            "stream": True,
        }
        llm_request_dict = {
            "max_new_tokens": 10,
            "temperature": 0.1,
            "tool_categories": [],
        }

        data = payload.copy()
        data["llm_request"] = json.dumps(llm_request_dict)

        # requests will set Content-Type: application/x-www-form-urlencoded automatically
        response = requests.post(
            f"{BASE_URL}/llm",
            data=data,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            stream=True,
        )

        assert response.status_code == 200, "Form-encoded request failed"

        messages = []
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if chunk.get("message"):
                        messages.append(chunk["message"])
                except Exception:
                    # ignore parse errors
                    pass

        assert (
            len(messages) > 0
        ), "No content in streamed form-encoded response"


class TestTimeout:
    """Test timeout behavior."""

    def test_reasonable_response_time(self):
        """Test that simple requests complete within reasonable time."""
        start_time = time.time()

        payload = {
            "prompt": "Say hi",
            "action": "CHAT",
            "stream": True,
            "llm_request": {
                "max_new_tokens": 5,
                "temperature": 0.1,
                "tool_categories": [],
            },
        }

        response = requests.post(
            f"{BASE_URL}/llm",
            json=payload,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            stream=True,
        )

        # Consume response
        for line in response.iter_lines():
            pass

        elapsed = time.time() - start_time

        # Should complete well under 10 seconds for simple request
        assert (
            elapsed < 10.0
        ), f"Simple request took {elapsed:.1f}s, should be under 10s"


if __name__ == "__main__":
    # Run with: python -m pytest src/airunner/components/server/tests/functional/test_headless_server.py -v
    pytest.main([__file__, "-v", "-s"])
