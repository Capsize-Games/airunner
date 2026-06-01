"""Service-owned TTS API service."""

from __future__ import annotations

from airunner_services.contract_enums import SignalCode
from airunner_services.api.api_service_base import APIServiceBase


class TTSAPIService(APIServiceBase):
	"""Emit TTS-related signals through the shared API layer."""

	def play_audio(self, message) -> None:
		"""Queue one final TTS message for playback."""
		self.emit_signal(
			SignalCode.TTS_QUEUE_SIGNAL,
			{"message": message, "is_end_of_message": True},
		)

	def toggle(self, enabled) -> None:
		"""Toggle TTS on or off."""
		self.emit_signal(SignalCode.TOGGLE_TTS_SIGNAL, {"enabled": enabled})

	def start(self) -> None:
		"""Enable TTS."""
		self.emit_signal(
			SignalCode.TTS_ENABLE_SIGNAL,
			{
				"source": "runtime_control",
				"request_scoped": True,
			},
		)

	def stop(self) -> None:
		"""Disable TTS."""
		self.emit_signal(SignalCode.TTS_DISABLE_SIGNAL, {})

	def add_to_stream(self, response) -> None:
		"""Forward one streamed TTS response chunk when GUI support exists."""
		stream_signal = getattr(
			SignalCode,
			"TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL",
			None,
		)
		if stream_signal is None:
			return
		self.emit_signal(stream_signal, {"message": response})

	def disable(self) -> None:
		"""Disable TTS."""
		self.emit_signal(SignalCode.TTS_DISABLE_SIGNAL, {})