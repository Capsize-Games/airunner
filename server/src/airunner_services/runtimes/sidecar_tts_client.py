"""HTTP+WebSocket runtime client for the supervised TTS sidecar."""

from __future__ import annotations

import asyncio
import base64
import threading
from dataclasses import replace
from typing import Any, Callable, Optional, Protocol
from urllib.parse import urlencode

import requests

from airunner_services.runtimes.contracts import RuntimeAction
from airunner_services.runtimes.contracts import RuntimeDescriptor
from airunner_services.runtimes.contracts import RuntimeHealth
from airunner_services.runtimes.contracts import RuntimeHealthStatus
from airunner_services.runtimes.contracts import RuntimeKind
from airunner_services.runtimes.contracts import RuntimeMode
from airunner_services.runtimes.contracts import TTSInvocationRequest
from airunner_services.runtimes.contracts import TransportKind
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.message_envelopes import load_message_types
from airunner_services.runtimes.registry import RuntimeRegistry
from airunner_services.runtimes.registry import RuntimeRoute
from airunner_services.runtimes.sidecar_tts_launcher import (
	SidecarTTSLauncher,
)
from airunner_services.runtimes.tts_daemon_runtime_settings import (
	TTSDaemonRuntimeSettings,
	resolve_tts_daemon_runtime_settings,
)
from airunner_services.runtimes.websocket_transport import (
	SidecarWebSocketTransport,
	WebSocketTransportDisconnected,
)

DEFAULT_PROVIDER = "local"
_INNER_RUNTIME_STATUS_TIMEOUT_SECONDS = 1.0


class TTSLauncherLike(Protocol):
	"""Launcher contract required by the TTS sidecar client."""

	endpoint: str
	api_base_url: str

	def start(self) -> None: ...
	def stop(self) -> None: ...
	def is_running(self) -> bool: ...
	def is_ready(self) -> bool: ...
	def health_status(self) -> tuple[RuntimeHealthStatus, str]: ...


TTSLauncherFactory = Callable[[TTSDaemonRuntimeSettings], TTSLauncherLike]


