"""API Bridge — typed facade over GuiDaemonClient for the GUI layer.

Provides high-level, signal-aware methods for all model execution
operations. Every GUI interaction with the backend should go through
this bridge, replacing direct in-process worker dispatch.

The bridge translates between the GUI's data types (dict-based signals,
ImageRequest objects) and the daemon client's HTTP API calls, emitting
Qt signals for progress and completion events.
"""

from __future__ import annotations

import base64
import io
import threading
from typing import Any, Callable, Dict, Optional

from airunner.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class APIBridgeError(RuntimeError):
    """Error raised when the API bridge cannot complete a request."""


class APIBridge:
    """High-level GUI facade over the daemon HTTP client.

    All methods that produce observable results emit the appropriate
    SignalCode so GUI widgets can react without knowing about HTTP.
    """

    def __init__(
        self,
        daemon_client: GuiDaemonClient,
        *,
        signal_emitter: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
    ) -> None:
        """Initialize the bridge.

        Args:
            daemon_client: The daemon HTTP client instance.
            signal_emitter: Callable that emits (SignalCode, data_dict).
                When None, signals are not emitted (headless mode).
        """
        self._client = daemon_client
        self._emit = signal_emitter or self._noop_emitter
        self._logger = logger

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """Return True when the daemon is reachable."""
        try:
            return self._client.is_available()
        except Exception:
            return False

    def ensure_connected(self) -> bool:
        """Ensure the daemon is connected."""
        return self._client.is_available()

    # ------------------------------------------------------------------
    # Art generation
    # ------------------------------------------------------------------

    def generate_image(
        self,
        *,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg_scale: float = 7.5,
        seed: Optional[int] = None,
        num_images: int = 1,
        model: Optional[str] = None,
        version: Optional[str] = None,
        scheduler: Optional[str] = None,
        pipeline: Optional[str] = None,
        strength: Optional[float] = None,
        image_b64: Optional[str] = None,
        skip_auto_export: bool = False,
    ) -> Dict[str, Any]:
        """Submit an art generation request synchronously.

        Returns the job response with a job_id for polling.
        """
        return self._client.start_art_generation(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            seed=seed,
            num_images=num_images,
            model=model,
            version=version,
            scheduler=scheduler,
            pipeline=pipeline,
            strength=strength,
            image_b64=image_b64,
            skip_auto_export=skip_auto_export,
        )

    def generate_image_async(self, data: Dict[str, Any]) -> None:
        """Submit an art generation request in a background thread.

        Extracts parameters from the legacy signal data dict and polls
        for completion, emitting IMAGE_GENERATED_SIGNAL on success.
        """
        image_request = data.get("image_request")
        if image_request is None:
            self._emit(
                SignalCode.SD_GENERATE_IMAGE_SIGNAL,
                {"error": "No image_request in signal data"},
            )
            return

        def _worker() -> None:
            try:
                # Build parameters from the ImageRequest object or dict
                params = self._extract_image_params(data, image_request)
                response = self._client.start_art_generation(**params)
                job_id = response.get("job_id", "")
                if not job_id:
                    raise APIBridgeError(
                        f"No job_id in response: {response}"
                    )

                png_bytes = self._client.wait_art_job(
                    job_id,
                    timeout_seconds=1800.0,
                    progress_callback=lambda s: self._emit_progress(s),
                )

                images = self._decode_images(png_bytes)
                self._emit(
                    SignalCode.SD_GENERATE_IMAGE_SIGNAL,
                    {"images": images, "job_id": job_id},
                )
            except Exception as exc:
                self._logger.error(
                    "Art generation failed: %s", exc, exc_info=True
                )
                self._emit(
                    SignalCode.SD_GENERATE_IMAGE_SIGNAL,
                    {"error": str(exc)},
                )

        thread = threading.Thread(
            target=_worker,
            name="airunner-api-art-generate",
            daemon=True,
        )
        thread.start()

    def cancel_generation(self, job_id: str) -> None:
        """Cancel an active art generation job."""
        try:
            self._client.cancel_art_job(job_id)
        except Exception as exc:
            self._logger.warning("Failed to cancel art job %s: %s", job_id, exc)

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    def chat_completion(
        self,
        messages: list[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Send a chat completion request (non-streaming)."""
        # The LLM route uses a POST /api/v1/llm/chat/completions endpoint.
        # Delegate through the daemon client's internal request method
        # for a clean API surface.
        response = self._client._request(
            "POST",
            "/api/v1/llm/chat/completions",
            json_payload={
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
            },
            timeout_seconds=300.0,
        )
        return response.json()

    def interrupt_llm(self) -> None:
        """Interrupt the active daemon-side LLM request."""
        self._client.interrupt_llm()

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------

    def synthesize_tts(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: float = 1.0,
        model: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> bytes:
        """Synthesize speech and return audio bytes."""
        return self._client.synthesize_tts(
            text=text,
            voice=voice,
            speed=speed,
            model=model,
            model_type=model_type,
        )

    # ------------------------------------------------------------------
    # STT
    # ------------------------------------------------------------------

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        *,
        mime_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        """Transcribe audio bytes to text."""
        return self._client.transcribe_audio(
            audio_bytes,
            mime_type=mime_type,
        )

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def load_model(
        self,
        runtime_name: str,
        *,
        deployment_mode: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Load a model runtime through the daemon."""
        return self._client.load_runtime(
            runtime_name,
            deployment_mode=deployment_mode,
            metadata=metadata,
        )

    def unload_model(
        self,
        runtime_name: str,
        *,
        deployment_mode: str = "default",
    ) -> Dict[str, Any]:
        """Unload a model runtime through the daemon."""
        return self._client.unload_runtime(
            runtime_name,
            deployment_mode=deployment_mode,
        )

    def model_status(
        self,
        runtime_name: str,
        *,
        provider: str = "local",
        deployment_mode: str = "default",
    ) -> Dict[str, Any]:
        """Query the status of a daemon runtime."""
        return self._client.runtime_status(
            runtime_name,
            provider=provider,
            deployment_mode=deployment_mode,
        )

    # ------------------------------------------------------------------
    # Downloads
    # ------------------------------------------------------------------

    def download_model(
        self,
        repo_id: str,
        *,
        model_type: str = "art",
        output_dir: str = "",
    ) -> Dict[str, Any]:
        """Initiate a model download through the daemon."""
        response = self._client._request(
            "POST",
            "/api/v1/downloads/start",
            json_payload={
                "repo_id": repo_id,
                "model_type": model_type,
                "output_dir": output_dir,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _noop_emitter(code: Any, data: Dict[str, Any]) -> None:
        """No-op signal emitter for headless mode."""

    @staticmethod
    def _extract_image_params(
        data: Dict[str, Any],
        image_request: Any,
    ) -> Dict[str, Any]:
        """Extract generation parameters from a signal data dict."""
        # Handle both ImageRequest objects and plain dicts
        if isinstance(image_request, dict):
            req = image_request
        else:
            req = {
                "prompt": getattr(image_request, "prompt", ""),
                "negative_prompt": getattr(image_request, "negative_prompt", ""),
                "width": getattr(image_request, "width", 1024),
                "height": getattr(image_request, "height", 1024),
                "steps": getattr(image_request, "steps", 20),
                "cfg_scale": getattr(image_request, "scale", 7.5),
                "seed": getattr(image_request, "seed", None),
                "num_images": getattr(image_request, "n_samples", 1),
                "model": getattr(image_request, "model_path", None),
                "version": getattr(image_request, "version", None),
                "scheduler": getattr(image_request, "scheduler", None),
                "pipeline": getattr(image_request, "pipeline_action", None),
                "strength": getattr(image_request, "strength", None),
                "skip_auto_export": getattr(
                    image_request, "skip_auto_export", False
                ),
                "image_b64": data.get("image_b64"),
            }
        return {k: v for k, v in req.items() if v is not None}

    @staticmethod
    def _decode_images(png_bytes: bytes) -> list[Any]:
        """Decode PNG bytes from the daemon into PIL Image objects."""
        from PIL import Image

        # The daemon may return a single PNG or a ZIP of PNGs.
        # For now, try single image.
        try:
            image = Image.open(io.BytesIO(png_bytes))
            return [image.copy()]
        except Exception:
            return []

    def _emit_progress(self, status: Dict[str, Any]) -> None:
        """Emit art generation progress as a signal."""
        self._emit(SignalCode.SD_PROGRESS_SIGNAL, status)
