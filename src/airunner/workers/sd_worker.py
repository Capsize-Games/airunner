import torch
from PySide6.QtCore import QThread
from PySide6.QtCore import QObject, Signal, Slot

from airunner.enums import QueueType, SignalCode, ModelType, ModelStatus, ModelAction
from airunner.workers.worker import Worker
torch.backends.cuda.matmul.allow_tf32 = True


class GenerateWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, sd, message):
        super().__init__()
        self.sd = sd
        self.message = message

    @Slot()
    def run(self):
        try:
            self.sd.handle_generate_signal(self.message)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class SDWorker(Worker):
    queue_type = QueueType.GET_LAST_ITEM

    def __init__(self, prefix="SDWorker"):
        self.signals = [
            (SignalCode.RESET_APPLIED_MEMORY_SETTINGS, self.on_reset_applied_memory_settings),
            (SignalCode.SD_CANCEL_SIGNAL, self.on_sd_cancel_signal),
            (SignalCode.SD_MOVE_TO_CPU_SIGNAL, self.on_move_to_cpu),
            (SignalCode.START_AUTO_IMAGE_GENERATION_SIGNAL, self.on_start_auto_image_generation_signal),
            (SignalCode.STOP_AUTO_IMAGE_GENERATION_SIGNAL, self.on_stop_auto_image_generation_signal),
            (SignalCode.DO_GENERATE_SIGNAL, self.on_do_generate_signal),
            (SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL, self.on_interrupt_image_generation_signal),
            (SignalCode.CHANGE_SCHEDULER_SIGNAL, self.on_change_scheduler_signal),
            (SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal),
            (SignalCode.SD_TOKENIZER_LOAD_SIGNAL, self.on_tokenizer_load_signal),
            (SignalCode.SD_TOKENIZER_UNLOAD_SIGNAL, self.on_tokenizer_unload_signal),
            (SignalCode.SD_LOAD_SIGNAL, self.on_load_stablediffusion_signal),
            (SignalCode.SD_UNLOAD_SIGNAL, self.on_unload_stablediffusion_signal),
            (SignalCode.CONTROLNET_LOAD_SIGNAL, self.on_load_controlnet_signal),
            (SignalCode.CONTROLNET_UNLOAD_SIGNAL, self.on_unload_controlnet_signal),
            (SignalCode.LORA_UPDATE_SIGNAL, self.on_update_lora_signal),
            (SignalCode.EMBEDDING_SCAN_SIGNAL, self.scan_for_embeddings),
            (SignalCode.EMBEDDING_DELETE_MISSING_SIGNAL, self.delete_missing_embeddings),
            (SignalCode.SD_STATE_CHANGED_SIGNAL, self.handle_sd_state_changed_signal),
            (SignalCode.SAFETY_CHECKER_LOAD_SIGNAL, self.on_load_safety_checker),
            (SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL, self.on_unload_safety_checker),
        ]
        self.sd = None
        super().__init__(prefix=prefix)
        self.__requested_action = ModelAction.NONE
        self._threads = []
        self._workers = []

    def handle_sd_state_changed_signal(self):
        self.sd.controlnet_handle_sd_state_changed_signal()
        self.sd.scheduler_handle_sd_state_changed_signal()

    def on_load_safety_checker(self):
        if self.sd:
            self.sd.load_safety_checker()

    def on_unload_safety_checker(self):
        if self.sd:
            self.sd.unload_safety_checker()

    def scan_for_embeddings(self):
        if self.sd:
            self.sd.scan_for_embeddings()

    def delete_missing_embeddings(self, message):
        if self.sd:
            self.sd.delete_missing_embeddings(message)

    def get_embeddings(self, message):
        if self.sd:
            self.sd.get_embeddings(message)

    def on_update_lora_signal(self, message):
        if self.sd:
            self.sd.on_update_lora_signal(message)

    def on_add_lora_signal(self, message):
        if self.sd:
            self.sd.on_add_lora_signal(message)

    def on_load_controlnet_signal(self):
        if self.sd:
            self.sd.load_controlnet()

    def on_unload_controlnet_signal(self):
        if self.sd:
            self.sd.unload_controlnet()

    def on_load_stablediffusion_signal(self, data: dict = None):
        if self.sd:
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.SD,
                    "status": ModelStatus.LOADING,
                    "path": ""
                }
            )
            self.sd.load_stable_diffusion()

    def on_unload_stablediffusion_signal(self):
        if self.sd and self.sd.sd_model_status in (
            ModelStatus.LOADED,
            ModelStatus.FAILED,
            ModelStatus.READY,
        ):
            self.sd.on_unload_stablediffusion_signal()
        elif self.sd and self.sd.sd_model_status is ModelStatus.LOADING:
            self.__requested_action = ModelAction.CLEAR

    def on_tokenizer_load_signal(self, data: dict = None):
        if self.sd:
            self.sd.on_tokenizer_load_signal(data)

    def on_tokenizer_unload_signal(self, data: dict = None):
        if self.sd:
            self.sd.on_tokenizer_unload_signal(data)

    def start_worker_thread(self):
        if self.application_settings.sd_enabled:
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.SD,
                    "status": ModelStatus.LOADING,
                    "path": ""
                }
            )
        from airunner.aihandler.stablediffusion.sd_handler import SDHandler
        self.sd = SDHandler()
        if self.application_settings.sd_enabled:
            self.sd.load_stable_diffusion()

    def handle_message(self, message):
        if self.sd:
            self.sd.run()

    def on_reset_applied_memory_settings(self):
        if self.sd:
            self.sd.reset_applied_memory_settings()

    def on_sd_cancel_signal(self):
        print("on_sd_cancel_signal")

    def on_move_to_cpu(self):
        if self.sd:
            self.sd.move_pipe_to_cpu()

    def on_start_auto_image_generation_signal(self):
        # self.sd_mode = SDMode.DRAWING
        # self.generate()
        pass

    def on_stop_auto_image_generation_signal(self):
        #self.sd_mode = SDMode.STANDARD
        pass

    def on_do_generate_signal(self, message: dict):
        if self.sd:
            thread = QThread()
            worker = GenerateWorker(self.sd, message)
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            worker.error.connect(self.handle_error)
            self._threads.append(thread)
            self._workers.append(worker)
            thread.start()

    def handle_error(self, error_message):
        print(f"Error: {error_message}")

    def on_interrupt_image_generation_signal(self):
        if self.sd:
            self.sd.interrupt_image_generation_signal()

    def on_change_scheduler_signal(self, data: dict):
        if self.sd:
            self.sd.load_scheduler(force_scheduler_name=data["scheduler"])

    def on_model_status_changed_signal(self, message: dict):
        if self.sd and message["model"] == ModelType.SD:
            if self.__requested_action is ModelAction.CLEAR:
                self.on_unload_stablediffusion_signal()
            self.__requested_action = ModelAction.NONE
