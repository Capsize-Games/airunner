"""Runtime control, TTS, STT, and hardware endpoints for the GUI daemon
client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlencode


@dataclass
class HardwareProfile:
    """Serialized hardware profile returned by the daemon."""

    total_vram_gb: float
    available_vram_gb: float
    total_ram_gb: float
    available_ram_gb: float
    cuda_available: bool
    device_name: str | None
    cpu_count: int
    platform: str


class RuntimeClientMixin:
    """Daemon runtime control, TTS, STT, and hardware API endpoints."""

    _request: Any
    _sleep: Any
    _time_fn: Any
    _poll_interval_seconds: float

    # ------------------------------------------------------------------
    # Hardware profiling
    # ------------------------------------------------------------------

    def get_hardware_profile(self) -> HardwareProfile:
        """Return the host hardware profile from the daemon."""
        response = self._request("GET", "/api/v1/daemon/hardware")
        payload = response.json()
        return HardwareProfile(
            total_vram_gb=float(payload["total_vram_gb"]),
            available_vram_gb=float(payload["available_vram_gb"]),
            total_ram_gb=float(payload["total_ram_gb"]),
            available_ram_gb=float(payload["available_ram_gb"]),
            cuda_available=bool(payload["cuda_available"]),
            device_name=payload.get("device_name"),
            cpu_count=int(payload["cpu_count"]),
            platform=str(payload.get("platform", "")),
        )

    # ------------------------------------------------------------------
    # Runtime control
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
        """Poll one runtime summary until it reaches the requested
        state."""
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
        """Submit one STT transcription request through the daemon
        API."""
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
        """Call one daemon runtime control endpoint and return its
        payload."""
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
    def _runtime_matches(
        summary: Dict[str, Any], loaded: bool
    ) -> bool:
        """Return True when one runtime summary matches the target
        state."""
        summary_loaded = bool(summary.get("loaded"))
        summary_status = str(summary.get("status", "")).lower()
        if loaded:
            return summary_loaded and summary_status == "ready"
        return not summary_loaded
