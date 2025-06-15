from airunner.components.llm.workers.llm_generate_worker import LLMGenerateWorker
from airunner.workers.mask_generator_worker import MaskGeneratorWorker
from airunner.workers.sd_worker import SDWorker

try:
    from airunner.components.stt.workers.audio_capture_worker import AudioCaptureWorker
    from airunner.components.stt.workers.audio_processor_worker import AudioProcessorWorker
    from airunner.workers.tts_generator_worker import TTSGeneratorWorker
    from airunner.workers.tts_vocalizer_worker import TTSVocalizerWorker
except OSError:
    AudioCaptureWorker = None
    AudioProcessorWorker = None
    TTSGeneratorWorker = None
    TTSVocalizerWorker = None

from airunner.utils.application.create_worker import create_worker


class WorkerManager:
    def __init__(self, logger=None):
        self.logger = logger
        self._mask_generator_worker = None
        self._sd_worker = None
        self._stt_audio_capture_worker = None
        self._stt_audio_processor_worker = None
        self._tts_generator_worker = None
        self._tts_vocalizer_worker = None
        self._llm_generate_worker = None
        if self.logger:
            self.logger.debug("WorkerManager initialized.")

    def initialize_workers(self):
        self.logger.debug("Initializing worker manager...")
        self._mask_generator_worker = create_worker(MaskGeneratorWorker)
        self._sd_worker = create_worker(SDWorker)
        if AudioCaptureWorker is not None:
            self._stt_audio_capture_worker = create_worker(AudioCaptureWorker)
        if AudioProcessorWorker is not None:
            self._stt_audio_processor_worker = create_worker(
                AudioProcessorWorker
            )
        if TTSGeneratorWorker is not None:
            self._tts_generator_worker = create_worker(TTSGeneratorWorker)
        if TTSVocalizerWorker is not None:
            self._tts_vocalizer_worker = create_worker(TTSVocalizerWorker)
        self._llm_generate_worker = create_worker(LLMGenerateWorker)

    @property
    def mask_generator_worker(self):
        return self._mask_generator_worker

    @property
    def sd_worker(self):
        return self._sd_worker

    @property
    def stt_audio_capture_worker(self):
        return self._stt_audio_capture_worker

    @property
    def stt_audio_processor_worker(self):
        return self._stt_audio_processor_worker

    @property
    def tts_generator_worker(self):
        return self._tts_generator_worker

    @property
    def tts_vocalizer_worker(self):
        return self._tts_vocalizer_worker

    @property
    def llm_generate_worker(self):
        return self._llm_generate_worker

    # Add properties or methods to access workers as needed
