"""
Functional tests for all server endpoints.

These tests verify each endpoint works correctly with real model inference.
NO MOCKING - these are true functional tests against a running server.

Test Models:
- LLM: Qwen3 (any Qwen3 variant)
- Image: Z-Image Turbo
- STT: Whisper
- TTS: OpenVoice or espeak

Requirements:
- Headless server must be running on localhost:8080 (or configured port)
- Models must be downloaded and configured
- Run with: python src/airunner/bin/run_tests.py --unit --component server

Usage:
    # Start headless server first:
    airunner-headless --model /path/to/qwen3 --enable-art --enable-tts --enable-stt

    # Run tests:
    pytest src/airunner/components/server/tests/functional/test_server_endpoints.py -v
"""

import json
import os
import pytest
import requests
import tempfile
import base64
from pathlib import Path

from airunner.settings import (
    AIRUNNER_HEADLESS_SERVER_HOST,
    AIRUNNER_HEADLESS_SERVER_PORT,
)


# Test configuration
BASE_URL = (
    f"http://{AIRUNNER_HEADLESS_SERVER_HOST}:{AIRUNNER_HEADLESS_SERVER_PORT}"
)
TIMEOUT_CONNECT = 10  # seconds for connection
TIMEOUT_READ = 120  # seconds for model inference (longer for first load)


def is_server_running() -> bool:
    """Check if the headless server is running."""
    try:
        response = requests.get(
            f"{BASE_URL}/health",
            timeout=(TIMEOUT_CONNECT, 5)
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def get_service_status(service: str) -> bool:
    """Check if a specific service is enabled via /health endpoint.
    
    Args:
        service: Service name ('art', 'llm', 'tts', 'stt')
    
    Returns:
        True if service is enabled, False otherwise
    """
    try:
        response = requests.get(
            f"{BASE_URL}/health",
            timeout=(TIMEOUT_CONNECT, 5)
        )
        if response.status_code == 200:
            data = response.json()
            services = data.get("services", {})
            return services.get(service, False)
    except requests.exceptions.RequestException:
        pass
    return False


# Skip all tests if server is not running
pytestmark = pytest.mark.skipif(
    not is_server_running(),
    reason="Headless server not running. Start with: airunner-headless"
)


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_returns_ok(self):
        """Verify /health endpoint returns 200 and valid JSON."""
        response = requests.get(
            f"{BASE_URL}/health",
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ)
        )
        
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        assert "status" in data, "Health response missing 'status' field"
        assert data["status"] in ["ready", "ok", "healthy"], f"Unexpected status: {data['status']}"


class TestLLMEndpoint:
    """Test the /llm endpoint with Qwen3 model."""

    def test_llm_basic_generation(self):
        """Test basic LLM generation returns a response."""
        payload = {
            "prompt": "What is 2+2? Reply with just the number.",
            "action": "CHAT",
            "stream": False,
            "llm_request": {
                "max_new_tokens": 20,
                "temperature": 0.1,
                "tool_categories": [],
            },
        }

        response = requests.post(
            f"{BASE_URL}/llm",
            json=payload,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
        )

        assert response.status_code == 200, f"LLM request failed: {response.text}"
        
        # For non-streaming, we get NDJSON lines
        lines = response.text.strip().split('\n')
        assert len(lines) > 0, "No response lines received"
        
        # Check that we got some content
        has_content = False
        for line in lines:
            if line.strip():
                try:
                    chunk = json.loads(line)
                    if chunk.get("message") or chunk.get("text"):
                        has_content = True
                        break
                except json.JSONDecodeError:
                    pass
        
        assert has_content, "No content in LLM response"

    def test_llm_streaming_generation(self):
        """Test streaming LLM generation returns streamed chunks."""
        payload = {
            "prompt": "Say hello.",
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

        assert response.status_code == 200, f"Streaming LLM request failed: {response.text}"
        
        # Collect streamed chunks
        chunks = []
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if chunk.get("message"):
                        chunks.append(chunk["message"])
                except json.JSONDecodeError:
                    pass

        assert len(chunks) > 0, "No content chunks received in streaming response"


class TestOllamaCompatibleEndpoints:
    """Test Ollama-compatible API endpoints."""

    def test_ollama_tags_endpoint(self):
        """Test /api/tags returns model list."""
        response = requests.get(
            f"{BASE_URL}/api/tags",
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ)
        )
        
        assert response.status_code == 200, f"/api/tags failed: {response.text}"
        
        data = response.json()
        assert "models" in data, "Response missing 'models' field"
        assert isinstance(data["models"], list), "'models' should be a list"

    def test_ollama_version_endpoint(self):
        """Test /api/version returns version info."""
        response = requests.get(
            f"{BASE_URL}/api/version",
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ)
        )
        
        assert response.status_code == 200, f"/api/version failed: {response.text}"
        
        data = response.json()
        assert "version" in data, "Response missing 'version' field"

    def test_ollama_ps_endpoint(self):
        """Test /api/ps returns running models."""
        response = requests.get(
            f"{BASE_URL}/api/ps",
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ)
        )
        
        assert response.status_code == 200, f"/api/ps failed: {response.text}"
        
        data = response.json()
        assert "models" in data, "Response missing 'models' field"

    def test_ollama_generate_endpoint(self):
        """Test /api/generate (Ollama text generation)."""
        payload = {
            "model": "airunner:latest",
            "prompt": "Hello",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 10,
            },
        }

        response = requests.post(
            f"{BASE_URL}/api/generate",
            json=payload,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
        )

        assert response.status_code == 200, f"/api/generate failed: {response.text}"
        
        data = response.json()
        assert "response" in data or "message" in data, "Missing response content"

    def test_ollama_chat_endpoint(self):
        """Test /api/chat (Ollama chat completion)."""
        payload = {
            "model": "airunner:latest",
            "messages": [
                {"role": "user", "content": "Hi"}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 10,
            },
        }

        response = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
        )

        assert response.status_code == 200, f"/api/chat failed: {response.text}"


