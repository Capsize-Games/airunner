"""Async WebSocket transport for sidecar runtime communication.

Replaces HTTP polling with push-based messaging over WebSocket.
All sidecar clients share a single transport instance per daemon
connection.
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, Callable, Optional

import websockets
from websockets import State as WsState
from websockets.asyncio.client import connect as ws_connect
from websockets.asyncio.client import ClientConnection

from airunner_services.ipc.messages import (
	EnvelopeStatus,
	ErrorEnvelope,
	RequestEnvelope,
	ResponseEnvelope,
	StreamDelta,
)
from airunner_services.runtimes.contracts import (
	RuntimeDescriptor,
	TransportKind,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

# Defaults
_DEFAULT_CONNECT_TIMEOUT = 10.0

# ── Dedicated background event loop for all WebSocket operations ──
# The sidecar clients are called from ThreadPoolExecutor threads where
# no asyncio event loop is available.  This background thread runs a
# single event loop that all WS transports share via
# run_coroutine_threadsafe.

_ws_loop: Optional[asyncio.AbstractEventLoop] = None
_ws_loop_lock = threading.Lock()


def get_ws_event_loop() -> asyncio.AbstractEventLoop:
	"""Return a shared background event loop for WebSocket operations.

	Creates a daemon thread running ``run_forever`` on first call.
	All sidecar clients call ``run_coroutine_threadsafe`` against
	this loop so that async WS methods execute regardless of which
	thread the caller is on.
	"""
	global _ws_loop
	if _ws_loop is not None and not _ws_loop.is_closed():
		return _ws_loop
	with _ws_loop_lock:
		if _ws_loop is not None and not _ws_loop.is_closed():
			return _ws_loop
		loop = asyncio.new_event_loop()
		t = threading.Thread(
			target=loop.run_forever,
			daemon=True,
			name="ws-event-loop",
		)
		t.start()
		_ws_loop = loop
	return _ws_loop
_DEFAULT_RESPONSE_TIMEOUT = 30.0
_DEFAULT_STREAM_TIMEOUT = 1800.0
_DEFAULT_PING_INTERVAL = 5.0


def _ws_url(endpoint: str, path: str = "/ws") -> str:
	"""Convert an HTTP endpoint to a WebSocket URL.

	Args:
		endpoint: Base HTTP endpoint (e.g. ``http://127.0.0.1:8190``).
		path: WebSocket path to append.

	Returns:
		WebSocket URL (e.g. ``ws://127.0.0.1:8190/ws``).
	"""
	host = endpoint.replace("http://", "ws://").replace(
		"https://", "wss://"
	)
	if path.startswith("/"):
		return f"{host}{path}"
	return f"{host}/{path}"


class WebSocketTransportError(RuntimeError):
	"""Base exception for WebSocket transport failures."""


class WebSocketTransportTimeout(WebSocketTransportError):
	"""Raised when a request times out waiting for a response."""


class WebSocketTransportDisconnected(WebSocketTransportError):
	"""Raised when the WebSocket connection is lost."""


ProgressCallback = Callable[[dict[str, Any]], None]


class SidecarWebSocketTransport:
	"""Async WebSocket transport for one sidecar daemon connection.

	This is a request-response transport that maps *one* connection to
	*one* sidecar daemon.  It supports two invocation patterns:

	Non-streaming:
		``transport.invoke(envelope) -> ResponseEnvelope``

	Streaming with progress push:
		``transport.invoke_stream(envelope, on_progress) -> ResponseEnvelope``

	Thread safety is handled by the caller (``_invoke_lock`` in each
	sidecar client) -- the transport itself is single-connection.
	"""

	def __init__(
		self,
		endpoint: str,
		ws_path: str = "/ws",
		*,
		connect_timeout: float = _DEFAULT_CONNECT_TIMEOUT,
		response_timeout: float = _DEFAULT_RESPONSE_TIMEOUT,
		stream_timeout: float = _DEFAULT_STREAM_TIMEOUT,
		ping_interval: float = _DEFAULT_PING_INTERVAL,
	) -> None:
		"""Initialise the transport with the daemon endpoint.

		Args:
			endpoint: HTTP base URL of the sidecar daemon.
			ws_path: WebSocket path on the daemon.
			connect_timeout: Seconds to wait for connection.
			response_timeout: Seconds to wait for a non-streaming response.
			stream_timeout: Seconds to wait for a streaming response.
			ping_interval: Seconds between WebSocket pings.
		"""
		self._ws_url = _ws_url(endpoint, ws_path)
		self._connect_timeout = connect_timeout
		self._response_timeout = response_timeout
		self._stream_timeout = stream_timeout
		self._ping_interval = ping_interval

		self._ws: ClientConnection | None = None
		self._receive_task: Optional[asyncio.Task] = None

		# Maps request_id -> Future[ResponseEnvelope] for one-shot calls
		self._pending_responses: dict[
			str, asyncio.Future[ResponseEnvelope]
		] = {}

		# Maps request_id -> list[callable] for stream subscribers
		self._pending_streams: dict[
			str, list[ProgressCallback]
		] = {}

		self._closed = False
		self._lock = asyncio.Lock()

	@property
	def is_connected(self) -> bool:
		"""Return True when the WebSocket is open."""
		ws = self._ws
		return ws is not None and ws.state is WsState.OPEN

	@property
	def descriptor(self) -> RuntimeDescriptor:
		"""Return a descriptor identifying this transport."""
		from airunner_services.runtimes.contracts import RuntimeKind as _RK
		from airunner_services.runtimes.contracts import RuntimeMode as _RM
		return RuntimeDescriptor(
			runtime=_RK.ART,
			provider="local",
			mode=_RM.SIDECAR,
			transport=TransportKind.WEBSOCKET,
			endpoint=self._ws_url,
			supports_streaming=True,
			allows_model_control=True,
		)

	async def connect(self) -> None:
		"""Open the WebSocket connection to the sidecar daemon.

		Raises:
			WebSocketTransportError: On connection failure.
		"""
		if self.is_connected:
			return
		try:
			self._ws = await asyncio.wait_for(
				ws_connect(
					self._ws_url,
					ping_interval=self._ping_interval,
				),
				timeout=self._connect_timeout,
			)
		except (OSError, asyncio.TimeoutError) as exc:
			raise WebSocketTransportError(
				f"Failed to connect to {self._ws_url}: {exc}"
			) from exc

		# Start the background reader that dispatches incoming messages.
		self._receive_task = asyncio.create_task(self._reader_loop())

	async def close(self) -> None:
		"""Close the WebSocket and cancel all pending calls."""
		self._closed = True
		if self._receive_task is not None:
			self._receive_task.cancel()
			try:
				await self._receive_task
			except asyncio.CancelledError:
				pass
			self._receive_task = None

		if self._ws is not None:
			await self._ws.close()
			self._ws = None

		# Fail all pending futures so callers don't hang.
		exc = WebSocketTransportDisconnected(
			"Transport closed while requests were pending"
		)
		for request_id, fut in self._pending_responses.items():
			if not fut.done():
				fut.set_exception(exc)
		self._pending_responses.clear()
		self._pending_streams.clear()

	async def invoke(
		self,
		envelope: RequestEnvelope,
		*,
		timeout: Optional[float] = None,
	) -> ResponseEnvelope:
		"""Send one request and wait for its response envelope.

		Args:
			envelope: The request to send.
			timeout: Override the default response timeout.

		Returns:
			The correlated response envelope.

		Raises:
			WebSocketTransportTimeout: When the response does not arrive.
			WebSocketTransportDisconnected: When the connection drops.
		"""
		ws = self._ws
		if ws is None or ws.state is not WsState.OPEN:
			raise WebSocketTransportDisconnected("Not connected")

		rid = envelope.request_id
		fut: asyncio.Future[ResponseEnvelope] = (
			asyncio.get_event_loop().create_future()
		)
		self._pending_responses[rid] = fut

		try:
			payload = envelope.model_dump(mode="json")
			async with self._lock:
				await ws.send(json.dumps(payload))

			actual_timeout = (
				timeout if timeout is not None else self._response_timeout
			)
			try:
				return await asyncio.wait_for(
					fut, timeout=actual_timeout,
				)
			except asyncio.TimeoutError as exc:
				raise WebSocketTransportTimeout(
					f"Request {rid} timed out after {actual_timeout}s"
				) from exc
		finally:
			self._pending_responses.pop(rid, None)

	async def invoke_stream(
		self,
		envelope: RequestEnvelope,
		on_progress: Optional[ProgressCallback] = None,
		*,
		timeout: Optional[float] = None,
	) -> ResponseEnvelope:
		"""Send one request and stream deltas until completion.

		The transport receives ``StreamDelta`` messages from the daemon
		and forwards each to ``on_progress``.  The final
		``ResponseEnvelope`` (success or failure) is returned.

		Args:
			envelope: The request to send.
			on_progress: Optional callback invoked for each progress delta.
			timeout: Override the default stream timeout.

		Returns:
			The final response envelope.
		"""
		ws = self._ws
		if ws is None or ws.state is not WsState.OPEN:
			raise WebSocketTransportDisconnected("Not connected")

		rid = envelope.request_id
		fut: asyncio.Future[ResponseEnvelope] = (
			asyncio.get_event_loop().create_future()
		)
		self._pending_responses[rid] = fut

		if on_progress is not None:
			self._pending_streams.setdefault(rid, []).append(on_progress)

		try:
			payload = envelope.model_dump(mode="json")
			async with self._lock:
				await ws.send(json.dumps(payload))

			actual_timeout = (
				timeout if timeout is not None else self._stream_timeout
			)
			try:
				return await asyncio.wait_for(
					fut, timeout=actual_timeout,
				)
			except asyncio.TimeoutError as exc:
				raise WebSocketTransportTimeout(
					f"Stream request {rid} timed out after "
					f"{actual_timeout}s"
				) from exc
		finally:
			self._pending_responses.pop(rid, None)
			self._pending_streams.pop(rid, None)

	async def _reader_loop(self) -> None:
		"""Background task that reads JSON messages from the WebSocket.

		Each incoming message is routed to the pending future or stream
		callback matching its ``request_id``.
		"""
		ws = self._ws
		if ws is None:
			return

		try:
			async for raw in ws:
				if self._closed:
					break
				try:
					data = json.loads(raw)
				except json.JSONDecodeError:
					logger.warning(
						"Ignoring non-JSON message from sidecar: %s",
						str(raw)[:200],
					)
					continue

				await self._dispatch_message(data)

		except websockets.ConnectionClosed as exc:
			if not self._closed:
				logger.warning(
					"WebSocket connection closed unexpectedly: %s", exc
				)
				self._fail_pending(
					WebSocketTransportDisconnected(
						f"Connection closed: {exc}"
					)
				)
		except Exception as exc:
			logger.error("WebSocket reader error: %s", exc)
			self._fail_pending(
				WebSocketTransportDisconnected(
					f"Reader error: {exc}"
				)
			)

	async def _dispatch_message(self, data: dict[str, Any]) -> None:
		"""Route one parsed JSON message to its pending consumer."""
		request_id = str(data.get("request_id", ""))
		if not request_id:
			logger.warning("Ignoring message without request_id")
			return

		msg_type = data.get("type", "")
		status = data.get("status", "")

		# StreamDelta messages have type="stream"
		if msg_type == "stream" or status == "stream":
			await self._dispatch_stream(data, request_id)
			return

		# Progress push messages from the daemon
		if msg_type == "progress":
			await self._dispatch_stream(
				{
					"request_id": request_id,
					"type": "progress",
					"delta": {
						"progress": data.get("progress", 0.0),
						"phase": data.get("phase", ""),
						"status": data.get("status", ""),
					},
				},
				request_id,
			)
			return

		# ResponseEnvelope-style messages
		envelope = self._build_response_envelope(data)
		fut = self._pending_responses.get(request_id)
		if fut is not None and not fut.done():
			fut.set_result(envelope)

	async def _dispatch_stream(
		self,
		data: dict[str, Any],
		request_id: str,
	) -> None:
		"""Forward a stream delta to all subscribers."""
		callbacks = self._pending_streams.get(request_id, [])
		if not callbacks:
			return

		delta = data.get("delta", data)
		progress = float(delta.get("progress", 0.0))
		status = str(delta.get("status", "") or "")
		payload = {
			"request_id": request_id,
			"status": status,
			"progress": progress,
			"phase": delta.get("phase", ""),
		}

		for cb in callbacks:
			try:
				cb(payload)
			except Exception:
				logger.exception(
					"Progress callback failed for %s", request_id
				)

	def _build_response_envelope(
		self,
		data: dict[str, Any],
	) -> ResponseEnvelope:
		"""Build a ``ResponseEnvelope`` from a parsed JSON dict."""
		status_str = str(data.get("status", "failed"))
		try:
			status = EnvelopeStatus(status_str)
		except ValueError:
			status = EnvelopeStatus.FAILED

		# Extract error if present (dict or string format)
		error = None
		raw_error = data.get("error")
		if raw_error is not None:
			if isinstance(raw_error, dict):
				error = ErrorEnvelope(
					code=str(raw_error.get("code", "unknown")),
					message=str(raw_error.get("message", "") or ""),
					retryable=bool(raw_error.get("retryable", False)),
				)
			else:
				error = ErrorEnvelope(
					code="error",
					message=str(raw_error),
				)

		return ResponseEnvelope(
			request_id=str(data.get("request_id", "")),
			status=status,
			payload=data.get("payload", data.get("result", {})),
			error=error,
			metadata=data.get("metadata", {}),
		)

	def _fail_pending(self, exception: Exception) -> None:
		"""Fail all pending futures with *exception*."""
		for request_id, fut in self._pending_responses.items():
			if not fut.done():
				fut.set_exception(exception)
		self._pending_responses.clear()


__all__ = [
	"SidecarWebSocketTransport",
	"WebSocketTransportError",
	"WebSocketTransportTimeout",
	"WebSocketTransportDisconnected",
	"get_ws_event_loop",
]
