"""HTTP client used by the GUI to communicate with the daemon API.

The daemon process is managed externally (e.g. by ``scripts/run.sh``).
This client connects to an already-running daemon and provides typed
methods for all API operations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional
from urllib.parse import urlencode

import requests

from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.enums import LLMActionType
from airunner_services.daemon_config import DaemonConfig
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

_ART_JOB_POLL_INTERVAL_SECONDS = 0.10


class GuiDaemonClient:
    """HTTP client for the local daemon API.

    The daemon is expected to already be running.  Use ``is_available()``
    to check reachability before issuing requests.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        *,
        session: Optional[requests.Session] = None,
        poll_interval_seconds: float = 0.25,
        request_timeout_seconds: float = 30.0,
        time_fn: Callable[[], float] = None,
        sleep: Callable[[float], None] = None,
    ) -> None:
        import time as _time

        self.config = DaemonConfig(config_path)
        self._session = session or requests.Session()
        self._poll_interval_seconds = poll_interval_seconds
        self._request_timeout_seconds = request_timeout_seconds
        self._time_fn = time_fn or _time.monotonic
        self._sleep = sleep or _time.sleep
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    @property
    def base_url(self) -> str:
        """Return the configured daemon base URL."""
        server = self.config.config.get("server", {})
        host = server.get("host", "127.0.0.1")
        port = server.get("port", 8188)
        return f"http://{host}:{port}"

    def is_available(self, *, timeout_seconds: float = 0.2) -> bool:
        """Return True when the daemon health endpoint responds."""
        return self._healthcheck_payload(timeout_seconds=timeout_seconds) is not None

    def health_check(self) -> Dict[str, Any]:
        """Return the daemon health payload."""
        response = self._request("GET", "/api/v1/health")
        return response.json()

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    def interrupt_llm(self) -> Dict[str, Any]:
        """Interrupt the active daemon-side LLM request."""
        response = self._request(
            "POST",
            "/api/v1/daemon/runtimes/llm/cancel",
            json_payload={
                "provider": "local",
                "deployment_mode": "default",
            },
        )
        return response.json()

    def unload_local_llm(
        self, *, timeout_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """Unload the daemon's local LLM runtime."""
        response = self._request(
            "POST",
            "/api/v1/daemon/runtimes/llm/unload",
            json_payload={
                "provider": "local",
                "deployment_mode": "default",
            },
            timeout_seconds=timeout_seconds,
        )
        return response.json()

    def stream_llm_request(
        self,
        prompt: str,
        llm_request: LLMRequest,
        action: LLMActionType,
        request_id: str,
        *,
        search_hints: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[int] = None,
        node_id: Optional[str] = None,
    ) -> Iterable[Dict[str, Any]]:
        """Yield NDJSON chunks from the daemon's legacy LLM endpoint."""
        headers = {"x-request-id": request_id}
        with self._request(
            "POST",
            "/llm/generate",
            json_payload=self._llm_payload(
                prompt,
                llm_request,
                action,
                search_hints=search_hints,
                conversation_id=conversation_id,
                node_id=node_id,
            ),
            headers=headers,
            stream=True,
        ) as response:
            for line in response.iter_lines(chunk_size=1):
                if not line:
                    continue
                yield json.loads(line.decode("utf-8"))

    # ------------------------------------------------------------------
    # Daemon status / runtime control
    # ------------------------------------------------------------------

    def daemon_runtime_status(
        self, *, timeout_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """Return combined daemon lifecycle and runtime status."""
        response = self._request(
            "GET",
            "/api/v1/daemon/status",
            timeout_seconds=timeout_seconds,
        )
        return response.json()

    def runtime_status(
        self,
        runtime_name: str,
        *,
        provider: str = "local",
        deployment_mode: str = "default",
    ) -> Dict[str, Any]:
        """Return the daemon summary for one runtime route."""
        query = urlencode(
            {"provider": provider, "deployment_mode": deployment_mode}
        )
        response = self._request(
            "GET",
            f"/api/v1/daemon/runtimes/{runtime_name}?{query}",
        )
        return response.json()

    def wait_runtime_ready(
        self,
        runtime_name: str,
        *,
        loaded: bool,
        provider: str = "local",
        deployment_mode: str = "default",
        timeout_seconds: float = 30.0,
    ) -> bool:
        """Poll one runtime summary until it reaches the requested state."""
        deadline = self._time_fn() + timeout_seconds
        while self._time_fn() < deadline:
            try:
                summary = self.runtime_status(
                    runtime_name,
                    provider=provider,
                    deployment_mode=deployment_mode,
                )
            except RuntimeError:
                self._sleep(self._poll_interval_seconds)
                continue
            if self._runtime_matches(summary, loaded):
                return True
            self._sleep(self._poll_interval_seconds)
        return False

    def cancel_runtime(
        self,
        runtime_name: str,
        *,
        provider: str = "local",
        deployment_mode: str = "default",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cancel one runtime request through the daemon control API."""
        return self._runtime_action(
            runtime_name,
            "cancel",
            provider=provider,
            deployment_mode=deployment_mode,
            request_id=request_id,
        )

    def load_runtime(
        self,
        runtime_name: str,
        *,
        provider: str = "local",
        deployment_mode: str = "default",
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Load one runtime through the daemon control API."""
        return self._runtime_action(
            runtime_name,
            "load",
            provider=provider,
            deployment_mode=deployment_mode,
            request_id=request_id,
            metadata=metadata,
            timeout_seconds=timeout_seconds,
        )

    def unload_runtime(
        self,
        runtime_name: str,
        *,
        provider: str = "local",
        deployment_mode: str = "default",
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Unload one runtime through the daemon control API."""
        return self._runtime_action(
            runtime_name,
            "unload",
            provider=provider,
            deployment_mode=deployment_mode,
            request_id=request_id,
            metadata=metadata,
            timeout_seconds=timeout_seconds,
        )

    # ------------------------------------------------------------------
    # Art generation
    # ------------------------------------------------------------------

    def start_art_generation(
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
        """Submit one art generation request through the daemon art route."""
        self.logger.info(
            "GuiDaemonClient.start_art_generation model=%s version=%s "
            "scheduler=%s steps=%s size=%sx%s",
            model,
            version,
            scheduler,
            steps,
            width,
            height,
        )
        response = self._request(
            "POST",
            "/api/v1/art/generate",
            json_payload={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "seed": seed,
                "num_images": num_images,
                "model": model,
                "version": version,
                "scheduler": scheduler,
                "pipeline": pipeline,
                "strength": strength,
                "image_b64": image_b64,
                "skip_auto_export": skip_auto_export,
            },
            timeout_seconds=30.0,
        )
        return response.json()

    def art_job_status(self, job_id: str) -> Dict[str, Any]:
        """Return the current daemon art-job status payload."""
        response = self._request("GET", f"/api/v1/art/status/{job_id}")
        return response.json()

    def art_job_result(self, job_id: str) -> bytes:
        """Return the PNG payload for one completed daemon art job."""
        response = self._request(
            "GET",
            f"/api/v1/art/result/{job_id}",
            timeout_seconds=120.0,
        )
        return response.content

    def wait_art_job(
        self,
        job_id: str,
        *,
        timeout_seconds: float = 1800.0,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> bytes:
        """Poll one art job until it completes and return the PNG bytes."""
        deadline = self._time_fn() + timeout_seconds
        poll_interval = min(
            self._poll_interval_seconds,
            _ART_JOB_POLL_INTERVAL_SECONDS,
        )
        last_status: Optional[str] = None
        last_progress: Optional[float] = None
        while self._time_fn() < deadline:
            status = self.art_job_status(job_id)
            state = str(status.get("status", "")).lower()
            progress = float(status.get("progress") or 0.0)
            if progress_callback is not None and (
                state != last_status or progress != last_progress
            ):
                progress_callback(status)
            if state != last_status or progress != last_progress:
                self.logger.debug(
                    "GuiDaemonClient.wait_art_job job_id=%s "
                    "status=%s progress=%.1f",
                    job_id,
                    state,
                    progress,
                )
                last_status = state
                last_progress = progress
            if state == "completed":
                return self.art_job_result(job_id)
            if state == "failed":
                raise RuntimeError(
                    str(status.get("error") or "Art generation failed")
                )
            if state == "cancelled":
                raise RuntimeError("Art generation cancelled")
            self._sleep(poll_interval)
        try:
            self.cancel_art_job(job_id)
        except RuntimeError:
            pass
        raise RuntimeError("Timed out waiting for art generation")

    def cancel_art_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel one daemon-backed art job."""
        response = self._request("DELETE", f"/api/v1/art/cancel/{job_id}")
        return response.json()

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
        request_id: Optional[str] = None,
    ) -> bytes:
        """Synthesize one TTS utterance through the daemon TTS route."""
        response = self._request(
            "POST",
            "/api/v1/tts/synthesize",
            json_payload={
                "text": text,
                "voice": voice,
                "speed": speed,
                "model": model,
                "model_type": model_type,
                "request_id": request_id,
            },
            timeout_seconds=120.0,
        )
        return response.content

    # ------------------------------------------------------------------
    # STT
    # ------------------------------------------------------------------

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        *,
        mime_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        """Submit one STT transcription request through the daemon API."""
        response = self._request(
            "POST",
            "/api/v1/stt/transcribe",
            files={"audio": ("audio.bin", audio_bytes, mime_type)},
            timeout_seconds=120.0,
        )
        return response.json()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _healthcheck_payload(
        self, *, timeout_seconds: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """Return the daemon /health payload when it is reachable."""
        try:
            response = self._session.request(
                "GET",
                f"{self.base_url}/api/v1/health",
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
        timeout_seconds: Optional[float] = None,
    ) -> requests.Response:
        """Perform an HTTP request against the daemon.

        Raises RuntimeError when the daemon is unreachable or the request
        fails.
        """

        try:
            response = self._session.request(
                method,
                f"{self.base_url}{path}",
                json=json_payload,
                files=files,
                headers=headers,
                stream=stream,
                timeout=timeout_seconds or self._request_timeout_seconds,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise RuntimeError(str(exc)) from exc

    def _runtime_action(
        self,
        runtime_name: str,
        action: str,
        *,
        provider: str,
        deployment_mode: str,
        request_id: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Call one daemon runtime control endpoint and return its payload."""
        response = self._request(
            "POST",
            f"/api/v1/daemon/runtimes/{runtime_name}/{action}",
            json_payload={
                "provider": provider,
                "deployment_mode": deployment_mode,
                "request_id": request_id,
                "metadata": metadata or {},
            },
            timeout_seconds=timeout_seconds,
        )
        return response.json()

    @staticmethod
    def _runtime_matches(summary: Dict[str, Any], loaded: bool) -> bool:
        """Return True when one runtime summary matches the target state."""
        summary_loaded = bool(summary.get("loaded"))
        summary_status = str(summary.get("status", "")).lower()
        if loaded:
            return summary_loaded and summary_status == "ready"
        return not summary_loaded

    @staticmethod
    def _llm_payload(
        prompt: str,
        llm_request: LLMRequest,
        action: LLMActionType,
        *,
        search_hints: Optional[Dict[str, Any]],
        conversation_id: Optional[int],
        node_id: Optional[str],
    ) -> Dict[str, Any]:
        """Build the legacy daemon payload from an LLM request object."""
        payload = {
            "prompt": prompt,
            "action": action.name,
            "stream": True,
        }
        payload.update(GuiDaemonClient._llm_request_fields(llm_request))
        if search_hints is not None:
            payload["search_hints"] = search_hints
        if conversation_id is not None:
            payload["conversation_id"] = conversation_id
        if node_id is not None:
            payload["node_id"] = node_id
        return payload

    @staticmethod
    def _llm_request_fields(llm_request: LLMRequest) -> Dict[str, Any]:
        """Return JSON-safe fields that the daemon legacy route understands."""
        payload = llm_request.to_dict()
        extra_fields = {
            "model_service": llm_request.model_service,
            "api_model": llm_request.api_model,
            "dtype": llm_request.dtype,
            "use_memory": llm_request.use_memory,
            "tool_categories": llm_request.tool_categories,
            "system_prompt": llm_request.system_prompt,
            "response_format": llm_request.response_format,
            "rag_files": llm_request.rag_files,
            "ephemeral_conversation": llm_request.ephemeral_conversation,
            "enable_thinking": llm_request.enable_thinking,
            "model": llm_request.model,
            "force_tool": llm_request.force_tool,
            "include_mood": llm_request.include_mood,
            "include_datetime": llm_request.include_datetime,
            "include_style": llm_request.include_style,
            "include_memory": llm_request.include_memory,
            "include_ui_context": llm_request.include_ui_context,
        }
        for key, value in extra_fields.items():
            if value is not None:
                payload[key] = value
        return payload