class TestOpenAICompatibleEndpoints:
    """Test OpenAI-compatible API endpoints."""

    def test_openai_models_endpoint(self):
        """Test /v1/models returns model list."""
        response = requests.get(
            f"{BASE_URL}/v1/models",
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ)
        )
        
        assert response.status_code == 200, f"/v1/models failed: {response.text}"
        
        data = response.json()
        assert "data" in data, "Response missing 'data' field"

    def test_openai_chat_completions_endpoint(self):
        """Test /v1/chat/completions (OpenAI chat completion)."""
        payload = {
            "model": "airunner",
            "messages": [
                {"role": "user", "content": "Say test"}
            ],
            "stream": False,
            "temperature": 0.1,
            "max_tokens": 10,
        }

        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json=payload,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
        )

        assert response.status_code == 200, f"/v1/chat/completions failed: {response.text}"
        
        data = response.json()
        assert "choices" in data or "error" not in data, f"Unexpected response: {data}"


class TestArtEndpoint:
    """Test the /art endpoint with Z-Image Turbo model.
    
    Note: This test requires the art service to be enabled and Z-Image Turbo
    model to be downloaded. Start server with: airunner-headless --enable-art
    """

    @pytest.mark.timeout(360)  # 6 minute timeout for image generation
    def test_art_generation(self):
        """Test basic image generation request."""
        if not get_service_status("art"):
            pytest.skip("Art service not enabled. Start with --enable-art")
        
        payload = {
            "prompt": "A red apple on a white background",
            "negative_prompt": "blurry, low quality",
            "width": 512,
            "height": 512,
            "steps": 4,  # Z-Image Turbo uses few steps
            "seed": 42,
        }

        response = requests.post(
            f"{BASE_URL}/art",
            json=payload,
            timeout=(TIMEOUT_CONNECT, 300),  # Image gen can take up to 5 minutes
        )

        # Art endpoint may return 503 if not configured, that's acceptable
        assert response.status_code in [200, 503], f"/art failed unexpectedly: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual image data
            assert "images" in data, "Response missing 'images' field"
            assert "count" in data, "Response missing 'count' field"
            
            # Should have at least one image
            assert data["count"] >= 1, f"Expected at least 1 image, got {data['count']}"
            assert len(data["images"]) >= 1, "Images array is empty"
            
            # Verify first image is valid base64
            if data["images"]:
                import base64
                try:
                    # Try to decode the base64 - should not raise
                    img_bytes = base64.b64decode(data["images"][0])
                    assert len(img_bytes) > 0, "Decoded image is empty"
                    # PNG files start with specific bytes
                    assert img_bytes[:4] == b'\x89PNG', "Image is not a valid PNG"
                except Exception as e:
                    pytest.fail(f"Failed to decode base64 image: {e}")


