"""HTTP runtime client for the supervised TTS sidecar."""

from __future__ import annotations

import base64
import threading
from dataclasses import replace
from typing import Any, Optional

import requests

from airunner.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner.runtimes.base import RuntimeClient
from airunner.runtimes.contracts import (
    RuntimeAction,
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeKind,
    RuntimeMode,
    TTSInvocationRequest,
    TransportKind,
)
from airunner.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner.runtimes.sidecar_tts_launcher import SidecarTTSLauncher
from airunner.runtimes.tts_daemon_runtime_settings import (
    TTSDaemonRuntimeSettings,
    resolve_tts_daemon_runtime_settings,
)

DEFAULT_PROVIDER = "local"


class SidecarTTSClient(RuntimeClient):
    """Route TTS envelopes through one supervised sidecar daemon."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        *,
        settings: Optional[TTSDaemonRuntimeSettings] = None,
        launcher: Optional[SidecarTTSLauncher] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        resolved_settings = settings or resolve_tts_daemon_runtime_settings()
        self._base_settings = resolved_settings
        self._settings = resolved_settings
        self._launcher = launcher or SidecarTTSLauncher(resolved_settings)
        self._managed_launcher = launcher is None
        self._session = session or requests.Session()
        self._active_requests: set[str] = set()
        self._active_requests_lock = threading.Lock()
        self._invoke_lock = threading.Lock()
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.TTS,
            provider=provider,
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
            endpoint=resolved_settings.endpoint,
            supports_streaming=False,
            allows_model_control=True,
        )

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Invoke one sidecar control action or synthesis request."""
        if request.runtime is not RuntimeKind.TTS:
            raise ValueError("SidecarTTSClient only supports TTS")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_runtime(request)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_runtime(request.request_id)
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("SidecarTTSClient only supports invoke")
        return self._synthesize_speech(request)

    def healthcheck(self) -> RuntimeHealth:
        """Return the health of the managed TTS runtime."""
        status, details = self._launcher.health_status()
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=status,
            details=details,
            metadata=self._metadata(),
        )

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Interrupt an active TTS synthesis request when one exists."""
        should_cancel = self._untrack_request(request_id)
        if should_cancel and self._launcher.is_running():
            try:
                self._request(
                    "POST",
                    f"{self._launcher.endpoint}/api/v1/daemon/runtimes/tts"
                    "/cancel",
                    json_payload={"request_id": request_id},
                )
            except RuntimeError:
                pass
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True, **self._metadata()},
        )

    def close(self) -> None:
        """Release the managed sidecar process during shutdown."""
        self._launcher.stop()
        close = getattr(self._session, "close", None)
        if close is not None:
            close()

    def _status_response(self, request_id: str) -> ResponseEnvelope:
        """Return a neutral status envelope for runtime control callers."""
        health = self.healthcheck()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"status": health.status.value},
            metadata=health.metadata,
        )

    def _load_runtime(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Start the managed TTS daemon."""
        try:
            settings = self._settings_for_control(request.metadata)
            self._ensure_launcher(settings)
            self._launcher.start()
            self._request(
                "POST",
                f"{self._launcher.endpoint}/api/v1/daemon/runtimes/tts/load",
                json_payload={
                    "provider": self.descriptor.provider,
                    "deployment_mode": RuntimeMode.LOCAL_FALLBACK.value,
                    "request_id": request.request_id,
                    "metadata": dict(request.metadata or {}),
                },
            )
        except RuntimeError as exc:
            return self._failure_response(
                request.request_id,
                "tts_load_failed",
                str(exc),
            )
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"model_status": "loaded"},
            metadata=self._metadata(),
        )

    def _settings_for_control(
        self,
        metadata: Optional[dict[str, Any]],
    ) -> TTSDaemonRuntimeSettings:
        """Return sidecar settings adjusted for one load request."""
        metadata = metadata or {}
        return replace(
            self._base_settings,
            tts_model_path=(
                metadata.get("model_path")
                or self._base_settings.tts_model_path
            ),
            tts_model_type=(
                metadata.get("model_type")
                or self._base_settings.tts_model_type
            ),
        )

    def _unload_runtime(self, request_id: str) -> ResponseEnvelope:
        """Stop the managed TTS daemon."""
        self._launcher.stop()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"model_status": "unloaded"},
            metadata=self._metadata(),
        )

    def _synthesize_speech(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Execute one TTS request through the supervised sidecar daemon."""
        invocation = TTSInvocationRequest.model_validate(request.payload)
        with self._invoke_lock:
            try:
                settings = self._settings_for_invocation(invocation)
                self._ensure_launcher(settings)
                self._launcher.start()
                self._track_request(request.request_id)
                audio_bytes = self._request(
                    "POST",
                    f"{self._launcher.api_base_url}/synthesize",
                    json_payload={
                        "text": invocation.text,
                        "voice": invocation.voice,
                        "speed": invocation.speed,
                        "model": invocation.model,
                        "model_type": invocation.metadata.get("model_type"),
                        "request_id": request.request_id,
                    },
                    expect_json=False,
                )
            except RuntimeError as exc:
                return self._runtime_error_response(
                    request.request_id,
                    str(exc),
                )
            finally:
                self._untrack_request(request.request_id)

        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={
                "accepted": True,
                "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
            },
            metadata=self._metadata(),
        )

    def _settings_for_invocation(
        self,
        invocation: TTSInvocationRequest,
    ) -> TTSDaemonRuntimeSettings:
        """Return sidecar settings adjusted for one synthesis request."""
        metadata = invocation.metadata
        return replace(
            self._base_settings,
            tts_model_path=invocation.model or self._base_settings.tts_model_path,
            tts_model_type=(
                metadata.get("model_type")
                or self._base_settings.tts_model_type
            ),
        )

    def _ensure_launcher(self, settings: TTSDaemonRuntimeSettings) -> None:
        """Refresh the managed launcher when request settings change."""
        if not self._managed_launcher:
            self._settings = settings
            return
        if settings == self._settings:
            return
        self._launcher.stop()
        self._settings = settings
        self._launcher = SidecarTTSLauncher(settings)

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_payload: Optional[dict[str, Any]] = None,
        expect_json: bool = True,
    ) -> Any:
        """Perform one HTTP request against the sidecar daemon."""
        try:
            response = self._session.request(
                method,
                url,
                json=json_payload,
                timeout=self._settings.request_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(self._request_error_message(exc)) from exc
        if expect_json:
            return response.json()
        return response.content

    def _track_request(self, request_id: str) -> None:
        """Track one active synthesis request for cancellation."""
        with self._active_requests_lock:
            self._active_requests.add(request_id)

    def _untrack_request(self, request_id: str) -> bool:
        """Remove one active request identifier when it exists."""
        with self._active_requests_lock:
            if request_id not in self._active_requests:
                return False
            self._active_requests.remove(request_id)
            return True

    def _metadata(self) -> dict[str, Any]:
        """Return stable sidecar metadata for health and control responses."""
        metadata = {
            "endpoint": self._launcher.endpoint,
            "tts_api_url": self._launcher.api_base_url,
        }
        if self._settings.tts_model_path:
            metadata["model_path"] = self._settings.tts_model_path
        if self._settings.tts_model_type:
            metadata["model_type"] = self._settings.tts_model_type
        return metadata

    @staticmethod
    def _request_error_message(error: requests.RequestException) -> str:
        """Return a useful message extracted from one request failure."""
        response = getattr(error, "response", None)
        if response is not None and getattr(response, "text", ""):
            return str(response.text)
        return str(error)

    @staticmethod
    def _failure_response(
        request_id: str,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> ResponseEnvelope:
        """Return a normalized failure envelope."""
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.FAILED,
            error=ErrorEnvelope(
                code=code,
                message=message,
                retryable=retryable,
            ),
        )

    def _runtime_error_response(
        self,
        request_id: str,
        message: str,
    ) -> ResponseEnvelope:
        """Return a runtime failure response inferred from one message."""
        if "Timed out" in message:
            return self._failure_response(
                request_id,
                "tts_timeout",
                message,
                retryable=True,
            )
        return self._failure_response(
            request_id,
            "tts_invoke_failed",
            message,
            retryable=True,
        )


def register_sidecar_tts_client(
    registry: RuntimeRegistry,
    tts_client: Optional[RuntimeClient] = None,
) -> RuntimeRegistry:
    """Register the sidecar-backed TTS client under the sidecar route."""
    client = tts_client or SidecarTTSClient()
    registry.register(
        RuntimeRoute(
            RuntimeKind.TTS,
            provider=client.descriptor.provider,
            deployment_mode=RuntimeMode.SIDECAR.value,
        ),
        client,
    )
    return registry