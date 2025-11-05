"""
Unit tests for AIRunnerClient library.

Tests client methods with mocked HTTP responses.
"""

import json
import pytest
import responses
from airunner.components.eval.client import AIRunnerClient, AIRunnerClientError


@pytest.fixture
def client():
    """Create a test client instance."""
    return AIRunnerClient(base_url="http://localhost:8188")


@responses.activate
def test_health_check_success(client):
    """Test successful health check."""
    responses.add(
        responses.GET,
        "http://localhost:8188/health",
        json={"status": "ready"},
        status=200,
    )

    result = client.health_check()
    assert result["status"] == "ready"


@responses.activate
def test_health_check_failure(client):
    """Test health check failure."""
    responses.add(
        responses.GET,
        "http://localhost:8188/health",
        status=500,
    )

    with pytest.raises(AIRunnerClientError):
        client.health_check()


@responses.activate
def test_list_models_success(client):
    """Test listing models."""
    responses.add(
        responses.GET,
        "http://localhost:8188/llm/models",
        json={"models": ["model1", "model2"]},
        status=200,
    )

    models = client.list_models()
    assert models == ["model1", "model2"]


@responses.activate
def test_generate_success(client):
    """Test non-streaming generation."""
    responses.add(
        responses.POST,
        "http://localhost:8188/llm/generate",
        json={"text": "Hello, world!", "done": True},
        status=200,
    )

    result = client.generate("Say hello")
    assert result["text"] == "Hello, world!"


@responses.activate
def test_generate_with_params(client):
    """Test generation with additional parameters."""

    def request_callback(request):
        payload = json.loads(request.body)
        assert payload["prompt"] == "Test prompt"
        assert payload["model"] == "test-model"
        assert payload["max_tokens"] == 100
        assert payload["temperature"] == 0.7
        assert payload["stream"] is False
        return (200, {}, json.dumps({"text": "Response"}))

    responses.add_callback(
        responses.POST,
        "http://localhost:8188/llm/generate",
        callback=request_callback,
        content_type="application/json",
    )

    client.generate(
        "Test prompt",
        model="test-model",
        max_tokens=100,
        temperature=0.7,
    )


@responses.activate
def test_generate_stream_not_allowed(client):
    """Test that stream=True raises ValueError in generate()."""
    with pytest.raises(ValueError, match="use generate_stream"):
        client.generate("Test", stream=True)


@responses.activate
def test_generate_stream_success(client):
    """Test streaming generation."""
    # Mock streaming response
    stream_data = [
        {"text": "Hello", "done": False},
        {"text": " ", "done": False},
        {"text": "world", "done": False},
        {"text": "!", "done": True},
    ]

    ndjson_response = "\n".join(json.dumps(chunk) for chunk in stream_data)

    responses.add(
        responses.POST,
        "http://localhost:8188/llm/generate",
        body=ndjson_response,
        status=200,
        content_type="application/x-ndjson",
        stream=True,
    )

    chunks = list(client.generate_stream("Test"))
    assert len(chunks) == 4
    assert chunks[0]["text"] == "Hello"
    assert chunks[-1]["done"] is True


@responses.activate
def test_generate_failure(client):
    """Test generation request failure."""
    responses.add(
        responses.POST,
        "http://localhost:8188/llm/generate",
        status=500,
    )

    with pytest.raises(AIRunnerClientError):
        client.generate("Test")


def test_client_custom_base_url():
    """Test client with custom base URL."""
    client = AIRunnerClient(base_url="http://custom:9999/")
    assert client.base_url == "http://custom:9999"


def test_client_custom_timeout():
    """Test client with custom timeout."""
    client = AIRunnerClient(timeout=60)
    assert client.timeout == 60
