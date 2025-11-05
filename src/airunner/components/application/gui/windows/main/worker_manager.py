"""
Worker Manager for handling various application workers.

This class uses inline imports to avoid slow startup times. Do not move
imports to the top of the file.
"""

from typing import Dict
from airunner.components.application.workers.worker import Worker
from airunner.enums import SignalCode
from airunner.utils.application.create_worker import create_worker


class WorkerManager(Worker):
    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL: self.on_llm_request_signal,
            SignalCode.START_AUTO_IMAGE_GENERATION_SIGNAL: self.on_start_auto_image_generation_signal,
            SignalCode.DO_GENERATE_SIGNAL: self.on_do_generate_signal,
            SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL: self.on_tts_generator_worker_add_to_stream_signal,
            SignalCode.TTS_ENABLE_SIGNAL: self.on_enable_tts_signal,
            SignalCode.STT_LOAD_SIGNAL: self.on_stt_load_signal,
            SignalCode.STT_START_CAPTURE_SIGNAL: self.on_stt_start_capture_signal,
        }
        super().__init__()
        self._mask_generator_worker = None
        self._sd_worker = None
        self._stt_audio_capture_worker = None
        self._stt_audio_processor_worker = None
        self._tts_generator_worker = None
        self._tts_vocalizer_worker = None
        self._llm_generate_worker = None
        self._document_worker = None
        if self.logger:
            self.logger.debug("WorkerManager initialized.")

    def handle_message(self, message: Dict):
        data = message.get("data", {})
        request_type = message.get("request_type")
        try:
            if request_type == "llm_generate":
                if self.llm_generate_worker is not None:
                    self.llm_generate_worker.on_llm_request_signal(data)
            elif request_type == "image_auto_generate":
                if self.sd_worker is not None:
                    self.sd_worker.on_start_auto_image_generation_signal(data)
            elif request_type == "image_generate":
                if self.sd_worker is not None:
                    self.sd_worker.on_do_generate_signal(data)
            elif request_type == "tts_generate":
                if self.tts_vocalizer_worker is not None:
                    self.tts_vocalizer_worker.on_tts_generator_worker_add_to_stream_signal(
                        data
                    )
            elif request_type == "tts_enable":
                if self.tts_generator_worker is not None:
                    self.tts_generator_worker.on_enable_tts_signal(data)
            elif request_type == "stt_load":
                if self.stt_audio_processor_worker is not None:
                    self.stt_audio_processor_worker.on_stt_load_signal(data)
            elif request_type == "stt_start_capture":
                if self.stt_audio_capture_worker is not None:
                    self.stt_audio_capture_worker.on_stt_start_capture_signal(
                        data
                    )

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing worker requests: {e}")

    @property
    def mask_generator_worker(self):
        if self._mask_generator_worker is None:
            from airunner.components.art.workers.mask_generator_worker import (
                MaskGeneratorWorker,
            )

            self._mask_generator_worker = create_worker(MaskGeneratorWorker)
        return self._mask_generator_worker

    @property
    def sd_worker(self):
        if self._sd_worker is None:
            from airunner.components.art.workers.sd_worker import SDWorker

            self._sd_worker = create_worker(SDWorker)
            # reference self.mask_generator_worker to ensure it is created
            _ = self.mask_generator_worker
        return self._sd_worker

    @property
    def stt_audio_capture_worker(self):
        if self._stt_audio_capture_worker is None:
            from airunner.components.stt.workers.audio_capture_worker import (
                AudioCaptureWorker,
            )

            self._stt_audio_capture_worker = create_worker(AudioCaptureWorker)
        return self._stt_audio_capture_worker

    @property
    def stt_audio_processor_worker(self):
        if self._stt_audio_processor_worker is None:
            from airunner.components.stt.workers.audio_processor_worker import (
                AudioProcessorWorker,
            )

            self._stt_audio_processor_worker = create_worker(
                AudioProcessorWorker
            )
        return self._stt_audio_processor_worker

    @property
    def tts_generator_worker(self):
        if self._tts_generator_worker is None:
            from airunner.components.tts.workers.tts_generator_worker import (
                TTSGeneratorWorker,
            )

            self._tts_generator_worker = create_worker(TTSGeneratorWorker)
        return self._tts_generator_worker

    @property
    def tts_vocalizer_worker(self):
        if self._tts_vocalizer_worker is None:
            from airunner.components.tts.workers.tts_vocalizer_worker import (
                TTSVocalizerWorker,
            )

            self._tts_vocalizer_worker = create_worker(TTSVocalizerWorker)
        return self._tts_vocalizer_worker

    @property
    def llm_generate_worker(self):
        if self._llm_generate_worker is None:
            from airunner.components.llm.workers.llm_generate_worker import (
                LLMGenerateWorker,
            )

            self._llm_generate_worker = create_worker(LLMGenerateWorker)
        return self._llm_generate_worker

    @property
    def document_worker(self):
        if self._document_worker is None:
            from airunner.components.documents.workers.document_worker import (
                DocumentWorker,
            )

            self._document_worker = create_worker(DocumentWorker)
        return self._document_worker

    def on_llm_request_signal(self, data: Dict):
        self.add_to_queue(
            {
                "data": data,
                "request_type": "llm_generate",
            }
        )

    def on_start_auto_image_generation_signal(self, data: Dict):
        self.add_to_queue(
            {
                "data": data,
                "request_type": "image_auto_generate",
            }
        )

    def on_do_generate_signal(self, data: Dict):
        self.add_to_queue(
            {
                "data": data,
                "request_type": "image_generate",
            }
        )

    def on_tts_generator_worker_add_to_stream_signal(self, data: Dict):
        self.add_to_queue({"data": data, "request_type": "tts_generate"})

    def on_enable_tts_signal(self, data: Dict):
        self.add_to_queue(
            {
                "data": data,
                "request_type": "tts_enable",
            }
        )

    def on_stt_load_signal(self, data: Dict):
        self.add_to_queue(
            {
                "data": data,
                "request_type": "stt_load",
            }
        )

    def on_stt_start_capture_signal(self, data: Dict):
        self.add_to_queue(
            {
                "data": data,
                "request_type": "stt_start_capture",
            }
        )
