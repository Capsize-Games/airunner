"""HTTP runtime client for the supervised llama.cpp sidecar."""

from __future__ import annotations

import json
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
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
from airunner_services.runtimes.sidecar_http_transport import (
	CancellableHTTPTransport,
)
from airunner_services.runtimes.sidecar_openai_protocol import (
	SidecarRequestError as _SidecarRequestError,
	completion_payload as normalize_completion_payload,
	decode_completion_json,
	iter_openai_sse,
	stream_deltas,
)


DEFAULT_PROVIDER = "local"
LlamaSettingsResolver = Callable[..., LlamaCppRuntimeSettings]


@dataclass
class _ActiveRequest:
	"""Cancellation and backend ownership for one invocation."""

	profile: Optional[str]
	cancelled: threading.Event
	expected_binding: Optional[str] = None
	response: Any = None
	backend_started: bool = False


class _LeasedOpenAIStream:
	"""Own one cancellable request lease, including an unstarted stream."""

	def __init__(
		self,
		client: "SidecarLLMClient",
		request_id: str,
		record: _ActiveRequest,
		source: Iterable[dict[str, Any]],
	) -> None:
		self._client = client
		self._request_id = request_id
		self._record = record
		self._source = iter(source)
		self._finished = False

	def __iter__(self) -> "_LeasedOpenAIStream":
		return self

	def __next__(self) -> dict[str, Any]:
		if self._finished:
			raise StopIteration
		try:
			return next(self._source)
		except BaseException:
			self._finish()
			raise

	def close(self) -> None:
		"""Cancel this lease and release it after an in-flight read exits."""
		if self._finished:
			return
		self._record.cancelled.set()
		if self._record.response is not None:
			self._client._interrupt_response(self._record.response)
		try:
			close = getattr(self._source, "close", None)
			if callable(close):
				close()
		except ValueError:
			# The iterator is currently executing; its next() call will finish
			# the lease after the interrupted transport returns.
			return
		finally:
			if not self._source_is_running():
				self._finish()

	def _source_is_running(self) -> bool:
		state = getattr(self._source, "gi_running", False)
		return bool(state)

	def _finish(self) -> None:
		if self._finished:
			return
		self._finished = True
		self._client._release_request(self._request_id, self._record)

	def __del__(self) -> None:
		self.close()



