"""HTTP client used by the GUI to launch or connect to the daemon."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional
from urllib.parse import urlencode

import requests

from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.daemon_client.daemon_connection_state import (
    DaemonConnectionState,
)
from airunner.daemon_client.daemon_launcher import DaemonLauncher
from airunner.enums import LLMActionType
from airunner.services.daemon_config import DaemonConfig
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

StateCallback = Callable[[DaemonConnectionState, str], None]


class GuiDaemonClient:
    """Start, connect to, and communicate with the local daemon."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        *,
        launcher: Optional[DaemonLauncher] = None,
        session: Optional[requests.Session] = None,
        auto_start: bool = True,
        startup_timeout_seconds: float = 20.0,
        poll_interval_seconds: float = 0.25,
        request_timeout_seconds: float = 30.0,
        state_callback: Optional[StateCallback] = None,
        time_fn: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = DaemonConfig(config_path)
        self._launcher = launcher or DaemonLauncher(self.config.config_path)
        self._session = session or requests.Session()
        self._auto_start = auto_start
        self._startup_timeout_seconds = startup_timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._request_timeout_seconds = request_timeout_seconds
        self._state_callback = state_callback
        self._time_fn = time_fn
        self._sleep = sleep
        self._state = DaemonConnectionState.NOT_STARTED
        self._last_error = ""
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    @property
    def state(self) -> DaemonConnectionState:
        """Return the current daemon connection state."""
        return self._state

    @property
    def last_error(self) -> str:
        """Return the most recent daemon connection or request error."""
        return self._last_error

    @property
    def base_url(self) -> str:
        """Return the configured daemon base URL."""
        server = self.config.config.get("server", {})
        host = server.get("host", "127.0.0.1")
        port = server.get("port", 8188)
        return f"http://{host}:{port}"

    def ensure_connected(self, *, auto_start: Optional[bool] = None) -> bool:
        """Return True when the daemon is reachable, starting it when allowed."""
        if self._healthcheck_ready():
            self._set_state(DaemonConnectionState.CONNECTED, "connected")
            return True

        if not self._resolved_auto_start(auto_start):
            self._set_state(
                DaemonConnectionState.DISCONNECTED,
                self._last_error or "daemon unavailable",
            )
            return False

        self._prepare_connection_attempt()
        try:
            self._launcher.start()
        except OSError as exc:
            self._last_error = str(exc)
            self._set_state(DaemonConnectionState.FAILED, self._last_error)
            return False
        return self._wait_until_ready()

    def reconnect(self) -> bool:
        """Force a reconnect attempt to the daemon."""
        self._set_state(DaemonConnectionState.RECONNECTING, "reconnecting")
        return self.ensure_connected(auto_start=True)

    def disconnect(self, *, stop_process: bool = False) -> None:
        """Mark the daemon disconnected and optionally stop the process."""
        if stop_process:
            self._launcher.stop()
        self._set_state(DaemonConnectionState.DISCONNECTED, "disconnected")

    def health_check(self) -> Dict[str, Any]:
        """Return the daemon health payload."""
        response = self._request("GET", "/health", auto_start=False)
        return response.json()

    def interrupt_llm(self) -> Dict[str, Any]:
        """Interrupt the active daemon-side LLM request."""
        response = self._request(
            "POST",
            "/admin/interrupt",
            json_payload={"kind": "process"},
            auto_start=False,
        )
        return response.json()

    def daemon_runtime_status(
        self,
        *,
        auto_start: bool = False,
    ) -> Dict[str, Any]:
        """Return combined daemon lifecycle and runtime status."""
        response = self._request(
            "GET",
            "/api/v1/daemon/status",
            auto_start=auto_start,
        )
        return response.json()

    def runtime_status(
        self,
        runtime_name: str,
        *,
        provider: str = "local",
        deployment_mode: str = "default",
        auto_start: bool = False,
    ) -> Dict[str, Any]:
        """Return the daemon summary for one runtime route."""
        query = urlencode(
            {
                "provider": provider,
                "deployment_mode": deployment_mode,
            }
        )
        response = self._request(
            "GET",
            f"/api/v1/daemon/runtimes/{runtime_name}?{query}",
            auto_start=auto_start,
        )
        return response.json()

    def wait_runtime_ready(
        self,
        runtime_name: str,
        *,
        loaded: bool,
        provider: str = "local",
        deployment_mode: str = "default",
        auto_start: bool = False,
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
                    auto_start=auto_start,
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
        auto_start: bool = False,
    ) -> Dict[str, Any]:
        """Cancel one runtime request through the daemon control API."""
        return self._runtime_action(
            runtime_name,
            "cancel",
            provider=provider,
            deployment_mode=deployment_mode,
            request_id=request_id,
            auto_start=auto_start,
        )

    def synthesize_tts(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: float = 1.0,
        model: Optional[str] = None,
        model_type: Optional[str] = None,
        request_id: Optional[str] = None,
        auto_start: bool = True,
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
            auto_start=auto_start,
            timeout_seconds=120.0,
        )
        return response.content

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
        auto_start: bool = True,
    ) -> Dict[str, Any]:
        """Submit one art generation request through the daemon art route."""
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
            },
            auto_start=auto_start,
            timeout_seconds=30.0,
        )
        return response.json()

    def art_job_status(
        self,
        job_id: str,
        *,
        auto_start: bool = False,
    ) -> Dict[str, Any]:
        """Return the current daemon art-job status payload."""
        response = self._request(
            "GET",
            f"/api/v1/art/status/{job_id}",
            auto_start=auto_start,
        )
        return response.json()

    def art_job_result(
        self,
        job_id: str,
        *,
        auto_start: bool = False,
    ) -> bytes:
        """Return the PNG payload for one completed daemon art job."""
        response = self._request(
            "GET",
            f"/api/v1/art/result/{job_id}",
            auto_start=auto_start,
            timeout_seconds=120.0,
        )
        return response.content

    def wait_art_job(
        self,
        job_id: str,
        *,
        auto_start: bool = False,
        timeout_seconds: float = 1800.0,
    ) -> bytes:
        """Poll one art job until it completes and return the PNG bytes."""
        deadline = self._time_fn() + timeout_seconds
        while self._time_fn() < deadline:
            status = self.art_job_status(job_id, auto_start=auto_start)
            state = str(status.get("status", "")).lower()
            if state == "completed":
                return self.art_job_result(job_id, auto_start=auto_start)
            if state == "failed":
                raise RuntimeError(
                    str(status.get("error") or "Art generation failed")
                )
            if state == "cancelled":
                raise RuntimeError("Art generation cancelled")
            self._sleep(self._poll_interval_seconds)
        try:
            self.cancel_art_job(job_id, auto_start=False)
        except RuntimeError:
            pass
        raise RuntimeError("Timed out waiting for art generation")

    def cancel_art_job(
        self,
        job_id: str,
        *,
        auto_start: bool = False,
    ) -> Dict[str, Any]:
        """Cancel one daemon-backed art job."""
        response = self._request(
            "DELETE",
            f"/api/v1/art/cancel/{job_id}",
            auto_start=auto_start,
        )
        return response.json()

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        *,
        mime_type: str = "application/octet-stream",
        auto_start: bool = True,
    ) -> Dict[str, Any]:
        """Submit one STT transcription request through the daemon API."""
        response = self._request(
            "POST",
            "/api/v1/stt/transcribe",
            files={
                "audio": (
                    "audio.bin",
                    audio_bytes,
                    mime_type,
                )
            },
            auto_start=auto_start,
            timeout_seconds=120.0,
        )
        return response.json()

    def load_runtime(
        self,
        runtime_name: str,
        *,
        provider: str = "local",
        deployment_mode: str = "default",
        request_id: Optional[str] = None,
        auto_start: bool = True,
    ) -> Dict[str, Any]:
        """Load one runtime through the daemon control API."""
        return self._runtime_action(
            runtime_name,
            "load",
            provider=provider,
            deployment_mode=deployment_mode,
            request_id=request_id,
            auto_start=auto_start,
        )

    def unload_runtime(
        self,
        runtime_name: str,
        *,
        provider: str = "local",
        deployment_mode: str = "default",
        request_id: Optional[str] = None,
        auto_start: bool = True,
    ) -> Dict[str, Any]:
        """Unload one runtime through the daemon control API."""
        return self._runtime_action(
            runtime_name,
            "unload",
            provider=provider,
            deployment_mode=deployment_mode,
            request_id=request_id,
            auto_start=auto_start,
        )

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
        enable_consciousness: Optional[bool] = None,
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
                enable_consciousness=enable_consciousness,
            ),
            headers=headers,
            stream=True,
        ) as response:
            for line in response.iter_lines():
                if not line:
                    continue
                yield json.loads(line.decode("utf-8"))

    def _resolved_auto_start(self, auto_start: Optional[bool]) -> bool:
        """Return the effective auto-start behavior for this call."""
        if auto_start is None:
            return self._auto_start
        return auto_start

    def _prepare_connection_attempt(self) -> None:
        """Set the state for a new connection attempt."""
        if self._state is DaemonConnectionState.NOT_STARTED:
            self._set_state(DaemonConnectionState.CONNECTING, "starting daemon")
            return
        self._set_state(DaemonConnectionState.RECONNECTING, "starting daemon")

    def _wait_until_ready(self) -> bool:
        """Wait for the daemon health endpoint to become ready."""
        deadline = self._time_fn() + self._startup_timeout_seconds
        while self._time_fn() < deadline:
            if self._healthcheck_ready():
                self._set_state(DaemonConnectionState.CONNECTED, "connected")
                return True
            self._sleep(self._poll_interval_seconds)

        self._last_error = "Timed out waiting for daemon to become ready"
        self._set_state(DaemonConnectionState.FAILED, self._last_error)
        return False

    def _healthcheck_ready(self) -> bool:
        """Return True when the daemon responds successfully to /health."""
        try:
            response = self._session.request(
                "GET",
                f"{self.base_url}/health",
                timeout=5,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            self._last_error = str(exc)
            return False

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
        auto_start: bool = True,
        timeout_seconds: Optional[float] = None,
    ) -> requests.Response:
        """Perform an HTTP request against the daemon."""
        if not self.ensure_connected(auto_start=auto_start):
            raise RuntimeError(self._last_error or "daemon unavailable")

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
            self._set_state(DaemonConnectionState.CONNECTED, "connected")
            return response
        except requests.RequestException as exc:
            self._last_error = str(exc)
            self._set_state(DaemonConnectionState.DISCONNECTED, self._last_error)
            raise RuntimeError(self._last_error) from exc

    def _runtime_action(
        self,
        runtime_name: str,
        action: str,
        *,
        provider: str,
        deployment_mode: str,
        request_id: Optional[str],
        auto_start: bool,
    ) -> Dict[str, Any]:
        """Call one daemon runtime control endpoint and return its payload."""
        response = self._request(
            "POST",
            f"/api/v1/daemon/runtimes/{runtime_name}/{action}",
            json_payload={
                "provider": provider,
                "deployment_mode": deployment_mode,
                "request_id": request_id,
            },
            auto_start=auto_start,
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

    def _set_state(self, state: DaemonConnectionState, details: str) -> None:
        """Update the tracked daemon connection state."""
        self._state = state
        if state in {
            DaemonConnectionState.DISCONNECTED,
            DaemonConnectionState.FAILED,
        }:
            self._last_error = details
        if self._state_callback is not None:
            self._state_callback(state, details)

    @staticmethod
    def _llm_payload(
        prompt: str,
        llm_request: LLMRequest,
        action: LLMActionType,
        *,
        search_hints: Optional[Dict[str, Any]],
        conversation_id: Optional[int],
        node_id: Optional[str],
        enable_consciousness: Optional[bool],
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
        if enable_consciousness is not None:
            payload["enable_consciousness"] = enable_consciousness
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
            "use_mode_routing": llm_request.use_mode_routing,
            "mode_override": llm_request.mode_override,
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