class SidecarTTSClient(RuntimeClient):
	"""Route TTS envelopes through one supervised sidecar daemon.

	Supports both WebSocket (preferred) and HTTP (legacy) transport.
	WebSocket is used for INVOKE actions when enabled.
	"""

	@staticmethod
	def _normalize_model_type(value: Any) -> Optional[str]:
		"""Return one stable TTS model name string for sidecar settings."""
		if value is None:
			return None
		resolved = getattr(value, "value", value)
		text = str(resolved).strip()
		if not text:
			return None
		if "." in text:
			text = text.split(".")[-1]
		alias = {
			"OPENVOICE": "OpenVoice",
			"ESPEAK": "Espeak",
		}
		return alias.get(text.upper(), text)

	def __init__(
		self,
		provider: str = DEFAULT_PROVIDER,
		*,
		settings: Optional[TTSDaemonRuntimeSettings] = None,
		launcher: Optional[TTSLauncherLike] = None,
		launcher_factory: Optional[TTSLauncherFactory] = None,
		session: Optional[requests.Session] = None,
	) -> None:
		resolved_settings = settings or resolve_tts_daemon_runtime_settings()
		resolved_launcher_factory = launcher_factory
		if launcher is None and resolved_launcher_factory is None:
			resolved_launcher_factory = SidecarTTSLauncher
		self._base_settings = resolved_settings
		self._settings = resolved_settings
		self._launcher_factory = resolved_launcher_factory
		self._launcher = launcher
		self._managed_launcher = (
			launcher is None and resolved_launcher_factory is not None
		)
		if self._managed_launcher:
			self._launcher = resolved_launcher_factory(resolved_settings)
		self._session = session or requests.Session()
		self._active_requests: set[str] = set()
		self._active_requests_lock = threading.Lock()
		self._invoke_lock = threading.Lock()
		self._ws_transport: Optional[SidecarWebSocketTransport] = None

		self.descriptor = RuntimeDescriptor(
			runtime=RuntimeKind.TTS,
			provider=provider,
			mode=RuntimeMode.SIDECAR,
			transport=TransportKind.WEBSOCKET,
			endpoint=resolved_settings.endpoint,
			supports_streaming=True,
			allows_model_control=True,
		)

	def invoke(self, request: Any) -> Any:
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
		metadata = self._metadata()
		if self._launcher is None:
			return RuntimeHealth(
				descriptor=self.descriptor,
				status=RuntimeHealthStatus.UNKNOWN,
				details="TTS launcher is not configured",
				metadata=metadata,
			)
		status, details = self._launcher.health_status()
		if status is RuntimeHealthStatus.READY:
			inner_summary = self._inner_runtime_summary()
			if inner_summary is not None:
				status = self._summary_health_status(inner_summary)
				details = str(
					inner_summary.get("details")
					or inner_summary.get("status")
					or details
				)
				metadata.update(inner_summary.get("metadata") or {})
		return RuntimeHealth(
			descriptor=self.descriptor,
			status=status,
			details=details,
			metadata=metadata,
		)

	def cancel(self, request_id: str) -> Any:
		"""Interrupt an active TTS synthesis request when one exists."""
		messages = load_message_types()
		launcher = self._launcher
		should_cancel = self._untrack_request(request_id)
		if should_cancel and launcher is not None and launcher.is_running():
			try:
				self._request(
					"POST",
					f"{launcher.endpoint}/api/v1/daemon/runtimes/tts"
					"/cancel",
					json_payload={"request_id": request_id},
				)
			except RuntimeError:
				pass
		return messages.ResponseEnvelope(
			request_id=request_id,
			status=messages.EnvelopeStatus.CANCELLED,
			metadata={"best_effort": True, **self._metadata()},
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
		if self._launcher is not None:
			self._launcher.stop()
		close = getattr(self._session, "close", None)
		if close is not None:
			close()

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

	def _load_runtime(self, request: Any) -> Any:
		"""Start the managed TTS daemon."""
		messages = load_message_types()
		try:
			settings = self._settings_for_control(request.metadata)
			self._ensure_launcher(settings)
			launcher = self._require_launcher()
			launcher.start()
			self._request(
				"POST",
				f"{launcher.endpoint}/api/v1/daemon/runtimes/tts/load",
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
		return messages.ResponseEnvelope(
			request_id=request.request_id,
			status=messages.EnvelopeStatus.SUCCEEDED,
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
				self._normalize_model_type(metadata.get("model_type"))
				or self._normalize_model_type(
					self._base_settings.tts_model_type
				)
			),
		)

	def _unload_runtime(self, request_id: str) -> Any:
		"""Stop the managed TTS daemon."""
		messages = load_message_types()
		if self._launcher is not None:
			self._launcher.stop()
		return messages.ResponseEnvelope(
			request_id=request_id,
			status=messages.EnvelopeStatus.SUCCEEDED,
			payload={"model_status": "unloaded"},
			metadata=self._metadata(),
		)

	def _ensure_ws_transport(self, endpoint: str) -> SidecarWebSocketTransport:
		"""Return or create a WebSocket transport for the given endpoint."""
		ws = self._ws_transport
		if ws is not None:
			if ws.is_connected:
				return ws
			asyncio.run_coroutine_threadsafe(
				ws.close(), asyncio.get_event_loop(),
			)
			self._ws_transport = None
		ws = SidecarWebSocketTransport(endpoint)
		try:
			asyncio.run_coroutine_threadsafe(
				ws.connect(), asyncio.get_event_loop(),
			).result(timeout=10)
		except Exception as exc:
			raise RuntimeError(
				f"Failed to connect WebSocket transport: {exc}"
			) from exc
		self._ws_transport = ws
		return ws

	def _synthesize_speech(self, request: Any) -> Any:
		"""Execute one TTS request via WebSocket transport only.

		Raises immediately when the WebSocket connection cannot be
		established -- no HTTP fallback.
		"""
		messages = load_message_types()
		invocation = TTSInvocationRequest.model_validate(request.payload)
		with self._invoke_lock:
			try:
				settings = self._settings_for_invocation(invocation)
				self._ensure_launcher(settings)
				launcher = self._require_launcher()
				launcher.start()
				return self._synthesize_via_websocket(
					request, invocation, launcher,
				)
			except RuntimeError as exc:
				return self._runtime_error_response(
					request.request_id,
					str(exc),
				)

	def _ws_transport_available(self, launcher: TTSLauncherLike) -> bool:
		"""Check if WebSocket transport is available for this launcher."""
		ws = self._ws_transport
		return ws is not None and ws.is_connected

	def _synthesize_via_websocket(
		self,
		request: Any,
		invocation: TTSInvocationRequest,
		launcher: TTSLauncherLike,
	) -> Any:
		"""Send one TTS synthesis request through the WebSocket transport."""
		messages = load_message_types()
		ws = self._ensure_ws_transport(launcher.endpoint)

		payload = {
			"text": invocation.text,
			"voice": invocation.voice,
			"speed": invocation.speed,
			"model": invocation.model,
			"model_type": invocation.metadata.get("model_type"),
		}

		envelope = messages.RequestEnvelope(
			request_id=request.request_id,
			runtime=messages.RuntimeKind.TTS,
			action=messages.RuntimeAction.INVOKE,
			payload=payload,
			metadata={"request_id": request.request_id},
		)

		try:
			response = asyncio.run_coroutine_threadsafe(
				ws.invoke(envelope),
				asyncio.get_event_loop(),
			).result(timeout=self._settings.request_timeout_seconds)
		except WebSocketTransportDisconnected:
			return self._failure_response(
				request.request_id,
				"tts_disconnected",
				"WebSocket connection lost",
			)
		except TimeoutError:
			return self._failure_response(
				request.request_id,
				"tts_timeout",
				"Timed out waiting for TTS response via WebSocket",
				retryable=True,
			)

		if response.status is messages.EnvelopeStatus.FAILED:
			err = "TTS synthesis failed"
			if response.error:
				err = getattr(response.error, "message", None) or err
			return self._runtime_error_response(request.request_id, err)

		payload_data = response.payload or {}
		audio_b64 = (
			payload_data.get("audio_b64")
			or payload_data.get("audio")
			or ""
		)
		return messages.ResponseEnvelope(
			request_id=request.request_id,
			status=messages.EnvelopeStatus.SUCCEEDED,
			payload={
				"accepted": True,
				"audio_b64": audio_b64,
			},
			metadata={"ws": True, **self._metadata()},
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
				self._normalize_model_type(metadata.get("model_type"))
				or self._normalize_model_type(
					self._base_settings.tts_model_type
				)
			),
		)

	def _ensure_launcher(self, settings: TTSDaemonRuntimeSettings) -> None:
		"""Refresh the managed launcher when request settings change."""
		if not self._managed_launcher:
			self._settings = settings
			return
		if self._launcher_factory is None:
			self._settings = settings
			return
		if settings == self._settings:
			return
		if self._launcher is not None:
			self._launcher.stop()
		self._settings = settings
		self._launcher = self._launcher_factory(settings)

	def _require_launcher(self) -> TTSLauncherLike:
		"""Return the configured launcher or raise a runtime error."""
		launcher = self._launcher
		if launcher is None:
			raise RuntimeError("TTS launcher is not configured")
		return launcher

	def _inner_runtime_summary(self) -> Optional[dict[str, Any]]:
		"""Return the nested local-fallback TTS summary from the sidecar."""
		launcher = self._launcher
		if launcher is None or not launcher.is_ready():
			return None
		query = urlencode(
			{
				"provider": self.descriptor.provider,
				"deployment_mode": RuntimeMode.LOCAL_FALLBACK.value,
			}
		)
		try:
			return self._request(
				"GET",
				f"{launcher.endpoint}/api/v1/daemon/runtimes/tts?{query}",
				timeout_seconds=_INNER_RUNTIME_STATUS_TIMEOUT_SECONDS,
			)
		except RuntimeError:
			return None

	@staticmethod
	def _summary_health_status(summary: dict[str, Any]) -> RuntimeHealthStatus:
		"""Translate one nested runtime summary into runtime health."""
		status = str(summary.get("status", "")).strip().lower()
		if status == "ready":
			return RuntimeHealthStatus.READY
		if status == "starting":
			return RuntimeHealthStatus.STARTING
		if status == "failed":
			return RuntimeHealthStatus.FAILED
		if status == "stopped":
			return RuntimeHealthStatus.STOPPED
		if bool(summary.get("loaded")):
			return RuntimeHealthStatus.READY
		return RuntimeHealthStatus.UNKNOWN

	def _request(
		self,
		method: str,
		url: str,
		*,
		json_payload: Optional[dict[str, Any]] = None,
		expect_json: bool = True,
		timeout_seconds: Optional[float] = None,
	) -> Any:
		"""Perform one HTTP request against the sidecar daemon."""
		try:
			response = self._session.request(
				method,
				url,
				json=json_payload,
				timeout=(
					self._settings.request_timeout_seconds
					if timeout_seconds is None
					else timeout_seconds
				),
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
		launcher = self._launcher
		endpoint = launcher.endpoint if launcher is not None else self._settings.endpoint
		api_base_url = (
			launcher.api_base_url
			if launcher is not None
			else f"{self._settings.endpoint}/api/v1/tts"
		)
		metadata = {
			"endpoint": endpoint,
			"tts_api_url": api_base_url,
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

	def _runtime_error_response(
		self,
		request_id: str,
		message: str,
	) -> Any:
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
	if tts_client is None:
		raise ValueError("register_sidecar_tts_client requires a configured client")
	client = tts_client
	registry.register(
		RuntimeRoute(
			RuntimeKind.TTS,
			provider=client.descriptor.provider,
			deployment_mode=RuntimeMode.SIDECAR.value,
		),
		client,
	)
	return registry


__all__ = ["SidecarTTSClient", "register_sidecar_tts_client"]