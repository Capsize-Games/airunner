"""HTTP+WebSocket runtime client for the supervised whisper.cpp sidecar."""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from airunner_services.runtimes.contracts import RuntimeAction
from airunner_services.runtimes.contracts import RuntimeDescriptor
from airunner_services.runtimes.contracts import RuntimeHealth
from airunner_services.runtimes.contracts import RuntimeKind
from airunner_services.runtimes.contracts import RuntimeMode
from airunner_services.runtimes.contracts import STTInvocationRequest
from airunner_services.runtimes.contracts import TransportKind
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.message_envelopes import load_message_types
from airunner_services.runtimes.registry import RuntimeRegistry
from airunner_services.runtimes.registry import RuntimeRoute
from airunner_services.runtimes.sidecar_stt_launcher import (
    SidecarSTTLauncher,
)
from airunner_services.runtimes.whisper_cpp_runtime_settings import (
    WhisperCppRuntimeSettings,
    resolve_whisper_cpp_runtime_settings,
)
from airunner_services.runtimes.websocket_transport import (
    SidecarWebSocketTransport,
    WebSocketTransportDisconnected,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

DEFAULT_PROVIDER = "local"
WhisperSettingsResolver = Callable[[], WhisperCppRuntimeSettings]


class SidecarSTTClient(RuntimeClient):
    """Route STT runtime envelopes through a supervised whisper.cpp server.

    Supports both WebSocket (via the stt_ws_adapter process) and HTTP
    (direct to whisper.cpp).  WebSocket is preferred for consistency.
    """

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        *,
        settings: Optional[WhisperCppRuntimeSettings] = None,
        settings_resolver: Optional[WhisperSettingsResolver] = None,
        launcher: Optional[SidecarSTTLauncher] = None,
        http_opener=urlopen,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._settings_resolver = (
            settings_resolver or resolve_whisper_cpp_runtime_settings
        )
        resolved_settings = settings or self._settings_resolver()
        self._settings = resolved_settings
        self._launcher = launcher or SidecarSTTLauncher(resolved_settings)
        self._managed_launcher = launcher is None
        self._http_opener = http_opener
        self._timeout_seconds = timeout_seconds

        self._ws_transport: Optional[SidecarWebSocketTransport] = None
        # Adapter port offset: adapter listens on whisper.cpp port + 1000
        self._adapter_port = resolved_settings.port + 1000

        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.STT,
            provider=provider,
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.WEBSOCKET,
            endpoint=resolved_settings.endpoint,
            supports_streaming=False,
            allows_model_control=True,
        )

    def invoke(self, request: Any) -> Any:
        """Invoke a sidecar control action or transcription request."""
        if request.runtime is not RuntimeKind.STT:
            raise ValueError("SidecarSTTClient only supports STT")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_model(request.request_id)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_model(request.request_id)
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("SidecarSTTClient only supports invoke")
        return self._transcribe(request)

    def healthcheck(self) -> RuntimeHealth:
        """Return the health of the managed whisper.cpp runtime."""
        status, details = self._launcher.health_status()
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=status,
            details=details,
            metadata=self._metadata(),
        )

    def cancel(self, request_id: str) -> Any:
        """Cancel active work by stopping the current sidecar process."""
        messages = load_message_types()
        self._launcher.stop()
        return messages.ResponseEnvelope(
            request_id=request_id,
            status=messages.EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def close(self) -> None:
        """Release the managed sidecar process during shutdown."""
        if self._ws_transport is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._ws_transport.close(),
                    asyncio.get_event_loop(),
                ).result(timeout=5)
            except Exception:
                pass
            self._ws_transport = None
        self._launcher.stop()

    def _status_response(self, request_id: str) -> Any:
        """Return a neutral status envelope for runtime control callers."""
        messages = load_message_types()
        health = self.healthcheck()
        return messages.ResponseEnvelope(
            request_id=request_id,
            status=messages.EnvelopeStatus.SUCCEEDED,
            payload={"status": health.status.value},
            metadata=health.metadata,
        )

    def _load_model(self, request_id: str) -> Any:
        """Start the managed whisper.cpp process."""
        messages = load_message_types()
        try:
            self._prepare_launcher(for_reload=True)
            self._launcher.start()
        except RuntimeError as exc:
            return self._failure_response(
                request_id,
                "stt_load_failed",
                str(exc),
            )
        return messages.ResponseEnvelope(
            request_id=request_id,
            status=messages.EnvelopeStatus.SUCCEEDED,
            payload={"model_status": "loaded"},
            metadata=self._metadata(),
        )

    def _unload_model(self, request_id: str) -> Any:
        """Stop the managed whisper.cpp process."""
        messages = load_message_types()
        self._launcher.stop()
        return messages.ResponseEnvelope(
            request_id=request_id,
            status=messages.EnvelopeStatus.SUCCEEDED,
            payload={"model_status": "unloaded"},
            metadata=self._metadata(),
        )

    def _ensure_ws_transport(self) -> SidecarWebSocketTransport:
        """Return or create a WebSocket transport for the adapter."""
        ws = self._ws_transport
        if ws is not None and ws.is_connected:
            return ws
        if ws is not None:
            asyncio.run_coroutine_threadsafe(
                ws.close(), asyncio.get_event_loop(),
            )
        endpoint = f"http://127.0.0.1:{self._adapter_port}"
        ws = SidecarWebSocketTransport(endpoint)
        try:
            asyncio.run_coroutine_threadsafe(
                ws.connect(), asyncio.get_event_loop(),
            ).result(timeout=10)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to connect STT WebSocket adapter: {exc}"
            ) from exc
        self._ws_transport = ws
        return ws

    def _transcribe(self, request: Any) -> Any:
        """Execute a transcription request via WebSocket transport only.

        Raises immediately when the WebSocket connection cannot be
        established -- no HTTP fallback.
        """
        messages = load_message_types()
        invocation = STTInvocationRequest.model_validate(request.payload)
        try:
            audio_bytes = base64.b64decode(
                invocation.audio_b64, validate=True,
            )
        except Exception:
            return self._failure_response(
                request.request_id,
                "stt_invalid_audio",
                "Invalid base64 audio payload",
            )

        try:
            return self._transcribe_via_websocket(
                request, invocation, audio_bytes,
            )
        except RuntimeError as exc:
            return self._failure_response(
                request.request_id,
                "stt_invoke_failed",
                str(exc),
                retryable=True,
            )

    def _transcribe_via_websocket(
        self,
        request: Any,
        invocation: STTInvocationRequest,
        audio_bytes: bytes,
    ) -> Any:
        """Send one transcription request through the WebSocket adapter."""
        messages = load_message_types()
        ws = self._ensure_ws_transport()

        payload = {
            "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
            "mime_type": invocation.mime_type or "audio/wav",
            "language": invocation.language or "auto",
        }

        envelope = messages.RequestEnvelope(
            request_id=request.request_id,
            runtime=messages.RuntimeKind.STT,
            action=messages.RuntimeAction.INVOKE,
            payload=payload,
        )

        try:
            response = asyncio.run_coroutine_threadsafe(
                ws.invoke(envelope),
                asyncio.get_event_loop(),
            ).result(timeout=self._timeout_seconds)
        except (WebSocketTransportDisconnected, TimeoutError) as exc:
            raise RuntimeError(str(exc)) from exc

        if response.status is messages.EnvelopeStatus.FAILED:
            err = "STT transcription failed"
            if response.error:
                err = getattr(response.error, "message", None) or err
            raise RuntimeError(err)

        payload_data = response.payload or {}
        return messages.ResponseEnvelope(
            request_id=request.request_id,
            status=messages.EnvelopeStatus.SUCCEEDED,
            payload={
                "text": str(payload_data.get("text", "")),
                "language": str(
                    payload_data.get(
                        "language", invocation.language or "auto",
                    )
                ),
            },
            metadata={"ws": True, **self._metadata()},
        )

    def _open_request(
        self,
        audio_bytes: bytes,
        invocation: STTInvocationRequest,
    ):
        """Open a multipart HTTP request against the sidecar."""
        boundary = f"airunner-whisper-{uuid4().hex}"
        body = self._multipart_body(boundary, audio_bytes, invocation)
        request = Request(
            url=self._launcher.inference_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": (
                    f"multipart/form-data; boundary={boundary}"
                ),
                "Accept": "application/json",
            },
        )
        try:
            return self._http_opener(
                request, timeout=self._timeout_seconds,
            )
        except HTTPError as exc:
            message = self._http_error_message(exc)
            raise RuntimeError(message) from exc
        except URLError as exc:
            raise RuntimeError(str(exc.reason)) from exc

    def _prepare_launcher(
        self, *, for_reload: bool = False,
    ) -> None:
        """Refresh managed launcher settings before starting."""
        if not self._managed_launcher:
            return
        resolved_settings = self._settings_resolver()
        if resolved_settings == self._settings and not for_reload:
            return
        if for_reload:
            self._launcher.stop()
        self._settings = resolved_settings
        self._launcher = SidecarSTTLauncher(resolved_settings)

    @staticmethod
    def _multipart_body(
        boundary: str,
        audio_bytes: bytes,
        invocation: STTInvocationRequest,
    ) -> bytes:
        """Encode one whisper.cpp multipart inference request body."""
        parts = [
            SidecarSTTClient._form_field(
                boundary, "response_format", "json",
            ),
            SidecarSTTClient._form_field(
                boundary, "language", invocation.language or "auto",
            ),
        ]
        parts.append(
            SidecarSTTClient._file_field(
                boundary,
                filename="audio.wav",
                content_type=invocation.mime_type or "audio/wav",
                payload=audio_bytes,
            )
        )
        parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        return b"".join(parts)

    @staticmethod
    def _form_field(boundary: str, name: str, value: str) -> bytes:
        """Encode one multipart form field."""
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode("utf-8")

    @staticmethod
    def _file_field(
        boundary: str,
        *,
        filename: str,
        content_type: str,
        payload: bytes,
    ) -> bytes:
        """Encode one multipart file field."""
        header = (
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"file\"; "
            f"filename=\"{filename}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
        return b"".join([header, payload, b"\r\n"])

    @staticmethod
    def _decode_json(response: Any) -> dict[str, Any]:
        """Decode a JSON response body from the sidecar."""
        raw = response.read().decode("utf-8")
        return json.loads(raw or "{}")

    @staticmethod
    def _transcription_payload(
        data: dict[str, Any],
        language: Optional[str],
    ) -> dict[str, Any]:
        """Normalize whisper.cpp JSON into neutral payload shape."""
        text = data.get("text") or data.get("transcription", "")
        if not text and isinstance(data.get("result"), dict):
            result = data["result"]
            text = result.get("text") or result.get("transcription", "")
            language = result.get("language") or language
        return {
            "text": str(text),
            "language": data.get("language") or language,
        }

    def _metadata(self) -> dict[str, Any]:
        """Return stable sidecar metadata for health and control."""
        metadata = {
            "endpoint": self._launcher.endpoint,
            "inference_url": self._launcher.inference_url,
        }
        if self._settings.model_id:
            metadata["model_id"] = self._settings.model_id
        if self._settings.model_path:
            metadata["model_path"] = self._settings.model_path
        return metadata

    @staticmethod
    def _http_error_message(error: HTTPError) -> str:
        """Return a useful message from an HTTP error body."""
        try:
            body = error.read().decode("utf-8")
        except Exception:
            body = ""
        return body or f"HTTP {error.code} from whisper.cpp sidecar"

    @staticmethod
    def _failure_response(
        request_id: str,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> Any:
        """Return a normalized failure envelope."""
        messages = load_message_types()
        return messages.ResponseEnvelope(
            request_id=request_id,
            status=messages.EnvelopeStatus.FAILED,
            error=messages.ErrorEnvelope(
                code=code,
                message=message,
                retryable=retryable,
            ),
        )


def register_sidecar_stt_client(
    registry: RuntimeRegistry,
    stt_client: Optional[RuntimeClient] = None,
) -> RuntimeRegistry:
    """Register the sidecar-backed STT client on default routes."""
    client = stt_client or SidecarSTTClient()
    for route in (
        RuntimeRoute(
            RuntimeKind.STT,
            provider=client.descriptor.provider,
        ),
        RuntimeRoute(
            RuntimeKind.STT,
            provider=client.descriptor.provider,
            deployment_mode=RuntimeMode.SIDECAR.value,
        ),
    ):
        registry.register(route, client)
    return registry


__all__ = [
    "SidecarSTTClient",
    "register_sidecar_stt_client",
]
