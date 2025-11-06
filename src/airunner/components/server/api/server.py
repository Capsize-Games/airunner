"""
HTTP API endpoints for AI Runner: /llm, /art, /stt, /tts
- /llm/generate: POST, accepts JSON with prompt + llm_request params, streams NDJSON responses
- /llm/models: GET, lists available models
- /health: GET, returns server health status
- /art: POST, accepts ImageRequest dict, returns ImageResponse dict
- /stt, /tts: POST, stubbed
"""

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler
from typing import Optional
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
        elif path == "/llm/generate_batch":
            self._handle_llm_batch(data)
        elif path == "/admin/reset_memory":
            self._handle_reset_memory()
        elif path == "/admin/reset_database":
            self._handle_reset_database()
        elif path == "/art":
            self._handle_stub("STT not implemented")
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

        # DEBUG: Log incoming request data
        logger.debug(f"Incoming request data keys: {list(data.keys())}")
        logger.debug(f"stream value: {stream} (type: {type(stream)})")
        if "tool_categories" in data:
            logger.debug(
                f"tool_categories in request: {data['tool_categories']}"
            )
        else:
            logger.debug("NO tool_categories in request!")

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
        logger.debug(f"llm_request_data after mapping: {llm_request_data}")

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

        logger.debug(f"stream={stream}, about to branch...")

        if stream:
            logger.debug("Taking STREAM path")
            # Stream NDJSON responses
            self._handle_llm_stream(
                prompt, system_prompt, action, llm_request, request_id
            )
        else:
            logger.debug("Taking NON-STREAM path")
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

        logger.debug(f"Creating LLMRequest from params: {params}")

        # Override with provided parameters
        for key, value in params.items():
            if hasattr(llm_request, key):
                setattr(llm_request, key, value)
                logger.debug(f"Set LLMRequest.{key} = {value}")
            else:
                logger.warning(
                    f"Ignoring unknown LLMRequest parameter: {key}={value}"
                )

        logger.debug(
            f"Final LLMRequest.max_new_tokens = {llm_request.max_new_tokens}"
        )
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
        logger.debug(
            f"Sending to API with llm_request.max_new_tokens={llm_request.max_new_tokens}"
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
        logger.debug(
            f"_handle_llm_non_stream ENTERED with request_id={request_id}"
        )
        self._set_headers(200)
        logger.debug("_handle_llm_non_stream Headers set")

        # Collect all response chunks
        complete_message = []
        executed_tools = []  # Track tools executed
        complete_event = threading.Event()

        def collect_callback(data: dict):
            """Callback to collect response chunks."""
            logger.debug(
                f"HTTP Callback {id(collect_callback)} CALLED with data keys: {list(data.keys())}"
            )
            response = data.get("response")
            logger.debug(
                f"HTTP Callback Response type: {type(response)}, is_end: {response.is_end_of_message if response else None}"
            )
            logger.info(
                f"HTTP Callback Received response: message_len={len(response.message) if response else 0}, is_end={response.is_end_of_message if response else None}"
            )
            if response:
                complete_message.append(response.message)
                # Extract tools from response object if this is the final message
                if (
                    response.is_end_of_message
                    and hasattr(response, "tools")
                    and response.tools
                ):
                    executed_tools.extend(response.tools)
                logger.debug(
                    f"HTTP Callback Complete message so far: {len(complete_message)} chunks"
                )
                if response.is_end_of_message:
                    logger.debug(
                        f"HTTP Callback END OF MESSAGE - setting event {id(complete_event)}"
                    )
                    logger.info(
                        "HTTP Callback End of message detected, setting event"
                    )
                    complete_event.set()
                    logger.debug(
                        f"HTTP Callback Event set: {complete_event.is_set()}"
                    )
                else:
                    logger.debug(
                        "HTTP Callback Not end yet, waiting for more..."
                    )

        logger.debug(
            f"HTTP Server Registering callback {id(collect_callback)} for request {request_id}"
        )
        logger.debug(f"HTTP Server Event object: {id(complete_event)}")

        # Send LLM request with request_id and callback
        logger.debug("HTTP Server About to call api.llm.send_request...")
        api = get_api()
        api.llm.send_request(
            prompt=prompt,
            action=action,
            llm_request=llm_request,
            request_id=request_id,
            callback=collect_callback,
        )
        logger.debug("HTTP Server api.llm.send_request completed")

        logger.debug(
            f"HTTP Server Waiting for event {id(complete_event)} with 300s timeout..."
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
                "tools": executed_tools,  # Include list of executed tools
            }
        else:
            # Timeout
            response_data = {
                "message": "Request timeout",
                "is_first_message": True,
                "is_end_of_message": True,
                "sequence_number": 0,
                "error": True,
                "tools": [],
            }

        self.wfile.write(json.dumps(response_data).encode("utf-8"))

    def _handle_llm_batch(self, data):
        """Handle batch LLM generation request.

        Expected JSON format:
        {
            "prompts": ["prompt1", "prompt2", ...],
            "system_prompt": "...",  // optional, applied to all
            "action": "CHAT",  // optional
            "stream": false,  // batch doesn't support streaming
            "async": false,  // if true, returns batch_id immediately
            "llm_request": {...}  // optional params for all requests
        }
        """
        prompts = data.get("prompts")
        if not prompts or not isinstance(prompts, list):
            self._set_headers(400)
            self.wfile.write(
                json.dumps(
                    {"error": "Missing or invalid 'prompts' field"}
                ).encode("utf-8")
            )
            return

        system_prompt = data.get("system_prompt")
        action_str = data.get("action", "CHAT")
        is_async = data.get("async", False)
        llm_request_data = data.get("llm_request", {})

        # Handle top-level LLM parameters
        param_mapping = {
            "temperature": "temperature",
            "max_tokens": "max_new_tokens",
            "top_p": "top_p",
            "top_k": "top_k",
            "repetition_penalty": "repetition_penalty",
            "use_memory": "use_memory",
            "tool_categories": "tool_categories",
        }

        for client_param, llm_param in param_mapping.items():
            if client_param in data and client_param not in [
                "prompts",
                "system_prompt",
                "action",
                "stream",
                "async",
                "llm_request",
            ]:
                llm_request_data[llm_param] = data[client_param]

        # Parse action type
        try:
            action = (
                LLMActionType[action_str]
                if isinstance(action_str, str)
                else action_str
            )
        except KeyError:
            action = LLMActionType.CHAT

        # Create LLMRequest
        llm_request = self._create_llm_request(llm_request_data)

        if is_async:
            # Async mode: return batch_id immediately
            batch_id = str(uuid.uuid4())
            # TODO: Store batch state for polling
            self._set_headers(202)  # Accepted
            response_data = {
                "batch_id": batch_id,
                "status": "processing",
                "total": len(prompts),
            }
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
        else:
            # Sync mode: process all and return responses
            self._handle_llm_batch_sync(
                prompts, system_prompt, action, llm_request
            )

    def _handle_llm_batch_sync(
        self,
        prompts: list,
        system_prompt: Optional[str],
        action: LLMActionType,
        llm_request: LLMRequest,
    ):
        """Handle synchronous batch LLM generation."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time

        self._set_headers(200)

        responses = []
        total = len(prompts)

        def process_single_prompt(index, prompt):
            """Process a single prompt and return (index, result)."""
            start_time = time.time()
            request_id = str(uuid.uuid4())
            complete_message = []
            complete_event = threading.Event()

            def collect_callback(data: dict):
                response = data.get("response")
                if response:
                    complete_message.append(response.message)
                    if response.is_end_of_message:
                        complete_event.set()

            api = get_api()
            api.llm.send_request(
                prompt=prompt,
                action=action,
                llm_request=llm_request,
                request_id=request_id,
                callback=collect_callback,
            )

            # Wait for completion
            if complete_event.wait(timeout=300):
                text = "".join(complete_message)
                success = True
                error = None
            else:
                text = ""
                success = False
                error = "Request timeout"

            return {
                "index": index,
                "prompt": prompt,
                "text": text,
                "success": success,
                "error": error,
                "duration": time.time() - start_time,
            }

        # Process prompts in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(process_single_prompt, i, prompt): i
                for i, prompt in enumerate(prompts)
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    responses.append(result)
                except Exception as e:
                    index = futures[future]
                    responses.append(
                        {
                            "index": index,
                            "prompt": prompts[index],
                            "text": "",
                            "success": False,
                            "error": str(e),
                            "duration": 0.0,
                        }
                    )

        # Sort by original order
        responses.sort(key=lambda x: x["index"])

        response_data = {
            "responses": responses,
            "total": total,
            "successful": sum(1 for r in responses if r["success"]),
            "failed": sum(1 for r in responses if not r["success"]),
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

    def _handle_reset_memory(self):
        """Reset LLM conversation memory.

        This endpoint clears the LLM's conversation history, useful for
        tests to prevent contamination between test runs.

        This clears:
        1. In-memory workflow state and checkpoints
        2. Persisted conversation in database
        3. Creates a FRESH conversation with new ID to prevent checkpoint restoration
        """
        try:
            api = get_api()

            # CRITICAL: Create a brand NEW conversation to avoid checkpoint contamination
            # Simply clearing isn't enough - LangGraph checkpoints persist in class-level state
            from airunner.components.llm.data.conversation import Conversation
            import datetime

            try:
                # Mark all conversations as non-current
                Conversation.objects.update_by(
                    {"current": True}, current=False
                )

                # Create a completely fresh conversation
                new_convo = Conversation(
                    title=f"Test {datetime.datetime.now().isoformat()}",
                    value=[],
                    current=True,
                    chatbot_name="Test",
                    user_name="Test User",
                )
                new_convo.save()
                new_conv_id = new_convo.id

                logger.info(
                    f"Created new conversation ID {new_conv_id} for fresh start"
                )

                # Update workflow manager to use new conversation
                if hasattr(api.llm, "model_manager") and api.llm.model_manager:
                    workflow_manager = getattr(
                        api.llm.model_manager, "_workflow_manager", None
                    )
                    if workflow_manager:
                        # Set new conversation ID - this will rebuild workflow with fresh state
                        if hasattr(workflow_manager, "set_conversation_id"):
                            workflow_manager.set_conversation_id(new_conv_id)
                            logger.info(
                                f"Workflow manager using new conversation {new_conv_id}"
                            )
                        # Also clear memory to be thorough
                        if hasattr(workflow_manager, "clear_memory"):
                            workflow_manager.clear_memory()
                            logger.info("LLM conversation memory cleared")

            except Exception as db_err:
                logger.error(
                    f"Error creating new conversation: {db_err}", exc_info=True
                )

            self._set_headers(200)
            self.wfile.write(
                json.dumps({"status": "memory_cleared"}).encode("utf-8")
            )
        except Exception as e:
            logger.error(f"Error resetting memory: {e}", exc_info=True)
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def _handle_reset_database(self):
        """Reset test database by clearing all test-related tables.

        This endpoint is specifically for test isolation - it clears
        tables that accumulate test data (like Events) to prevent
        contamination between test runs.

        ONLY clears tables when AIRUNNER_ENVIRONMENT=test to prevent
        accidental data loss in production.
        """
        import os

        try:
            # SAFETY: Only allow in test environment
            if os.environ.get("AIRUNNER_ENVIRONMENT") != "test":
                self._set_headers(403)
                self.wfile.write(
                    json.dumps(
                        {
                            "error": "reset_database only allowed in test environment"
                        }
                    ).encode("utf-8")
                )
                return

            # Clear test data tables
            from airunner.components.calendar.data.event import Event
            from airunner.components.data.session_manager import session_scope

            deleted_counts = {}
            with session_scope() as session:
                # Clear calendar events
                event_count = session.query(Event).delete()
                deleted_counts["events"] = event_count
                session.commit()

            logger.info(f"Test database cleared: {deleted_counts}")

            self._set_headers(200)
            self.wfile.write(
                json.dumps(
                    {"status": "database_cleared", "deleted": deleted_counts}
                ).encode("utf-8")
            )
        except Exception as e:
            logger.error(f"Error resetting database: {e}", exc_info=True)
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))


# Usage: pass AIRunnerAPIRequestHandler to your HTTP server for /llm, /art, /stt, /tts endpoints.
