import os
from typing import Dict, Optional
import threading

import torch
from PySide6.QtCore import QThread
from PySide6.QtCore import QObject, Signal, Slot

from airunner.enums import QueueType, SignalCode, ModelType, ModelAction
from airunner.workers.worker import Worker
from airunner.handlers import StableDiffusionModelManager
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.data.models.ai_models import AIModels
from airunner.settings import (
    AIRUNNER_SD_ON,
    AIRUNNER_ART_MODEL_PATH,
    AIRUNNER_ART_MODEL_VERSION,
    AIRUNNER_ART_PIPELINE,
    AIRUNNER_ART_SCHEDULER,
    AIRUNNER_ART_USE_COMPEL,
)

torch.backends.cuda.matmul.allow_tf32 = True


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
        data["settings"] = self.generator_settings
        self._handle_load_stable_diffusion(data)

    def _get_model_path_from_image_request(
        self, image_request: Optional[ImageRequest]
    ) -> Optional[str]:
        model_path = None

        if image_request is not None:
            model_path = image_request.model_path

        if (
            model_path is None or model_path == ""
        ) and self.generator_settings.model is not None:
            aimodel = AIModels.objects.get(self.generator_settings.model)
            if aimodel is not None:
                model_path = aimodel.path

        if model_path is None or model_path == "":
            self.send_missing_model_alert(
                "You have no Stable Diffusion models. Download one and try again."
            )

        if not os.path.exists(model_path):
            self.send_missing_model_alert(
                f"The model at path {model_path} does not exist."
            )

        return model_path

    def _process_image_request(self, data: Dict) -> Dict:
        settings = self.generator_settings
        image_request = data.get("image_request", None)
        model_path = self._get_model_path_from_image_request(image_request)

        if image_request is None:
            data["image_request"] = ImageRequest(
                pipeline_action=settings.pipeline_action,
                generator_name=settings.generator_name,
                prompt=settings.prompt,
                negative_prompt=settings.negative_prompt,
                second_prompt=settings.second_prompt,
                second_negative_prompt=settings.second_negative_prompt,
                random_seed=settings.random_seed,
                model_path=model_path,
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
        return data

    def _handle_load_stable_diffusion(self, data: Dict):
        print("HANDLE LOAD STABLE DIFFUSION", self.sd)
        data = self._process_image_request(data)
        self._load_sd(data)
        # if self.sd:
        #     thread = threading.Thread(target=self._load_sd, args=(data,))
        #     thread.start()

    def on_unload_stablediffusion_signal(self, data=None):
        # if self.sd:
        #     thread = threading.Thread(target=self._unload_sd, args=(data,))
        #     thread.start()
        self._unload_sd(data)

    def _load_sd(self, data: Dict = None):
        print("_LOAD_SD FUNCTION", data)
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
        self.sd = StableDiffusionModelManager()
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
        print("ON DO GENERATE SIGNAL")
        message["callback"] = self._finalize_do_generate_signal
        message["settings"] = self.generator_settings
        self._handle_load_stable_diffusion(message)

    def _finalize_do_generate_signal(self, message: Dict):
        print("_finalize_do_generate_signal", message)
        try:
            self.sd.handle_generate_signal(message)
        except ValueError as e:
            self.logger.error(f"Failed to generate: {e}")
            print(message)

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

    def send_missing_model_alert(self, message):
        self.emit_signal(
            SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL,
            {"do_clear": True},
        )
        self.emit_signal(
            SignalCode.MISSING_REQUIRED_MODELS,
            {
                "title": "Model Not Found",
                "message": message,
            },
        )
        self.emit_signal(SignalCode.TOGGLE_SD_SIGNAL, {"enabled": False})
