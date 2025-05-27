from airunner.workers.llm_generate_worker import LLMGenerateWorker
from airunner.workers.mask_generator_worker import MaskGeneratorWorker
from airunner.workers.sd_worker import SDWorker

try:
    from airunner.workers.audio_capture_worker import AudioCaptureWorker
    from airunner.workers.audio_processor_worker import AudioProcessorWorker
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
        self._worker_threads = []  # List of (worker, thread) tuples
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
        if self.logger:
            self.logger.debug("Initializing worker manager...")
            self.logger.info("imported workers, initializing")
        self._mask_generator_worker, _ = create_worker(
            MaskGeneratorWorker, registry=self._worker_threads
        )
        if self.logger:
            self.logger.debug("MaskGeneratorWorker created.")
        self._sd_worker, _ = create_worker(SDWorker, registry=self._worker_threads)
        if self.logger:
            self.logger.debug("SDWorker created.")
        if AudioCaptureWorker is not None:
            self._stt_audio_capture_worker, _ = create_worker(
                AudioCaptureWorker, registry=self._worker_threads
            )
            if self.logger:
                self.logger.debug("AudioCaptureWorker created.")
        if AudioProcessorWorker is not None:
            self._stt_audio_processor_worker, _ = create_worker(
                AudioProcessorWorker, registry=self._worker_threads
            )
            if self.logger:
                self.logger.debug("AudioProcessorWorker created.")
        if TTSGeneratorWorker is not None:
            self._tts_generator_worker, _ = create_worker(
                TTSGeneratorWorker, registry=self._worker_threads
            )
            if self.logger:
                self.logger.debug("TTSGeneratorWorker created.")
        if TTSVocalizerWorker is not None:
            self._tts_vocalizer_worker, _ = create_worker(
                TTSVocalizerWorker, registry=self._worker_threads
            )
            if self.logger:
                self.logger.debug("TTSVocalizerWorker created.")
        self._llm_generate_worker, _ = create_worker(
            LLMGenerateWorker, registry=self._worker_threads
        )
        if self.logger:
            self.logger.debug("LLMGenerateWorker created.")
            self.logger.info("INITIALIZE WORKERS COMPLETE")

    def shutdown_workers(self):
        """
        Stop all managed workers and join their threads to ensure clean shutdown.
        """
        if self.logger:
            self.logger.info("Shutting down all workers and threads...")
        for worker, thread in self._worker_threads:
            stop = getattr(worker, "stop", None)
            cancel = getattr(worker, "cancel", None)
            if callable(stop):
                try:
                    stop()
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error stopping worker {worker}: {e}")
            elif callable(cancel):
                try:
                    cancel()
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error canceling worker {worker}: {e}")
            if thread is not None:
                try:
                    if thread.isRunning():
                        thread.quit()
                        thread.wait(3000)
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error joining thread {thread}: {e}")
        self._worker_threads.clear()

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
