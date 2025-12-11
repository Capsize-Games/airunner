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
import io
import json
import base64
import threading
import uuid
from http.server import BaseHTTPRequestHandler
from typing import Dict, Optional
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.enums import LLMActionType, SignalCode, EngineResponseCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application.get_logger import get_logger
from airunner.components.application.api.api import API
from airunner.components.calendar.data.event import Event
from airunner.components.data.session_manager import session_scope
from airunner.components.llm.data.conversation import Conversation
from airunner.utils.application.get_logger import get_logger

# Lazy import to avoid circular dependency
_api = None
logger = get_logger(__name__)


def get_api():
    """Get or create the API singleton instance."""
    global _api
    logger.info(
        f"DEBUG get_api: _api is {'None' if _api is None else type(_api).__name__}"
    )
    if _api is None:
        _api = API()
    return _api


def set_api(api_instance):
    """Set the global API instance.

    Use this when creating an API instance manually (e.g., in headless mode)
    to ensure tools can access it via get_api().

    Args:
        api_instance: The API/App instance to register globally
    """
    global _api
    logger.info(
        f"DEBUG set_api: Setting global API to {type(api_instance).__name__}"
    )
    _api = api_instance
    logger.info(
        f"DEBUG set_api: Global API is now {'None' if _api is None else type(_api).__name__}"
    )


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
        
        # Check via worker manager if available
        if hasattr(api, '_worker_manager') and api._worker_manager:
            worker = getattr(api._worker_manager, 'llm_generate_worker', None)
            if worker:
                manager = getattr(worker, 'model_manager', None)
                if manager:
                    # Check if chat_model is loaded
                    return getattr(manager, '_chat_model', None) is not None
        return False

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
        
        self.logger.info(f"Auto-loading LLM model: {model_path}")
        
        # Import SignalCode here to avoid circular imports
        from airunner.enums import SignalCode
        
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

    def _ensure_art_model_loaded(self) -> tuple[bool, str]:
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
        
        # Get art model path from environment or settings
        art_model_path = os.environ.get("AIRUNNER_ART_MODEL_PATH")
        
        if not art_model_path:
            # Try to get from settings
            try:
                from airunner.components.art.data.generator_settings import GeneratorSettings
                settings = GeneratorSettings.objects.first()
                if settings:
                    art_model_path = settings.model
            except Exception:
                pass
        
        if not art_model_path:
            return False, "No art model configured. Use --art-model flag or configure in AIRunner GUI."
        
        self.logger.info(f"Auto-loading art model: {art_model_path}")
        
        from airunner.enums import SignalCode
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
        else:
            self.logger.warning(f"[Ollama API] Unknown GET endpoint: {path}")
            self._send_json_response({"error": "Not found"}, status=404)

    def _handle_ollama_root(self):
        """Handle root endpoint - Ollama returns 'Ollama is running'."""
        self._send_text_response("Ollama is running")

    def _handle_health(self):
        """Health check endpoint."""
        health_data = {
            "status": "ready",
            "services": {
                "llm": os.environ.get("AIRUNNER_LLM_ON", "1") == "1",
                "art": os.environ.get("AIRUNNER_SD_ON", "0") == "1",
                "tts": os.environ.get("AIRUNNER_TTS_ON", "0") == "1",
                "stt": os.environ.get("AIRUNNER_STT_ON", "0") == "1",
            },
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
        """Handle Ollama /api/tags endpoint - list available models.
        
        Response format matches Ollama's /api/tags specification.
        Returns actual model info from AIRunner settings when available.
        """
        import re
        
        # Try to get actual model info from settings
        model_name = "airunner:latest"
        model_family = "qwen"
        parameter_size = "8B"
        quantization = "Q4_K_M"
        
        try:
            from airunner.components.llm.data.llm_generator_settings import LLMGeneratorSettings
            settings = LLMGeneratorSettings.objects.first()
            if settings and settings.model_version:
                # Extract model name from path (e.g., "Qwen2.5-7B-Instruct-4bit")
                import os
                model_basename = os.path.basename(settings.model_version)
                model_name = f"{model_basename}:latest"
                
                # Try to detect model family from name
                name_lower = model_basename.lower()
                if "qwen" in name_lower:
                    model_family = "qwen"
                elif "llama" in name_lower:
                    model_family = "llama"
                elif "mistral" in name_lower:
                    model_family = "mistral"
                elif "phi" in name_lower:
                    model_family = "phi"
                
                # Extract parameter size
                size_match = re.search(r'(\d+\.?\d*)b', name_lower)
                if size_match:
                    parameter_size = f"{size_match.group(1).upper()}B"
                
                # Detect quantization level
                if "4bit" in name_lower or "q4" in name_lower:
                    quantization = "Q4_K_M"
                elif "8bit" in name_lower or "q8" in name_lower:
                    quantization = "Q8_0"
                elif "fp16" in name_lower or "f16" in name_lower:
                    quantization = "F16"
        except Exception as e:
            self.logger.debug(f"Could not get model settings: {e}")
        
        # Calculate approximate size based on parameter count and quantization
        param_num = float(parameter_size.replace("B", ""))
        if quantization.startswith("Q4"):
            size_bytes = int(param_num * 0.5 * 1e9)  # ~0.5 bytes per param for Q4
        elif quantization.startswith("Q8"):
            size_bytes = int(param_num * 1.0 * 1e9)  # ~1 byte per param for Q8
        else:
            size_bytes = int(param_num * 2.0 * 1e9)  # ~2 bytes per param for F16
        
        models_data = {
            "models": [
                {
                    "name": model_name,
                    "model": model_name,
                    "modified_at": "2024-12-01T00:00:00.000000000Z",
                    "size": size_bytes,
                    "digest": f"sha256:{''.join(f'{ord(c):02x}' for c in model_name[:32]).ljust(64, '0')}",
                    "details": {
                        "parent_model": "",
                        "format": "gguf",
                        "family": model_family,
                        "families": [model_family],
                        "parameter_size": parameter_size,
                        "quantization_level": quantization
                    }
                }
            ]
        }
        self._send_json_response(models_data)

    def _handle_ollama_ps(self):
        """Handle Ollama /api/ps endpoint - list running models.
        
        This shows which models are currently loaded in memory.
        """
        # Try to get actual model info
        model_name = "airunner:latest"
        try:
            from airunner.components.llm.data.llm_generator_settings import LLMGeneratorSettings
            settings = LLMGeneratorSettings.objects.first()
            if settings and settings.model_version:
                import os
                model_name = os.path.basename(settings.model_version)
                model_name = f"{model_name}:latest"
        except Exception:
            pass
        
        # Check if model is loaded
        api = get_api()
        is_loaded = api is not None and hasattr(api, 'llm') and api.llm is not None
        
        if is_loaded:
            models_data = {
                "models": [
                    {
                        "name": model_name,
                        "model": model_name,
                        "size": 4500000000,
                        "digest": f"sha256:{''.join(f'{ord(c):02x}' for c in model_name[:32]).ljust(64, '0')}",
                        "details": {
                            "parent_model": "",
                            "format": "gguf",
                            "family": "qwen",
                            "families": ["qwen"],
                            "parameter_size": "8B",
                            "quantization_level": "Q4_K_M"
                        },
                        "expires_at": "2099-12-31T23:59:59.000000000Z",
                        "size_vram": 4500000000
                    }
                ]
            }
        else:
            models_data = {"models": []}
        
        self._send_json_response(models_data)

    def _handle_ollama_version(self):
        """Handle Ollama /api/version endpoint.
        
        Returns a version string that mimics Ollama's format.
        """
        # Use a recent Ollama version to ensure compatibility
        # VS Code may check for minimum version support
        self._send_json_response({"version": "0.9.0"})

    def _handle_ollama_show(self, data):
        """Handle Ollama /api/show endpoint - show model information.
        
        Returns full model metadata including capabilities for VS Code compatibility.
        """
        model_name = data.get("name", "airunner:latest")
        
        # Get actual model info from settings if available
        api = get_api()
        llm_settings = None
        if api and hasattr(api, 'llm_generator_settings'):
            llm_settings = api.llm_generator_settings
        
        # Determine model family from name
        family = "llama"
        families = ["llama"]
        name_lower = model_name.lower()
        
        if "qwen" in name_lower:
            family = "qwen"
            families = ["qwen"]
        elif "mistral" in name_lower:
            family = "mistral"
            families = ["mistral"]
        elif "phi" in name_lower:
            family = "phi"
            families = ["phi"]
        
        # Determine capabilities based on model type
        capabilities = ["completion", "tools"]
        
        # Add vision capability for VL (vision-language) models
        if "-vl" in name_lower or "vl-" in name_lower or "vision" in name_lower:
            capabilities.append("vision")
        
        # Detect parameter size from model name
        import re
        parameter_size = "8B"
        size_match = re.search(r'(\d+\.?\d*)b', name_lower)
        if size_match:
            parameter_size = f"{size_match.group(1).upper()}B"
        
        # Detect context length based on model
        num_ctx = 4096
        if "qwen3" in name_lower:
            num_ctx = 40960  # Qwen3 supports 40K context
            if "30b" in name_lower or "235b" in name_lower or "4b" in name_lower:
                num_ctx = 262144  # MoE models support 256K
        
        model_info = {
            "modelfile": f"FROM {model_name}\nPARAMETER temperature 0.7\nPARAMETER num_ctx {num_ctx}",
            "parameters": f"temperature 0.7\nnum_ctx {num_ctx}",
            "template": "{{ if .System }}<|im_start|>system\n{{ .System }}<|im_end|>\n{{ end }}{{ if .Prompt }}<|im_start|>user\n{{ .Prompt }}<|im_end|>\n{{ end }}<|im_start|>assistant\n{{ .Response }}<|im_end|>",
            "license": "Apache 2.0",
            "modified_at": "2024-12-01T00:00:00.000000000Z",
            "details": {
                "parent_model": "",
                "format": "gguf",
                "family": family,
                "families": families,
                "parameter_size": parameter_size,
                "quantization_level": "Q4_K_M"
            },
            "model_info": {
                "general.architecture": family,
                "general.file_type": 15,
                "general.parameter_count": int(float(parameter_size.replace("B", "")) * 1e9) if parameter_size.replace(".", "").replace("B", "").isdigit() else 8000000000,
                "general.quantization_version": 2,
                "tokenizer.ggml.model": "gpt2",
                "context_length": num_ctx
            },
            "capabilities": capabilities
        }
        self._send_json_response(model_info)

    def _handle_ollama_generate(self, data):
        """Handle Ollama /api/generate endpoint - text generation.
        
        Request format:
        {
            "model": "airunner:latest",
            "prompt": "Why is the sky blue?",
            "stream": true,
            "options": {"temperature": 0.7, "num_predict": 100}
        }
        
        Automatically loads the model if not already loaded.
        """
        # Ensure model is loaded (auto-load if needed)
        success, error_msg = self._ensure_llm_model_loaded()
        if not success:
            self._send_json_response({
                "error": error_msg,
                "hint": "Start with --model flag or configure model in AIRunner GUI"
            }, status=503)
            return
        
        prompt = data.get("prompt", "")
        model = data.get("model", "airunner:latest")
        stream = data.get("stream", True)
        options = data.get("options", {})
        system = data.get("system", "")
        
        if not prompt:
            self._send_json_response({"error": "prompt is required"}, status=400)
            return
        
        llm_request = LLMRequest()
        llm_request.temperature = options.get("temperature", 0.7)
        llm_request.max_new_tokens = options.get("num_predict", 2048)
        if system:
            llm_request.system_prompt = system
        
        request_id = str(uuid.uuid4())
        
        if stream:
            self._handle_ollama_generate_stream(prompt, model, llm_request, request_id)
        else:
            self._handle_ollama_generate_non_stream(prompt, model, llm_request, request_id)

    def _handle_ollama_generate_stream(self, prompt, model, llm_request, request_id):
        """Handle streaming Ollama generate response."""
        self._set_headers(200, content_type="application/x-ndjson")
        
        complete_event = threading.Event()
        start_time = time.time()
        
        def stream_callback(data: dict):
            response = data.get("response")
            if response:
                created_at = time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime())
                
                ollama_response = {
                    "model": model,
                    "created_at": created_at,
                    "response": response.message,
                    "done": response.is_end_of_message,
                }
                
                if response.is_end_of_message:
                    duration_ns = int((time.time() - start_time) * 1e9)
                    ollama_response.update({
                        "total_duration": duration_ns,
                        "load_duration": 0,
                        "prompt_eval_count": len(prompt) // 4,
                        "prompt_eval_duration": duration_ns // 10,
                        "eval_count": 100,
                        "eval_duration": duration_ns,
                    })
                    complete_event.set()
                
                self.wfile.write(json.dumps(ollama_response).encode("utf-8") + b"\n")
                self.wfile.flush()
        
        api = get_api()
        if not api:
            error_response = {"error": "API not initialized"}
            self.wfile.write(json.dumps(error_response).encode("utf-8") + b"\n")
            return
        
        try:
            api.llm.send_request(
                prompt=prompt,
                action=LLMActionType.CHAT,
                llm_request=llm_request,
                request_id=request_id,
                callback=stream_callback,
            )
            
            if not complete_event.wait(timeout=300):
                error_response = {
                    "model": model,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime()),
                    "response": "",
                    "done": True,
                    "error": "Request timeout"
                }
                self.wfile.write(json.dumps(error_response).encode("utf-8") + b"\n")
                
        except Exception as e:
            self.logger.error(f"Ollama generate error: {e}", exc_info=True)
            error_response = {
                "model": model,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime()),
                "response": "",
                "done": True,
                "error": str(e)
            }
            self.wfile.write(json.dumps(error_response).encode("utf-8") + b"\n")
        
        # Close connection to signal end of stream
        self.close_connection = True

    def _handle_ollama_generate_non_stream(self, prompt, model, llm_request, request_id):
        """Handle non-streaming Ollama generate response."""
        complete_event = threading.Event()
        complete_message = []
        start_time = time.time()
        
        def collect_callback(data: dict):
            response = data.get("response")
            if response:
                complete_message.append(response.message)
                if response.is_end_of_message:
                    complete_event.set()
        
        api = get_api()
        if not api:
            self._send_json_response({"error": "API not initialized"}, status=500)
            return
        
        try:
            api.llm.send_request(
                prompt=prompt,
                action=LLMActionType.CHAT,
                llm_request=llm_request,
                request_id=request_id,
                callback=collect_callback,
            )
            
            if complete_event.wait(timeout=300):
                duration_ns = int((time.time() - start_time) * 1e9)
                full_response = "".join(complete_message)
                
                response_data = {
                    "model": model,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime()),
                    "response": full_response,
                    "done": True,
                    "total_duration": duration_ns,
                    "load_duration": 0,
                    "prompt_eval_count": len(prompt) // 4,
                    "prompt_eval_duration": duration_ns // 10,
                    "eval_count": len(full_response) // 4,
                    "eval_duration": duration_ns,
                }
                self._send_json_response(response_data)
            else:
                self._send_json_response({"error": "Request timeout"}, status=504)
                
        except Exception as e:
            self.logger.error(f"Ollama generate error: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, status=500)

    def _handle_ollama_chat(self, data):
        """Handle Ollama /api/chat endpoint - chat completion with tool support.
        
        Request format:
        {
            "model": "airunner:latest",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Hello!"}
            ],
            "stream": true,
            "options": {"temperature": 0.7},
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather for a location",
                        "parameters": {...}
                    }
                }
            ]
        }
        
        Automatically loads the model if not already loaded.
        """
        # Ensure model is loaded (auto-load if needed)
        success, error_msg = self._ensure_llm_model_loaded()
        if not success:
            self._send_json_response({
                "error": error_msg,
                "hint": "Start with --model flag or configure model in AIRunner GUI"
            }, status=503)
            return
        
        messages = data.get("messages", [])
        model = data.get("model", "airunner:latest")
        stream = data.get("stream", True)
        options = data.get("options", {})
        tools = data.get("tools", [])
        
        self.logger.info(f"[Ollama API] /api/chat request: model={model}, stream={stream}, messages={len(messages)}, tools={len(tools)} tool(s)")
        
        if not messages:
            self._send_json_response({"error": "messages is required"}, status=400)
            return
        
        # Extract system prompt and find the last user message
        # VS Code/Ollama clients send the full conversation history
        system_prompt = ""
        last_user_content = ""
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_prompt = content
            elif role == "user":
                # Keep tracking the latest user message
                last_user_content = content
        
        # Use just the last user message as the prompt
        # The LLMModelManager/WorkflowManager handles conversation history internally
        prompt = last_user_content
        
        self.logger.info(f"[Ollama API] Extracted prompt: {prompt[:100]}...")
        if system_prompt:
            self.logger.info(f"[Ollama API] System prompt: {system_prompt[:100]}...")
        
        llm_request = LLMRequest()
        llm_request.temperature = options.get("temperature", 0.7)
        llm_request.max_new_tokens = options.get("num_predict", 2048)
        
        # CRITICAL: Set system prompt from the request
        # This allows VS Code and other clients to provide their own system prompt
        if system_prompt:
            llm_request.system_prompt = system_prompt
        
        # For Ollama API requests, don't use conversation memory
        # The client manages its own history and sends it with each request
        llm_request.use_memory = False
        
        # Handle tools - if tools provided, enable them; otherwise disable all tools
        # This prevents AIRunner's default tools from interfering with simple chat
        if tools:
            llm_request.tools = tools
            llm_request.tool_categories = None  # Enable all tools when tools are provided
            self.logger.info(f"[Ollama API] Passing {len(tools)} tools to LLM")
        else:
            # Explicitly disable tools for simple chat requests
            llm_request.tool_categories = []  # Empty list = no tools
            self.logger.info("[Ollama API] No tools provided, disabling all tools")
        
        request_id = str(uuid.uuid4())
        
        if stream:
            self._handle_ollama_chat_stream(prompt, model, llm_request, request_id, tools)
        else:
            self._handle_ollama_chat_non_stream(prompt, model, llm_request, request_id, tools)

    def _handle_ollama_chat_stream(self, prompt, model, llm_request, request_id, tools=None):
        """Handle streaming Ollama chat response with tool support."""
        self._set_headers(200, content_type="application/x-ndjson")
        
        complete_event = threading.Event()
        start_time = time.time()
        tool_calls_made = []
        
        def stream_callback(data: dict):
            response = data.get("response")
            if response:
                created_at = time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime())
                
                ollama_response = {
                    "model": model,
                    "created_at": created_at,
                    "message": {
                        "role": "assistant",
                        "content": response.message,
                    },
                    "done": response.is_end_of_message,
                }
                
                # Check if response contains tool calls
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    ollama_response["message"]["tool_calls"] = response.tool_calls
                    ollama_response["message"]["content"] = ""
                
                if response.is_end_of_message:
                    duration_ns = int((time.time() - start_time) * 1e9)
                    ollama_response.update({
                        "done_reason": "stop",
                        "total_duration": duration_ns,
                        "load_duration": 0,
                        "prompt_eval_count": len(prompt) // 4,
                        "prompt_eval_duration": duration_ns // 10,
                        "eval_count": 100,
                        "eval_duration": duration_ns,
                    })
                    complete_event.set()
                
                self.wfile.write(json.dumps(ollama_response).encode("utf-8") + b"\n")
                self.wfile.flush()
        
        api = get_api()
        if not api:
            error_response = {"error": "API not initialized"}
            self.wfile.write(json.dumps(error_response).encode("utf-8") + b"\n")
            return
        
        try:
            api.llm.send_request(
                prompt=prompt,
                action=LLMActionType.CHAT,
                llm_request=llm_request,
                request_id=request_id,
                callback=stream_callback,
            )
            
            if not complete_event.wait(timeout=300):
                error_response = {
                    "model": model,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime()),
                    "message": {"role": "assistant", "content": ""},
                    "done": True,
                    "error": "Request timeout"
                }
                self.wfile.write(json.dumps(error_response).encode("utf-8") + b"\n")
                
        except Exception as e:
            self.logger.error(f"Ollama chat error: {e}", exc_info=True)
            error_response = {
                "model": model,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime()),
                "message": {"role": "assistant", "content": ""},
                "done": True,
                "error": str(e)
            }
            self.wfile.write(json.dumps(error_response).encode("utf-8") + b"\n")
        
        # Close connection to signal end of stream
        self.close_connection = True

    def _handle_ollama_chat_non_stream(self, prompt, model, llm_request, request_id, tools=None):
        """Handle non-streaming Ollama chat response with tool support."""
        complete_event = threading.Event()
        complete_message = []
        tool_calls_result = []
        start_time = time.time()
        
        def collect_callback(data: dict):
            response = data.get("response")
            if response:
                complete_message.append(response.message)
                # Collect tool calls if present
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    tool_calls_result.extend(response.tool_calls)
                if response.is_end_of_message:
                    complete_event.set()
        
        api = get_api()
        if not api:
            self._send_json_response({"error": "API not initialized"}, status=500)
            return
        
        try:
            api.llm.send_request(
                prompt=prompt,
                action=LLMActionType.CHAT,
                llm_request=llm_request,
                request_id=request_id,
                callback=collect_callback,
            )
            
            if complete_event.wait(timeout=300):
                duration_ns = int((time.time() - start_time) * 1e9)
                full_response = "".join(complete_message)
                
                message_data = {
                    "role": "assistant",
                    "content": full_response,
                }
                
                # Add tool calls if present
                if tool_calls_result:
                    message_data["tool_calls"] = tool_calls_result
                    message_data["content"] = ""
                
                response_data = {
                    "model": model,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime()),
                    "message": message_data,
                    "done_reason": "stop",
                    "done": True,
                    "total_duration": duration_ns,
                    "load_duration": 0,
                    "prompt_eval_count": len(prompt) // 4,
                    "prompt_eval_duration": duration_ns // 10,
                    "eval_count": len(full_response) // 4,
                    "eval_duration": duration_ns,
                }
                self._send_json_response(response_data)
            else:
                self._send_json_response({"error": "Request timeout"}, status=504)
                
        except Exception as e:
            self.logger.error(f"Ollama chat error: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, status=500)

    def _handle_ollama_ps(self):
        """Handle Ollama /api/ps endpoint - list running models.
        
        VS Code uses this to check if a model is loaded.
        """
        # Return the currently loaded model as "running"
        ps_data = {
            "models": [
                {
                    "name": "airunner:latest",
                    "model": "airunner:latest",
                    "size": 5000000000,  # ~5GB placeholder
                    "digest": "sha256:airunner",
                    "details": {
                        "parent_model": "",
                        "format": "gguf",
                        "family": "qwen",
                        "families": ["qwen"],
                        "parameter_size": "8B",
                        "quantization_level": "Q4_K_M"
                    },
                    "expires_at": "2099-12-31T23:59:59Z",
                    "size_vram": 5000000000
                }
            ]
        }
        self._send_json_response(ps_data)

    def _handle_ollama_pull(self, data):
        """Handle Ollama /api/pull endpoint - pretend to pull a model.
        
        Since AIRunner manages its own models, we just return success.
        VS Code may call this when trying to ensure a model exists.
        """
        model = data.get("model", "airunner:latest")
        stream = data.get("stream", True)
        
        if stream:
            self._set_headers(200, content_type="application/x-ndjson")
            # Simulate pull progress
            responses = [
                {"status": "pulling manifest"},
                {"status": f"pulling {model}"},
                {"status": "verifying sha256 digest"},
                {"status": "writing manifest"},
                {"status": "success"}
            ]
            for resp in responses:
                self.wfile.write(json.dumps(resp).encode("utf-8") + b"\n")
                self.wfile.flush()
        else:
            self._send_json_response({"status": "success"})

    def _handle_ollama_embed(self, data):
        """Handle Ollama /api/embed endpoint - generate embeddings.
        
        Placeholder - returns dummy embeddings.
        TODO: Implement actual embedding generation if needed.
        """
        model = data.get("model", "airunner:latest")
        input_text = data.get("input", data.get("prompt", ""))
        
        # Generate placeholder embeddings (384 dimensions like all-MiniLM)
        import random
        if isinstance(input_text, list):
            embeddings = [[random.uniform(-1, 1) for _ in range(384)] for _ in input_text]
        else:
            embeddings = [[random.uniform(-1, 1) for _ in range(384)]]
        
        response_data = {
            "model": model,
            "embeddings": embeddings,
            "total_duration": 1000000,
            "load_duration": 100000,
            "prompt_eval_count": len(str(input_text)) // 4
        }
        self._send_json_response(response_data)

    def _handle_ollama_copy(self, data):
        """Handle Ollama /api/copy endpoint - copy a model.
        
        Since AIRunner manages models differently, we just return success.
        """
        self._send_json_response({"status": "success"})

    def _handle_ollama_create(self, data):
        """Handle Ollama /api/create endpoint - create a model.
        
        Since AIRunner manages models differently, we simulate success.
        """
        model = data.get("model", "custom:latest")
        stream = data.get("stream", True)
        
        if stream:
            self._set_headers(200, content_type="application/x-ndjson")
            responses = [
                {"status": "reading model metadata"},
                {"status": "creating system layer"},
                {"status": "writing manifest"},
                {"status": "success"}
            ]
            for resp in responses:
                self.wfile.write(json.dumps(resp).encode("utf-8") + b"\n")
                self.wfile.flush()
        else:
            self._send_json_response({"status": "success"})

    # =========================================================================
    # End of Ollama-Compatible API Endpoints
    # =========================================================================

    # =========================================================================
    # OpenAI-Compatible API Endpoints (for VS Code Copilot BYOK)
    # =========================================================================

    def _handle_openai_models(self, data):
        """Handle OpenAI /v1/models endpoint - list available models."""
        models_data = {
            "object": "list",
            "data": [
                {
                    "id": "airunner",
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": "airunner",
                    "permission": [],
                    "root": "airunner",
                    "parent": None,
                }
            ]
        }
        self._send_json_response(models_data)

    def _handle_openai_chat_completions(self, data):
        """Handle OpenAI /v1/chat/completions endpoint with tool calling support.
        
        Request format:
        {
            "model": "airunner",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Hello!"}
            ],
            "stream": true,
            "temperature": 0.7,
            "max_tokens": 2048,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather",
                        "parameters": {...}
                    }
                }
            ],
            "tool_choice": "auto"
        }
        
        Response with tool calls:
        {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": null,
                    "tool_calls": [{
                        "id": "call_xxx",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": "{\"city\": \"Tokyo\"}"
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }]
        }
        
        Automatically loads the model if not already loaded.
        """
        # Ensure model is loaded (auto-load if needed)
        success, error_msg = self._ensure_llm_model_loaded()
        if not success:
            self._send_json_response({
                "error": {
                    "message": error_msg,
                    "type": "service_unavailable",
                    "hint": "Start with --model flag or configure model in AIRunner GUI"
                }
            }, status=503)
            return
        
        messages = data.get("messages", [])
        model = data.get("model", "airunner")
        stream = data.get("stream", False)
        temperature = data.get("temperature", 0.7)
        max_tokens = data.get("max_tokens", 2048)
        tools = data.get("tools", [])
        tool_choice = data.get("tool_choice", "auto")
        
        if not messages:
            self._send_json_response({
                "error": {
                    "message": "messages is required",
                    "type": "invalid_request_error"
                }
            }, status=400)
            return
        
        # Extract system prompt and find the last user message
        # The client sends the full conversation history
        system_prompt = ""
        last_user_content = ""
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_prompt = content
            elif role == "user":
                # Keep tracking the latest user message
                last_user_content = content
        
        # Use just the last user message as the prompt
        # The LLMModelManager/WorkflowManager handles conversation history internally
        prompt = last_user_content
        
        self.logger.info(f"[OpenAI API] Extracted prompt: {prompt[:100]}...")
        if system_prompt:
            self.logger.info(f"[OpenAI API] System prompt: {system_prompt[:100]}...")
        
        # Enhance system prompt with tool definitions if tools are provided
        if tools:
            tool_descriptions = self._format_tools_for_prompt(tools)
            enhanced_system = system_prompt or ""
            if enhanced_system:
                enhanced_system += "\n\n"
            enhanced_system += tool_descriptions
            system_prompt = enhanced_system
        
        llm_request = LLMRequest()
        llm_request.temperature = temperature
        llm_request.max_new_tokens = max_tokens
        if system_prompt:
            llm_request.system_prompt = system_prompt
        
        # For API requests, don't use conversation memory
        # The client manages its own history and sends it with each request
        llm_request.use_memory = False
        
        # Handle tools - if tools provided, enable them; otherwise disable all tools
        if tools:
            llm_request.tool_categories = None  # Enable all tools when tools are provided
            self.logger.info(f"[OpenAI API] Tools provided, enabling tool categories")
        else:
            # Explicitly disable tools for simple chat requests
            llm_request.tool_categories = []  # Empty list = no tools
            self.logger.info("[OpenAI API] No tools provided, disabling all tools")
        
        request_id = str(uuid.uuid4())
        
        if stream:
            self._handle_openai_chat_stream(prompt, model, llm_request, request_id, tools)
        else:
            self._handle_openai_chat_non_stream(prompt, model, llm_request, request_id, tools)

    def _format_tools_for_prompt(self, tools):
        """Format OpenAI tool definitions into a prompt-friendly format.
        
        This converts OpenAI-style tool definitions into instructions
        that help the LLM understand available tools.
        """
        if not tools:
            return ""
        
        lines = ["You have access to the following tools:"]
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                name = func.get("name", "")
                desc = func.get("description", "")
                params = func.get("parameters", {})
                
                lines.append(f"\n**{name}**: {desc}")
                if params.get("properties"):
                    lines.append("  Parameters:")
                    for param_name, param_info in params["properties"].items():
                        param_type = param_info.get("type", "any")
                        param_desc = param_info.get("description", "")
                        required = param_name in params.get("required", [])
                        req_str = " (required)" if required else " (optional)"
                        lines.append(f"    - {param_name}: {param_type}{req_str} - {param_desc}")
        
        lines.append("\nTo use a tool, respond with a JSON object in this format:")
        lines.append('{"tool_call": {"name": "tool_name", "arguments": {"arg1": "value1"}}}')
        lines.append("\nOnly use a tool if it's necessary to answer the user's question.")
        
        return "\n".join(lines)

    def _parse_tool_calls_from_response(self, response_text, tools):
        """Parse tool calls from LLM response text.
        
        Looks for JSON tool call patterns in the response and extracts them.
        Returns (content, tool_calls) tuple.
        """
        import re
        
        if not tools or not response_text:
            return response_text, []
        
        # Try to find JSON tool call pattern
        tool_call_pattern = r'\{[\s]*"tool_call"[\s]*:[\s]*\{[^}]+\}[\s]*\}'
        matches = re.findall(tool_call_pattern, response_text, re.DOTALL)
        
        tool_calls = []
        for i, match in enumerate(matches):
            try:
                parsed = json.loads(match)
                if "tool_call" in parsed:
                    tc = parsed["tool_call"]
                    tool_calls.append({
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": json.dumps(tc.get("arguments", {}))
                        }
                    })
            except json.JSONDecodeError:
                continue
        
        if tool_calls:
            # Remove tool call JSON from response content
            content = re.sub(tool_call_pattern, "", response_text).strip()
            return content if content else None, tool_calls
        
        return response_text, []

    def _handle_openai_chat_stream(self, prompt, model, llm_request, request_id, tools=None):
        """Handle streaming OpenAI chat response (SSE format).
        
        Note: Tool calls in streaming mode are complex. For now, we accumulate
        the full response and check for tool calls at the end.
        """
        self._set_headers(200, content_type="text/event-stream")
        
        complete_event = threading.Event()
        start_time = time.time()
        accumulated_response = []
        
        def stream_callback(data: dict):
            response = data.get("response")
            if response:
                chunk_id = f"chatcmpl-{request_id[:8]}"
                created = int(time.time())
                
                # Accumulate response for tool call detection
                accumulated_response.append(response.message)
                
                if response.is_end_of_message:
                    # Check for tool calls in accumulated response
                    full_text = "".join(accumulated_response)
                    content, tool_calls = self._parse_tool_calls_from_response(full_text, tools)
                    
                    if tool_calls:
                        # Send tool call chunk
                        chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {
                                    "tool_calls": tool_calls
                                },
                                "finish_reason": "tool_calls"
                            }]
                        }
                        self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
                    else:
                        # Send final chunk with finish_reason
                        chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop"
                            }]
                        }
                        self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
                    
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                    complete_event.set()
                else:
                    # Send content chunk
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": response.message},
                            "finish_reason": None
                        }]
                    }
                    self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
                    self.wfile.flush()
        
        api = get_api()
        if not api:
            error_chunk = {"error": {"message": "API not initialized"}}
            self.wfile.write(f"data: {json.dumps(error_chunk)}\n\n".encode("utf-8"))
            return
        
        try:
            api.llm.send_request(
                prompt=prompt,
                action=LLMActionType.CHAT,
                llm_request=llm_request,
                request_id=request_id,
                callback=stream_callback,
            )
            
            if not complete_event.wait(timeout=300):
                error_chunk = {"error": {"message": "Request timeout"}}
                self.wfile.write(f"data: {json.dumps(error_chunk)}\n\n".encode("utf-8"))
                
        except Exception as e:
            self.logger.error(f"OpenAI chat stream error: {e}", exc_info=True)
            error_chunk = {"error": {"message": str(e)}}
            self.wfile.write(f"data: {json.dumps(error_chunk)}\n\n".encode("utf-8"))
        
        # Close connection to signal end of stream
        self.close_connection = True

    def _handle_openai_chat_non_stream(self, prompt, model, llm_request, request_id, tools=None):
        """Handle non-streaming OpenAI chat response with tool calling support."""
        complete_event = threading.Event()
        complete_message = []
        start_time = time.time()
        
        def collect_callback(data: dict):
            response = data.get("response")
            if response:
                complete_message.append(response.message)
                if response.is_end_of_message:
                    complete_event.set()
        
        api = get_api()
        if not api:
            self._send_json_response({
                "error": {"message": "API not initialized"}
            }, status=500)
            return
        
        try:
            api.llm.send_request(
                prompt=prompt,
                action=LLMActionType.CHAT,
                llm_request=llm_request,
                request_id=request_id,
                callback=collect_callback,
            )
            
            if complete_event.wait(timeout=300):
                full_response = "".join(complete_message)
                created = int(time.time())
                
                # Check for tool calls in response
                content, tool_calls = self._parse_tool_calls_from_response(full_response, tools)
                
                if tool_calls:
                    # Response with tool calls
                    response_data = {
                        "id": f"chatcmpl-{request_id[:8]}",
                        "object": "chat.completion",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": content,
                                "tool_calls": tool_calls
                            },
                            "finish_reason": "tool_calls"
                        }],
                        "usage": {
                            "prompt_tokens": len(prompt) // 4,
                            "completion_tokens": len(full_response) // 4,
                            "total_tokens": (len(prompt) + len(full_response)) // 4
                        }
                    }
                else:
                    # Regular response without tool calls
                    response_data = {
                        "id": f"chatcmpl-{request_id[:8]}",
                        "object": "chat.completion",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": full_response
                            },
                            "finish_reason": "stop"
                        }],
                        "usage": {
                            "prompt_tokens": len(prompt) // 4,
                            "completion_tokens": len(full_response) // 4,
                            "total_tokens": (len(prompt) + len(full_response)) // 4
                        }
                    }
                self._send_json_response(response_data)
            else:
                self._send_json_response({
                    "error": {"message": "Request timeout"}
                }, status=504)
                
        except Exception as e:
            self.logger.error(f"OpenAI chat error: {e}", exc_info=True)
            self._send_json_response({
                "error": {"message": str(e)}
            }, status=500)

    # =========================================================================
    # End of OpenAI-Compatible API Endpoints
    # =========================================================================

    def _extract_llm_request_data(self, data: Dict) -> Dict:
        """Extract and normalize llm_request data from request.

        Args:
            data: Request data dictionary

        Returns:
            Normalized llm_request dictionary
        """
        llm_request_raw = data.get("llm_request", {})
        return llm_request_raw if isinstance(llm_request_raw, dict) else {}

    def _map_top_level_params(self, data: Dict, llm_request_data: Dict):
        """Map top-level parameters to llm_request fields."""
        param_mapping = {
            "temperature": "temperature",
            "max_tokens": "max_new_tokens",
            "top_p": "top_p",
            "top_k": "top_k",
            "repetition_penalty": "repetition_penalty",
            "use_memory": "use_memory",
            "tool_categories": "tool_categories",
            # Legacy flag from external clients (e.g., uwuchat) to enable
            # AI Runner's built-in tools. When True, we set tool_categories
            # to None so the tool classifier can pick the right categories.
            # When False, we disable tools by setting an empty list.
            "use_airunner_tools": "tool_categories",
            "model": "model",
            "rag_files": "rag_files",
            # Mode-based routing / override options
            "use_mode_routing": "use_mode_routing",
            "mode_override": "mode_override",
        }
        excluded = {
            "prompt",
            "system_prompt",
            "action",
            "stream",
            "llm_request",
        }
        for client_param, llm_param in param_mapping.items():
            if client_param in data and client_param not in excluded:
                value = data[client_param]

                if client_param == "use_airunner_tools":
                    # Map boolean flag to tool_categories behaviour.
                    # True  -> None (auto-classify/select tools)
                    # False -> []   (disable tools)
                    if value is True:
                        llm_request_data[llm_param] = None
                    elif value is False:
                        llm_request_data[llm_param] = []
                    # If a non-boolean slips through, fall back to raw value
                    # to preserve caller intent.
                    else:
                        llm_request_data[llm_param] = value
                else:
                    llm_request_data[llm_param] = value

        # If the client did not send any tool configuration at all, default to
        # auto tool selection (None) instead of disabling tools (empty list).
        # Many external clients omit tool_categories when they actually want
        # AI Runner's built-in tools. This keeps legacy callers working while
        # still honoring explicit empty lists to disable tools.
        if "tool_categories" not in llm_request_data and "tools" not in data:
            llm_request_data["tool_categories"] = None

    def _parse_action_type(self, action_str: str) -> LLMActionType:
        """Parse action string to LLMActionType enum.

        Args:
            action_str: Action string from request

        Returns:
            LLMActionType enum value
        """
        try:
            return (
                LLMActionType[action_str]
                if isinstance(action_str, str)
                else action_str
            )
        except KeyError:
            return LLMActionType.CHAT

    def _handle_llm(self, data):
        """Handle LLM generation request with streaming support.
        
        Automatically loads the model if not already loaded.
        """
        print("HANDLE LLM CALLED")
        print("data", data)
        
        # Ensure model is loaded (auto-load if needed)
        success, error_msg = self._ensure_llm_model_loaded()
        if not success:
            self._send_json_response({
                "error": "Model not available",
                "details": error_msg,
                "hint": "Start with --model flag or configure model in AIRunner GUI"
            }, status=503)
            return
        
        prompt = data.get("prompt")
        if not prompt:
            self._send_json_response({"error": "Missing 'prompt' field"}, status=400)
            return

        system_prompt = data.get("system_prompt")
        action = self._parse_action_type(data.get("action", "CHAT"))
        stream = data.get("stream", True)
        llm_request_data = self._extract_llm_request_data(data)
        self._map_top_level_params(data, llm_request_data)
        llm_request = self._create_llm_request(llm_request_data)
        if system_prompt:
            llm_request.system_prompt = system_prompt
        request_id = str(uuid.uuid4())
        if stream:
            self._handle_llm_stream(prompt, action, llm_request, request_id)
        else:
            self._handle_llm_non_stream(
                prompt, action, llm_request, request_id
            )

    def _create_llm_request(self, params: Dict) -> LLMRequest:
        """Create LLMRequest from dictionary parameters.

        Args:
            params: Dictionary of LLM parameters

        Returns:
            LLMRequest object with specified or default parameters
        """
        llm_request = LLMRequest()
        self.logger.debug(f"Creating LLMRequest from params: {params}")
        for key, value in params.items():
            if hasattr(llm_request, key):
                setattr(llm_request, key, value)
                self.logger.debug(f"Set LLMRequest.{key} = {value}")
            else:
                self.logger.warning(
                    f"Ignoring unknown LLMRequest parameter: {key}={value}"
                )
        return llm_request

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
                    "tools": getattr(response, "tools", None),
                }
                try:
                    self.logger.debug(
                        f"HTTP Server: stream_callback invoked: msg_len={len(response.message) if response and response.message else 0}, is_end={response.is_end_of_message}, seq={getattr(response, 'sequence_number', None)}"
                    )
                except Exception:
                    pass
                self.wfile.write(
                    json.dumps(response_data).encode("utf-8") + b"\n"
                )
                self.wfile.flush()

                if response.is_end_of_message:
                    complete_event.set()

        # Send LLM request with request_id and callback
        api = get_api()
        self.logger.debug(
            f"Sending to API with llm_request.max_new_tokens={llm_request.max_new_tokens}"
        )
        import inspect

        self.logger.info(
            f"HTTP Server: send_request file: {inspect.getfile(api.llm.send_request)}"
        )
        self.logger.info(
            f"HTTP Server: About to call api.llm.send_request, api type={type(api)}, api.llm type={type(api.llm)}"
        )
        try:
            api.llm.send_request(
                prompt=prompt,
                action=action,
                llm_request=llm_request,
                request_id=request_id,
                callback=stream_callback,
            )
            self.logger.debug(
                "HTTP Server: send_request returned (non-blocking)"
            )
            self.logger.info(
                "HTTP Server: api.llm.send_request completed successfully"
            )
        except Exception as e:
            self.logger.error(
                f"HTTP Server: Exception calling send_request: {e}",
                exc_info=True,
            )
            # Immediately return error NDJSON to HTTP client - avoids long timeout
            try:
                error_response = {
                    "message": f"Error invoking LLM: {str(e)}",
                    "is_first_message": True,
                    "is_end_of_message": True,
                    "sequence_number": 0,
                    "error": True,
                }
                self.wfile.write(
                    json.dumps(error_response).encode("utf-8") + b"\n"
                )
                self.wfile.flush()
            except Exception:
                pass
            return

        # Wait for completion (with timeout)
        self.logger.debug(
            f"HTTP Server: Waiting for completion event with timeout {self._timeout}s (request_id={request_id})"
        )
        if not complete_event.wait(
            timeout=self._timeout
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
        else:
            self.logger.debug(
                f"HTTP Server: complete_event set for request_id={request_id}"
            )
        
        # Close connection to signal end of stream
        self.close_connection = True

    def _handle_llm_non_stream(
        self,
        prompt: str,
        action: LLMActionType,
        llm_request: LLMRequest,
        request_id: str,
    ):
        """Handle non-streaming LLM response as single JSON object."""
        self.logger.debug(
            f"_handle_llm_non_stream ENTERED with request_id={request_id}"
        )

        # Collect all response chunks
        complete_message = []
        executed_tools = []  # Track tools executed
        complete_event = threading.Event()

        def collect_callback(data: dict):
            """Callback to collect response chunks."""
            self.logger.debug(
                f"HTTP Callback {id(collect_callback)} CALLED with data keys: {list(data.keys())}"
            )
            response = data.get("response")
            self.logger.debug(
                f"HTTP Callback Response type: {type(response)}, is_end: {response.is_end_of_message if response else None}"
            )
            self.logger.info(
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
                    self.logger.info(
                        f"HTTP Callback Tools found in response: {response.tools}"
                    )
                    executed_tools.extend(response.tools)
                elif response.is_end_of_message:
                    self.logger.warning(
                        f"HTTP Callback End of message but no tools. has_tools_attr={hasattr(response, 'tools')}, tools_value={getattr(response, 'tools', None)}"
                    )
                self.logger.debug(
                    f"HTTP Callback Complete message so far: {len(complete_message)} chunks"
                )
                if response.is_end_of_message:
                    self.logger.debug(
                        f"HTTP Callback END OF MESSAGE - setting event {id(complete_event)}"
                    )
                    self.logger.info(
                        "HTTP Callback End of message detected, setting event"
                    )
                    complete_event.set()
                    self.logger.debug(
                        f"HTTP Callback Event set: {complete_event.is_set()}"
                    )
                else:
                    self.logger.debug(
                        "HTTP Callback Not end yet, waiting for more..."
                    )

        self.logger.debug(
            f"HTTP Server Registering callback {id(collect_callback)} for request {request_id}"
        )
        self.logger.debug(f"HTTP Server Event object: {id(complete_event)}")

        # Send LLM request with request_id and callback
        self.logger.debug("HTTP Server About to call api.llm.send_request...")
        api = get_api()
        api.llm.send_request(
            prompt=prompt,
            action=action,
            llm_request=llm_request,
            request_id=request_id,
            callback=collect_callback,
        )
        self.logger.debug("HTTP Server api.llm.send_request completed")

        self.logger.debug(
            f"HTTP Server Waiting for event {id(complete_event)} with {self._timeout}s timeout..."
        )

        # Wait for completion (with timeout)
        if complete_event.wait(
            timeout=self._timeout
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

        self._send_json_response(response_data)

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
            self._send_json_response(
                {"error": "Missing or invalid 'prompts' field"},
                status=400
            )
            return

        system_prompt = data.get("system_prompt")
        action_str = data.get("action", "CHAT")
        is_async = data.get("async", False)

        # Ensure llm_request_data is always a dict, not a string
        llm_request_raw = data.get("llm_request", {})
        llm_request_data = (
            llm_request_raw if isinstance(llm_request_raw, dict) else {}
        )

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
            if complete_event.wait(timeout=self._timeout):
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

        self._send_json_response(response_data)

    def _handle_art(self, data):
        """Handle art/Stable Diffusion generation request.
        
        Request format:
        {
            "prompt": "A beautiful sunset over mountains",
            "negative_prompt": "blurry, low quality",
            "width": 1024,
            "height": 1024,
            "steps": 20,
            "seed": 42,
            "scale": 7.5,
            ...
        }
        
        Response format:
        {
            "images": ["base64_encoded_image_1", "base64_encoded_image_2", ...],
            "metadata": {...},
            "seed": 42
        }
        
        Automatically loads the model if not already loaded.
        """
        # Ensure model is loaded (auto-load if needed)
        success, error_msg = self._ensure_art_model_loaded()
        if not success:
            self._send_json_response({
                "error": "Art model not available",
                "details": error_msg,
                "hint": "Start with --enable-art --art-model flag or configure in AIRunner GUI"
            }, status=503)
            return
        
        # Validate prompt
        prompt = data.get("prompt", "")
        if not prompt:
            self._send_json_response({"error": "Missing 'prompt' field"}, status=400)
            return
        
        # Set up threading event and result holder
        complete_event = threading.Event()
        result_holder = {"response": None, "error": None}
        
        def on_complete(response):
            """Callback when image generation completes."""
            self.logger.info(f"Art generation callback received: {type(response)}")
            if isinstance(response, ImageResponse):
                result_holder["response"] = response
            elif isinstance(response, str):
                # Error message
                result_holder["error"] = response
            else:
                result_holder["response"] = response
            complete_event.set()
        
        # Create ImageRequest from data with callback
        image_request = self._create_image_request(data)
        image_request.callback = on_complete
        
        # Get API
        api = get_api()
        if not api:
            self._send_json_response({"error": "API not initialized"}, status=500)
            return
        
        # Emit the generation signal
        self.logger.info(f"Sending art generation request: prompt='{prompt[:50]}...'")
        api.emit_signal(SignalCode.DO_GENERATE_SIGNAL, {"image_request": image_request})
        
        # Wait for completion (timeout: 5 minutes for image generation)
        if complete_event.wait(timeout=300):
            if result_holder["error"]:
                self._send_json_response({
                    "error": result_holder["error"]
                }, status=500)
            elif result_holder["response"]:
                response = result_holder["response"]
                response_data = self._format_art_response(response)
                self._send_json_response(response_data)
            else:
                self._send_json_response({
                    "error": "No response received"
                }, status=500)
        else:
            self._send_json_response({
                "error": "Image generation timeout",
                "hint": "Generation took longer than 5 minutes"
            }, status=504)
    
    def _create_image_request(self, data: dict) -> ImageRequest:
        """Create an ImageRequest from HTTP request data.
        
        Args:
            data: Dictionary of request parameters
            
        Returns:
            ImageRequest object with specified parameters
        """
        from airunner.enums import GeneratorSection
        
        # Map HTTP request fields to ImageRequest fields
        image_request = ImageRequest(
            prompt=data.get("prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            second_prompt=data.get("second_prompt", ""),
            second_negative_prompt=data.get("second_negative_prompt", ""),
            width=data.get("width", 1024),
            height=data.get("height", 1024),
            steps=data.get("steps", 20),
            seed=data.get("seed", 42),
            scale=data.get("scale", 7.5),
            random_seed=data.get("random_seed", True),
            n_samples=data.get("n_samples", 1),
            images_per_batch=data.get("images_per_batch", 1),
            generator_section=GeneratorSection.TXT2IMG,
            pipeline_action="txt2img",
        )
        
        # Handle model path if specified
        model_path = data.get("model_path") or os.environ.get("AIRUNNER_ART_MODEL_PATH")
        if model_path:
            image_request.model_path = model_path
        
        return image_request
    
    def _format_art_response(self, response) -> dict:
        """Format ImageResponse for HTTP response.
        
        Converts PIL images to base64 encoded strings.
        
        Args:
            response: ImageResponse object or dict containing images
            
        Returns:
            Dictionary suitable for JSON response
        """
        images_base64 = []
        metadata = {}
        seed = None
        
        # Handle ImageResponse object
        if isinstance(response, ImageResponse):
            images = response.images or []
            metadata = response.data or {}
            
            # Extract seed from metadata if available
            image_request = metadata.get("image_request")
            if image_request and hasattr(image_request, "seed"):
                seed = image_request.seed
        elif isinstance(response, dict):
            # Handle dict response
            images = response.get("images", [])
            metadata = response.get("data", {})
            seed = metadata.get("seed")
        else:
            images = []
        
        # Convert PIL images to base64
        for img in images:
            if img is not None:
                try:
                    # Save PIL image to bytes buffer as PNG
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    buffer.seek(0)
                    
                    # Encode to base64
                    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    images_base64.append(img_base64)
                except Exception as e:
                    self.logger.error(f"Failed to encode image: {e}")
        
        return {
            "images": images_base64,
            "metadata": {
                "width": metadata.get("width"),
                "height": metadata.get("height"),
                "steps": metadata.get("steps"),
                "prompt": metadata.get("prompt"),
            } if metadata else {},
            "seed": seed,
            "count": len(images_base64),
        }

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
            self.logger.info(f"TTS request: '{text[:50]}...'")
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
                self.logger.info(f"STT transcription received: '{transcription[:50]}...'")
                result_holder["transcription"] = transcription
                complete_event.set()
            
            # Register for transcription response
            from airunner.utils.application.signal_mediator import SignalMediator
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
                # Clear calendar events
                event_count = session.query(Event).delete()
                deleted_counts["events"] = event_count
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
