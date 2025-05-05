import os
from typing import Dict, Optional

import torch
from airunner.handlers.stablediffusion.stable_diffusion_model_manager import (
    StableDiffusionModelManager,
)
from airunner.handlers.stablediffusion.sdxl_model_manager import (
    SDXLModelManager,
)
from airunner.handlers.flux.flux_model_manager import (
    FluxModelManager,
)

from airunner.enums import (
    QueueType,
    SignalCode,
    ModelType,
    ModelAction,
)
from airunner.workers.worker import Worker
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.data.models.ai_models import AIModels
from airunner.enums import StableDiffusionVersion

torch.backends.cuda.matmul.allow_tf32 = True


class SDWorker(Worker):
    queue_type = QueueType.GET_LAST_ITEM

    def __init__(self):
        self._sd: Optional[StableDiffusionModelManager] = None
        self._sdxl: Optional[SDXLModelManager] = None
        self._flux: Optional[FluxModelManager] = None
        self._safety_checker = None
        self._model_manager = None
        self._version: StableDiffusionVersion = StableDiffusionVersion.NONE
        self.signal_handlers = {
            SignalCode.SD_CANCEL_SIGNAL: self.on_sd_cancel_signal,
            SignalCode.START_AUTO_IMAGE_GENERATION_SIGNAL: self.on_start_auto_image_generation_signal,
            SignalCode.STOP_AUTO_IMAGE_GENERATION_SIGNAL: self.on_stop_auto_image_generation_signal,
            SignalCode.DO_GENERATE_SIGNAL: self.on_do_generate_signal,
            SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL: self.on_interrupt_image_generation_signal,
            SignalCode.CHANGE_SCHEDULER_SIGNAL: self.on_change_scheduler_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.SD_LOAD_SIGNAL: self.on_load_art_signal,
            SignalCode.SD_ART_MODEL_CHANGED: self.on_art_model_changed,
            SignalCode.SD_UNLOAD_SIGNAL: self.on_unload_art_signal,
            SignalCode.CONTROLNET_LOAD_SIGNAL: self.on_load_controlnet_signal,
            SignalCode.CONTROLNET_UNLOAD_SIGNAL: self.on_unload_controlnet_signal,
            SignalCode.INPUT_IMAGE_SETTINGS_CHANGED: self.on_input_image_settings_changed_signal,
            SignalCode.LORA_UPDATE_SIGNAL: self.on_update_lora_signal,
            SignalCode.EMBEDDING_UPDATE_SIGNAL: self.on_update_embeddings_signal,
            SignalCode.EMBEDDING_DELETE_MISSING_SIGNAL: self.delete_missing_embeddings,
            SignalCode.SAFETY_CHECKER_LOAD_SIGNAL: self.on_load_safety_checker,
            SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL: self.on_unload_safety_checker,
        }
        self._current_model = None
        self._current_version = None
        self._current_pipeline = None
        self._requested_model = None
        self._requested_version = None
        self._requested_pipeline = None
        super().__init__()
        self.__requested_action = ModelAction.NONE
        self._threads = []
        self._workers = []

    @property
    def version(self) -> StableDiffusionVersion:
        version = self._version
        if version is StableDiffusionVersion.NONE:
            version = StableDiffusionVersion(self.generator_settings.version)
        if not self.application_settings.sd_enabled:
            return StableDiffusionVersion.NONE
        return version

    @version.setter
    def version(self, value: StableDiffusionVersion):
        self._version = value

    @property
    def model_manager(self):
        if self._model_manager is None:
            version = StableDiffusionVersion(self.generator_settings.version)
            if version is StableDiffusionVersion.SD1_5:
                self._model_manager = self.sd
            elif version in (
                StableDiffusionVersion.SDXL1_0,
                StableDiffusionVersion.SDXL_TURBO,
                StableDiffusionVersion.SDXL_LIGHTNING,
                StableDiffusionVersion.SDXL_HYPER,
            ):
                self._model_manager = self.sdxl
            elif version is StableDiffusionVersion.FLUX_S:
                self._model_manager = self.flux
            else:
                raise ValueError(
                    f"Unsupported Stable Diffusion version: {version}"
                )
        return self._model_manager

    @model_manager.setter
    def model_manager(self, value):
        self._model_manager = value

    @property
    def sd(self):
        if self._sd is None:
            self._sd = StableDiffusionModelManager()
        return self._sd

    @property
    def sdxl(self):
        if self._sdxl is None:
            self._sdxl = SDXLModelManager()
        return self._sdxl

    @property
    def flux(self):
        if self._flux is None:
            self._flux = FluxModelManager()
        return self._flux

    def on_load_safety_checker(self):
        if self.model_manager:
            self._load_safety_checker()

    def on_unload_safety_checker(self):
        if self.model_manager:
            self._unload_safety_checker()

    def scan_for_embeddings(self):
        if self.model_manager:
            self.model_manager.scan_for_embeddings()

    def delete_missing_embeddings(self, message):
        if self.model_manager:
            self.model_manager.delete_missing_embeddings(message)

    def get_embeddings(self, message):
        if self.model_manager:
            self.model_manager.get_embeddings(message)

    def on_update_lora_signal(self):
        self._reload_lora()

    def _reload_lora(self):
        if self.model_manager:
            self.model_manager.reload_lora()

    def on_update_embeddings_signal(self):
        if self.model_manager:
            self.model_manager.reload_embeddings()

    def on_add_lora_signal(self, message):
        if self.model_manager:
            self.model_manager.on_add_lora_signal(message)

    def on_load_controlnet_signal(self, data=None):
        self.add_to_queue(
            {
                "action": ModelAction.LOAD,
                "type": ModelType.CONTROLNET,
                "data": data,
            }
        )

    def on_input_image_settings_changed_signal(self, data: Dict):
        if self.model_manager:
            self.model_manager.settings_changed()

    def on_unload_controlnet_signal(self, _data=None):
        if self.model_manager:
            self._unload_controlnet()

    def on_load_art_signal(self, data: Dict = None):
        self.add_to_queue(
            {"action": ModelAction.LOAD, "type": ModelType.SD, "data": data}
        )

    def on_art_model_changed(self, data: Dict = None):
        self.unload_model_manager()

    def on_unload_art_signal(self, data=None):
        self.add_to_queue(
            {"action": ModelAction.UNLOAD, "type": ModelType.SD, "data": data}
        )

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

        if image_request is not None:
            version = image_request.version
        else:
            version = settings.version
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
                crops_coords_top_left=settings.crops_coords_top_left,
                negative_crops_coords_top_left=settings.negative_crops_coords_top_left,
                original_size=settings.original_size,
                target_size=settings.target_size,
                negative_original_size=settings.negative_original_size,
                negative_target_size=settings.negative_target_size,
                lora_scale=settings.lora_scale,
                quality_effects=settings.quality_effects,
                width=self.application_settings.working_width,
                height=self.application_settings.working_height,
            )
        new_version = StableDiffusionVersion(version)
        if new_version is not self.version:
            self.version = new_version
        return data

    def load_model_manager(self, data: Dict = None):
        data["settings"] = self.generator_settings
        data = self._process_image_request(data)
        do_reload = data.get("do_reload", False)
        if self.model_manager:
            if do_reload:
                self.model_manager.reload()
            elif not self.model_manager.sd_is_loaded:
                self.model_manager.load()
        if data:
            callback = data.get("callback", None)
            if callback is not None:
                callback(data)

    def unload_model_manager(self, data: Dict = None):
        if self._model_manager is not None:
            self._model_manager.unload()
            self.model_manager = None
        if data:
            callback = data.get("callback", None)
            if callback is not None:
                callback(data)

    def _load_controlnet(self):
        if self.model_manager:
            self.model_manager.load_controlnet()

    def _unload_controlnet(self):
        if self.model_manager:
            self.model_manager.unload_controlnet()

    def _load_safety_checker(self):
        if self.model_manager:
            self.model_manager.load_safety_checker()

    def _unload_safety_checker(self):
        if self.model_manager:
            self.model_manager.unload_safety_checker()

    def on_tokenizer_load_signal(self, data: Dict = None):
        if self.model_manager:
            self.model_manager.sd_load_tokenizer(data)

    @property
    def is_flux(self) -> bool:
        return self.generator_settings.version in (
            StableDiffusionVersion.FLUX_S.value,
        )

    @staticmethod
    def on_sd_cancel_signal(_data=None):
        print("on_sd_cancel_signal")

    def on_start_auto_image_generation_signal(self, _data=None):
        pass

    def on_stop_auto_image_generation_signal(self, _data=None):
        # self.model_manager_mode = SDMode.STANDARD
        pass

    def on_do_generate_signal(self, message: Dict):
        self.add_to_queue(
            {
                "action": ModelAction.GENERATE,
                "type": ModelType.SD,
                "message": message,
            }
        )

    def on_interrupt_image_generation_signal(self, _data=None):
        if self.model_manager:
            self.model_manager.interrupt_image_generation()

    def on_change_scheduler_signal(self, data: Dict):
        if self.model_manager:
            self.model_manager.load_scheduler(data["scheduler"])

    def on_model_status_changed_signal(self, message: Dict):
        if self.model_manager and message["model"] == ModelType.SD:
            if self.__requested_action is ModelAction.CLEAR:
                self.on_unload_art_signal()
            self.__requested_action = ModelAction.NONE

    def start_worker_thread(self):
        if self.model_manager and self.application_settings.sd_enabled:
            self.model_manager.load()

    def handle_message(self, message: Optional[Dict] = None):
        if message is not None:
            action = message.get("action", None)
            model_type = message.get("type", None)
            data = message.get("message", {})
            if action is not None and model_type is not None:
                if action is ModelAction.LOAD:
                    if model_type is ModelType.SD:
                        self.load_model_manager(data)
                    elif model_type is ModelType.CONTROLNET:
                        self._load_controlnet()
                elif action == ModelAction.UNLOAD:
                    if model_type is ModelType.SD:
                        self.unload_model_manager(data)
                    elif model_type is ModelType.CONTROLNET:
                        self._unload_controlnet()
                elif action is ModelAction.GENERATE:
                    if model_type is ModelType.SD:
                        self._generate_image(data)

    def _generate_image(self, message: Dict):
        message["callback"] = self._finalize_do_generate_signal
        self.load_model_manager(message)

    def _finalize_do_generate_signal(self, message: Dict):
        if self.model_manager:
            self.model_manager.handle_generate_signal(message)

    def handle_error(self, error_message):
        self.logger.error(f"SDWorker Error: {error_message}")

    def send_missing_model_alert(self, message):
        self.api.art.clear_progress_bar()
        self.api.art.missing_required_models(message)
        self.api.art.toggle_sd(enabled=False)
