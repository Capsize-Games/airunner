"""Service-owned STT audio processor worker."""

from airunner_services.runtimes.stt_executor import STTExecutor
from airunner_services.runtimes.runtime_registry_stt_executor import (
	RuntimeRegistrySTTExecutor,
)
from airunner_services.utils.application.enum_resolver import signal_code_proxy
from airunner_services.workers.worker import Worker


SignalCode = signal_code_proxy(
	{
		"STT_START_CAPTURE_SIGNAL": "stt_start_capture",
		"STT_STOP_CAPTURE_SIGNAL": "stt_stop_capture",
	}
)


class AudioProcessorWorker(Worker):
	"""Process audio payloads through local or daemon-backed STT."""

	fs = 0

	def __init__(self):
		self._executor = None
		super().__init__()

	def start_worker_thread(self):
		self._initialize_stt_handler()
		if self.application_settings.stt_enabled:
			self._stt_load()

	def _initialize_stt_handler(self):
		if self._executor is None:
			self._executor = self._create_stt_executor()

	def _create_stt_executor(self) -> STTExecutor:
		"""Create the shared STT executor used by the processor worker."""
		return RuntimeRegistrySTTExecutor(api=self._current_api())

	def _current_api(self):
	    """Return the registered service API reference."""
	    return peek_registered_api()

	def _daemon_client(self):
	    """Return the daemon client when STT is running remotely."""
	    api = self._current_api()
	    return getattr(api, "daemon_client", None) if api else None

	def _emit_transcription(self, transcription: str) -> None:
		"""Forward one transcription to the shared UI boundary."""
		api = AudioProcessorWorker._current_api(self)
		stt_service = getattr(api, "stt", None) if api is not None else None
		if stt_service is not None:
			stt_service.audio_processor_response(transcription)
			return
		self.emit_signal(
			SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
			{"transcription": transcription},
		)

	def on_stt_load_signal(self, data: dict = None):
		if self._executor is None:
			self._initialize_stt_handler()

		if self._executor:
			self._stt_load()

	def on_stt_unload_signal(self, data: dict = None):
		if self._executor:
			self._stt_unload()

	def unload(self):
		self._stt_unload()

	def load(self):
		self._initialize_stt_handler()
		self._stt_load()

	def _stt_load(self):
		if self._daemon_client() is not None:
			return
		if self._executor and self._executor.load():
			self.emit_signal(SignalCode.STT_START_CAPTURE_SIGNAL)

	def _stt_unload(self):
		if self._daemon_client() is not None:
			return
		self.emit_signal(SignalCode.STT_STOP_CAPTURE_SIGNAL)
		if self._executor:
			self._executor.unload()

	def on_stt_process_audio_signal(self, message):
		self.logger.debug(
			"on_stt_process_audio_signal called, message keys: %s",
			message.keys() if message else "None",
		)
		self.add_to_queue(message)

	def handle_message(self, audio_data):
		message_type = audio_data.get("_message_type") if audio_data else None
		if message_type == "stt_load":
			self.on_stt_load_signal(audio_data.get("data"))
			return
		if message_type == "stt_unload":
			self.on_stt_unload_signal(audio_data.get("data"))
			return

		self.logger.debug(
			"handle_message called, _executor=%s, audio_data keys: %s",
			self._executor,
			audio_data.keys() if audio_data else "None",
		)
		daemon_client = self._daemon_client()
		if daemon_client is not None:
			transcription = self._transcribe_via_daemon(
				daemon_client,
				audio_data,
			)
			if transcription:
				AudioProcessorWorker._emit_transcription(
					self,
					transcription,
				)
			return
		if self._executor is None:
			self.logger.warning("STT handler not initialized, skipping audio")
			return
		if not self._executor.stt_is_loaded:
			self.logger.warning("STT model not loaded, skipping audio")
			return
		self.logger.debug("Processing audio through STT executor")
		transcription = self._executor.transcribe(audio_data)
		if transcription:
			AudioProcessorWorker._emit_transcription(self, transcription)

	def _transcribe_via_daemon(self, daemon_client, audio_data) -> str:
		"""Send one live-capture payload through the daemon STT route."""
		item = audio_data.get("item") if audio_data else None
		if not item:
			return ""
		try:
			response = daemon_client.transcribe_audio(
				item,
				mime_type=audio_data.get(
					"mime_type",
					"application/octet-stream",
				),
			)
		except RuntimeError as exc:
			self.logger.warning("Daemon STT request failed: %s", exc)
			return ""
		return str(response.get("text", "") or "")

	def update_properties(self):
		self.fs = self.stt_settings.fs