"""HTTP runtime client for the supervised llama.cpp sidecar."""

from __future__ import annotations

import json
import shutil
from typing import Any, Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from airunner.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    RequestEnvelope,
    ResponseEnvelope,
    StreamDelta,
)
from airunner.runtimes.base import RuntimeClient
from airunner.runtimes.contracts import (
    LLMInvocationRequest,
    RuntimeAction,
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)
from airunner.runtimes.llama_cpp_runtime_settings import (
    LlamaCppRuntimeSettings,
    resolve_llama_cpp_runtime_settings,
)
from airunner.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner.runtimes.sidecar_launcher import SidecarLauncher

DEFAULT_PROVIDER = "local"


class SidecarLLMClient(RuntimeClient):
    """Route LLM runtime envelopes through a supervised llama.cpp server."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        *,
        settings: Optional[LlamaCppRuntimeSettings] = None,
        launcher: Optional[SidecarLauncher] = None,
        http_opener=urlopen,
        timeout_seconds: float = 120.0,
    ) -> None:
        resolved_settings = settings or resolve_llama_cpp_runtime_settings()
        self._settings = resolved_settings
        self._launcher = launcher or SidecarLauncher(resolved_settings)
        self._managed_launcher = launcher is None
        self._http_opener = http_opener
        self._timeout_seconds = timeout_seconds
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.LLM,
            provider=provider,
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
            endpoint=resolved_settings.endpoint,
            supports_streaming=True,
            allows_model_control=True,
        )

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Invoke a non-streaming request or a sidecar control action."""
        if request.runtime is not RuntimeKind.LLM:
            raise ValueError("SidecarLLMClient only supports LLM")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_model(request.request_id)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_model(request.request_id)
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("SidecarLLMClient only supports invoke")
        return self._invoke_chat(request)

    def stream(self, request: RequestEnvelope) -> Iterable[StreamDelta]:
        """Stream deltas from the sidecar's OpenAI-compatible endpoint."""
        invocation = LLMInvocationRequest.model_validate(request.payload)
        try:
            self._ensure_capable()
            self._launcher.start()
            payload = self._chat_payload(invocation, stream=True)
            with self._open_request(payload) as response:
                yield from self._stream_response(request.request_id, response)
        except RuntimeError as exc:
            yield self._failure_delta(request.request_id, str(exc))

    def _ensure_capable(self) -> None:
        """Verify the sidecar can be started before attempting a request.

        Raises RuntimeError with a clear diagnostic when the environment
        is missing a GGUF model or the llama-server executable.

        Skipped when the launcher is externally provided (test injection
        or custom deployment).
        """
        if not self._managed_launcher:
            return
        if not self._settings.model_path:
            raise RuntimeError(
                "No LLM model configured. Please select a GGUF model in "
                "Settings to use the local LLM."
            )
        executable = self._settings.executable
        if not self._executable_exists(executable):
            raise RuntimeError(
                f"llama-server binary not found: {executable}. "
                "Please install llama.cpp or set "
                "AIRUNNER_LLAMA_SERVER_BIN to the full path."
            )

    @staticmethod
    def _executable_exists(executable: str) -> bool:
        """Return True when an executable can be located."""
        if shutil.which(executable) is not None:
            return True
        import os
        from pathlib import Path
        expanded = os.path.expanduser(executable)
        return Path(expanded).exists()

    def healthcheck(self) -> RuntimeHealth:
        """Return the health of the managed llama.cpp runtime."""
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
        """Start the managed llama.cpp process."""
        try:
            self._prepare_launcher(for_reload=True)
            self._launcher.start()
        except RuntimeError as exc:
            return self._failure_response(
                request_id,
                "llm_load_failed",
                str(exc),
            )
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"model_status": "loaded"},
            metadata=self._metadata(),
        )

    def _unload_model(self, request_id: str) -> ResponseEnvelope:
        """Stop the managed llama.cpp process."""
        self._launcher.stop()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"model_status": "unloaded"},
            metadata=self._metadata(),
        )

    def _invoke_chat(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Execute a non-streaming chat completion through the sidecar."""
        invocation = LLMInvocationRequest.model_validate(request.payload)
        try:
            self._ensure_capable()
            self._prepare_launcher()
            self._launcher.start()
            with self._open_request(self._chat_payload(invocation)) as response:
                data = self._decode_json(response)
        except RuntimeError as exc:
            return self._failure_response(
                request.request_id,
                "llm_invoke_failed",
                str(exc),
                retryable=True,
            )

        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload=self._completion_payload(data),
            metadata=self._metadata(),
        )

    def _chat_payload(
        self,
        invocation: LLMInvocationRequest,
        *,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Convert a neutral invocation into the sidecar JSON payload."""
        payload = {
            "messages": [message.model_dump() for message in invocation.messages],
            "stream": stream,
            "temperature": invocation.temperature,
        }
        if invocation.max_tokens is not None:
            payload["max_tokens"] = invocation.max_tokens
        if invocation.model:
            payload["model"] = invocation.model
        if invocation.tool_choice is not None:
            payload["tool_choice"] = invocation.tool_choice
        return payload

    def _open_request(self, payload: dict[str, Any]):
        """Open an HTTP request against the sidecar completion endpoint."""
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url=f"{self._launcher.endpoint}/v1/chat/completions",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
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
        resolved_settings = resolve_llama_cpp_runtime_settings()
        if resolved_settings == self._settings and not for_reload:
            return
        if for_reload:
            self._launcher.stop()
        self._settings = resolved_settings
        self._launcher = SidecarLauncher(resolved_settings)

    @staticmethod
    def _decode_json(response: Any) -> dict[str, Any]:
        """Decode a JSON response body from the sidecar."""
        raw = response.read().decode("utf-8")
        return json.loads(raw or "{}")

    @staticmethod
    def _completion_payload(data: dict[str, Any]) -> dict[str, Any]:
        """Normalize sidecar JSON into AIRunner's neutral payload shape."""
        choices = data.get("choices") or [{}]
        message = choices[0].get("message") or {}
        return {
            "content": message.get("content", "") or "",
            "tools": message.get("tool_calls") or [],
            "usage": data.get("usage") or {},
        }

    def _stream_response(
        self,
        request_id: str,
        response: Any,
    ) -> Iterable[StreamDelta]:
        """Parse SSE deltas from llama.cpp into neutral runtime chunks."""
        sequence = 0
        while True:
            line = response.readline()
            if not line:
                return
            if not line.startswith(b"data:"):
                continue
            payload = line.split(b":", 1)[1].strip()
            if payload == b"[DONE]":
                yield StreamDelta(request_id=request_id, sequence=sequence, final=True)
                return

            data = json.loads(payload.decode("utf-8"))
            choice = (data.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}
            final = choice.get("finish_reason") is not None
            chunk = {}
            if delta.get("content"):
                chunk["content"] = delta["content"]
            if delta.get("tool_calls"):
                chunk["tool_calls"] = delta["tool_calls"]
            yield StreamDelta(
                request_id=request_id,
                sequence=sequence,
                delta=chunk,
                final=final,
            )
            sequence += 1
            if final:
                return

    def _metadata(self) -> dict[str, Any]:
        """Return stable sidecar metadata for health and control responses."""
        metadata = {"endpoint": self._launcher.endpoint}
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
        return body or f"HTTP {error.code} from llama.cpp sidecar"

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

    @staticmethod
    def _failure_delta(request_id: str, message: str) -> StreamDelta:
        """Return a terminal stream delta for streaming failures."""
        return StreamDelta(
            request_id=request_id,
            final=True,
            status=EnvelopeStatus.FAILED,
            metadata={"error": message},
        )


def register_sidecar_llm_client(
    registry: RuntimeRegistry,
    llm_client: Optional[RuntimeClient] = None,
) -> RuntimeRegistry:
    """Register the sidecar-backed LLM client under the default local route."""
    client = llm_client or SidecarLLMClient()
    routes = (
        RuntimeRoute(RuntimeKind.LLM, provider=client.descriptor.provider),
        RuntimeRoute(
            RuntimeKind.LLM,
            provider=client.descriptor.provider,
            deployment_mode=RuntimeMode.SIDECAR.value,
        ),
    )
    for route in routes:
        registry.register(route, client)
    return registry
