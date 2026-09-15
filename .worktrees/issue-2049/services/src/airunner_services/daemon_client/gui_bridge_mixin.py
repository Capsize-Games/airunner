"""GUI-side bridge helpers for the canonical daemon HTTP client.

These methods are used by the desktop client to route the legacy
signal-based generation flows through the daemon and to decode the
daemon's hardware profile into a plain dataclass.  They live next to the
canonical HTTP client so the GUI and daemon stay in lockstep.
"""

from __future__ import annotations

import io
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from airunner_common.contract_enums import SignalCode


class APIBridgeError(RuntimeError):
    """Error raised when the API bridge cannot complete a request."""


@dataclass
class HardwareProfile:
    """Serialized hardware profile returned by the daemon."""

    total_vram_gb: float
    available_vram_gb: float
    total_ram_gb: float
    available_ram_gb: float
    cuda_available: bool
    cuda_compute_capability: tuple[int, int] | None = None
    device_name: str | None = None
    cpu_count: int = 0
    platform: str = ""


class GuiBridgeMixin:
    """Legacy GUI bridge methods layered on top of ``GuiDaemonClient``.

    ``GuiDaemonClient`` is constructed with the service-owned mixin first in
    its MRO, so ``_emit`` and ``_request`` resolve to the methods it defines.
    """

    _emit: Callable[[Any, Dict[str, Any]], None]

    @property
    def is_connected(self) -> bool:
        """Return True when the daemon is reachable."""
        try:
            return self.is_available()
        except Exception:
            return False

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

    def get_hardware_profile(self) -> HardwareProfile:
        """Return the host hardware profile from the daemon."""
        response = self._request("GET", "/api/v1/daemon/hardware")
        payload = response.json()
        capability = payload.get("cuda_compute_capability")
        if isinstance(capability, (list, tuple)) and len(capability) >= 2:
            capability_tuple = (int(capability[0]), int(capability[1]))
        else:
            capability_tuple = None
        return HardwareProfile(
            total_vram_gb=float(payload["total_vram_gb"]),
            available_vram_gb=float(payload["available_vram_gb"]),
            total_ram_gb=float(payload["total_ram_gb"]),
            available_ram_gb=float(payload["available_ram_gb"]),
            cuda_available=bool(payload["cuda_available"]),
            cuda_compute_capability=capability_tuple,
            device_name=payload.get("device_name"),
            cpu_count=int(payload["cpu_count"]),
            platform=str(payload.get("platform", "")),
        )

    def estimate_vram(
        self,
        model_path: str,
    ) -> Dict[str, Any]:
        """Return a VRAM estimate for one model path."""
        from urllib.parse import urlencode

        query = urlencode({"model_path": model_path})
        response = self._request(
            "GET",
            f"/api/v1/art/vram-estimate?{query}",
        )
        return response.json()

    def get_bootstrap_data(self) -> Dict[str, Any]:
        """Return model and pipeline bootstrap data from the daemon."""
        response = self._request(
            "GET",
            "/api/v1/art/bootstrap",
        )
        return response.json()

    def geolocate_zip(
        self,
        zipcode: str,
    ) -> Dict[str, Any]:
        """Return lat/lon for a US ZIP code from the daemon."""
        response = self._request(
            "GET",
            f"/api/v1/daemon/geolocation/{zipcode}",
        )
        return response.json()

    def start_setup(
        self,
        *,
        enabled_models: Dict[str, bool],
        base_path: str,
        prefer_pre_quantized: bool = True,
        progress_callback: Optional[
            Callable[[Dict[str, Any]], None]
        ] = None,
    ) -> None:
        """Run one daemon-backed setup install with SSE progress events."""
        import json

        response = self._request(
            "POST",
            "/api/v1/setup/install",
            json_payload={
                "enabled_models": enabled_models,
                "base_path": base_path,
                "prefer_pre_quantized": prefer_pre_quantized,
            },
            timeout_seconds=3600.0,
            stream=True,
        )
        for line in response.iter_lines():
            if not line or not line.startswith(b"data: "):
                continue
            try:
                payload = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            if progress_callback is not None:
                progress_callback(payload)

    def start_huggingface_file_download(
        self,
        *,
        repo_id: str,
        filename: str,
        output_dir: str,
    ) -> Dict[str, Any]:
        """Queue one daemon-backed single-file HuggingFace download."""
        response = self._request(
            "POST",
            "/api/v1/downloads/huggingface/file",
            json_payload={
                "repo_id": repo_id,
                "filename": filename,
                "output_dir": output_dir,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    def start_nltk_download(
        self,
        *,
        data_names: list[str],
    ) -> Dict[str, Any]:
        """Queue one daemon-backed NLTK data download job."""
        response = self._request(
            "POST",
            "/api/v1/downloads/nltk",
            json_payload={"data_names": data_names},
            timeout_seconds=30.0,
        )
        return response.json()

    def start_civitai_file_download(
        self,
        *,
        url: str,
        output_path: str,
        file_size: int,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Queue one daemon-backed single-file CivitAI download."""
        response = self._request(
            "POST",
            "/api/v1/downloads/civitai/file",
            json_payload={
                "url": url,
                "output_path": output_path,
                "file_size": file_size,
                "api_key": api_key,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    def search_civitai_models(
        self,
        *,
        query: str = "",
        base_models: Optional[list[str]] = None,
        model_types: Optional[list[str]] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return one filtered CivitAI browser search payload."""
        response = self._request(
            "POST",
            "/api/v1/downloads/civitai/models",
            json_payload={
                "query": query,
                "base_models": base_models,
                "model_types": model_types,
                "limit": limit,
                "cursor": cursor,
                "api_key": api_key,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    def fetch_civitai_model(
        self,
        *,
        model_id: str,
        base_models: Optional[list[str]] = None,
        model_types: Optional[list[str]] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return one filtered CivitAI browser detail payload."""
        response = self._request(
            "POST",
            "/api/v1/downloads/civitai/model",
            json_payload={
                "model_id": model_id,
                "base_models": base_models,
                "model_types": model_types,
                "api_key": api_key,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    def fetch_civitai_image(
        self,
        *,
        url: str,
        max_bytes: Optional[int] = None,
    ) -> bytes:
        """Fetch one CivitAI preview image through the daemon."""
        response = self._request(
            "POST",
            "/api/v1/downloads/civitai/image",
            json_payload={
                "url": url,
                "max_bytes": max_bytes,
            },
            timeout_seconds=30.0,
        )
        return response.content

    def start_rag_document_index(
        self,
        *,
        file_paths: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """Trigger daemon-backed document indexing."""
        response = self._request(
            "POST",
            "/api/v1/llm/rag/index",
            json_payload={"file_paths": file_paths},
        )
        return response.json()

    def cancel_rag_document_index(self) -> Dict[str, Any]:
        """Request cancellation for the daemon-backed indexing flow."""
        response = self._request(
            "POST",
            "/api/v1/llm/rag/index/cancel",
        )
        return response.json()

    def rag_document_index_status(self) -> Dict[str, Any]:
        """Return the current daemon-backed indexing status payload."""
        response = self._request(
            "GET",
            "/api/v1/llm/rag/index/status",
        )
        return response.json()

    # ------------------------------------------------------------------
    # Private bridge helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _noop_emitter(code: Any, data: Dict[str, Any]) -> None:
        """No-op signal emitter."""
        del code, data

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
