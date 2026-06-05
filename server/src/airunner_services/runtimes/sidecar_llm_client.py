"""HTTP+WebSocket runtime client for the supervised llama.cpp sidecar."""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from airunner_services.runtimes.contracts import LLMInvocationRequest
from airunner_services.runtimes.contracts import RuntimeAction
from airunner_services.runtimes.contracts import RuntimeDescriptor
from airunner_services.runtimes.contracts import RuntimeHealth
from airunner_services.runtimes.contracts import RuntimeKind
from airunner_services.runtimes.contracts import RuntimeMode
from airunner_services.runtimes.contracts import TransportKind
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.llama_cpp_runtime_settings import (
	LlamaCppRuntimeSettings,
	resolve_llama_cpp_runtime_settings,
)
from airunner_services.runtimes.message_envelopes import load_message_types
from airunner_services.runtimes.registry import RuntimeRegistry
from airunner_services.runtimes.registry import RuntimeRoute
from airunner_services.runtimes.sidecar_launcher import SidecarLauncher
from airunner_services.runtimes.websocket_transport import (
	SidecarWebSocketTransport,
)

DEFAULT_PROVIDER = "local"
LlamaSettingsResolver = Callable[[Optional[str]], LlamaCppRuntimeSettings]


class SidecarLLMClient(RuntimeClient):
	"""Route LLM runtime envelopes through a supervised llama.cpp server.

	Supports both WebSocket (via the llm_ws_adapter process) and HTTP
	(direct to llama.cpp).  WebSocket is preferred for consistency with
	other sidecar runtimes.
	"""

	def __init__(
		self,
		provider: str = DEFAULT_PROVIDER,
		*,
		settings: Optional[LlamaCppRuntimeSettings] = None,
		settings_resolver: Optional[LlamaSettingsResolver] = None,
		launcher: Optional[SidecarLauncher] = None,
		http_opener=urlopen,
		timeout_seconds: float = 120.0,
	) -> None:
		self._settings_resolver = (
			settings_resolver or resolve_llama_cpp_runtime_settings
		)
		resolved_settings = settings or self._resolve_settings(None)
		self._settings = resolved_settings
		self._launcher = launcher or SidecarLauncher(resolved_settings)
		self._managed_launcher = launcher is None
		self._http_opener = http_opener
		self._timeout_seconds = timeout_seconds
		self._ws_transport: Optional[SidecarWebSocketTransport] = None
		# Adapter port offset: adapter listens on llama.cpp port + 1000
		self._adapter_port = resolved_settings.port + 1000

		self.descriptor = RuntimeDescriptor(
			transport=TransportKind.WEBSOCKET,
			runtime=RuntimeKind.LLM,
			provider=provider,
			mode=RuntimeMode.SIDECAR,
			endpoint=resolved_settings.endpoint,
			supports_streaming=True,
			allows_model_control=True,
		)

	def invoke(self, request: Any) -> Any:
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

	def stream(self, request: Any) -> Iterable[Any]:
		"""Stream deltas from the sidecar's OpenAI-compatible endpoint."""
		invocation = LLMInvocationRequest.model_validate(request.payload)
		try:
			self._prepare_launcher(
				self._runtime_profile(invocation),
			)
			self._launcher.start()
			payload = self._chat_payload(invocation, stream=True)
			with self._open_request(payload) as response:
				yield from self._stream_response(request.request_id, response)
		except RuntimeError as exc:
			yield self._failure_delta(request.request_id, str(exc))

	def healthcheck(self) -> RuntimeHealth:
		"""Return the health of the managed llama.cpp runtime."""
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
		"""Start the managed llama.cpp process."""
		messages = load_message_types()
		try:
			self._prepare_launcher(None, for_reload=True)
			self._launcher.start()
		except RuntimeError as exc:
			return self._failure_response(
				request_id,
				"llm_load_failed",
				str(exc),
			)
		return messages.ResponseEnvelope(
			request_id=request_id,
			status=messages.EnvelopeStatus.SUCCEEDED,
			payload={"model_status": "loaded"},
			metadata=self._metadata(),
		)

	def _unload_model(self, request_id: str) -> Any:
		"""Stop the managed llama.cpp process."""
		messages = load_message_types()
		self._launcher.stop()
		return messages.ResponseEnvelope(
			request_id=request_id,
			status=messages.EnvelopeStatus.SUCCEEDED,
			payload={"model_status": "unloaded"},
			metadata=self._metadata(),
		)

	def _invoke_chat(self, request: Any) -> Any:
		"""Execute a non-streaming chat completion via WebSocket adapter.

		Raises immediately when the WebSocket connection cannot be
		established -- no HTTP fallback.
		"""
		invocation = LLMInvocationRequest.model_validate(request.payload)
		try:
			self._prepare_launcher(self._runtime_profile(invocation))
			self._launcher.start()
			return self._invoke_via_websocket(request, invocation)
		except RuntimeError as exc:
			return self._failure_response(
				request.request_id,
				"llm_invoke_failed",
				str(exc),
				retryable=True,
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
		runtime_profile = invocation.metadata.get("gguf_runtime_profile")
		if isinstance(runtime_profile, str) and runtime_profile.strip():
			payload["metadata"] = {
				"gguf_runtime_profile": runtime_profile.strip(),
			}
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

	@staticmethod
	def _runtime_profile(invocation: LLMInvocationRequest) -> Optional[str]:
		"""Return the requested GGUF runtime profile from invocation metadata."""
		profile = invocation.metadata.get("gguf_runtime_profile")
		if not isinstance(profile, str):
			return None
		return profile.strip() or None

	def _resolve_settings(
		self,
		runtime_profile: Optional[str],
	) -> LlamaCppRuntimeSettings:
		"""Resolve runtime settings with backward-compatible resolver calls."""
		try:
			return self._settings_resolver(runtime_profile)
		except TypeError:
			return self._settings_resolver()

	def _prepare_launcher(
		self,
		runtime_profile: Optional[str],
		*,
		for_reload: bool = False,
	) -> None:
		"""Refresh managed launcher settings before starting the sidecar."""
		if not self._managed_launcher:
			return
		resolved_settings = self._resolve_settings(runtime_profile)
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
	) -> Iterable[Any]:
		"""Parse SSE deltas from llama.cpp into neutral runtime chunks."""
		messages = load_message_types()
		sequence = 0
		while True:
			line = response.readline()
			if not line:
				return
			if not line.startswith(b"data:"):
				continue
			payload = line.split(b":", 1)[1].strip()
			if payload == b"[DONE]":
				yield messages.StreamDelta(
					request_id=request_id,
					sequence=sequence,
					final=True,
				)
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
			yield messages.StreamDelta(
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
		metadata["runtime_profile"] = self._settings.runtime_profile
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

	@staticmethod
	def _failure_delta(request_id: str, message: str) -> Any:
		"""Return a terminal stream delta for streaming failures."""
		messages = load_message_types()
		return messages.StreamDelta(
			request_id=request_id,
			final=True,
			status=messages.EnvelopeStatus.FAILED,
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


__all__ = ["SidecarLLMClient", "register_sidecar_llm_client"]