class SidecarLLMClient(RuntimeClient):
	"""Route LLM runtime envelopes through a supervised llama.cpp server."""

	def __init__(
		self,
		provider: str = DEFAULT_PROVIDER,
		*,
		settings: Optional[LlamaCppRuntimeSettings] = None,
		settings_resolver: Optional[LlamaSettingsResolver] = None,
		launcher: Optional[SidecarLauncher] = None,
		http_opener=None,
		timeout_seconds: float = 120.0,
	) -> None:
		self._uses_default_settings_resolver = (
			settings_resolver is None
			or settings_resolver is resolve_llama_cpp_runtime_settings
		)
		self._settings_resolver = (
			settings_resolver or resolve_llama_cpp_runtime_settings
		)
		resolved_settings = settings or self._resolve_settings(None)
		self._settings = resolved_settings
		self._launcher = launcher or SidecarLauncher(resolved_settings)
		self._managed_launcher = launcher is None
		self._uses_default_http_opener = http_opener is None
		self._http_opener = urlopen if http_opener is None else http_opener
		self._timeout_seconds = timeout_seconds
		self._active_requests: dict[str, _ActiveRequest] = {}
		self._active_requests_lock = threading.RLock()
		self._active_requests_condition = threading.Condition(
			self._active_requests_lock
		)
		self._launcher_lock = threading.RLock()
		self._control_action_active = False
		self._bound_model_selection: Optional[dict[str, Any]] = None
		self._bound_backend_identity: Optional[tuple[Any, ...]] = None
		self._bound_model_file_identity: Optional[tuple[Any, ...]] = None
		self._bound_model_token: Optional[str] = None
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
			with self._open_request(payload, record=record) as response:
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
		"""Release the shared process through centralized lease admission."""
		if not self.stop_backend():
			raise RuntimeError(
				"The shared LLM backend still has active requests"
			)

	def start_backend(
		self,
		runtime_profile: Optional[str],
		*,
		model_path: Optional[str] = None,
		model_id: Optional[str] = None,
		n_ctx: Optional[int] = None,
		n_gpu_layers: Optional[int] = None,
		timeout_seconds: float = 120.0,
	) -> str:
		"""Bind and load one selected model, returning its request lease token."""
		selection = self._model_selection(
			model_path=model_path,
			model_id=model_id,
			n_ctx=n_ctx,
			n_gpu_layers=n_gpu_layers,
		)
		self._acquire_control_action(wait_for_idle=True, timeout_seconds=timeout_seconds)
		try:
			with self._launcher_lock:
				previous_identity = self._bound_backend_identity
				self._prepare_launcher(
					runtime_profile,
					selected_model=selection,
				)
				self._validate_selected_model(
					self._settings,
					selection,
					runtime_profile,
				)
				identity = self._backend_identity(
					self._settings, selection, runtime_profile
				)
				if (
					previous_identity is not None
					and identity != previous_identity
				):
					# Settings equality misses replacement of a GGUF at the same path.
					self._launcher.stop()
				self._launcher.start()
				if (
					self._backend_identity(
						self._settings, selection, runtime_profile
					)
					!= identity
				):
					self._launcher.stop()
					raise RuntimeError(
						"The selected GGUF file changed while the backend was loading"
					)
				return self._set_backend_binding(identity, selection)
		finally:
			self._end_control_action()

	def current_binding(
		self,
		runtime_profile: Optional[str],
		*,
		model_path: Optional[str],
		model_id: Optional[str],
		n_ctx: Optional[int],
		n_gpu_layers: Optional[int],
	) -> Optional[str]:
		"""Return a ready matching backend token without changing its state."""
		selection = self._model_selection(
			model_path=model_path,
			model_id=model_id,
			n_ctx=n_ctx,
			n_gpu_layers=n_gpu_layers,
		)
		with self._active_requests_lock:
			token = self._bound_model_token
			identity = self._bound_backend_identity
			settings = self._settings
			launcher = self._launcher
		if token is None or identity is None:
			return None
		try:
			self._validate_selected_model(settings, selection, runtime_profile)
			expected_identity = self._backend_identity(
				settings, selection, runtime_profile
			)
		except (OSError, RuntimeError, ValueError):
			return None
		if identity != expected_identity:
			return None
		health_status = getattr(launcher, "health_status", None)
		if not callable(health_status):
			return None
		try:
			status, _details = health_status()
		except Exception:
			return None
		if getattr(status, "value", status) != "ready":
			return None
		with self._active_requests_lock:
			if (
				self._bound_model_token != token
				or self._bound_backend_identity != identity
				or self._launcher is not launcher
			):
				return None
		return token

	def stop_backend(
		self,
		*,
		expected_binding: Optional[str] = None,
		timeout_seconds: float = 120.0,
	) -> bool:
		"""Unload the shared backend after current request leases drain."""
		# Stale proxies no longer own this backend, so they must not wait for
		# unrelated active request leases before returning a no-op.
		if expected_binding is not None:
			with self._active_requests_lock:
				if expected_binding != self._bound_model_token:
					return True
		try:
			self._acquire_control_action(
				wait_for_idle=True,
				timeout_seconds=timeout_seconds,
			)
		except RuntimeError:
			return False
		try:
			with self._launcher_lock:
				if (
					expected_binding is not None
					and expected_binding != self._bound_model_token
				):
					# A stale adapter no longer owns the currently loaded model.
					return True
				self._launcher.stop()
				self._clear_backend_binding()
			return True
		finally:
			self._end_control_action()

	def openai_request(
		self,
		request_id: str,
		payload: dict[str, Any],
		*,
		runtime_profile: Optional[str],
		endpoint_path: str,
		expected_binding: Optional[str] = None,
	) -> Any:
		"""Proxy one native-model API request through this leased backend."""
		if endpoint_path not in {"/v1/chat/completions", "/v1/completions"}:
			raise ValueError("Unsupported llama-server completion endpoint")
		if payload.get("stream") is True:
			return self._stream_openai_request(
				request_id,
				payload,
				runtime_profile=runtime_profile,
				endpoint_path=endpoint_path,
				expected_binding=expected_binding,
			)
		return self._invoke_openai_request(
			request_id,
			payload,
			runtime_profile=runtime_profile,
			endpoint_path=endpoint_path,
			expected_binding=expected_binding,
		)

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
				identity = self._backend_identity(
					self._settings, None, self._settings.runtime_profile
				)
				self._set_backend_binding(identity, None, force_new=True)
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
				self._clear_backend_binding()
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
			with self._open_request(
				self._chat_payload(invocation), record=record
			) as response:
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

	def _invoke_openai_request(
		self,
		request_id: str,
		payload: dict[str, Any],
		*,
		runtime_profile: Optional[str],
		endpoint_path: str,
		expected_binding: Optional[str],
	) -> dict[str, Any]:
		record, failure = self._reserve_request(
			request_id, runtime_profile, expected_binding=expected_binding
		)
		if failure is not None or record is None:
			message = failure[1] if failure is not None else "The LLM runtime is busy"
			raise _SidecarRequestError(message)
		try:
			self._start_for_request(request_id, record)
			if record.cancelled.is_set():
				raise _SidecarRequestError("The LLM request was cancelled")
			with self._open_request(
				payload, endpoint_path=endpoint_path, record=record
			) as response:
				if not self._attach_response(request_id, record, response):
					raise _SidecarRequestError("The LLM request was cancelled")
				data = self._decode_json(response)
			if not self._complete_request(request_id, record):
				raise _SidecarRequestError("The LLM request was cancelled")
			return data
		except Exception as exc:
			self._complete_request(request_id, record)
			if isinstance(exc, _SidecarRequestError):
				raise
			raise _SidecarRequestError(self._client_error_message(exc)) from exc
		finally:
			self._release_request(request_id, record)

	def _stream_openai_request(
		self,
		request_id: str,
		payload: dict[str, Any],
		*,
		runtime_profile: Optional[str],
		endpoint_path: str,
		expected_binding: Optional[str],
	) -> Iterable[dict[str, Any]]:
		record, failure = self._reserve_request(
			request_id, runtime_profile, expected_binding=expected_binding
		)
		if failure is not None or record is None:
			message = failure[1] if failure is not None else "The LLM runtime is busy"
			raise _SidecarRequestError(message)
		return _LeasedOpenAIStream(
			self,
			request_id,
			record,
			self._stream_openai_request_body(
				request_id,
			payload,
				record=record,
				endpoint_path=endpoint_path,
			),
		)

	def _stream_openai_request_body(
		self,
		request_id: str,
		payload: dict[str, Any],
		*,
		record: _ActiveRequest,
		endpoint_path: str,
	) -> Iterable[dict[str, Any]]:
		"""Run the already reserved stream request."""
		try:
			self._start_for_request(request_id, record)
			if record.cancelled.is_set():
				return
			with self._open_request(
				payload, endpoint_path=endpoint_path, record=record
			) as response:
				if not self._attach_response(request_id, record, response):
					return
				for event in self._iter_openai_sse(response):
					if record.cancelled.is_set():
						return
					yield event
			if not self._complete_request(request_id, record):
				return
		except Exception as exc:
			if record.cancelled.is_set():
				return
			self._complete_request(request_id, record)
			if isinstance(exc, _SidecarRequestError):
				raise
			raise _SidecarRequestError(self._client_error_message(exc)) from exc
		finally:
			self._release_request(request_id, record)

	@staticmethod
	def _iter_openai_sse(response: Any) -> Iterable[dict[str, Any]]:
		"""Yield validated provider SSE events for compatibility callers."""
		return iter_openai_sse(response)

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

	def _open_request(
		self,
		payload: dict[str, Any],
		*,
		endpoint_path: str = "/v1/chat/completions",
		record: Optional[_ActiveRequest] = None,
	):
		"""Open one authenticated request through the selected HTTP transport."""
		request = self._build_http_request(payload, endpoint_path)
		if self._uses_default_http_opener:
			return self._open_cancellable_request(request, record)
		return self._open_injected_request(request)

	def _build_http_request(
		self, payload: dict[str, Any], endpoint_path: str
	) -> Request:
		"""Build the HTTP request and apply private sidecar auth headers."""
		headers = {
			"Content-Type": "application/json",
			"Accept": (
				"text/event-stream"
				if payload.get("stream") is True
				else "application/json"
			),
		}
		internal_auth_headers = getattr(
			self._launcher, "internal_auth_headers", None
		)
		if callable(internal_auth_headers):
			headers.update(internal_auth_headers())
		return Request(
			url=f"{self._launcher.endpoint}{endpoint_path}",
			data=json.dumps(payload).encode("utf-8"),
			method="POST",
			headers=headers,
		)

	def _open_cancellable_request(
		self, request: Request, record: Optional[_ActiveRequest]
	):
		"""Open a default transport with cancellation published before headers."""
		transport = CancellableHTTPTransport(request, self._timeout_seconds)
		if record is not None:
			with self._active_requests_lock:
				if record.cancelled.is_set():
					transport.interrupt()
					raise _SidecarRequestError(
						"The LLM request was cancelled"
					)
				record.response = transport
		try:
			return transport.open()
		except HTTPError as exc:
			try:
				exc.close()
			finally:
				transport.close()
			raise _SidecarRequestError(
				f"Local LLM sidecar returned HTTP {exc.code}"
			) from exc
		except URLError as exc:
			transport.close()
			raise _SidecarRequestError(
				"Could not connect to the local LLM sidecar"
			) from exc
		except Exception:
			transport.close()
			raise

	def _open_injected_request(self, request: Request):
		"""Use a caller-supplied opener without changing its invocation contract."""
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
		*,
		selected_model: Optional[dict[str, Any]] = None,
	) -> LlamaCppRuntimeSettings:
		"""Resolve a profile's settings for one optional selected model."""
		selection = selected_model or {}
		if self._uses_default_settings_resolver:
			return resolve_llama_cpp_runtime_settings(
				runtime_profile=runtime_profile,
				selected_model_id=selection.get("model_id"),
				selected_model_path=selection.get("model_path"),
				selected_n_ctx=selection.get("n_ctx"),
				selected_n_gpu_layers=selection.get("n_gpu_layers"),
			)
		try:
			resolved = self._settings_resolver(
				runtime_profile,
				**{
					f"selected_{key}": value
					for key, value in selection.items()
				},
			)
		except TypeError:
			try:
				resolved = self._settings_resolver(runtime_profile)
			except TypeError:
				resolved = self._settings_resolver()
			if not selection:
				return resolved
			selected_model_id = selection.get("model_id")
			selected_model_path = selection.get("model_path")
			if not selected_model_path or not resolved.model_path:
				raise RuntimeError(
					"The sidecar settings resolver cannot bind the selected GGUF"
				)
			try:
				models_match = Path(selected_model_path).expanduser().samefile(
					Path(resolved.model_path).expanduser()
				)
			except OSError:
				models_match = False
			if not models_match:
				raise RuntimeError(
					"The configured sidecar model does not match the selected GGUF"
				)
			if (
				resolved.model_id
				and selected_model_id
				and resolved.model_id != selected_model_id
			):
				raise RuntimeError(
					"The configured sidecar model does not match the selected GGUF"
				)
			resolved = replace(
				resolved,
				model_id=selected_model_id or resolved.model_id,
				runtime_profile=runtime_profile or "default",
				n_ctx=(selection.get("n_ctx") or resolved.n_ctx),
				n_gpu_layers=(
					selection.get("n_gpu_layers")
					if selection.get("n_gpu_layers") is not None
					else resolved.n_gpu_layers
				),
			)
		return resolved

	@staticmethod
	def _model_selection(
		*,
		model_path: Optional[str],
		model_id: Optional[str],
		n_ctx: Optional[int],
		n_gpu_layers: Optional[int],
	) -> Optional[dict[str, Any]]:
		if not model_path:
			return None
		return {
			"model_path": str(model_path),
			"model_id": model_id,
			"n_ctx": n_ctx,
			"n_gpu_layers": n_gpu_layers,
		}

	@staticmethod
	def _validate_selected_model(
		settings: LlamaCppRuntimeSettings,
		selection: Optional[dict[str, Any]],
		runtime_profile: Optional[str] = None,
	) -> None:
		"""Require launcher settings to match the adapter's actual GGUF file."""
		if selection is None:
			return
		selected_path = Path(selection["model_path"]).expanduser().resolve(
			strict=True
		)
		configured_path = Path(settings.model_path or "").expanduser().resolve(
			strict=True
		)
		if (
			not selected_path.is_file()
			or selected_path.suffix.lower() != ".gguf"
			or not configured_path.is_file()
			or not selected_path.samefile(configured_path)
		):
			raise RuntimeError(
				"The configured sidecar model does not match the selected GGUF"
			)
		selected_model_id = selection.get("model_id")
		if (
			settings.model_id
			and selected_model_id
			and settings.model_id != selected_model_id
		):
			raise RuntimeError(
				"The configured sidecar model ID does not match the selected GGUF"
			)
		if selection.get("n_ctx") is not None and settings.n_ctx != selection["n_ctx"]:
			raise RuntimeError(
				"The configured sidecar context does not match the selected GGUF"
			)
		if (
			selection.get("n_gpu_layers") is not None
			and settings.n_gpu_layers != selection["n_gpu_layers"]
		):
			raise RuntimeError(
				"The configured sidecar offload does not match the selected GGUF"
			)
		if (
			runtime_profile
			and settings.runtime_profile != runtime_profile
		):
			raise RuntimeError(
				"The configured sidecar profile does not match the selected GGUF"
			)

	def _prepare_launcher(
		self,
		runtime_profile: Optional[str],
		*,
		for_reload: bool = False,
		selected_model: Optional[dict[str, Any]] = None,
	) -> None:
		"""Refresh managed launcher settings before starting the sidecar."""
		if not self._managed_launcher:
			return
		resolved_settings = self._resolve_settings(
			runtime_profile,
			selected_model=selected_model,
		)
		if resolved_settings == self._settings and not for_reload:
			return
		self._launcher.stop()
		self._settings = resolved_settings
		self._launcher = SidecarLauncher(resolved_settings)

	@staticmethod
	def _model_file_identity(model_path: Optional[str]) -> Optional[tuple[Any, ...]]:
		"""Fingerprint the selected file without reading model contents."""
		if not model_path:
			return None
		try:
			path = Path(model_path).expanduser().resolve(strict=True)
			stat = path.stat()
		except OSError:
			return None
		if not path.is_file():
			return None
		return (
			str(path),
			stat.st_dev,
			stat.st_ino,
			stat.st_size,
			stat.st_mtime_ns,
			stat.st_ctime_ns,
		)

	@classmethod
	def _backend_identity(
		cls,
		settings: LlamaCppRuntimeSettings,
		selection: Optional[dict[str, Any]],
		runtime_profile: Optional[str],
	) -> tuple[Any, ...]:
		"""Return immutable identity for model bytes and effective settings."""
		model_path = (
			selection.get("model_path") if selection else settings.model_path
		)
		model_id = (
			selection.get("model_id") if selection else settings.model_id
		)
		settings_identity = tuple(
			sorted((key, repr(value)) for key, value in settings.__dict__.items())
		)
		return (
			runtime_profile or settings.runtime_profile or "default",
			model_id,
			cls._model_file_identity(model_path),
			settings_identity,
		)

	def _set_backend_binding(
		self,
		identity: tuple[Any, ...],
		selection: Optional[dict[str, Any]],
		*,
		force_new: bool = False,
	) -> str:
		"""Publish one loaded backend identity and its opaque lease token."""
		with self._active_requests_lock:
			if (
				force_new
				or identity != self._bound_backend_identity
				or self._bound_model_token is None
			):
				self._bound_model_token = uuid.uuid4().hex
			self._bound_backend_identity = identity
			self._bound_model_file_identity = identity[2]
			self._bound_model_selection = selection
			return self._bound_model_token

	def _clear_backend_binding(self) -> None:
		"""Invalidate tokens held by adapters after unload."""
		with self._active_requests_lock:
			self._bound_model_selection = None
			self._bound_backend_identity = None
			self._bound_model_file_identity = None
			self._bound_model_token = None

	def _binding_failure(self, expected_binding: str) -> Optional[str]:
		"""Explain why a proxy's selected model lease is stale."""
		if expected_binding != self._bound_model_token:
			return "The selected LLM backend changed; reload the selected model"
		if self._bound_model_file_identity is not None:
			selection = self._bound_model_selection or {}
			model_path = selection.get("model_path") or self._settings.model_path
			if (
				self._model_file_identity(model_path)
				!= self._bound_model_file_identity
			):
				return "The selected GGUF file changed; reload the selected model"
		return None

	def _reserve_request(
		self,
		request_id: str,
		profile: Optional[str],
		*,
		expected_binding: Optional[str] = None,
	) -> tuple[Optional[_ActiveRequest], Optional[tuple[str, str]]]:
		"""Reserve identity and profile before touching the shared backend."""
		selected_profile = (profile or "default").strip() or "default"
		with self._active_requests_lock:
			failure = self._reservation_conflict(
				request_id, selected_profile, expected_binding
			)
			if failure is not None:
				return None, failure
			record = _ActiveRequest(
				profile=profile,
				cancelled=threading.Event(),
				expected_binding=expected_binding,
			)
			self._active_requests[request_id] = record
			return record, None

	def _reservation_conflict(
		self,
		request_id: str,
		selected_profile: str,
		expected_binding: Optional[str] = None,
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
		if expected_binding is not None:
			binding_failure = self._binding_failure(expected_binding)
			if binding_failure is not None:
				return ("llm_model_binding_stale", binding_failure)
		if any(
			(record.profile or "default") != selected_profile
			for record in self._active_requests.values()
		):
			return (
				"llm_runtime_busy",
				"The LLM runtime is serving another profile",
			)
		if expected_binding is not None and any(
			record.expected_binding is not None
			and record.expected_binding != expected_binding
			for record in self._active_requests.values()
		):
			return (
				"llm_runtime_busy",
				"The LLM runtime is serving another model binding",
			)
		return None

	def _begin_control_action(self) -> bool:
		"""Exclude new requests while load/unload owns launcher admission."""
		with self._active_requests_lock:
			if self._control_action_active or self._active_requests:
				return False
			self._control_action_active = True
			return True

	def _acquire_control_action(
		self,
		*,
		wait_for_idle: bool,
		timeout_seconds: float,
	) -> None:
		"""Reserve load/unload admission, optionally waiting for leases."""
		deadline = time.monotonic() + max(0.0, timeout_seconds)
		with self._active_requests_condition:
			if self._control_action_active:
				raise RuntimeError("LLM runtime control is already active")
			self._control_action_active = True
			while self._active_requests:
				if not wait_for_idle:
					self._control_action_active = False
					self._active_requests_condition.notify_all()
					raise RuntimeError("LLM runtime has active requests")
				remaining = deadline - time.monotonic()
				if remaining <= 0:
					self._control_action_active = False
					self._active_requests_condition.notify_all()
					raise RuntimeError("Timed out waiting for active LLM requests")
				self._active_requests_condition.wait(remaining)

	def _end_control_action(self) -> None:
		with self._active_requests_condition:
			self._control_action_active = False
			self._active_requests_condition.notify_all()

	def _start_for_request(
		self,
		request_id: str,
		record: _ActiveRequest,
	) -> None:
		"""Prepare/start under one lock and protect active backend ownership."""
		with self._launcher_lock:
			if record.cancelled.is_set():
				return
			if record.expected_binding is not None:
				binding_failure = self._binding_failure(
					record.expected_binding
				)
				if binding_failure is not None:
					raise _SidecarRequestError(binding_failure)
			if self._managed_launcher:
				selected_model = self._bound_model_selection
				if (
					selected_model is not None
					and (record.profile or "default")
					!= (self._settings.runtime_profile or "default")
				):
					selected_model = None
				resolved = self._resolve_settings(
					record.profile,
					selected_model=selected_model,
				)
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
				self._prepare_launcher(
					record.profile,
					selected_model=selected_model,
				)
				self._validate_selected_model(
					self._settings,
					selected_model,
					record.profile,
				)
			self._launcher.start()
			if record.expected_binding is None and self._managed_launcher:
				identity = self._backend_identity(
					self._settings, selected_model, record.profile
				)
				self._set_backend_binding(identity, selected_model)
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
		with self._active_requests_condition:
			if self._active_requests.get(request_id) is record:
				self._active_requests.pop(request_id, None)
				self._active_requests_condition.notify_all()

	def _complete_request(
		self,
		request_id: str,
		record: _ActiveRequest,
	) -> bool:
		"""Atomically close cancellation ownership at a terminal result."""
		with self._active_requests_condition:
			if self._active_requests.get(request_id) is record:
				self._active_requests.pop(request_id, None)
				self._active_requests_condition.notify_all()
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
		"""Decode an OpenAI-compatible completion response."""
		return decode_completion_json(response)

	@staticmethod
	def _completion_payload(data: dict[str, Any]) -> dict[str, Any]:
		"""Normalize provider completion data for compatibility callers."""
		return normalize_completion_payload(data)

	def _stream_response(
		self,
		request_id: str,
		response: Any,
	) -> Iterable[Any]:
		"""Convert provider SSE events to neutral stream deltas."""
		return stream_deltas(request_id, response)

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
