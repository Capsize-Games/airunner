"""
HTTP API endpoints for AI Runner: /llm, /art, /stt, /tts
- /llm/generate: POST, accepts JSON with prompt + llm_request params, streams NDJSON responses
- /llm/models: GET, lists available models
- /health: GET, returns server health status
- /art: POST, accepts ImageRequest dict, returns ImageResponse dict
- /stt, /tts: POST, stubbed
"""

import json
import logging
import queue
import threading
import uuid
from http.server import BaseHTTPRequestHandler
from typing import Optional
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.enums import LLMActionType
from airunner.utils.application.get_logger import get_logger

# Module-level logger
logger = get_logger(__name__)

# Lazy import to avoid circular dependency
_api = None


def get_api():
    """Get or create the API singleton instance."""
    global _api
    if _api is None:
        from airunner.components.application.api.api import API

        _api = API()
    return _api


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
            "use_memory": false,  // optional, disable conversation history
            "llm_request": {  // optional LLM parameters
                "temperature": 0.8,
                "max_new_tokens": 100,
                ...
            }
            // OR top-level params (will be moved to llm_request):
            "temperature": 0.8,
            "max_tokens": 100,
            ...
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

        # DEBUG: Log incoming request data (using print to bypass logger issues)
        print(
            f"[SERVER DEBUG] Incoming request data keys: {list(data.keys())}",
            flush=True,
        )
        if "tool_categories" in data:
            print(
                f"[SERVER DEBUG] tool_categories in request: {data['tool_categories']}",
                flush=True,
            )
        else:
            print(f"[SERVER DEBUG] NO tool_categories in request!", flush=True)

        # Handle top-level LLM parameters (for convenience)
        # Map common parameter names to LLMRequest fields
        param_mapping = {
            "temperature": "temperature",
            "max_tokens": "max_new_tokens",
            "top_p": "top_p",
            "top_k": "top_k",
            "repetition_penalty": "repetition_penalty",
            "use_memory": "use_memory",
            "tool_categories": "tool_categories",  # CRITICAL: Allow disabling tools
        }

        for client_param, llm_param in param_mapping.items():
            if client_param in data and client_param not in [
                "prompt",
                "system_prompt",
                "action",
                "stream",
                "llm_request",
            ]:
                llm_request_data[llm_param] = data[client_param]

        # DEBUG: Show what got mapped
        print(
            f"[SERVER DEBUG] llm_request_data after mapping: {llm_request_data}",
            flush=True,
        )

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

        import sys

        sys.stderr.write(
            f"\n[SERVER] Creating LLMRequest from params: {params}\n"
        )
        sys.stderr.flush()

        # Override with provided parameters
        for key, value in params.items():
            if hasattr(llm_request, key):
                setattr(llm_request, key, value)
                sys.stderr.write(f"[SERVER] Set LLMRequest.{key} = {value}\n")
                sys.stderr.flush()
            else:
                logger.warning(
                    f"Ignoring unknown LLMRequest parameter: {key}={value}"
                )

        sys.stderr.write(
            f"[SERVER] Final LLMRequest.max_new_tokens = {llm_request.max_new_tokens}\n"
        )
        sys.stderr.flush()
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

        # Register callback to collect streaming responses
        complete_event = threading.Event()

        def stream_callback(data: dict):
            """Callback for streaming responses."""
            response = data.get("response")
            if response:
                # Convert action enum to string for JSON serialization
                action_str = getattr(response, "action", None)
                if action_str is not None:
                    action_str = (
                        str(action_str.value)
                        if hasattr(action_str, "value")
                        else str(action_str)
                    )
                else:
                    action_str = (
                        str(action.value)
                        if hasattr(action, "value")
                        else str(action)
                    )

                response_data = {
                    "message": response.message,
                    "is_first_message": response.is_first_message,
                    "is_end_of_message": response.is_end_of_message,
                    "sequence_number": getattr(response, "sequence_number", 0),
                    "action": action_str,
                }
                self.wfile.write(
                    json.dumps(response_data).encode("utf-8") + b"\n"
                )
                self.wfile.flush()

                if response.is_end_of_message:
                    complete_event.set()

        # Send LLM request with request_id and callback
        api = get_api()
        print(
            f"[SERVER DEBUG] Sending to API with llm_request.max_new_tokens={llm_request.max_new_tokens}",
            flush=True,
        )
        api.llm.send_request(
            prompt=prompt,
            action=action,
            llm_request=llm_request,
            request_id=request_id,
            callback=stream_callback,
        )

        # Wait for completion (with timeout)
        if not complete_event.wait(
            timeout=300
        ):  # 5 minute timeout for longer generations
            # Timeout - send error response
            error_response = {
                "message": "Request timeout",
                "is_first_message": True,
                "is_end_of_message": True,
                "sequence_number": 0,
                "error": True,
            }
            self.wfile.write(
                json.dumps(error_response).encode("utf-8") + b"\n"
            )
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

        # Collect all response chunks
        complete_message = []
        complete_event = threading.Event()

        def collect_callback(data: dict):
            """Callback to collect response chunks."""
            print(
                f"[HTTP Callback {id(collect_callback)}] CALLED with data keys: {list(data.keys())}"
            )
            response = data.get("response")
            print(
                f"[HTTP Callback] Response type: {type(response)}, is_end: {response.is_end_of_message if response else None}"
            )
            logger.info(
                f"[HTTP Callback] Received response: message_len={len(response.message) if response else 0}, is_end={response.is_end_of_message if response else None}"
            )
            if response:
                complete_message.append(response.message)
                print(
                    f"[HTTP Callback] Complete message so far: {len(complete_message)} chunks"
                )
                if response.is_end_of_message:
                    print(
                        f"[HTTP Callback] END OF MESSAGE - setting event {id(complete_event)}"
                    )
                    logger.info(
                        f"[HTTP Callback] End of message detected, setting event"
                    )
                    complete_event.set()
                    print(
                        f"[HTTP Callback] Event set: {complete_event.is_set()}"
                    )
                else:
                    logger.debug(
                        f"[HTTP Callback] Not end yet, waiting for more..."
                    )

        print(
            f"[HTTP Server] Registering callback {id(collect_callback)} for request {request_id}"
        )
        print(f"[HTTP Server] Event object: {id(complete_event)}")

        # Send LLM request with request_id and callback
        api = get_api()
        api.llm.send_request(
            prompt=prompt,
            action=action,
            llm_request=llm_request,
            request_id=request_id,
            callback=collect_callback,
        )

        print(
            f"[HTTP Server] Waiting for event {id(complete_event)} with 300s timeout..."
        )

        # Wait for completion (with timeout)
        if complete_event.wait(
            timeout=300
        ):  # 5 minute timeout for longer generations
            # Success - return complete message
            response_data = {
                "message": "".join(complete_message),
                "is_first_message": True,
                "is_end_of_message": True,
                "sequence_number": 0,
                "action": (
                    action.value if hasattr(action, "value") else str(action)
                ),
            }
        else:
            # Timeout
            response_data = {
                "message": "Request timeout",
                "is_first_message": True,
                "is_end_of_message": True,
                "sequence_number": 0,
                "error": True,
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
