"""llama-cpp-shaped proxy backed by the supervised shared sidecar."""

from __future__ import annotations

import threading
import uuid
from typing import Any, Iterator


class SidecarLlamaServerProxy:
	"""Expose the subset of llama-cpp's API used by ChatGGUF."""

	def __init__(
		self,
		client: Any,
		runtime_profile: str | None,
		*,
		model_path: str | None = None,
		model_id: str | None = None,
		n_ctx: int | None = None,
		n_gpu_layers: int | None = None,
	) -> None:
		self._client = client
		self._runtime_profile = runtime_profile
		self._model_path = model_path
		self._model_id = model_id
		self._n_ctx = n_ctx
		self._n_gpu_layers = n_gpu_layers
		self._binding_token: str | None = None
		self._request_ids: set[str] = set()
		self._lock = threading.Lock()

	def load(self) -> None:
		"""Start and health-check the selected shared backend profile."""
		self._binding_token = self._client.start_backend(
			self._runtime_profile,
			model_path=self._model_path,
			model_id=self._model_id,
			n_ctx=self._n_ctx,
			n_gpu_layers=self._n_gpu_layers,
		)

	def close(self) -> None:
		"""Stop the shared backend after all request leases have drained."""
		if self._binding_token is None:
			return
		if not self._client.stop_backend(
			expected_binding=self._binding_token,
			timeout_seconds=5.0,
		):
			raise RuntimeError("The shared LLM backend still has active requests")

	def reconcile_binding(self) -> bool:
		"""Adopt a current matching binding after a supervised reload."""
		token = self._client.current_binding(
			self._runtime_profile,
			model_path=self._model_path,
			model_id=self._model_id,
			n_ctx=self._n_ctx,
			n_gpu_layers=self._n_gpu_layers,
		)
		if token is None:
			return False
		self._binding_token = token
		return True

	def cancel_active_requests(self) -> None:
		"""Cancel only requests that this adapter instance owns."""
		with self._lock:
			request_ids = tuple(self._request_ids)
		for request_id in request_ids:
			self._client.cancel(request_id)

	def _register_request(self, request_id: str) -> None:
		with self._lock:
			self._request_ids.add(request_id)

	def _release_request(self, request_id: str) -> None:
		with self._lock:
			self._request_ids.discard(request_id)

	def create_chat_completion(self, **payload: Any) -> Any:
		"""Forward chat completions through this adapter's model binding."""
		return self._request("/v1/chat/completions", payload)

	def create_completion(self, **payload: Any) -> Any:
		"""Forward preformatted prompts through this adapter's model binding."""
		return self._request("/v1/completions", payload)

	def _request(self, endpoint_path: str, payload: dict[str, Any]) -> Any:
		if self._binding_token is None:
			raise RuntimeError(
				"The selected LLM backend must be loaded before requesting generation"
			)
		request_id = str(uuid.uuid4())
		payload = dict(payload)
		if payload.get("stream") is True and endpoint_path == "/v1/chat/completions":
			payload.setdefault("stream_options", {"include_usage": True})
		is_stream = payload.get("stream") is True
		if not is_stream:
			self._register_request(request_id)
		try:
			result = self._client.openai_request(
				request_id,
				payload,
				runtime_profile=self._runtime_profile,
				endpoint_path=endpoint_path,
				expected_binding=self._binding_token,
			)
			if not is_stream:
				return result
			return _TrackedStream(self, request_id, result)
		finally:
			if not is_stream:
				self._release_request(request_id)


class _TrackedStream:
	"""Release stream ownership on completion, error, or explicit close."""

	def __init__(
		self,
		owner: SidecarLlamaServerProxy,
		request_id: str,
		source: Iterator[dict[str, Any]],
	) -> None:
		self._owner = owner
		self._request_id = request_id
		self._source = iter(source)
		self._owner._register_request(self._request_id)
		self._registered = True
		self._closed = False

	def __iter__(self) -> "_TrackedStream":
		return self

	def __next__(self) -> dict[str, Any]:
		if self._closed:
			raise StopIteration
		try:
			event = next(self._source)
		except BaseException:
			self.close()
			raise
		# llama-cpp-python consumers assume a first choice is present. Keep
		# provider usage on that event while supplying an empty delta/text.
		if not event.get("choices") and isinstance(event.get("usage"), dict):
			event = dict(event)
			event["choices"] = [
				{
					"index": 0,
					"delta": {},
					"text": "",
					"finish_reason": None,
				}
			]
		return event

	def close(self) -> None:
		"""Close the provider stream and release adapter ownership."""
		if self._closed:
			return
		self._closed = True
		try:
			close = getattr(self._source, "close", None)
			if callable(close):
				close()
		finally:
			if self._registered:
				self._owner._release_request(self._request_id)

	def __del__(self) -> None:
		self.close()
