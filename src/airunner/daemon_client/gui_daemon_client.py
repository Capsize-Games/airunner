"""HTTP client used by the GUI to communicate with the daemon API.

The daemon process is managed externally (e.g. by ``scripts/run.sh``).
This client connects to an already-running daemon and provides typed
methods for all API operations, organised into domain mixins.

API bridge and signal adapter functionality is included directly so
that callers get a single ``GuiDaemonClient`` instead of three layers.
"""

from __future__ import annotations

import base64
import io
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from airunner.daemon_client.art_mixin import ArtClientMixin
from airunner.daemon_client.base import _DaemonClientBase
from airunner.daemon_client.downloads_mixin import DownloadsClientMixin
from airunner.daemon_client.llm_mixin import LLMClientMixin
from airunner.daemon_client.runtime_mixin import RuntimeClientMixin
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class APIBridgeError(RuntimeError):
    """Error raised when the API bridge cannot complete a request."""


class GuiDaemonClient(
    _DaemonClientBase,
    LLMClientMixin,
    ArtClientMixin,
    DownloadsClientMixin,
    RuntimeClientMixin,
):
    """HTTP client for the local daemon API with domain mixins,
    high-level convenience methods, and signal integration.

    The daemon is expected to already be running.  Use
    ``is_available()`` to check reachability before issuing requests.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        *,
        session=None,
        poll_interval_seconds: float = 0.25,
        request_timeout_seconds: float = 30.0,
        time_fn: Callable[[], float] = None,
        sleep: Callable[[float], None] = None,
        signal_emitter: Optional[
            Callable[[Any, Dict[str, Any]], None]
        ] = None,
    ) -> None:
        super().__init__(
            config_path=config_path,
            session=session,
            poll_interval_seconds=poll_interval_seconds,
            request_timeout_seconds=request_timeout_seconds,
            time_fn=time_fn,
            sleep=sleep,
        )
        self._emit = signal_emitter or self._noop_emitter
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    # ------------------------------------------------------------------
    # API bridge convenience methods
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """Return True when the daemon is reachable."""
        try:
            return self.is_available()
        except Exception:
            return False

    def ensure_connected(self) -> bool:
        """Ensure the daemon is connected."""
        return self.is_available()

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
        """Submit an art generation request synchronously."""
        return self.start_art_generation(
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
        """Submit an art generation request in a background thread."""
        image_request = data.get("image_request")
        if image_request is None:
            self._emit(
                SignalCode.SD_GENERATE_IMAGE_SIGNAL,
                {"error": "No image_request in signal data"},
            )
            return

        def _worker() -> None:
            try:
                params = self._extract_image_params(data, image_request)
                response = self.start_art_generation(**params)
                job_id = response.get("job_id", "")
                if not job_id:
                    raise APIBridgeError(
                        f"No job_id in response: {response}"
                    )

                png_bytes = self.wait_art_job(
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
                self.logger.error(
                    "Art generation failed: %s", exc, exc_info=True,
                )
                self._emit(
                    SignalCode.SD_GENERATE_IMAGE_SIGNAL,
                    {"error": str(exc)},
                )

        thread = threading.Thread(
            target=_worker,
            name="airunner-daemon-art-generate",
            daemon=True,
        )
        thread.start()

    def cancel_generation(self, job_id: str) -> None:
        """Cancel an active art generation job."""
        try:
            self.cancel_art_job(job_id)
        except Exception as exc:
            self.logger.warning(
                "Failed to cancel art job %s: %s", job_id, exc,
            )

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
        response = self._request(
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

    def download_model(
        self,
        repo_id: str,
        *,
        model_type: str = "art",
        output_dir: str = "",
    ) -> Dict[str, Any]:
        """Initiate a model download through the daemon."""
        response = self._request(
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
    # Signal adapter handlers
    # ------------------------------------------------------------------

    @property
    def signal_handlers(
        self,
    ) -> Dict[Any, Callable[[Dict[str, Any]], None]]:
        """Return the signal-to-API handler mapping."""
        return {
            SignalCode.DO_GENERATE_SIGNAL: self._on_do_generate,
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL: (
                self._on_llm_request
            ),
            SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL: (
                self._on_stt_transcribe
            ),
            SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL: (
                self._on_interrupt_image_generation
            ),
            SignalCode.INTERRUPT_PROCESS_SIGNAL: (
                self._on_interrupt_process
            ),
            SignalCode.SD_LOAD_SIGNAL: self._on_load_art,
            SignalCode.SD_UNLOAD_SIGNAL: self._on_unload_art,
            SignalCode.LLM_LOAD_SIGNAL: self._on_llm_load,
            SignalCode.LLM_UNLOAD_SIGNAL: self._on_llm_unload,
            SignalCode.STT_LOAD_SIGNAL: self._on_stt_load,
            SignalCode.STT_UNLOAD_SIGNAL: self._on_stt_unload,
        }

    # ------------------------------------------------------------------
    # Private bridge helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _noop_emitter(code: Any, data: Dict[str, Any]) -> None:
        """No-op signal emitter."""

    @staticmethod
    def _extract_image_params(
        data: Dict[str, Any],
        image_request: Any,
    ) -> Dict[str, Any]:
        """Extract generation parameters from a signal data dict."""
        if isinstance(image_request, dict):
            req = image_request
        else:
            req = {
                "prompt": getattr(image_request, "prompt", ""),
                "negative_prompt": getattr(
                    image_request, "negative_prompt", "",
                ),
                "width": getattr(image_request, "width", 1024),
                "height": getattr(image_request, "height", 1024),
                "steps": getattr(image_request, "steps", 20),
                "cfg_scale": getattr(image_request, "scale", 7.5),
                "seed": getattr(image_request, "seed", None),
                "num_images": getattr(image_request, "n_samples", 1),
                "model": getattr(image_request, "model_path", None),
                "version": getattr(image_request, "version", None),
                "scheduler": getattr(image_request, "scheduler", None),
                "pipeline": getattr(
                    image_request, "pipeline_action", None,
                ),
                "strength": getattr(image_request, "strength", None),
                "skip_auto_export": getattr(
                    image_request, "skip_auto_export", False,
                ),
                "image_b64": data.get("image_b64"),
            }
        return {k: v for k, v in req.items() if v is not None}

    @staticmethod
    def _decode_images(png_bytes: bytes) -> list[Any]:
        """Decode PNG bytes from the daemon into PIL Image objects."""
        from PIL import Image

        try:
            image = Image.open(io.BytesIO(png_bytes))
            return [image.copy()]
        except Exception:
            return []

    def _emit_progress(self, status: Dict[str, Any]) -> None:
        """Emit art generation progress as a signal."""
        self._emit(SignalCode.SD_PROGRESS_SIGNAL, status)

    # ------------------------------------------------------------------
    # Private signal adapter handlers
    # ------------------------------------------------------------------

    def _on_do_generate(self, data: Dict[str, Any]) -> None:
        self.logger.debug("Routing DO_GENERATE_SIGNAL to daemon")
        self.generate_image_async(data)

    def _on_interrupt_image_generation(
        self, data: Dict[str, Any],
    ) -> None:
        job_id = data.get("job_id", "")
        if job_id:
            self.cancel_generation(job_id)

    def _on_llm_request(self, data: Dict[str, Any]) -> None:
        self.logger.debug("Routing LLM request to daemon")
        prompt = data.get("prompt", "")
        if prompt:
            self.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
        else:
            self.logger.warning("LLM request signal had no prompt")

    def _on_interrupt_process(self, _data: Dict[str, Any]) -> None:
        self.interrupt_llm()

    def _on_stt_transcribe(self, data: Dict[str, Any]) -> None:
        audio_bytes = data.get("audio_bytes")
        if audio_bytes:
            result = self.transcribe_audio(
                audio_bytes,
                mime_type=str(
                    data.get("mime_type") or "application/octet-stream",
                ),
            )
            transcription = str(result.get("text", "") or "")
            if transcription:
                self._emit(
                    SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
                    {
                        "transcription": transcription,
                        "language": result.get("language"),
                    },
                )

    def _on_load_art(self, _data: Dict[str, Any]) -> None:
        self.load_runtime("art", deployment_mode="sidecar")

    def _on_unload_art(self, _data: Dict[str, Any]) -> None:
        self.unload_runtime("art", deployment_mode="sidecar")

    def _on_llm_load(self, _data: Dict[str, Any]) -> None:
        self.load_runtime("llm")

    def _on_llm_unload(self, _data: Dict[str, Any]) -> None:
        self.unload_runtime("llm")

    def _on_stt_load(self, _data: Dict[str, Any]) -> None:
        self.load_runtime("stt", deployment_mode="sidecar")

    def _on_stt_unload(self, _data: Dict[str, Any]) -> None:
        self.unload_runtime("stt", deployment_mode="sidecar")
