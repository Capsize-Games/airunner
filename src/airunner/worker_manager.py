from PySide6.QtCore import QObject, Signal

from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.handlers.logger import Logger
from airunner.utils.create_worker import create_worker
from airunner.workers.audio_capture_worker import AudioCaptureWorker
from airunner.workers.audio_processor_worker import AudioProcessorWorker
from airunner.workers.llm_generate_worker import LLMGenerateWorker
from airunner.workers.mask_generator_worker import MaskGeneratorWorker
from airunner.workers.sd_worker import SDWorker
from airunner.workers.tts_generator_worker import TTSGeneratorWorker
from airunner.workers.tts_vocalizer_worker import TTSVocalizerWorker


class WorkerManager(QObject, MediatorMixin, SettingsMixin):
    """
    The engine is responsible for processing requests and offloading
    them to the appropriate AI model controller.
    """
    # Signals
    request_signal_status = Signal(str)
    image_generated_signal = Signal(dict)

    def __init__(
        self,
        disable_sd: bool = False,
        disable_llm: bool = False,
        disable_tts: bool = False,
        disable_stt: bool = False,
        agent_options: dict = None
    ):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super().__init__()
        self.logger = Logger(prefix=self.__class__.__name__)
        self._sd_worker = None
        self._llm_request_worker = None
        self._llm_generate_worker = None
        self._tts_generator_worker = None
        self._tts_vocalizer_worker = None
        self._stt_audio_capture_worker = None
        self._stt_audio_processor_worker = None

        self.agent_options = agent_options

        if not disable_sd:
            self.register_sd_workers()

        if not disable_llm:
            self.register_llm_workers(self.agent_options)

        if not disable_tts:
            self.register_tts_workers()

        if not disable_stt:
            self.register_stt_workers()

        self.mask_generator_worker = create_worker(MaskGeneratorWorker)

    def register_sd_workers(self):
        self._sd_worker = create_worker(SDWorker)

    def register_llm_workers(self, agent_options):
        self._llm_generate_worker = create_worker(LLMGenerateWorker, agent_options=agent_options)

    def register_tts_workers(self):
        self._tts_generator_worker = create_worker(TTSGeneratorWorker)
        self._tts_vocalizer_worker = create_worker(TTSVocalizerWorker)

    def register_stt_workers(self):
        self._stt_audio_capture_worker = create_worker(AudioCaptureWorker)
        self._stt_audio_processor_worker = create_worker(AudioProcessorWorker)
