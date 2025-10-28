"""
HTTP API endpoints for AI Runner: /llm, /art, /stt, /tts
- /llm/generate: POST, accepts JSON with prompt + llm_request params, streams NDJSON responses
- /llm/models: GET, lists available models
- /health: GET, returns server health status
- /art: POST, accepts ImageRequest dict, returns ImageResponse dict
- /stt, /tts: POST, stubbed
"""

import json
import queue
import threading
import uuid
from http.server import BaseHTTPRequestHandler
from typing import Optional
from airunner.components.application.api.api import API
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.enums import LLMActionType

api = API()


class AIRunnerAPIRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        path = self.path.rstrip("/")
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            self._set_headers(400)
            self.wfile.write(
                json.dumps({"error": "Invalid JSON"}).encode("utf-8")
            )
            return
        if path == "/llm" or path == "/llm/generate":
            self._handle_llm(data)
        elif path == "/art":
            self._handle_art(data)
        elif path == "/stt":
            self._handle_stub("STT not implemented")
        elif path == "/tts":
            self._handle_stub("TTS not implemented")
        else:
            self._set_headers(404)
            self.wfile.write(
                json.dumps({"error": "Not found"}).encode("utf-8")
            )

    def do_GET(self):
        """Handle GET requests for /health and other endpoints."""
        path = self.path.rstrip("/")

        if path == "/health":
            self._handle_health()
        elif path == "/llm/models":
            self._handle_llm_models()
        else:
            self._set_headers(404)
            self.wfile.write(
                json.dumps({"error": "Not found"}).encode("utf-8")
            )

    def _handle_health(self):
        """Health check endpoint."""
        self._set_headers(200)
        health_data = {
            "status": "ready",
            "services": {
                "llm": True,
                "art": True,
                "tts": False,  # Stub for now
                "stt": False,  # Stub for now
            },
            "version": "2.0.0",
        }
        self.wfile.write(json.dumps(health_data).encode("utf-8"))

    def _handle_llm_models(self):
        """List available LLM models."""
        self._set_headers(200)
        # TODO: Get actual model list from API
        models_data = {
            "models": [{"name": "default", "type": "local", "loaded": False}]
        }
        self.wfile.write(json.dumps(models_data).encode("utf-8"))

    def _handle_llm(self, data):
        """Handle LLM generation request with streaming support.

        Expected JSON format:
        {
            "prompt": "What is the capital of France?",
            "system_prompt": "You are a helpful assistant",  // optional
            "action": "CHAT",  // optional, default: CHAT
            "stream": true,  // optional, default: true
            "llm_request": {  // optional LLM parameters
                "temperature": 0.8,
                "max_new_tokens": 100,
                ...
            }
        }
        """
        # Parse request parameters
        prompt = data.get("prompt")
        if not prompt:
            self._set_headers(400)
            self.wfile.write(
                json.dumps({"error": "Missing 'prompt' field"}).encode("utf-8")
            )
            return

        system_prompt = data.get("system_prompt")
        action_str = data.get("action", "CHAT")
        stream = data.get("stream", True)
        llm_request_data = data.get("llm_request", {})

        # Parse action type
        try:
            action = (
                LLMActionType[action_str]
                if isinstance(action_str, str)
                else action_str
            )
        except KeyError:
            action = LLMActionType.CHAT

        # Create LLMRequest from provided parameters
        llm_request = self._create_llm_request(llm_request_data)

        # Generate unique request ID for correlation
        request_id = str(uuid.uuid4())

        if stream:
            # Stream NDJSON responses
            self._handle_llm_stream(
                prompt, system_prompt, action, llm_request, request_id
            )
        else:
            # Return single JSON response
            self._handle_llm_non_stream(
                prompt, system_prompt, action, llm_request, request_id
            )

    def _create_llm_request(self, params: dict) -> LLMRequest:
        """Create LLMRequest from dictionary parameters.

        Args:
            params: Dictionary of LLM parameters

        Returns:
            LLMRequest object with specified or default parameters
        """
        # Start with defaults
        llm_request = LLMRequest()

        # Override with provided parameters
        for key, value in params.items():
            if hasattr(llm_request, key):
                setattr(llm_request, key, value)

        return llm_request

    def _handle_llm_stream(
        self,
        prompt: str,
        system_prompt: Optional[str],
        action: LLMActionType,
        llm_request: LLMRequest,
        request_id: str,
    ):
        """Handle streaming LLM response as NDJSON.

        Each line is a JSON object with:
        - message: text chunk
        - is_first_message: bool
        - is_end_of_message: bool
        - sequence_number: int
        """
        self._set_headers(200, content_type="application/x-ndjson")

        # Create queue for collecting streamed responses
        response_queue = queue.Queue()
        complete_event = threading.Event()

        # Callback to collect responses
        def response_callback(response: LLMResponse):
            response_queue.put(response)
            if response.is_end_of_message:
                complete_event.set()

        # Send LLM request via API
        # Note: This uses the signal-based API which will emit responses
        # For headless mode, we need to implement request-response correlation
        # For now, use stub responses
        # TODO: Implement proper signal-based request correlation in issue #1894

        # STUB: Send fake streaming responses
        chunks = ["The", " capital", " of", " France", " is", " Paris", "."]
        for i, chunk in enumerate(chunks):
            response = LLMResponse(
                message=chunk,
                is_first_message=(i == 0),
                is_end_of_message=(i == len(chunks) - 1),
                sequence_number=i,
                action=(
                    action.value if hasattr(action, "value") else str(action)
                ),
            )
            response_data = {
                "message": response.message,
                "is_first_message": response.is_first_message,
                "is_end_of_message": response.is_end_of_message,
                "sequence_number": response.sequence_number,
                "action": response.action,
            }
            self.wfile.write(json.dumps(response_data).encode("utf-8") + b"\n")
            self.wfile.flush()

    def _handle_llm_non_stream(
        self,
        prompt: str,
        system_prompt: Optional[str],
        action: LLMActionType,
        llm_request: LLMRequest,
        request_id: str,
    ):
        """Handle non-streaming LLM response as single JSON object."""
        self._set_headers(200)

        # STUB: Return fake complete response
        # TODO: Implement proper signal-based request correlation in issue #1894
        response_data = {
            "message": "The capital of France is Paris.",
            "is_first_message": True,
            "is_end_of_message": True,
            "sequence_number": 0,
            "action": (
                action.value if hasattr(action, "value") else str(action)
            ),
        }
        self.wfile.write(json.dumps(response_data).encode("utf-8"))

    def _handle_art(self, data):
        self._set_headers(200)
        # For now, just return a stub ImageResponse
        response = ImageResponse(
            images=None,
            data=None,
            nsfw_content_detected=False,
            active_rect=None,
            is_outpaint=False,
        )
        self.wfile.write(json.dumps(response.to_dict()).encode("utf-8"))

    def _handle_stub(self, msg):
        self._set_headers(200)
        self.wfile.write(json.dumps({"result": msg}).encode("utf-8"))


# Usage: pass AIRunnerAPIRequestHandler to your HTTP server for /llm, /art, /stt, /tts endpoints.
