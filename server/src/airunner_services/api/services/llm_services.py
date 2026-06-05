"""Service-owned LLM API service with GUI hook points."""

from __future__ import annotations

from typing import Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.api.api_service_base import APIServiceBase
from airunner_services.api.services.llm_conversation_service_mixin import (
	LLMConversationServiceMixin,
)
from airunner_services.api.services.llm_daemon_stream_mixin import (
	LLMDaemonStreamMixin,
)
from airunner_services.api.services.llm_request_dispatch_mixin import (
	LLMRequestDispatchMixin,
)
from airunner_services.api.services.llm_unload_routing_mixin import (
	LLMUnloadRoutingMixin,
)
from airunner_services.llm.llm_response import LLMResponse
from airunner_services.utils.application.api_reference import (
	peek_registered_api,
)
from airunner_services.utils.application.enum_resolver import signal_code_proxy


SignalCode = signal_code_proxy()


class LLMAPIService(
	LLMUnloadRoutingMixin,
	LLMRequestDispatchMixin,
	LLMConversationServiceMixin,
	LLMDaemonStreamMixin,
	APIServiceBase,
):
	"""Canonical service-owned LLM API service."""

	def __init__(self) -> None:
		super().__init__()
		self._headless_tts_response_buffer: dict[str, str] = {}
		self._headless_tts_request_enabled: dict[str, bool] = {}

	def _register_request_tts_preference(
		self,
		request_id: str,
		do_tts_reply: bool,
	) -> None:
		"""Remember whether one request should be spoken headlessly."""
		self._headless_tts_request_enabled[request_id] = bool(do_tts_reply)

	def chatbot_changed(self) -> None:
		"""Emit one chatbot-changed signal."""
		self.emit_signal(SignalCode.CHATBOT_CHANGED)

	def finalize_image_generated_by_llm(self, _data) -> None:
		"""Ask the LLM to acknowledge a completed image request."""
		self.send_request(
			"The image request has completed. Write a single concise "
			"reply (1 short sentence) acknowledging the generated "
			"image.",
			action=LLMActionType.CHAT,
			do_tts_reply=True,
		)

	def send_llm_text_streamed_signal(self, response: LLMResponse) -> None:
		"""Emit one streamed LLM response chunk."""
		data = {"response": response}
		if response.request_id:
			data["request_id"] = response.request_id
		else:
			try:
				self.logger.warning(
					"[STREAM] Emitting streamed response without "
					"request_id; pending HTTP callbacks will not be "
					"notified"
				)
			except Exception:
				pass
		if self._forward_tts_stream_signal(data):
			data["_skip_worker_manager_tts"] = True
		elif self._forward_headless_tts_final_response(response):
			data["_skip_worker_manager_tts"] = True
		elif self._should_skip_headless_tts_stream(response):
			response.skip_tts_stream = True
			data["_skip_worker_manager_tts"] = True
		self.emit_signal(SignalCode.LLM_TEXT_STREAMED_SIGNAL, data)

	def send_llm_thinking_signal(
		self,
		status: str,
		content: str,
		request_id: Optional[str] = None,
	) -> None:
		"""Emit one thinking-status update."""
		self.emit_signal(
			SignalCode.LLM_THINKING_SIGNAL,
			self._thinking_signal_payload(status, content, request_id),
		)

	def _thinking_signal_payload(
		self,
		status: str,
		content: str,
		request_id: Optional[str] = None,
	) -> dict:
		"""Build one thinking-signal payload."""
		data = {
			"status": status,
			"content": content,
			"request_id": request_id,
		}
		if self._forward_tts_thinking_signal(data):
			data["_skip_worker_manager_tts"] = True
		return data

	def _forward_tts_stream_signal(self, data: dict) -> bool:
		"""Allow subclasses to fast-path streamed chunks to TTS."""
		del data
		return False

	def _forward_tts_thinking_signal(self, data: dict) -> bool:
		"""Allow subclasses to fast-path thinking updates to TTS."""
		del data
		return False

	def _should_skip_headless_tts_stream(
		self,
		response: LLMResponse,
	) -> bool:
		"""Return True when headless TTS should ignore raw stream chunks."""
		request_id = getattr(response, "request_id", None)
		if not request_id or not self._is_headless_tts_assistant_response(
			response,
		):
			return False
		if getattr(response, "is_end_of_message", False):
			return False
		return self._headless_tts_request_enabled.get(request_id, True)

	def _is_headless_tts_assistant_response(
		self,
		response: LLMResponse,
	) -> bool:
		"""Return True for assistant-visible chunks that headless TTS may speak."""
		if getattr(response, "is_system_message", False):
			return False
		message_type = getattr(response, "message_type", None)
		return message_type in (None, "", "assistant")

	def _forward_headless_tts_final_response(
		self,
		response: LLMResponse,
	) -> bool:
		"""Forward one completed visible reply to headless TTS."""
		request_id = getattr(response, "request_id", None)
		message = getattr(response, "message", "") or ""
		if not self._is_headless_tts_assistant_response(response):
			return False
		if request_id and not self._headless_tts_request_enabled.get(
			request_id,
			True,
		):
			if getattr(response, "is_end_of_message", False):
				self._headless_tts_response_buffer.pop(request_id, None)
				self._headless_tts_request_enabled.pop(request_id, None)
			return False

		if request_id and message and not getattr(
			response,
			"is_system_message",
			False,
		):
			buffered = self._headless_tts_response_buffer.get(request_id, "")
			self._headless_tts_response_buffer[request_id] = (
				buffered + message
			)

		if not request_id or not getattr(response, "is_end_of_message", False):
			return False

		full_message = (
			getattr(response, "final_visible_message", None)
			or self._headless_tts_response_buffer.pop(request_id, "")
		)
		self._headless_tts_response_buffer.pop(request_id, None)
		self._headless_tts_request_enabled.pop(request_id, None)
		if not full_message or getattr(response, "is_system_message", False):
			return False

		worker = self._tts_stream_worker()
		enqueue = getattr(worker, "add_to_queue", None)
		if callable(enqueue):
			enqueue(
				{
					"message": full_message,
					"is_end_of_message": True,
				}
			)
			return True

		handler = getattr(worker, "on_llm_text_streamed_signal", None)
		if not callable(handler):
			return False

		handler(
			{
				"response": LLMResponse(
					message=full_message,
					is_end_of_message=True,
					is_first_message=True,
					sequence_number=getattr(
						response,
						"sequence_number",
						0,
					),
					action=getattr(response, "action", None),
					node_id=getattr(response, "node_id", None),
					request_id=request_id,
				),
				"request_id": request_id,
			}
		)
		return True

	def _tts_stream_worker(self):
		"""Return the active TTS stream worker when one exists."""
		worker_manager = self._worker_manager()
		if worker_manager is None:
			return None
		return getattr(worker_manager, "tts_generator_worker", None)

	def _worker_manager(self):
		"""Return the active worker manager when one exists."""
		refresher = getattr(self, "refresh_api_reference", None)
		if callable(refresher):
			refreshed_api = refresher()
			if refreshed_api is not None:
				self.api = refreshed_api

		for candidate in (
			getattr(self, "api", None),
			peek_registered_api(),
		):
			if candidate is None:
				continue
			worker_manager = getattr(candidate, "_worker_manager", None)
			if worker_manager is not None:
				return worker_manager
		return None

	def _daemon_client(self):
	    """Return the daemon client when one is already attached."""
	    api = peek_registered_api()
	    return getattr(api, "daemon_client", None) if api else None