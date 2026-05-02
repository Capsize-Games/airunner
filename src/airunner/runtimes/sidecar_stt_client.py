"""HTTP runtime client for the supervised whisper.cpp sidecar."""

from __future__ import annotations

import base64
import json
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

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
    STTInvocationRequest,
    TransportKind,
)
from airunner.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner.runtimes.sidecar_stt_launcher import SidecarSTTLauncher
from airunner.runtimes.whisper_cpp_runtime_settings import (
    WhisperCppRuntimeSettings,
    resolve_whisper_cpp_runtime_settings,
)

DEFAULT_PROVIDER = "local"


class SidecarSTTClient(RuntimeClient):
    """Route STT runtime envelopes through a supervised whisper.cpp server."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        *,
        settings: Optional[WhisperCppRuntimeSettings] = None,
        launcher: Optional[SidecarSTTLauncher] = None,
        http_opener=urlopen,
        timeout_seconds: float = 120.0,
    ) -> None:
        resolved_settings = settings or resolve_whisper_cpp_runtime_settings()
        self._settings = resolved_settings
        self._launcher = launcher or SidecarSTTLauncher(resolved_settings)
        self._managed_launcher = launcher is None
        self._http_opener = http_opener
        self._timeout_seconds = timeout_seconds
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.STT,
            provider=provider,
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
            endpoint=resolved_settings.endpoint,
            supports_streaming=False,
            allows_model_control=True,
        )

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
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

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Cancel active work by stopping the current sidecar process."""
        self._launcher.stop()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def close(self) -> None:
        """Release the managed sidecar process during shutdown."""
        self._launcher.stop()

    def _status_response(self, request_id: str) -> ResponseEnvelope:
        """Return a neutral status envelope for runtime control callers."""
        health = self.healthcheck()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"status": health.status.value},
            metadata=health.metadata,
        )

    def _load_model(self, request_id: str) -> ResponseEnvelope:
        """Start the managed whisper.cpp process."""
        try:
            self._prepare_launcher(for_reload=True)
            self._launcher.start()
        except RuntimeError as exc:
            return self._failure_response(
                request_id,
                "stt_load_failed",
                str(exc),
            )
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"model_status": "loaded"},
            metadata=self._metadata(),
        )

    def _unload_model(self, request_id: str) -> ResponseEnvelope:
        """Stop the managed whisper.cpp process."""
        self._launcher.stop()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"model_status": "unloaded"},
            metadata=self._metadata(),
        )

    def _transcribe(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Execute a transcription request through the whisper.cpp sidecar."""
        invocation = STTInvocationRequest.model_validate(request.payload)
        try:
            audio_bytes = base64.b64decode(invocation.audio_b64, validate=True)
        except Exception:
            return self._failure_response(
                request.request_id,
                "stt_invalid_audio",
                "Invalid base64 audio payload",
            )

        try:
            self._prepare_launcher()
            self._launcher.start()
            with self._open_request(audio_bytes, invocation) as response:
                data = self._decode_json(response)
        except RuntimeError as exc:
            return self._failure_response(
                request.request_id,
                "stt_invoke_failed",
                str(exc),
                retryable=True,
            )

        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload=self._transcription_payload(data, invocation.language),
            metadata=self._metadata(),
        )

    def _open_request(self, audio_bytes: bytes, invocation: STTInvocationRequest):
        """Open a multipart HTTP request against the sidecar inference endpoint."""
        boundary = f"airunner-whisper-{uuid4().hex}"
        body = self._multipart_body(boundary, audio_bytes, invocation)
        request = Request(
            url=self._launcher.inference_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
        )
        try:
            return self._http_opener(request, timeout=self._timeout_seconds)
        except HTTPError as exc:
            message = self._http_error_message(exc)
            raise RuntimeError(message) from exc
        except URLError as exc:
            raise RuntimeError(str(exc.reason)) from exc

    def _prepare_launcher(self, *, for_reload: bool = False) -> None:
        """Refresh managed launcher settings before starting the sidecar."""
        if not self._managed_launcher:
            return
        resolved_settings = resolve_whisper_cpp_runtime_settings()
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
        parts = []
        parts.extend(
            [
                SidecarSTTClient._form_field(
                    boundary,
                    "response_format",
                    "json",
                ),
                SidecarSTTClient._form_field(
                    boundary,
                    "language",
                    invocation.language or "auto",
                ),
            ]
        )
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
            f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
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
            f"Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
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
        """Normalize whisper.cpp JSON into AIRunner's neutral payload shape."""
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
        """Return stable sidecar metadata for health and control responses."""
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
        """Return a useful message extracted from an HTTP error body."""
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


def register_sidecar_stt_client(
    registry: RuntimeRegistry,
    stt_client: Optional[RuntimeClient] = None,
) -> RuntimeRegistry:
    """Register the sidecar-backed STT client under the explicit sidecar route."""
    client = stt_client or SidecarSTTClient()
    registry.register(
        RuntimeRoute(
            RuntimeKind.STT,
            provider=client.descriptor.provider,
            deployment_mode=RuntimeMode.SIDECAR.value,
        ),
        client,
    )
    return registry