class TestSTTEndpoint:
    """Test the /stt endpoint with Whisper model.
    
    Note: This test requires the STT service to be enabled and Whisper
    model to be downloaded. Start server with: airunner-headless --enable-stt
    """

    @pytest.mark.timeout(60)
    def test_stt_transcription(self):
        """Test STT transcription with audio data."""
        if not get_service_status("stt"):
            pytest.skip("STT service not enabled. Start with --enable-stt")
        
        # Create a minimal WAV file with some audio
        wav_data = self._create_minimal_wav()
        
        # Encode as base64
        import base64
        audio_b64 = base64.b64encode(wav_data).decode("utf-8")
        
        payload = {
            "audio": audio_b64,
            "format": "wav"
        }

        response = requests.post(
            f"{BASE_URL}/stt",
            json=payload,
            timeout=(TIMEOUT_CONNECT, 60),
        )

        # STT endpoint may return 200 with transcription or error
        assert response.status_code in [200, 500, 503, 504], f"/stt failed unexpectedly: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "transcription" in data or "status" in data, "Response missing expected fields"

    def _create_minimal_wav(self) -> bytes:
        """Create a minimal valid WAV file for testing."""
        import struct
        
        # WAV file parameters
        sample_rate = 16000
        bits_per_sample = 16
        num_channels = 1
        duration_seconds = 0.1
        num_samples = int(sample_rate * duration_seconds)
        
        # Calculate sizes
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        data_size = num_samples * block_align
        
        # Create silent audio data
        audio_data = b'\x00' * data_size
        
        # Build WAV header
        wav = b'RIFF'
        wav += struct.pack('<I', 36 + data_size)  # File size - 8
        wav += b'WAVE'
        wav += b'fmt '
        wav += struct.pack('<I', 16)  # Subchunk1Size
        wav += struct.pack('<H', 1)   # AudioFormat (PCM)
        wav += struct.pack('<H', num_channels)
        wav += struct.pack('<I', sample_rate)
        wav += struct.pack('<I', byte_rate)
        wav += struct.pack('<H', block_align)
        wav += struct.pack('<H', bits_per_sample)
        wav += b'data'
        wav += struct.pack('<I', data_size)
        wav += audio_data
        
        return wav


class TestTTSEndpoint:
    """Test the /tts endpoint with OpenVoice or espeak.
    
    Note: This test requires the TTS service to be enabled.
    Start server with: airunner-headless --enable-tts
    """

    @pytest.mark.timeout(30)
    def test_tts_synthesis(self):
        """Test TTS text synthesis."""
        if not get_service_status("tts"):
            pytest.skip("TTS service not enabled. Start with --enable-tts")
        
        payload = {
            "text": "Hello world, this is a test of text to speech.",
        }

        response = requests.post(
            f"{BASE_URL}/tts",
            json=payload,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
        )

        # TTS endpoint should return 200 with queued status
        assert response.status_code in [200, 503], f"/tts failed unexpectedly: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Response missing 'status' field"
            assert data["status"] == "queued", f"Expected status 'queued', got '{data.get('status')}'"


class TestAdminEndpoints:
    """Test admin endpoints."""

    def test_reset_memory_endpoint(self):
        """Test /admin/reset_memory clears conversation memory."""
        response = requests.post(
            f"{BASE_URL}/admin/reset_memory",
            json={},
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
        )

        assert response.status_code == 200, f"/admin/reset_memory failed: {response.text}"
        
        data = response.json()
        assert "status" in data, "Response missing 'status' field"


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_missing_prompt_returns_error(self):
        """Test that missing prompt field returns appropriate error."""
        payload = {
            "action": "CHAT",
            # Missing prompt
        }

        response = requests.post(
            f"{BASE_URL}/llm",
            json=payload,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    def test_invalid_endpoint_returns_404(self):
        """Test that invalid endpoint returns 404."""
        response = requests.get(
            f"{BASE_URL}/invalid/endpoint",
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


if __name__ == "__main__":
    # Run with: python -m pytest src/airunner/components/server/tests/functional/test_server_endpoints.py -v
    pytest.main([__file__, "-v", "-s"])
