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
		"""Allow GUI subclasses to fast-path streamed chunks to TTS."""
		del data
		return False

	def _forward_tts_thinking_signal(self, data: dict) -> bool:
		"""Allow GUI subclasses to fast-path thinking updates to TTS."""
		del data
		return False

	def _tts_stream_worker(self):
		"""Return the active TTS stream worker when one exists."""
		return None

	def _worker_manager(self):
		"""Return the active worker manager when one exists."""
		return None

	def _daemon_client(self):
		"""Return the daemon client when one is already attached."""
		api = getattr(self, "api", None)
		if api is None or getattr(api, "headless", False):
			return None
		return getattr(api, "daemon_client", None)