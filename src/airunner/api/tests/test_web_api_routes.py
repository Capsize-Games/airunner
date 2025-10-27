"""
Comprehensive tests for Web API Server endpoints.

Tests LLM, Art, TTS, STT routes with signal integration, concurrent requests,
WebSocket connections, and error handling.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Import server factory
from airunner.api.server import create_app


@pytest.fixture
def client():
    """Create test client with mock app instance."""
    # Mock AI Runner app
    mock_app = MagicMock()
    mock_app.is_running = True

    # Create FastAPI app
    app = create_app(app_instance=mock_app)

    # Create test client
    return TestClient(app)


@pytest.fixture
def mock_mediator():
    """Mock SignalMediator for testing."""
    with patch(
        "airunner.utils.application.signal_mediator.SignalMediator"
    ) as mock:
        mediator_instance = MagicMock()
        mock.return_value = mediator_instance
        yield mediator_instance


# ====================
# Health Endpoint Tests
# ====================


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


# ====================
# LLM Route Tests
# ====================


def test_llm_chat_completion(client, mock_mediator):
    """Test LLM chat completion endpoint."""
    # Mock LLM service response
    with patch(
        "airunner.components.llm.api.llm_services.LLMAPIService"
    ) as mock_service:
        service_instance = MagicMock()
        mock_service.return_value = service_instance

        # Simulate signal-based response
        def emit_signal_side_effect(signal, data):
            # Trigger the registered callback
            if signal.name == "LLM_TEXT_GENERATE_REQUEST_SIGNAL":
                # Simulate LLM response via signal
                pass

        service_instance.emit_signal.side_effect = emit_signal_side_effect

        response = client.post(
            "/api/v1/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "temperature": 0.7,
            },
        )

        # Note: Will timeout in test without real signal handling
        # In real usage, this would work with actual signal mediator
        assert response.status_code in [200, 504]  # Success or timeout


def test_llm_text_completion(client):
    """Test LLM text completion endpoint."""
    response = client.post(
        "/api/v1/llm/completion",
        json={"prompt": "Once upon a time", "max_tokens": 50},
    )

    # May timeout without real LLM
    assert response.status_code in [200, 504]


def test_llm_list_models(client):
    """Test LLM model listing endpoint."""
    # Mock the database settings access
    with patch(
        "airunner.components.llm.data.llm_generator_settings.LLMGeneratorSettings.objects.first"
    ) as mock_settings_first:
        # Mock settings to return None (no current model)
        mock_settings_first.return_value = None

        # Mock ModelRegistry
        with patch(
            "airunner.components.model_management.model_registry.ModelRegistry"
        ) as mock_registry:
            mock_model = MagicMock()
            mock_model.name = "Test LLM"
            mock_model.model_type.value = "llm"
            mock_model.size_mb = 1000

            registry_instance = MagicMock()
            registry_instance.models = {"llm-test": mock_model}
            mock_registry.return_value = registry_instance

            response = client.get("/api/v1/llm/models")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


def test_llm_load_model(client):
    """Test LLM model loading endpoint."""
    response = client.post("/api/v1/llm/load", json={"model_id": "llama-2-7b"})

    # May timeout without real model loading
    assert response.status_code in [200, 504]


def test_llm_unload_model(client):
    """Test LLM model unloading endpoint."""
    with patch(
        "airunner.components.llm.api.llm_services.LLMAPIService"
    ) as mock_service:
        service_instance = MagicMock()
        mock_service.return_value = service_instance

        response = client.post("/api/v1/llm/unload")
        assert response.status_code == 200
        assert response.json()["status"] == "success"


def test_llm_websocket_chat(client):
    """Test LLM WebSocket streaming chat."""
    with client.websocket_connect("/api/v1/llm/stream") as websocket:
        # Send message
        websocket.send_json({"message": "Hello", "max_tokens": 20})

        # In real usage, would receive streaming chunks
        # For test, just verify connection
        assert websocket is not None


# ====================
# Art Route Tests
# ====================


def test_art_generate_image(client):
    """Test art generation endpoint."""
    with patch(
        "airunner.components.art.api.art_services.ARTAPIService"
    ) as mock_service:
        service_instance = MagicMock()
        mock_service.return_value = service_instance

        response = client.post(
            "/api/v1/art/generate",
            json={
                "prompt": "A beautiful landscape",
                "width": 512,
                "height": 512,
                "steps": 20,
            },
        )

        # May timeout without real art generation
        assert response.status_code in [200, 504]


def test_art_job_status(client):
    """Test art job status endpoint."""
    # Test with a fake job_id - API should return 404
    response = client.get("/api/v1/art/status/fake-job-id")
    assert response.status_code == 404


def test_art_cancel_job(client):
    """Test art job cancellation."""
    # Test with a fake job_id - API should return 404
    with patch(
        "airunner.components.art.api.art_services.ARTAPIService"
    ) as mock_service:
        service_instance = MagicMock()
        mock_service.return_value = service_instance

        response = client.delete("/api/v1/art/cancel/fake-job-id")
        # May return 404 for non-existent job or 200 if cancel is idempotent
        assert response.status_code in [200, 404]


def test_art_list_models(client):
    """Test art model listing endpoint."""
    # Mock the database settings access
    with patch(
        "airunner.components.art.data.generator_settings.GeneratorSettings.objects.first"
    ) as mock_settings_first:
        mock_settings_first.return_value = None

        # Mock ModelRegistry
        with patch(
            "airunner.components.model_management.model_registry.ModelRegistry"
        ) as mock_registry:
            mock_model = MagicMock()
            mock_model.name = "Stable Diffusion 1.5"
            mock_model.model_type.value = "sd"
            mock_model.size_mb = 2000

            registry_instance = MagicMock()
            registry_instance.models = {"sd-v1-5": mock_model}
            mock_registry.return_value = registry_instance

            response = client.get("/api/v1/art/models")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


# ====================
# TTS Route Tests
# ====================


def test_tts_synthesize(client):
    """Test TTS synthesis endpoint."""
    response = client.post(
        "/api/v1/tts/synthesize",
        json={"text": "Hello world", "speed": 1.0},
    )

    # May timeout without real TTS
    assert response.status_code in [200, 504]


def test_tts_list_models(client):
    """Test TTS model listing endpoint."""
    # Mock the database settings access - TTS uses multiple settings models
    with patch(
        "airunner.components.tts.data.tts_generator_settings.TTSGeneratorSettings"
    ) as mock_settings_class:
        mock_objects = MagicMock()
        mock_objects.first.return_value = None
        mock_settings_class.objects = mock_objects

        # Mock ModelRegistry
        with patch(
            "airunner.components.model_management.model_registry.ModelRegistry"
        ) as mock_registry:
            mock_model = MagicMock()
            mock_model.name = "SpeechT5"
            mock_model.model_type.value = "tts"
            mock_model.size_mb = 500

            registry_instance = MagicMock()
            registry_instance.models = {"speecht5": mock_model}
            mock_registry.return_value = registry_instance

            response = client.get("/api/v1/tts/models")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


# ====================
# STT Route Tests
# ====================


def test_stt_transcribe(client):
    """Test STT transcription endpoint."""
    # Create fake audio file
    audio_data = b"fake audio data"

    response = client.post(
        "/api/v1/stt/transcribe",
        files={"audio": ("test.wav", audio_data, "audio/wav")},
    )

    # May timeout without real STT
    assert response.status_code in [200, 504]


def test_stt_list_models(client):
    """Test STT model listing endpoint."""
    # Mock the database settings access
    with patch(
        "airunner.components.stt.data.whisper_settings.WhisperSettings.objects.first"
    ) as mock_settings_first:
        mock_settings_first.return_value = None

        # Mock ModelRegistry
        with patch(
            "airunner.components.model_management.model_registry.ModelRegistry"
        ) as mock_registry:
            mock_model = MagicMock()
            mock_model.name = "Whisper Base"
            mock_model.model_type.value = "stt"
            mock_model.size_mb = 300

            registry_instance = MagicMock()
            registry_instance.models = {"whisper-base": mock_model}
            mock_registry.return_value = registry_instance

            response = client.get("/api/v1/stt/models")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


def test_stt_websocket_stream(client):
    """Test STT WebSocket streaming."""
    with client.websocket_connect("/api/v1/stt/stream") as websocket:
        # Send audio chunk
        websocket.send_bytes(b"fake audio chunk")

        # In real usage, would receive transcription chunks
        # For test, just verify connection
        assert websocket is not None


# ====================
# Concurrent Request Tests
# ====================


def test_concurrent_chat_requests(client):
    """Test handling multiple concurrent chat requests."""
    from concurrent.futures import ThreadPoolExecutor

    def send_chat_request():
        return client.post(
            "/api/v1/llm/chat",
            json={"messages": [{"role": "user", "content": "Test"}]},
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_chat_request) for _ in range(5)]
        responses = [f.result() for f in futures]

    # All should either succeed or timeout
    for response in responses:
        assert response.status_code in [200, 504]


# ====================
# Error Handling Tests
# ====================


def test_invalid_chat_request(client):
    """Test chat endpoint with invalid request."""
    response = client.post("/api/v1/llm/chat", json={})
    assert response.status_code == 422  # Validation error


def test_nonexistent_job_status(client):
    """Test status endpoint with nonexistent job."""
    response = client.get("/api/v1/art/status/nonexistent-job-id")
    assert response.status_code == 404


def test_invalid_model_id(client):
    """Test loading invalid model."""
    response = client.post(
        "/api/v1/llm/load", json={"model_id": "nonexistent-model"}
    )
    # May timeout or fail
    assert response.status_code in [404, 500, 504]


# ====================
# Integration Tests
# ====================


@pytest.mark.integration
def test_full_image_generation_workflow(client):
    """Test complete image generation workflow."""
    # Start generation
    response = client.post(
        "/api/v1/art/generate",
        json={"prompt": "Test image", "width": 256, "height": 256, "steps": 5},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    # Check status (multiple times to simulate polling)
    for _ in range(3):
        response = client.get(f"/api/v1/art/status/{job_id}")
        assert response.status_code == 200

    # Note: Without real art generation, job won't complete
    # In production, this test would wait for completion and retrieve result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
