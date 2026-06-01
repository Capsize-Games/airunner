"""
HTTP API endpoints for AI Runner with full Ollama and OpenAI compatibility.

This server can run on port 11434 to fully emulate Ollama, allowing VS Code
and other tools to use AIRunner as if it were Ollama.

Native AIRunner endpoints:
- /llm/generate: POST, accepts JSON with prompt + llm_request params, streams NDJSON responses
- /llm/models: GET, lists available models
- /health: GET, returns server health status
- /art: POST, accepts ImageRequest dict, returns ImageResponse dict
- /stt, /tts: POST, stubbed

Ollama-compatible endpoints (port 11434 recommended):
- /api/tags: GET, list available models
- /api/version: GET, get version info
- /api/generate: POST, text generation
- /api/chat: POST, chat completion
- /api/show: POST, show model info
- /api/ps: GET, list running models
- /api/embed: POST, generate embeddings (stubbed)

OpenAI-compatible endpoints:
- /v1/models: GET, list models
- /v1/chat/completions: POST, chat completion with tool calling support

Usage:
    # Run as Ollama replacement on port 11434
    airunner --headless --port 11434
    
    # VS Code will automatically detect it as Ollama
"""

import os
import json
import base64
import threading
from http.server import BaseHTTPRequestHandler
from typing import Dict, Optional, Any
import sys
import time
from airunner_services.api.legacy_openai_handlers import (
    handle_openai_chat_completions,
    handle_openai_chat_non_stream,
    handle_openai_chat_stream,
    handle_openai_models,
)
from airunner_services.api.legacy_ollama_metadata_handlers import (
    handle_ollama_ps,
    handle_ollama_show,
    handle_ollama_tags,
    handle_ollama_version,
)
from airunner_services.api.legacy_ollama_chat_handlers import (
    handle_ollama_chat,
    handle_ollama_chat_non_stream,
    handle_ollama_chat_stream,
)
from airunner_services.api.legacy_ollama_generation_handlers import (
    handle_ollama_copy,
    handle_ollama_create,
    handle_ollama_embed,
    handle_ollama_generate,
    handle_ollama_generate_non_stream,
    handle_ollama_generate_stream,
    handle_ollama_pull,
)
from airunner_services.api.legacy_art_job_handlers import (
    generate_first_png_bytes,
    handle_art_v1_generate,
    handle_art_v1_models,
    handle_art_v1_result,
    handle_art_v1_status,
)
from airunner_services.api.legacy_art_handlers import (
    create_image_request,
    format_art_response,
    handle_art,
)
from airunner_services.api.legacy_llm_batch_handlers import (
    handle_llm_batch,
    handle_llm_batch_sync,
)
from airunner_services.api.legacy_llm_request_handlers import (
    create_llm_request,
    extract_llm_request_data,
    handle_llm,
    map_top_level_params,
    parse_action_type,
)
from airunner_services.api.legacy_llm_response_handlers import (
    handle_llm_non_stream,
    handle_llm_stream,
)
from airunner_services.llm.llm_request import LLMRequest
from airunner_services.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner_services.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner_services.contract_enums import LLMActionType, SignalCode, EngineResponseCode
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.app.service_app import ServiceApp
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.utils.application.log_hygiene import summarize_text
from airunner_services.database.session import session_scope
from airunner_services.database.models.conversation import Conversation
from airunner_services.utils.application.get_logger import get_logger

# Lazy import to avoid circular dependency
_api: Optional[ServiceApp] = None
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# /api/v1/art/* compatibility layer
#
# Some clients expect an async-ish job API:
#   POST /api/v1/art/generate -> {job_id, status}
#   GET  /api/v1/art/status/{job_id} -> {job_id, status, ...}
#   GET  /api/v1/art/result/{job_id} -> raw PNG bytes
#
# The native AIRunner headless endpoint is POST /art (sync, base64 PNGs).
# We bridge these here to avoid 404s when clients are pointed at headless.
# ---------------------------------------------------------------------------

_ART_JOBS_LOCK = threading.Lock()
_ART_JOBS: dict[str, dict[str, Any]] = {}
_ART_JOBS_TTL_SECONDS = 60 * 60  # 1 hour


def _create_api_app() -> ServiceApp:
    """Create one service-owned app for legacy API routes."""
    return ServiceApp()


def get_api(create_if_missing: bool = True) -> Optional[ServiceApp]:
    """Return the cached service app, optionally creating it on demand."""
    global _api
    if _api is None and create_if_missing:
        _api = _create_api_app()
    return _api


