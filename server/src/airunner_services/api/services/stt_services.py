"""Service-owned STT API service."""

from airunner_services.contract_enums import SignalCode

from airunner_services.api.api_service_base import APIServiceBase


class STTAPIService(APIServiceBase):
	"""Emit STT-related signals through the shared API layer."""

	def audio_processor_response(self, transcription) -> None:
		"""Emit one processed transcription result."""
		self.emit_signal(
			SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
			{"transcription": transcription},
		)