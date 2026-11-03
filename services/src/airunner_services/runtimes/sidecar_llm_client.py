"""HTTP runtime client for the supervised llama.cpp sidecar."""

from __future__ import annotations

import json
import socket
import threading
from dataclasses import dataclass
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


DEFAULT_PROVIDER = "local"
LlamaSettingsResolver = Callable[[Optional[str]], LlamaCppRuntimeSettings]


@dataclass
class _ActiveRequest:
	"""Cancellation and backend ownership for one invocation."""

	profile: Optional[str]
	cancelled: threading.Event
	response: Any = None
	backend_started: bool = False


class _SidecarRequestError(RuntimeError):
	"""A sidecar failure with a client-safe public message."""

	def __init__(self, public_message: str) -> None:
		super().__init__(public_message)
		self.public_message = public_message


class SidecarLLMClient(RuntimeClient):
	"""Route LLM runtime envelopes through a supervised llama.cpp server."""

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
		self._active_requests: dict[str, _ActiveRequest] = {}
		self._active_requests_lock = threading.RLock()
		self._launcher_lock = threading.RLock()
		self._control_action_active = False
		self.descriptor = RuntimeDescriptor(
			runtime=RuntimeKind.LLM,
			provider=provider,
			mode=RuntimeMode.SIDECAR,
			transport=TransportKind.HTTP,
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
		profile = self._runtime_profile(invocation)
		record, failure = self._reserve_request(request.request_id, profile)
		if failure is not None:
			yield self._failure_delta(request.request_id, failure[1])
			return
		try:
			self._start_for_request(request.request_id, record)
			if record.cancelled.is_set():
				yield self._cancelled_delta(request.request_id)
				return
			payload = self._chat_payload(invocation, stream=True)
			payload["stream_options"] = {"include_usage": True}
			with self._open_request(payload) as response:
				if not self._attach_response(request.request_id, record, response):
					self._complete_request(request.request_id, record)
					yield self._cancelled_delta(request.request_id)
					return
				try:
					for delta in self._stream_response(
						request.request_id, response
					):
						if delta.final:
							if not self._complete_request(
								request.request_id, record
							):
								delta = self._cancelled_delta(
									request.request_id
								)
							yield delta
							return
						yield delta
				except Exception as exc:
					if record.cancelled.is_set():
						self._complete_request(request.request_id, record)
						yield self._cancelled_delta(request.request_id)
					else:
						self._complete_request(request.request_id, record)
						yield self._failure_delta(
							request.request_id,
							self._client_error_message(exc),
						)
		except Exception as exc:
			if record.cancelled.is_set():
				self._complete_request(request.request_id, record)
				yield self._cancelled_delta(request.request_id)
			else:
				self._complete_request(request.request_id, record)
				yield self._failure_delta(
					request.request_id, self._client_error_message(exc)
				)
		finally:
			self._release_request(request.request_id, record)

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
		"""Cancel only the matching active invocation or stream."""
		messages = load_message_types()
		with self._active_requests_lock:
			record = self._active_requests.get(request_id)
			if record is not None:
				record.cancelled.set()
				response = record.response
		if record is None:
			return messages.ResponseEnvelope(
				request_id=request_id,
				status=messages.EnvelopeStatus.FAILED,
				error=messages.ErrorEnvelope(
					code="llm_request_not_active",
					message="No active request matches this ID",
					retryable=False,
				),
			)
		if response is not None:
			self._interrupt_response(response)
		return messages.ResponseEnvelope(
			request_id=request_id,
			status=messages.EnvelopeStatus.CANCELLED,
			metadata={"request_scoped": True},
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
		if not self._begin_control_action():
			return self._failure_response(
				request_id,
				"llm_runtime_busy",
				"The LLM runtime has active requests",
				retryable=True,
			)
		try:
			with self._launcher_lock:
				self._prepare_launcher(None, for_reload=True)
				self._launcher.start()
		except RuntimeError as exc:
			return self._failure_response(
				request_id,
				"llm_load_failed",
				self._client_error_message(exc),
			)
		finally:
			self._end_control_action()
		return messages.ResponseEnvelope(
			request_id=request_id,
			status=messages.EnvelopeStatus.SUCCEEDED,
			payload={"model_status": "loaded"},
			metadata=self._metadata(),
		)

	def _unload_model(self, request_id: str) -> Any:
		"""Stop the managed llama.cpp process."""
		messages = load_message_types()
		if not self._begin_control_action():
			return self._failure_response(
				request_id,
				"llm_runtime_busy",
				"The LLM runtime has active requests",
				retryable=True,
			)
		try:
			with self._launcher_lock:
				self._launcher.stop()
		finally:
			self._end_control_action()
		return messages.ResponseEnvelope(
			request_id=request_id,
			status=messages.EnvelopeStatus.SUCCEEDED,
			payload={"model_status": "unloaded"},
			metadata=self._metadata(),
		)

	def _invoke_chat(self, request: Any) -> Any:
		"""Execute a non-streaming chat completion through the sidecar."""
		messages = load_message_types()
		invocation = LLMInvocationRequest.model_validate(request.payload)
		record, failure = self._reserve_request(
			request.request_id, self._runtime_profile(invocation)
		)
		if failure is not None:
			return self._failure_response(
				request.request_id,
				failure[0],
				failure[1],
				retryable=True,
			)
		try:
			self._start_for_request(request.request_id, record)
			if record.cancelled.is_set():
				return self._cancelled_response(request.request_id)
			with self._open_request(self._chat_payload(invocation)) as response:
				if not self._attach_response(request.request_id, record, response):
					return self._cancelled_response(request.request_id)
				data = self._decode_json(response)
				if record.cancelled.is_set():
					self._complete_request(request.request_id, record)
					return self._cancelled_response(request.request_id)
			completion = self._completion_payload(data)
			if not self._complete_request(request.request_id, record):
				return self._cancelled_response(request.request_id)
		except Exception as exc:
			if record.cancelled.is_set():
				self._complete_request(request.request_id, record)
				return self._cancelled_response(request.request_id)
			self._complete_request(request.request_id, record)
			return self._failure_response(
				request.request_id,
				"llm_invoke_failed",
				self._client_error_message(exc),
				retryable=True,
			)
		finally:
			self._release_request(request.request_id, record)

		return messages.ResponseEnvelope(
			request_id=request.request_id,
			status=messages.EnvelopeStatus.SUCCEEDED,
			payload=completion,
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
			"messages": [
				message.model_dump(exclude_none=True)
				for message in invocation.messages
			],
			"stream": stream,
			"temperature": invocation.temperature,
		}
		if invocation.max_tokens is not None:
			payload["max_tokens"] = invocation.max_tokens
		if invocation.model:
			payload["model"] = invocation.model
		if invocation.tool_choice is not None:
			payload["tool_choice"] = invocation.tool_choice
		if invocation.enable_thinking is not None:
			payload["chat_template_kwargs"] = {
				"enable_thinking": invocation.enable_thinking,
			}
		runtime_profile = invocation.metadata.get("gguf_runtime_profile")
		if isinstance(runtime_profile, str) and runtime_profile.strip():
			payload["metadata"] = {
				"gguf_runtime_profile": runtime_profile.strip(),
			}
		return payload

	def _open_request(self, payload: dict[str, Any]):
		"""Open an HTTP request against the sidecar completion endpoint."""
		body = json.dumps(payload).encode("utf-8")
		headers = {
			"Content-Type": "application/json",
			"Accept": "application/json",
		}
		internal_auth_headers = getattr(
			self._launcher, "internal_auth_headers", None
		)
		if callable(internal_auth_headers):
			headers.update(internal_auth_headers())
		request = Request(
			url=f"{self._launcher.endpoint}/v1/chat/completions",
			data=body,
			method="POST",
			headers=headers,
		)
		try:
			return self._http_opener(request, timeout=self._timeout_seconds)
		except HTTPError as exc:
			try:
				exc.close()
			except Exception:
				pass
			raise _SidecarRequestError(
				f"Local LLM sidecar returned HTTP {exc.code}"
			) from exc
		except URLError as exc:
			raise _SidecarRequestError(
				"Could not connect to the local LLM sidecar"
			) from exc

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
		self._launcher.stop()
		self._settings = resolved_settings
		self._launcher = SidecarLauncher(resolved_settings)

	def _reserve_request(
		self,
		request_id: str,
		profile: Optional[str],
	) -> tuple[Optional[_ActiveRequest], Optional[tuple[str, str]]]:
		"""Reserve identity and profile before touching the shared backend."""
		selected_profile = (profile or "default").strip() or "default"
		with self._active_requests_lock:
			failure = self._reservation_conflict(
				request_id, selected_profile
			)
			if failure is not None:
				return None, failure
			record = _ActiveRequest(
				profile=profile,
				cancelled=threading.Event(),
			)
			self._active_requests[request_id] = record
			return record, None

	def _reservation_conflict(
		self,
		request_id: str,
		selected_profile: str,
	) -> Optional[tuple[str, str]]:
		"""Return a bounded conflict when an ID or backend profile is busy."""
		if request_id in self._active_requests:
			return (
				"llm_request_conflict",
				"A request with this ID is already active",
			)
		if self._control_action_active:
			return (
				"llm_runtime_busy",
				"The LLM runtime is handling a control action",
			)
		if any(
			(record.profile or "default") != selected_profile
			for record in self._active_requests.values()
		):
			return (
				"llm_runtime_busy",
				"The LLM runtime is serving another profile",
			)
		return None

	def _begin_control_action(self) -> bool:
		"""Exclude new requests while load/unload owns launcher admission."""
		with self._active_requests_lock:
			if self._control_action_active or self._active_requests:
				return False
			self._control_action_active = True
			return True

	def _end_control_action(self) -> None:
		with self._active_requests_lock:
			self._control_action_active = False

	def _start_for_request(
		self,
		request_id: str,
		record: _ActiveRequest,
	) -> None:
		"""Prepare/start under one lock and protect active backend ownership."""
		with self._launcher_lock:
			if record.cancelled.is_set():
				return
			if self._managed_launcher:
				resolved = self._resolve_settings(record.profile)
				with self._active_requests_lock:
					other_backend_users = any(
						other_id != request_id
						and (other.backend_started or other.response is not None)
						for other_id, other in self._active_requests.items()
					)
				if resolved != self._settings and other_backend_users:
					raise _SidecarRequestError(
						"The LLM runtime settings changed during an active request"
					)
				self._prepare_launcher(record.profile)
			self._launcher.start()
			with self._active_requests_lock:
				if self._active_requests.get(request_id) is record:
					record.backend_started = True

	def _attach_response(
		self,
		request_id: str,
		record: _ActiveRequest,
		response: Any,
	) -> bool:
		"""Associate transport with its owner, interrupting late cancels."""
		with self._active_requests_lock:
			active = self._active_requests.get(request_id) is record
			if active and not record.cancelled.is_set():
				record.response = response
				return True
		self._interrupt_response(response)
		return False

	def _release_request(
		self,
		request_id: str,
		record: _ActiveRequest,
	) -> None:
		"""Release only the reservation owned by this invocation."""
		with self._active_requests_lock:
			if self._active_requests.get(request_id) is record:
				self._active_requests.pop(request_id, None)

	def _complete_request(
		self,
		request_id: str,
		record: _ActiveRequest,
	) -> bool:
		"""Atomically close cancellation ownership at a terminal result."""
		with self._active_requests_lock:
			if self._active_requests.get(request_id) is record:
				self._active_requests.pop(request_id, None)
			return not record.cancelled.is_set()

	def _active_request_count(self) -> int:
		with self._active_requests_lock:
			return len(self._active_requests)

	@staticmethod
	def _interrupt_response(response: Any) -> None:
		"""Interrupt a blocked HTTP read without taking its buffered-reader lock."""
		interrupt = getattr(response, "interrupt", None)
		if callable(interrupt):
			try:
				interrupt()
				return
			except Exception:
				pass
		file_pointer = getattr(response, "fp", None)
		raw = getattr(file_pointer, "raw", None)
		sock = getattr(raw, "_sock", None)
		if sock is None:
			sock = getattr(response, "_sock", None)
		if sock is not None:
			try:
				sock.shutdown(socket.SHUT_RDWR)
				return
			except OSError:
				pass
		# Custom transports may not expose their socket. Keep the caller's
		# cancellation acknowledgment independent of a potentially locked close.
		threading.Thread(
			target=SidecarLLMClient._close_response_safely,
			args=(response,),
			daemon=True,
		).start()

	@staticmethod
	def _close_response_safely(response: Any) -> None:
		try:
			response.close()
		except Exception:
			pass

	@staticmethod
	def _cancelled_response(request_id: str) -> Any:
		messages = load_message_types()
		return messages.ResponseEnvelope(
			request_id=request_id,
			status=messages.EnvelopeStatus.CANCELLED,
			metadata={"request_scoped": True},
		)

	@staticmethod
	def _decode_json(response: Any) -> dict[str, Any]:
		"""Decode a JSON response body from the sidecar."""
		raw = response.read()
		if not raw or not raw.strip():
			raise _SidecarRequestError(
				"The local LLM sidecar returned an empty response"
			)
		data = json.loads(raw.decode("utf-8"))
		if not isinstance(data, dict) or not isinstance(data.get("choices"), list):
			raise _SidecarRequestError(
				"The local LLM sidecar returned an invalid completion"
			)
		if not data["choices"]:
			raise _SidecarRequestError(
				"The local LLM sidecar returned no completion choices"
			)
		return data

	@staticmethod
	def _completion_payload(data: dict[str, Any]) -> dict[str, Any]:
		"""Normalize sidecar JSON into AIRunner's neutral payload shape."""
		choices = data.get("choices")
		if not isinstance(choices, list) or not choices:
			raise _SidecarRequestError(
				"The local LLM sidecar returned no completion choices"
			)
		choice = choices[0]
		if not isinstance(choice, dict):
			raise _SidecarRequestError(
				"The local LLM sidecar returned an invalid completion"
			)
		message = choice.get("message")
		if not isinstance(message, dict):
			raise _SidecarRequestError(
				"The local LLM sidecar returned an invalid completion"
			)
		content = message.get("content") or ""
		tools = message.get("tool_calls") or []
		finish_reason = choice.get("finish_reason")
		if (
			not isinstance(content, str)
			or not isinstance(tools, list)
			or any(not isinstance(tool, dict) for tool in tools)
			or (finish_reason is not None and not isinstance(finish_reason, str))
		):
			raise _SidecarRequestError(
				"The local LLM sidecar returned an invalid completion"
			)
		if not content and not tools and not finish_reason:
			raise _SidecarRequestError(
				"The local LLM sidecar returned an empty completion"
			)
		usage = data.get("usage") or {}
		if not isinstance(usage, dict):
			raise _SidecarRequestError(
				"The local LLM sidecar returned invalid usage data"
			)
		return {
			"content": content,
			"tools": tools,
			"usage": usage,
			"finish_reason": finish_reason or "stop",
		}

	def _stream_response(
		self,
		request_id: str,
		response: Any,
	) -> Iterable[Any]:
		"""Parse SSE deltas from llama.cpp into neutral runtime chunks."""
		messages = load_message_types()
		sequence = 0
		usage: dict[str, Any] | None = None
		completed = False
		while True:
			line = response.readline()
			if not line:
				raise _SidecarRequestError(
					"The local LLM sidecar stream ended unexpectedly"
				)
			if not line.startswith(b"data:"):
				continue
			payload = line.split(b":", 1)[1].strip()
			if payload == b"[DONE]":
				if not completed:
					raise _SidecarRequestError(
						"The local LLM sidecar ended without a completion"
					)
				yield messages.StreamDelta(
					request_id=request_id,
					sequence=sequence,
					final=True,
					metadata={"usage": usage} if usage is not None else {},
				)
				return

			data = json.loads(payload.decode("utf-8"))
			if not isinstance(data, dict):
				raise _SidecarRequestError(
					"The local LLM sidecar returned malformed stream data"
				)
			if "error" in data and data["error"] is not None:
				raise _SidecarRequestError(
					"The local LLM sidecar reported a generation error"
				)
			if "usage" in data:
				if not isinstance(data["usage"], dict):
					raise _SidecarRequestError(
						"The local LLM sidecar returned malformed usage data"
					)
				usage = data["usage"]
			choices = data.get("choices")
			if not isinstance(choices, list):
				raise _SidecarRequestError(
					"The local LLM sidecar returned malformed stream data"
				)
			if not choices:
				if usage is None:
					raise _SidecarRequestError(
						"The local LLM sidecar returned malformed stream data"
					)
				continue
			choice = choices[0]
			if not isinstance(choice, dict):
				raise _SidecarRequestError(
					"The local LLM sidecar returned malformed stream data"
				)
			delta = choice.get("delta") or {}
			if not isinstance(delta, dict):
				raise _SidecarRequestError(
					"The local LLM sidecar returned malformed stream data"
				)
			chunk = {}
			content = delta.get("content")
			tool_calls = delta.get("tool_calls")
			finish_reason = choice.get("finish_reason")
			if content is not None and not isinstance(content, str):
				raise _SidecarRequestError(
					"The local LLM sidecar returned malformed stream data"
				)
			if tool_calls is not None and not isinstance(tool_calls, list):
				raise _SidecarRequestError(
					"The local LLM sidecar returned malformed stream data"
				)
			if finish_reason is not None and not isinstance(finish_reason, str):
				raise _SidecarRequestError(
					"The local LLM sidecar returned malformed stream data"
				)
			if content:
				chunk["content"] = content
			if tool_calls:
				chunk["tool_calls"] = tool_calls
			if finish_reason is not None:
				chunk["finish_reason"] = finish_reason
				completed = True
			if chunk.get("content") or chunk.get("tool_calls"):
				completed = True
			yield messages.StreamDelta(
				request_id=request_id,
				sequence=sequence,
				delta=chunk,
				final=False,
				metadata={"usage": usage} if usage is not None else {},
			)
			sequence += 1

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
	def _client_error_message(error: Exception) -> str:
		"""Map transport/native errors to bounded messages without raw details."""
		if isinstance(error, _SidecarRequestError):
			return error.public_message[:160]
		if isinstance(error, HTTPError):
			return f"Local LLM sidecar returned HTTP {error.code}"
		if isinstance(error, URLError):
			return "Could not connect to the local LLM sidecar"
		if isinstance(error, (TimeoutError, socket.timeout)):
			return "The local LLM sidecar request timed out"
		if isinstance(error, (json.JSONDecodeError, UnicodeDecodeError)):
			return "The local LLM sidecar returned malformed data"
		if isinstance(error, (EOFError, OSError)):
			return "The local LLM sidecar connection was interrupted"
		return "The local LLM sidecar request failed"

	@staticmethod
	def _cancelled_delta(request_id: str) -> Any:
		"""Return a terminal cancellation event for one stream."""
		messages = load_message_types()
		return messages.StreamDelta(
			request_id=request_id,
			final=True,
			status=messages.EnvelopeStatus.CANCELLED,
			metadata={"cancelled": True},
		)

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
