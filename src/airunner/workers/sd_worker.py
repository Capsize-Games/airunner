import threading

import torch
from PySide6.QtCore import QThread
from PySide6.QtCore import QObject, Signal, Slot

from airunner.enums import QueueType, SignalCode, ModelType, ModelAction
from airunner.mediator_mixin import MediatorMixin
from airunner.workers.worker import Worker
from airunner.handlers.stablediffusion.stablediffusion_handler import StableDiffusionHandler

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

    def __init__(self):
        self.sd = None
        MediatorMixin.__init__(self)
        
        super().__init__(
            signals=(
                (SignalCode.RESET_APPLIED_MEMORY_SETTINGS, self.on_reset_applied_memory_settings),
                (SignalCode.SD_CANCEL_SIGNAL, self.on_sd_cancel_signal),
                (SignalCode.START_AUTO_IMAGE_GENERATION_SIGNAL, self.on_start_auto_image_generation_signal),
                (SignalCode.STOP_AUTO_IMAGE_GENERATION_SIGNAL, self.on_stop_auto_image_generation_signal),
                (SignalCode.DO_GENERATE_SIGNAL, self.on_do_generate_signal),
                (SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL, self.on_interrupt_image_generation_signal),
                (SignalCode.CHANGE_SCHEDULER_SIGNAL, self.on_change_scheduler_signal),
                (SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal),
                (SignalCode.SD_LOAD_SIGNAL, self.on_load_stablediffusion_signal),
                (SignalCode.SD_UNLOAD_SIGNAL, self.on_unload_stablediffusion_signal),
                (SignalCode.CONTROLNET_LOAD_SIGNAL, self.on_load_controlnet_signal),
                (SignalCode.CONTROLNET_UNLOAD_SIGNAL, self.on_unload_controlnet_signal),
                (SignalCode.LORA_UPDATE_SIGNAL, self.on_update_lora_signal),
                (SignalCode.EMBEDDING_UPDATE_SIGNAL, self.on_update_embeddings_signal),
                (SignalCode.EMBEDDING_DELETE_MISSING_SIGNAL, self.delete_missing_embeddings),
                (SignalCode.SD_STATE_CHANGED_SIGNAL, self.handle_sd_state_changed_signal),
                (SignalCode.SAFETY_CHECKER_LOAD_SIGNAL, self.on_load_safety_checker),
                (SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL, self.on_unload_safety_checker),
                (SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed),
            )
        )
        self.__requested_action = ModelAction.NONE
        self._threads = []
        self._workers = []

    def handle_sd_state_changed_signal(self, _data=None):
        self.sd.controlnet_handle_sd_state_changed_signal()
        self.sd.scheduler_handle_sd_state_changed_signal()

    def on_load_safety_checker(self):
        if self.sd:
            thread = threading.Thread(target=self._load_safety_checker)
            thread.start()

    def on_unload_safety_checker(self):
        if self.sd:
            thread = threading.Thread(target=self._unload_safety_checker)
            thread.start()
    
    def on_application_settings_changed(self):
        if self.sd:
            self.sd.on_application_settings_changed()

    def scan_for_embeddings(self):
        if self.sd:
            self.sd.scan_for_embeddings()

    def delete_missing_embeddings(self, message):
        if self.sd:
            self.sd.delete_missing_embeddings(message)

    def get_embeddings(self, message):
        if self.sd:
            self.sd.get_embeddings(message)

    def on_update_lora_signal(self):
        thread = threading.Thread(target=self._reload_lora)
        thread.start()

    def _reload_lora(self):
        if self.sd:
            self.sd.reload_lora()

    def on_update_embeddings_signal(self):
        if self.sd:
            self.sd.reload_embeddings()

    def on_add_lora_signal(self, message):
        if self.sd:
            self.sd.on_add_lora_signal(message)

    def on_load_controlnet_signal(self, _data=None):
        if self.sd:
            thread = threading.Thread(target=self._load_controlnet)
            thread.start()

    def on_unload_controlnet_signal(self, _data=None):
        if self.sd:
            thread = threading.Thread(target=self._unload_controlnet)
            thread.start()

    def on_load_stablediffusion_signal(self, data:dict=None):
        if self.sd:
            thread = threading.Thread(target=self._load_sd, args=(data,))
            thread.start()

    def on_unload_stablediffusion_signal(self, data=None):
        if self.sd:
            thread = threading.Thread(target=self._unload_sd, args=(data,))
            thread.start()

    def _load_sd(self, data:dict=None):
        do_reload = data.get("do_reload", False)
        if do_reload:
            self.sd.reload()
        else:
            self.sd.load()
        if data:
            callback = data.get("callback", None)
            if callback is not None:
                callback(data)

    def _unload_sd(self, data:dict=None):
        self.sd.unload()
        if data:
            callback = data.get("callback", None)
            if callback is not None:
                callback(data)

    def _load_controlnet(self):
        self.sd.load_controlnet()

    def _unload_controlnet(self):
        self.sd.unload_controlnet()

    def _load_safety_checker(self):
        self.sd.load_safety_checker()

    def _unload_safety_checker(self):
        self.sd.unload_safety_checker()

    def on_tokenizer_load_signal(self, data: dict = None):
        if self.sd:
            self.sd.sd_load_tokenizer(data)

    def start_worker_thread(self):
        self.sd = StableDiffusionHandler()
        if self.application_settings.sd_enabled:
            self.sd.load()

    def handle_message(self, message):
        if self.sd:
            self.sd.run()

    def on_reset_applied_memory_settings(self, _data=None):
        if self.sd:
            self.sd.reset_applied_memory_settings()

    def on_sd_cancel_signal(self, _data=None):
        print("on_sd_cancel_signal")

    def on_start_auto_image_generation_signal(self, _data=None):
        # self.sd_mode = SDMode.DRAWING
        # self.generate()
        pass

    def on_stop_auto_image_generation_signal(self, _data=None):
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

    def on_interrupt_image_generation_signal(self, _data=None):
        if self.sd:
            self.sd.interrupt_image_generation()

    def on_change_scheduler_signal(self, data: dict):
        if self.sd:
            self.sd.load_scheduler(data["scheduler"])

    def on_model_status_changed_signal(self, message: dict):
        if self.sd and message["model"] == ModelType.SD:
            if self.__requested_action is ModelAction.CLEAR:
                self.on_unload_stablediffusion_signal()
            self.__requested_action = ModelAction.NONE