def set_api(api_instance):
    """Set the global API instance.

    Use this when creating an API instance manually (e.g., in headless mode)
    to ensure tools can access it via get_api().

    Args:
        api_instance: The API/App instance to register globally
    """
    global _api
    _api = api_instance


class AIRunnerAPIRequestHandler(BaseHTTPRequestHandler):
    # Use HTTP/1.1 for better compatibility with VS Code and other clients
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._timeout: int = (
            60  # 60 second timeout for generation requests with RAG
        )
        super().__init__(*args, **kwargs)

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _send_json_response(self, data: dict, status: int = 200):
        """Send a complete JSON response with proper Content-Length header."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_text_response(self, text: str, status: int = 200):
        """Send a complete text response with proper Content-Length header."""
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes_response(self, data: bytes, *, status: int = 200, content_type: str = "application/octet-stream"):
        body = data or b""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _purge_old_art_jobs() -> None:
        now = time.time()
        with _ART_JOBS_LOCK:
            expired = [job_id for job_id, job in _ART_JOBS.items() if now - float(job.get("created_at", 0.0)) > _ART_JOBS_TTL_SECONDS]
            for job_id in expired:
                _ART_JOBS.pop(job_id, None)

    def _validate_model_available(self) -> tuple[bool, str, str]:
        """Check if the configured LLM model is available and downloaded.
        
        Returns:
            Tuple of (is_valid, model_path, error_message)
            - is_valid: True if model exists and is ready
            - model_path: The model path being validated
            - error_message: Human-readable error if not valid
        """
        api = get_api()
        if not api:
            return False, "", "API not initialized"
        
        # Get LLM settings from the API
        llm_settings = getattr(api, 'llm_generator_settings', None)
        if not llm_settings:
            return False, "", "LLM settings not configured"
        
        model_path = getattr(llm_settings, 'model_path', '') or ''
        model_name = getattr(llm_settings, 'model_name', '') or ''
        
        if not model_path:
            return False, "", f"No model path configured. Please run 'airunner' (GUI) first to download and select a model."
        
        # Check if path exists
        if not os.path.exists(model_path):
            return False, model_path, (
                f"Model not found at '{model_path}'. "
                f"The model '{model_name}' needs to be downloaded. "
                f"Please run 'airunner' (GUI) and download the model, or run 'airunner-setup' to download default models."
            )
        
        # Check for minimum required files (config.json or a .gguf file)
        has_config = os.path.exists(os.path.join(model_path, "config.json"))
        has_gguf = any(f.endswith('.gguf') for f in os.listdir(model_path) if os.path.isfile(os.path.join(model_path, f)))
        
        if not has_config and not has_gguf:
            return False, model_path, (
                f"Model at '{model_path}' appears incomplete (missing config.json or .gguf file). "
                f"Please re-download the model using the AIRunner GUI or 'airunner-setup'."
            )
        
        return True, model_path, ""

    def _is_llm_model_loaded(self) -> bool:
        """Check if an LLM model is currently loaded.
        
        Returns:
            True if a model is loaded and ready for inference
        """
        api = get_api()
        if not api:
            return False

        return self._llm_loaded_from_balancer(api) or self._llm_loaded_from_worker(
            api
        )

    @staticmethod
    def _llm_loaded_from_balancer(api) -> bool:
        """Return True when runtime state already reports one loaded LLM."""
        from airunner_services.contract_enums import ModelType

        balancer = getattr(api, "model_load_balancer", None)
        if balancer is None:
            balancer = getattr(api, "_model_load_balancer", None)
        if balancer is None:
            return False
        try:
            loaded_models = balancer.get_loaded_models() or []
        except Exception:
            return False
        return ModelType.LLM in loaded_models

    @staticmethod
    def _llm_loaded_from_worker(api) -> bool:
        """Return True when the local worker already has an LLM ready."""
        from airunner_services.contract_enums import ModelStatus

        worker_manager = getattr(api, "_worker_manager", None)
        if not worker_manager:
            return False

        worker = getattr(worker_manager, "_llm_generate_worker", None)
        if worker is None:
            return False

        status_getter = getattr(worker, "current_model_status", None)
        if callable(status_getter):
            try:
                if status_getter() in (ModelStatus.LOADED, ModelStatus.READY):
                    return True
            except Exception:
                pass

        manager = getattr(worker, "_model_manager", None)
        return bool(
            manager is not None
            and getattr(manager, "_chat_model", None) is not None
        )

    def _ensure_llm_model_loaded(self) -> tuple[bool, str]:
        """Ensure LLM model is loaded, triggering load if necessary.
        
        If no model is loaded and a model path is configured, this will
        trigger the model loading process and wait for it to complete.
        
        Returns:
            Tuple of (success, error_message)
        """
        # First validate model is available
        is_valid, model_path, error_msg = self._validate_model_available()
        if not is_valid:
            return False, error_msg
        
        # Check if already loaded
        if self._is_llm_model_loaded():
            return True, ""
        
        # Model not loaded - trigger loading
        api = get_api()
        if not api:
            return False, "API not initialized"
        
        self.logger.info("Auto-loading LLM model")
        
        # Import SignalCode here to avoid circular imports
        from airunner_services.contract_enums import SignalCode
        
        # Emit load signal
        api.emit_signal(
            SignalCode.LLM_LOAD_SIGNAL,
            {"model_path": model_path},
        )
        
        # Wait for model to load (with timeout)
        import time
        max_wait = 120  # 2 minute timeout
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if self._is_llm_model_loaded():
                self.logger.info("LLM model loaded successfully")
                return True, ""
            time.sleep(0.5)
        
        return False, f"Model loading timed out after {max_wait} seconds. Try starting the server with a model pre-loaded."

    def _is_art_model_loaded(self) -> bool:
        """Check if a Stable Diffusion/art model is currently loaded.
        
        Returns:
            True if a model is loaded and ready for inference
        """
        api = get_api()
        if not api:
            return False
        
        if hasattr(api, '_worker_manager') and api._worker_manager:
            worker = getattr(api._worker_manager, 'sd_worker', None)
            if worker:
                manager = getattr(worker, 'model_manager', None)
                if manager:
                    return getattr(manager, 'model_is_loaded', False)
        return False

    def _art_model_status(self) -> str:
        """Return the current art model lifecycle status string."""
        api = get_api()
        if not api:
            return "unloaded"

        worker_manager = getattr(api, "_worker_manager", None)
        if worker_manager is None:
            return "unloaded"

        worker = getattr(worker_manager, "_sd_worker", None)
        if worker is None:
            return "unloaded"

        manager = getattr(worker, "_model_manager", None)
        if manager is None:
            return "unloaded"

        try:
            model_status = manager.model_status.get(manager.model_type)
        except Exception:
            model_status = None

        status_value = str(getattr(model_status, "value", "")).strip().lower()
        if status_value:
            return status_value
        if getattr(manager, "sd_is_loading", False):
            return "loading"
        if getattr(manager, "model_is_loaded", False):
            return "loaded"
        return "unloaded"

    def _ensure_art_model_loaded(self, model_path: str | None = None) -> tuple[bool, str]:
        """Ensure art/Stable Diffusion model is loaded, triggering load if necessary.
        
        Returns:
            Tuple of (success, error_message)
        """
        # Check if Stable Diffusion is enabled
        if os.environ.get("AIRUNNER_SD_ON") != "1":
            return False, "Stable Diffusion service is not enabled. Start with --enable-art flag."
        
        # Check if already loaded
        if self._is_art_model_loaded():
            return True, ""
        
        api = get_api()
        if not api:
            return False, "API not initialized"
        
        # Prefer an explicit per-request model path if provided.
        art_model_path = (model_path or "").strip() or os.environ.get("AIRUNNER_ART_MODEL_PATH")
        
        if not art_model_path:
            # Try to get from settings
            try:
                from airunner_services.database.models.generator_settings import (
                    GeneratorSettings,
                )
                settings = GeneratorSettings.objects.first()
                if settings:
                    art_model_path = settings.model
            except Exception:
                pass
        
        if not art_model_path:
            return False, "No art model configured. Use --art-model flag or configure in AIRunner GUI."
        
        self.logger.info("Auto-loading art model")
        
        from airunner_services.contract_enums import SignalCode
        api.emit_signal(SignalCode.SD_LOAD_SIGNAL, {"model_path": art_model_path})
        
        # Wait for model to load
        import time
        max_wait = 120
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if self._is_art_model_loaded():
                self.logger.info("Art model loaded successfully")
                return True, ""
            time.sleep(0.5)
        
        return False, f"Art model loading timed out after {max_wait} seconds."

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_HEAD(self):
        """Handle HEAD requests - same as GET but no body."""
        path = self.path.rstrip("/")
        self.logger.info(f"[Ollama API] HEAD {self.path} from {self.client_address}")
        
        if path == "" or path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "17")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        elif path == "/api/version":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        elif path == "/api/tags":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def _read_request_body(self) -> bytes:
        """Read raw request body bytes from the HTTP request.

        Returns:
            Raw bytes from request body
        """
        content_length = int(self.headers.get("Content-Length", 0))
        transfer_encoding = (
            self.headers.get("Transfer-Encoding", "") or ""
        ).lower()

        if content_length > 0:
            return self.rfile.read(content_length)
        elif "chunked" in transfer_encoding:
            return self._read_chunked()
        else:
            return b""

    def _try_parse_json(self, post_data: bytes) -> Optional[Dict]:
        """Try to parse request body as JSON.

        Args:
            post_data: Raw request body bytes

        Returns:
            Parsed dict if successful, None otherwise
        """
        try:
            return json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            return None

    def _parse_llm_request_json(self, data: Dict):
        """Parse llm_request field from string to dict if needed.

        Args:
            data: Dictionary to update in-place
        """
        if "llm_request" in data and isinstance(data["llm_request"], str):
            try:
                data["llm_request"] = json.loads(data["llm_request"])
            except Exception:
                pass

    def _try_parse_form_data(self, post_data: bytes) -> Optional[Dict]:
        """Try to parse request body as form-encoded data.

        Args:
            post_data: Raw request body bytes

        Returns:
            Parsed dict if successful, None otherwise
        """
        from urllib.parse import parse_qs

        try:
            form = parse_qs(post_data.decode("utf-8"))
            data = {
                k: (v[0] if isinstance(v, list) and len(v) > 0 else v)
                for k, v in form.items()
            }
            self._parse_llm_request_json(data)
            return data
        except Exception:
            return None

    def _send_parse_error(self, error_msg: str):
        """Send a 400 error response for parse failures.

        Args:
            error_msg: Error message to send
        """
        self._send_json_response({"error": error_msg}, status=400)

    def _parse_request_body(self) -> Optional[Dict]:
        """Parse request body from JSON or form-encoded data.

        Returns:
            Dict containing parsed request data, or None if parsing failed
        """
        post_data = self._read_request_body()
        content_type = (self.headers.get("Content-Type", "") or "").lower()

        self.logger.debug(f"Content-Type: {content_type}")
        self.logger.debug(
            f"Raw post_data (first 200 chars): {post_data[:200]}"
        )

        result = self._try_parse_json(post_data)
        if result is not None:
            self.logger.debug("Successfully parsed as JSON")
            return result

        if "application/x-www-form-urlencoded" in content_type:
            self.logger.debug("Attempting to parse as form-encoded data")
            result = self._try_parse_form_data(post_data)
            if result is not None:
                self.logger.debug("Successfully parsed as form-encoded")
                return result
            self._send_parse_error("Invalid form data")
        else:
            self._send_parse_error("Invalid JSON")
        return None

    def do_POST(self):
        """Handle POST requests by parsing body and routing to appropriate handler."""
        path = self.path.rstrip("/")
        data = self._parse_request_body()
        if data is None:
            return  # Error response already sent by _parse_request_body

        # Route to appropriate handler
        route_map = {
            # Original AIRunner endpoints
            "/llm": self._handle_llm,
            "/llm/generate": self._handle_llm,
            "/llm/generate_batch": self._handle_llm_batch,
            "/admin/reset_memory": lambda d: self._handle_reset_memory(),
            "/admin/reset_database": lambda d: self._handle_reset_database(),
            "/admin/shutdown": lambda d: self._handle_shutdown(),
            "/art": self._handle_art,
            # Compatibility art job API
            "/api/v1/art/generate": self._handle_art_v1_generate,
            "/stt": self._handle_stt,
            "/tts": self._handle_tts,
            # Ollama-compatible endpoints (run on port 11434 to emulate Ollama)
            "/api/generate": self._handle_ollama_generate,
            "/api/chat": self._handle_ollama_chat,
            "/api/show": self._handle_ollama_show,
            "/api/pull": self._handle_ollama_pull,
            "/api/embed": self._handle_ollama_embed,
            "/api/embeddings": self._handle_ollama_embed,  # Legacy endpoint
            "/api/copy": self._handle_ollama_copy,
            "/api/create": self._handle_ollama_create,
            # OpenAI-compatible endpoints (for VS Code Copilot BYOK)
            "/v1/chat/completions": self._handle_openai_chat_completions,
            "/v1/models": self._handle_openai_models,
        }

        handler = route_map.get(path)
        if handler:
            handler(data)
        else:
            self._send_json_response({"error": "Not found"}, status=404)

    def do_GET(self):
        """Handle GET requests for /health and other endpoints."""
        path = self.path.rstrip("/")
        
        # Log all GET requests for debugging
        self.logger.info(f"[Ollama API] GET {self.path} from {self.client_address}")
        
        # Root endpoint - Ollama returns "Ollama is running"
        if path == "" or path == "/":
            self._handle_ollama_root()
        elif path == "/health":
            self._handle_health()
        elif path == "/llm/models":
            self._handle_llm_models()
        # Ollama-compatible endpoints
        elif path == "/api/tags":
            self._handle_ollama_tags()
        elif path == "/api/version":
            self._handle_ollama_version()
        elif path == "/api/ps":
            self._handle_ollama_ps()
        # OpenAI-compatible endpoints (for VS Code Copilot BYOK)
        elif path == "/v1/models":
            self._handle_openai_models(None)
        elif path.startswith("/api/v1/art/status/"):
            job_id = path.split("/api/v1/art/status/", 1)[-1].strip("/")
            self._handle_art_v1_status(job_id)
        elif path.startswith("/api/v1/art/result/"):
            job_id = path.split("/api/v1/art/result/", 1)[-1].strip("/")
            self._handle_art_v1_result(job_id)
        elif path == "/api/v1/art/models":
            self._handle_art_v1_models()
        else:
            self.logger.warning(f"[Ollama API] Unknown GET endpoint: {path}")
            self._send_json_response({"error": "Not found"}, status=404)

    # =========================================================================
    # Compatibility Art Job API (/api/v1/art/*)
    # =========================================================================

    def _handle_art_v1_generate(self, data: dict):
        handle_art_v1_generate(
            self,
            data,
            art_jobs=_ART_JOBS,
            art_jobs_lock=_ART_JOBS_LOCK,
        )

    def _handle_art_v1_status(self, job_id: str):
        handle_art_v1_status(self, job_id, art_jobs=_ART_JOBS, art_jobs_lock=_ART_JOBS_LOCK)

    def _handle_art_v1_result(self, job_id: str):
        handle_art_v1_result(self, job_id, art_jobs=_ART_JOBS, art_jobs_lock=_ART_JOBS_LOCK)

    def _handle_art_v1_models(self):
        handle_art_v1_models(self)

    def _generate_first_png_bytes(self, data: dict) -> bytes:
        return generate_first_png_bytes(self, data, get_api=get_api)

    def _handle_ollama_root(self):
        """Handle root endpoint - Ollama returns 'Ollama is running'."""
        self._send_text_response("Ollama is running")

    def _handle_health(self):
        """Health check endpoint."""
        art_model_status = "disabled"
        if os.environ.get("AIRUNNER_SD_ON", "0") == "1":
            art_model_status = self._art_model_status()
        health_data = {
            "status": "ready",
            "services": {
                "llm": os.environ.get("AIRUNNER_LLM_ON", "1") == "1",
                "art": os.environ.get("AIRUNNER_SD_ON", "0") == "1",
                "tts": os.environ.get("AIRUNNER_TTS_ON", "0") == "1",
                "stt": os.environ.get("AIRUNNER_STT_ON", "0") == "1",
            },
            "art_model_status": art_model_status,
            "art_model_loaded": art_model_status in {"loaded", "ready"},
            "version": "2.0.0",
        }
        self._send_json_response(health_data)

    def _handle_llm_models(self):
        """List available LLM models."""
        # TODO: Get actual model list from API
        models_data = {
            "models": [{"name": "default", "type": "local", "loaded": False}]
        }
        self._send_json_response(models_data)

    # =========================================================================
    # Ollama-Compatible API Endpoints (for VS Code Continue.dev)
    # =========================================================================

    def _handle_ollama_tags(self):
        handle_ollama_tags(self)

    def _handle_ollama_version(self):
        handle_ollama_version(self)

    def _handle_ollama_show(self, data):
        handle_ollama_show(self, data, get_api=get_api)

    def _handle_ollama_generate(self, data):
        handle_ollama_generate(self, data, get_api=get_api)

    def _handle_ollama_generate_stream(self, prompt, model, llm_request, request_id):
        handle_ollama_generate_stream(
            self,
            prompt,
            model,
            llm_request,
            request_id,
            get_api=get_api,
        )

    def _handle_ollama_generate_non_stream(self, prompt, model, llm_request, request_id):
        handle_ollama_generate_non_stream(
            self,
            prompt,
            model,
            llm_request,
            request_id,
            get_api=get_api,
        )

    def _handle_ollama_chat(self, data):
        handle_ollama_chat(self, data, get_api=get_api)

    def _handle_ollama_chat_stream(self, prompt, model, llm_request, request_id, tools=None):
        handle_ollama_chat_stream(
            self,
            prompt,
            model,
            llm_request,
            request_id,
            get_api=get_api,
            tools=tools,
        )

    def _handle_ollama_chat_non_stream(self, prompt, model, llm_request, request_id, tools=None):
        handle_ollama_chat_non_stream(
            self,
            prompt,
            model,
            llm_request,
            request_id,
            get_api=get_api,
            tools=tools,
        )

    def _handle_ollama_ps(self):
        handle_ollama_ps(self, get_api=get_api)

    def _handle_ollama_pull(self, data):
        handle_ollama_pull(self, data)

    def _handle_ollama_embed(self, data):
        handle_ollama_embed(self, data)

    def _handle_ollama_copy(self, data):
        handle_ollama_copy(self, data)

    def _handle_ollama_create(self, data):
        handle_ollama_create(self, data)

    # =========================================================================
    # End of Ollama-Compatible API Endpoints
    # =========================================================================

    # =========================================================================
    # OpenAI-Compatible API Endpoints (for VS Code Copilot BYOK)
    # =========================================================================

    def _handle_openai_models(self, data):
        handle_openai_models(self, data)

    def _handle_openai_chat_completions(self, data):
        handle_openai_chat_completions(self, data, get_api=get_api)

    def _handle_openai_chat_stream(self, prompt, model, llm_request, request_id, tools=None):
        handle_openai_chat_stream(
            self,
            prompt,
            model,
            llm_request,
            request_id,
            get_api=get_api,
            tools=tools,
        )

    def _handle_openai_chat_non_stream(self, prompt, model, llm_request, request_id, tools=None):
        handle_openai_chat_non_stream(
            self,
            prompt,
            model,
            llm_request,
            request_id,
            get_api=get_api,
            tools=tools,
        )

    # =========================================================================
    # End of OpenAI-Compatible API Endpoints
    # =========================================================================

    def _extract_llm_request_data(self, data: Dict) -> Dict:
        return extract_llm_request_data(data)

    def _map_top_level_params(self, data: Dict, llm_request_data: Dict):
        map_top_level_params(data, llm_request_data)

    def _parse_action_type(self, action_str: str) -> LLMActionType:
        return parse_action_type(action_str)

    def _handle_llm(self, data):
        handle_llm(self, data, get_api=get_api)

    def _create_llm_request(self, params: Dict) -> LLMRequest:
        return create_llm_request(self, params)

    def _parse_chunk_size(self, line: bytes) -> Optional[int]:
        """Parse chunk size from HTTP chunked encoding line.

        Args:
            line: Raw line containing chunk size

        Returns:
            Chunk size as integer, or None if invalid
        """
        try:
            return int(line.split(b";", 1)[0].strip(), 16)
        except Exception:
            return None

    def _consume_trailers(self):
        """Consume HTTP trailer headers until CRLF."""
        while True:
            trailer = self.rfile.readline()
            if not trailer or trailer.strip() == b"":
                break

    def _read_chunked(self) -> bytes:
        """Read a chunked HTTP request body from self.rfile.

        Returns the full concatenated body bytes.
        """
        data = b""
        try:
            while True:
                line = self.rfile.readline()
                if not line or not line.strip():
                    if not line:
                        break
                    continue
                size = self._parse_chunk_size(line.strip())
                if size is None:
                    break
                if size == 0:
                    self._consume_trailers()
                    break
                chunk = self.rfile.read(size)
                data += chunk
                self.rfile.read(2)  # Read trailing CRLF
        except Exception:
            pass
        return data

    def _handle_llm_stream(
        self,
        prompt: str,
        action: LLMActionType,
        llm_request: LLMRequest,
        request_id: str,
        search_hints: Optional[Dict] = None,
    ):
        handle_llm_stream(
            self,
            prompt,
            action,
            llm_request,
            request_id,
            get_api=get_api,
            search_hints=search_hints,
        )

    def _handle_llm_non_stream(
        self,
        prompt: str,
        action: LLMActionType,
        llm_request: LLMRequest,
        request_id: str,
        search_hints: Optional[Dict] = None,
    ):
        handle_llm_non_stream(
            self,
            prompt,
            action,
            llm_request,
            request_id,
            get_api=get_api,
            search_hints=search_hints,
        )

    def _handle_llm_batch(self, data):
        handle_llm_batch(self, data, get_api=get_api)

    def _handle_llm_batch_sync(
        self,
        prompts: list,
        system_prompt: Optional[str],
        action: LLMActionType,
        llm_request: LLMRequest,
    ):
        handle_llm_batch_sync(
            self,
            prompts,
            system_prompt,
            action,
            llm_request,
            get_api=get_api,
        )

    def _handle_art(self, data):
        handle_art(self, data, get_api=get_api)
    
    def _create_image_request(self, data: dict) -> ImageRequest:
        return create_image_request(data)
    
    def _format_art_response(self, response) -> dict:
        return format_art_response(self, response)

    def _handle_tts(self, data):
        """Handle text-to-speech request.
        
        Request format:
        {
            "text": "Hello, world!",
            "voice": "optional_voice_name",
            "speed": 1.0
        }
        
        Response format:
        {
            "status": "queued",
            "message": "Text queued for speech synthesis"
        }
        
        Note: Audio is played through the system's default audio output.
        For headless servers, ensure audio output is configured.
        """
        # Check if TTS is enabled
        if os.environ.get("AIRUNNER_TTS_ON") != "1":
            self._send_json_response({
                "error": "TTS service not enabled",
                "hint": "Start with --enable-tts flag"
            }, status=503)
            return
        
        # Validate text
        text = data.get("text", "")
        if not text:
            self._send_json_response({"error": "Missing 'text' field"}, status=400)
            return
        
        api = get_api()
        if not api:
            self._send_json_response({"error": "API not initialized"}, status=500)
            return
        
        try:
            # Queue the text for TTS
            # The TTS worker will pick this up and generate speech
            self.logger.info(
                "TTS request queued (%s)",
                summarize_text(text),
            )
            api.tts.play_audio(text)
            
            self._send_json_response({
                "status": "queued",
                "message": "Text queued for speech synthesis",
                "text_length": len(text),
            })
        except Exception as e:
            self.logger.error(f"TTS error: {e}")
            self._send_json_response({
                "error": f"TTS failed: {str(e)}"
            }, status=500)

    def _handle_stt(self, data):
        """Handle speech-to-text request.
        
        Request format (JSON with base64 audio):
        {
            "audio": "base64_encoded_audio_data",
            "format": "wav"  # optional, defaults to wav
        }
        
        Response format:
        {
            "transcription": "The transcribed text",
            "status": "success"
        }
        
        Note: Audio should be 16kHz mono WAV for best results.
        """
        # Check if STT is enabled
        if os.environ.get("AIRUNNER_STT_ON") != "1":
            self._send_json_response({
                "error": "STT service not enabled",
                "hint": "Start with --enable-stt flag"
            }, status=503)
            return
        
        # Get audio data
        audio_b64 = data.get("audio", "")
        if not audio_b64:
            self._send_json_response({"error": "Missing 'audio' field (base64 encoded)"}, status=400)
            return
        
        api = get_api()
        if not api:
            self._send_json_response({"error": "API not initialized"}, status=500)
            return
        
        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_b64)
            
            # Set up threading event and result holder
            complete_event = threading.Event()
            result_holder = {"transcription": None, "error": None}
            
            def on_transcription(signal_data: dict):
                """Handle transcription result."""
                transcription = signal_data.get("transcription", "")
                self.logger.info(
                    "STT transcription received (%s)",
                    summarize_text(transcription, label="transcription"),
                )
                result_holder["transcription"] = transcription
                complete_event.set()
            
            # Register for transcription response
            from airunner_services.utils.application.signal_mediator import SignalMediator
            mediator = SignalMediator()
            mediator.register(SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, on_transcription)
            
            try:
                # Send audio for processing
                self.logger.info(f"STT request: {len(audio_bytes)} bytes of audio")
                api.emit_signal(SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL, {"item": audio_bytes})
                
                # Wait for transcription (30 second timeout)
                if complete_event.wait(timeout=30):
                    if result_holder["transcription"] is not None:
                        self._send_json_response({
                            "transcription": result_holder["transcription"],
                            "status": "success"
                        })
                    else:
                        self._send_json_response({
                            "error": "No transcription received"
                        }, status=500)
                else:
                    self._send_json_response({
                        "error": "STT timeout",
                        "hint": "Transcription took longer than 30 seconds"
                    }, status=504)
            finally:
                mediator.unregister(SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, on_transcription)
                
        except Exception as e:
            self.logger.error(f"STT error: {e}")
            self._send_json_response({
                "error": f"STT failed: {str(e)}"
            }, status=500)

    def _handle_stub(self, msg):
        self._send_json_response({"result": msg})

    def _handle_reset_memory(self):
        """Reset LLM conversation memory.

        This endpoint clears the LLM's conversation history, useful for
        tests to prevent contamination between test runs.

        This clears:
        1. In-memory workflow state and checkpoints
        2. Persisted conversation in database
        3. Creates a FRESH conversation with new ID to prevent checkpoint restoration
        """
        self.logger.info("Endpoint called!")
        sys.stdout.flush()
        try:
            self.logger.info("Getting API...")
            sys.stdout.flush()
            api = get_api()
            self.logger.info(f"API: {api}")
            sys.stdout.flush()

            try:
                # Mark all conversations as non-current
                Conversation.objects.update_by(
                    {"current": True}, current=False
                )

                # Create a completely fresh conversation
                new_convo = Conversation.create()
                new_conv_id = new_convo.id

                self.logger.info(
                    f"Created new conversation ID {new_conv_id} for fresh start"
                )

                # Update workflow manager to use new conversation
                if hasattr(api.llm, "model_manager") and api.llm.model_manager:
                    workflow_manager = getattr(
                        api.llm.model_manager, "_workflow_manager", None
                    )
                    self.logger.info(
                        f"workflow_manager exists: {workflow_manager is not None}"
                    )
                    if workflow_manager:
                        # CRITICAL: Clear memory FIRST to wipe checkpoint cache
                        # BEFORE setting new conversation ID (which rebuilds workflow)
                        self.logger.info("About to call clear_memory()")
                        if hasattr(workflow_manager, "clear_memory"):
                            workflow_manager.clear_memory()
                            self.logger.info("LLM conversation memory cleared")
                            self.logger.info("clear_memory() called")

                        # NOW set new conversation ID - rebuilds workflow with clean state
                        self.logger.info("About to call set_conversation_id()")
                        if hasattr(workflow_manager, "set_conversation_id"):
                            workflow_manager.set_conversation_id(new_conv_id)
                            self.logger.info(
                                f"Workflow manager using new conversation {new_conv_id}"
                            )
                            self.logger.info(
                                f"set_conversation_id({new_conv_id}) called"
                            )

            except Exception as db_err:
                self.logger.error(
                    f"Error creating new conversation: {db_err}", exc_info=True
                )

            self._send_json_response({"status": "memory_cleared"})
        except Exception as e:
            self.logger.error(f"Error resetting memory: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, status=500)

    def _handle_reset_database(self):
        """Reset test database by clearing all test-related tables.

        This endpoint is specifically for test isolation - it clears
        tables that accumulate test data (like Events) to prevent
        contamination between test runs.

        ONLY clears tables when AIRUNNER_ENVIRONMENT=test to prevent
        accidental data loss in production.
        """
        try:
            # SAFETY: Only allow in test environment
            if os.environ.get("AIRUNNER_ENVIRONMENT") != "test":
                self._send_json_response(
                    {"error": "reset_database only allowed in test environment"},
                    status=403
                )
                return
            deleted_counts = {}
            with session_scope() as session:
                conversation_count = session.query(Conversation).delete()
                deleted_counts["conversations"] = conversation_count
                session.commit()

            self.logger.info(f"Test database cleared: {deleted_counts}")

            self._send_json_response(
                {"status": "database_cleared", "deleted": deleted_counts}
            )
        except Exception as e:
            self.logger.error(f"Error resetting database: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, status=500)

    def _handle_shutdown(self):
        """Gracefully shutdown the headless server.

        This endpoint allows clients to remotely shutdown the server.
        The shutdown happens after sending the response to avoid
        connection errors.
        """
        try:
            self._send_json_response({"status": "shutting_down"})

            # Schedule shutdown in a background thread to allow response to complete
            def delayed_shutdown():
                time.sleep(0.5)  # Let response finish sending
                self.logger.info(
                    "Shutdown requested via /admin/shutdown endpoint"
                )
                api = get_api()
                if api:
                    api.cleanup()
                sys.exit(0)

            shutdown_thread = threading.Thread(
                target=delayed_shutdown, daemon=True
            )
            shutdown_thread.start()

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, status=500)


# Usage: pass AIRunnerAPIRequestHandler to your HTTP server for /llm, /art, /stt, /tts endpoints.
