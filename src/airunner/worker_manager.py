import gc
import traceback
import numpy as np
import torch
from PySide6.QtCore import QObject, Signal
from numba import cuda

from airunner.enums import SignalCode, EngineResponseCode, WorkerType
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.aihandler.logger import Logger
from airunner.utils.create_worker import create_worker



class Message:
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name")
        self.message = kwargs.get("message")
        self.conversation = kwargs.get("conversation")


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
        do_load_llm_on_init: bool = False,
        agent_class=None,
        agent_options: dict = None,
        **kwargs
    ):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super().__init__()
        self.llm_loaded: bool = False
        self.sd_loaded: bool = False
        self.message = ""
        self.current_message = ""
        self.do_process_queue = None
        self.do_process_queue = None
        self.logger = Logger(prefix=self.__class__.__name__)
        self.is_capturing_image = False
        signals = [
            (SignalCode.STT_HEAR_SIGNAL, self.on_hear_signal),
            (SignalCode.ENGINE_CANCEL_SIGNAL, self.on_engine_cancel_signal),
            (SignalCode.ENGINE_STOP_PROCESSING_QUEUE_SIGNAL, self.on_engine_stop_processing_queue_signal),
            (SignalCode.ENGINE_START_PROCESSING_QUEUE_SIGNAL, self.on_engine_start_processing_queue_signal),
            (SignalCode.LOG_ERROR_SIGNAL, self.on_error_signal),
            (SignalCode.LOG_WARNING_SIGNAL, self.on_warning_signal),
            (SignalCode.LOG_STATUS_SIGNAL, self.on_status_signal),
            (SignalCode.LLM_RESPONSE_SIGNAL, self.on_llm_response_signal),
            (SignalCode.LLM_TEXT_STREAMED_SIGNAL, self.on_llm_text_streamed_signal),
            (SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL, self.on_AudioCaptureWorker_response_signal),
            (SignalCode.TTS_REQUEST, self.on_tts_request),
            (SignalCode.LLM_REQUEST_WORKER_RESPONSE_SIGNAL, self.on_llm_request_worker_response_signal),

            (SignalCode.LLM_UNLOAD_SIGNAL, self.llm_on_unload_signal),
            (SignalCode.LLM_LOAD_SIGNAL, self.llm_on_load_signal),
            (SignalCode.LLM_LOAD_MODEL_SIGNAL, self.llm_on_load_model_signal),
            (SignalCode.LLM_CLEAR_HISTORY_SIGNAL, self.llm_on_clear_history_signal),
            (SignalCode.INTERRUPT_PROCESS_SIGNAL, self.llm_on_interrupt_process_signal),
            (SignalCode.RAG_RELOAD_INDEX_SIGNAL, self.llm_on_reload_rag_index_signal),
            (SignalCode.ADD_CHATBOT_MESSAGE_SIGNAL, self.llm_add_chatbot_response_to_history),
            (SignalCode.LOAD_CONVERSATION, self.llm_on_load_conversation),
            (SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, self.on_llm_request_signal)
        ]
        for signal in signals:
            self.register(signal[0], signal[1])

        self.sd_worker = None
        self.sd_state = None
        self.llm_request_worker = None
        self.llm_generate_worker = None
        self.tts_generator_worker = None
        self.tts_vocalizer_worker = None
        self.stt_audio_capture_worker = None
        self.stt_audio_processor_worker = None

        if not disable_sd:
            self.register_sd_workers()

        if not disable_llm:
            self.register_llm_workers(agent_class, do_load_llm_on_init, agent_options)

        if not disable_tts:
            self.register_tts_workers()

        if not disable_stt:
            self.register_stt_workers()

    def on_llm_request_signal(self, message: dict):
        self.llm_generate_worker.add_to_queue(message)

    def llm_on_unload_signal(self, message):
        self.logger.debug("Unloading LLM")

        # Ensure all tensors and objects are deleted
        if self.llm_generate_worker:
            self.llm_generate_worker.on_unload_llm_signal(message)
            del self.llm_generate_worker
            self.llm_generate_worker = None

        gc.collect()

        if torch.cuda.is_available():
            with torch.no_grad():
                try:
                    for device_id in range(torch.cuda.device_count()):
                        torch.cuda.set_device(device_id)
                        self.logger.debug(
                            f"Device {device_id} before empty_cache: {torch.cuda.memory_allocated(device_id)} bytes")
                        torch.cuda.empty_cache()
                        self.logger.debug(
                            f"Device {device_id} after empty_cache: {torch.cuda.memory_allocated(device_id)} bytes")
                        self.logger.debug(f"Device {device_id} memory summary: {torch.cuda.memory_summary(device_id)}")
                        torch.cuda.reset_max_memory_allocated(device=device_id)
                        torch.cuda.reset_max_memory_cached(device=device_id)
                        torch.cuda.synchronize(device=device_id)
                except RuntimeError:
                    self.logger.error("Failed to clear CUDA memory")

            # Force garbage collection multiple times
            for _ in range(3):
                gc.collect()

            for device_id in range(torch.cuda.device_count()):
                cuda.select_device(device_id)
                cuda.close()

            gc.collect()

    def llm_on_load_signal(self):
        self.llm_generate_worker.on_load_llm_signal()

    def llm_on_load_model_signal(self):
        self.llm_generate_worker.on_load_model_signal()

    def llm_on_clear_history_signal(self):
        self.llm_generate_worker.on_clear_history_signal()

    def llm_on_interrupt_process_signal(self):
        self.llm_generate_worker.on_interrupt_process_signal()

    def llm_on_reload_rag_index_signal(self, data: dict = None):
        self.llm_generate_worker.on_reload_rag_index_signal(data)

    def llm_add_chatbot_response_to_history(self, message):
        self.llm_generate_worker.add_chatbot_response_to_history(message)

    def llm_on_load_conversation(self, message):
        self.llm_generate_worker.on_load_conversation(message)

    def register_sd_workers(self):
        self.sd_worker = create_worker(WorkerType.SDWorker)
        self.sd_state = "loaded"

    def register_llm_workers(self, agent_class, do_load_llm_on_init, agent_options):
        self.llm_generate_worker = create_worker(
            WorkerType.LLMGenerateWorker,
            do_load_on_init=do_load_llm_on_init,
            agent_class=agent_class,
            agent_options=agent_options
        )

    def register_tts_workers(self):
        self.tts_generator_worker = create_worker(WorkerType.TTSGeneratorWorker)
        self.tts_vocalizer_worker = create_worker(WorkerType.TTSVocalizerWorker)

    def register_stt_workers(self):
        self.stt_audio_capture_worker = create_worker(WorkerType.AudioCaptureWorker)
        self.stt_audio_processor_worker = create_worker(WorkerType.AudioProcessorWorker)

    def on_llm_request_worker_response_signal(self, message: dict):
        self.llm_generate_worker.on_llm_request_worker_response_signal(message)

    def handle_error(self, error_message):
        print(f"Error: {error_message}")

    def do_response(self, response):
        """
        Handle a response from the application by putting it into
        a response worker queue.
        """
        self.emit_signal(SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL, {
            'code': EngineResponseCode.IMAGE_GENERATED,
            'message': response
        })

    def on_engine_cancel_signal(self):
        self.logger.debug("Canceling")
        self.emit_signal(SignalCode.SD_CANCEL_SIGNAL)

    def on_engine_stop_processing_queue_signal(self):
        self.do_process_queue = False

    def on_engine_start_processing_queue_signal(self):
        self.do_process_queue = True

    def on_hear_signal(self, message):
        """
        This is a slot function for the hear_signal.
        The hear signal is triggered from the speech_to_text.listen function.
        """
        print("HEARD", message)

    def handle_generate_caption(self, message):
        pass

    def on_caption_generated_signal(self, message: dict):
        print("TODO: caption generated signal", message)

    def handle_text_generated(self, message, code):
        print("TODO: handle text generated no stream")

    def on_AudioCaptureWorker_response_signal(self, message: dict):
        item: np.ndarray = message["item"]
        self.logger.debug("Heard signal")
        self.stt_audio_processor_worker.add_to_queue(item)

    def on_tts_request(self, data: dict):
        self.tts_generator_worker.add_to_queue(data)

    def on_llm_response_signal(self, message: dict):
        self.do_response(message)
    
    def EngineRequestWorker_handle_default(self, message: dict):
        self.logger.error(f"Unknown code: {message['code']}")

    def on_error_signal(self, message: dict):
        traceback.print_stack()
        self.logger.error(message)

    def on_warning_signal(self, message: dict):
        self.logger.warning(message)

    def on_status_signal(self, message: dict):
        self.logger.debug(message)

    def on_llm_text_streamed_signal(self, data: dict):
        try:
            if self.application_settings.tts_enabled:
                self.do_tts_request(data["message"], data["is_end_of_message"])
        except TypeError as e:
            self.logger.error(f"Error in on_llm_text_streamed_signal: {e}")
        self.emit_signal(SignalCode.APPLICATION_ADD_BOT_MESSAGE_TO_CONVERSATION, data)

    def on_sd_image_generated_signal(self, message):
        self.emit_signal(SignalCode.SD_IMAGE_GENERATED_SIGNAL, message)

    def unload_stablediffusion(self):
        """
        Unload the Stable Diffusion model from memory.
        """
        self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL)

    def parse_message(self, message):
        if message:
            if message.startswith("\""):
                message = message[1:]
            if message.endswith("\""):
                message = message[:-1]
        return message
    
    def do_tts_request(self, message: str, is_end_of_message: bool=False):
        if self.application_settings.tts_enabled:
            self.emit_signal(SignalCode.TTS_REQUEST, {
                'message': message.replace("</s>", "") + ("." if is_end_of_message else ""),
                'tts_settings': self.tts_settings,
                'is_end_of_message': is_end_of_message,
            })
