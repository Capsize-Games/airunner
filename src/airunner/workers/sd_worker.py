from typing import Dict
import threading

import torch
from PySide6.QtCore import QThread
from PySide6.QtCore import QObject, Signal, Slot

from airunner.enums import QueueType, SignalCode, ModelType, ModelAction
from airunner.workers.worker import Worker
from airunner.handlers import StableDiffusionHandler
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.data.models import GeneratorSettings
from airunner.settings import (
    AIRUNNER_SD_ON,
    AIRUNNER_ART_MODEL_PATH,
    AIRUNNER_ART_MODEL_VERSION,
    AIRUNNER_ART_PIPELINE,
    AIRUNNER_ART_SCHEDULER,
    AIRUNNER_ART_USE_COMPEL,
)

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
        self.signal_handlers = {
            SignalCode.SD_CANCEL_SIGNAL: self.on_sd_cancel_signal,
            SignalCode.START_AUTO_IMAGE_GENERATION_SIGNAL: self.on_start_auto_image_generation_signal,
            SignalCode.STOP_AUTO_IMAGE_GENERATION_SIGNAL: self.on_stop_auto_image_generation_signal,
            SignalCode.DO_GENERATE_SIGNAL: self.on_do_generate_signal,
            SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL: self.on_interrupt_image_generation_signal,
            SignalCode.CHANGE_SCHEDULER_SIGNAL: self.on_change_scheduler_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.SD_LOAD_SIGNAL: self.on_load_stablediffusion_signal,
            SignalCode.SD_UNLOAD_SIGNAL: self.on_unload_stablediffusion_signal,
            SignalCode.CONTROLNET_LOAD_SIGNAL: self.on_load_controlnet_signal,
            SignalCode.CONTROLNET_UNLOAD_SIGNAL: self.on_unload_controlnet_signal,
            SignalCode.LORA_UPDATE_SIGNAL: self.on_update_lora_signal,
            SignalCode.EMBEDDING_UPDATE_SIGNAL: self.on_update_embeddings_signal,
            SignalCode.EMBEDDING_DELETE_MISSING_SIGNAL: self.delete_missing_embeddings,
            SignalCode.SAFETY_CHECKER_LOAD_SIGNAL: self.on_load_safety_checker,
            SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL: self.on_unload_safety_checker,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed,
        }
        super().__init__()
        self.__requested_action = ModelAction.NONE
        self._threads = []
        self._workers = []

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

    def on_load_stablediffusion_signal(self, data: Dict = None):
        if self.sd:
            thread = threading.Thread(target=self._load_sd, args=(data,))
            thread.start()

    def on_unload_stablediffusion_signal(self, data=None):
        if self.sd:
            thread = threading.Thread(target=self._unload_sd, args=(data,))
            thread.start()

    def _load_sd(self, data: Dict = None):
        do_reload = data.get("do_reload", False)
        if do_reload:
            self.sd.reload()
        else:
            self.sd.load()
        if data:
            callback = data.get("callback", None)
            if callback is not None:
                callback(data)

    def _unload_sd(self, data: Dict = None):
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

    def on_tokenizer_load_signal(self, data: Dict = None):
        if self.sd:
            self.sd.sd_load_tokenizer(data)

    def start_worker_thread(self):
        generator_settings = self.generator_settings
        model_path = generator_settings.aimodel.path if generator_settings.aimodel else ""
        if AIRUNNER_ART_MODEL_PATH != "":
            model_path = AIRUNNER_ART_MODEL_PATH
        
        model_version = generator_settings.version if generator_settings.version else ""
        if AIRUNNER_ART_MODEL_VERSION != "":
            model_version = AIRUNNER_ART_MODEL_VERSION
        
        pipeline = generator_settings.pipeline_action if generator_settings.pipeline_action else ""
        if AIRUNNER_ART_PIPELINE != "":
            pipeline = AIRUNNER_ART_PIPELINE
        
        scheduler_name = generator_settings.scheduler if generator_settings.scheduler else ""
        if AIRUNNER_ART_SCHEDULER != "":
            scheduler_name = AIRUNNER_ART_SCHEDULER
        
        use_compel = generator_settings.use_compel
        if AIRUNNER_ART_USE_COMPEL != "":
            use_compel = AIRUNNER_ART_USE_COMPEL

        self.sd = StableDiffusionHandler(
            model_path=model_path,
            model_version=model_version,
            pipeline=pipeline,
            scheduler_name=scheduler_name,
            use_compel=use_compel
        )
        
        if self.application_settings.sd_enabled or AIRUNNER_SD_ON:
            self.sd.load()

    def handle_message(self, message):
        if self.sd:
            self.sd.run()

    @staticmethod
    def on_sd_cancel_signal(_data=None):
        print("on_sd_cancel_signal")

    def on_start_auto_image_generation_signal(self, _data=None):
        pass

    def on_stop_auto_image_generation_signal(self, _data=None):
        # self.sd_mode = SDMode.STANDARD
        pass

    def on_do_generate_signal(self, message: Dict):
        if self.sd:
            if not message.get("image_request", None):
                settings = self.generator_settings
                message["image_request"] = ImageRequest(
                    pipeline_action=settings.pipeline_action,
                    generator_name=settings.generator_name,
                    prompt=settings.prompt,
                    negative_prompt=settings.negative_prompt,
                    second_prompt=settings.second_prompt,
                    second_negative_prompt=settings.second_negative_prompt,
                    random_seed=settings.random_seed,
                    model_path=settings.aimodel.path if settings.aimodel else "",
                    scheduler=settings.scheduler,
                    version=settings.version,
                    use_compel=settings.use_compel,
                    steps=settings.steps,
                    ddim_eta=settings.ddim_eta,
                    scale=settings.scale / 100,
                    seed=settings.seed,
                    strength=settings.strength / 100,
                    n_samples=settings.n_samples,
                    clip_skip=settings.clip_skip,
                    crops_coord_top_left=settings.crops_coord_top_left,
                    original_size=settings.original_size,
                    target_size=settings.target_size,
                    negative_original_size=settings.negative_original_size,
                    negative_target_size=settings.negative_target_size,
                    lora_scale=settings.lora_scale,
                )
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

    @staticmethod
    def handle_error(error_message):
        import traceback
        traceback.print_stack()
        print(f"SDWorker Error: {error_message}")

    def on_interrupt_image_generation_signal(self, _data=None):
        if self.sd:
            self.sd.interrupt_image_generation()

    def on_change_scheduler_signal(self, data: Dict):
        if self.sd:
            self.sd.load_scheduler(data["scheduler"])

    def on_model_status_changed_signal(self, message: Dict):
        if self.sd and message["model"] == ModelType.SD:
            if self.__requested_action is ModelAction.CLEAR:
                self.on_unload_stablediffusion_signal()
            self.__requested_action = ModelAction.NONE
