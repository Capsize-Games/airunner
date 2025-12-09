import os
import threading
from typing import Dict, Optional

import torch
from airunner.components.art.managers.stablediffusion.sdxl_model_manager import (
    SDXLModelManager,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_manager import (
    X4UpscaleManager,
)
from airunner.components.art.managers.flux.flux_model_manager import (
    FluxModelManager,
)
from airunner.components.art.managers.zimage.zimage_model_manager import (
    ZImageModelManager,
)

from airunner.enums import (
    QueueType,
    SignalCode,
    ModelType,
    ModelAction,
)
from airunner.components.application.workers.worker import Worker
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.data.ai_models import AIModels
from airunner.components.art.data.generator_settings import GeneratorSettings
from airunner.enums import StableDiffusionVersion
from airunner.components.application.exceptions import PipeNotLoadedException


torch.backends.cuda.matmul.allow_tf32 = True


class SDWorker(Worker):
    queue_type = QueueType.GET_LAST_ITEM

    def __init__(self, image_export_worker):
        self.image_export_worker = image_export_worker
        self._sdxl: Optional[SDXLModelManager] = None
        self._flux: Optional[FluxModelManager] = None
        self._zimage: Optional[ZImageModelManager] = None
        self._sd: Optional[SDModelManager] = None
        self._sdxl: Optional[SDXLModelManager] = None
        self._x4_upscaler: Optional[X4UpscaleManager] = None
        self._model_manager = None
        self._model_manager_lock = threading.Lock()  # Protects lazy model manager creation
        self._version: StableDiffusionVersion = StableDiffusionVersion.NONE
        self._current_model = None
        self._current_version = None
        self._current_pipeline = None
        self._requested_model = None
        self._requested_version = None
        self._requested_pipeline = None
        self._pending_scheduler: Optional[str] = None  # Deferred scheduler change
        self._is_generating: bool = False  # Track generation state
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
        # Use lock to prevent race condition when multiple threads access this property
        # simultaneously (e.g., worker thread loading model while main thread handles signal)
        with self._model_manager_lock:
            if self._model_manager is None:
                version = StableDiffusionVersion(self.generator_settings.version)

                if version in (
                    StableDiffusionVersion.FLUX_DEV,
                    StableDiffusionVersion.FLUX_SCHNELL,
                ):
                    self._model_manager = self.flux
                elif version in (
                    StableDiffusionVersion.Z_IMAGE_TURBO,
                    StableDiffusionVersion.Z_IMAGE_BASE,
                ):
                    self._model_manager = self.zimage
                elif version in (
                    StableDiffusionVersion.SDXL1_0,
                    StableDiffusionVersion.SDXL_TURBO,
                    StableDiffusionVersion.SDXL_LIGHTNING,
                    StableDiffusionVersion.SDXL_HYPER,
                ):
                    self._model_manager = self.sdxl
                elif version == StableDiffusionVersion.X4_UPSCALER:
                    self._model_manager = self.x4_upscaler
                else:
                    raise ValueError(
                        f"Unsupported Stable Diffusion version: {version}"
                    )
            return self._model_manager

    @model_manager.setter
    def model_manager(self, value):
        with self._model_manager_lock:
            self._model_manager = value

    @property
    def flux(self):
        if self._flux is None:
            self._flux = FluxModelManager()
            self._flux.image_export_worker = self.image_export_worker
        return self._flux

    @property
    def zimage(self):
        if self._zimage is None:
            self._zimage = ZImageModelManager()
            self._zimage.image_export_worker = self.image_export_worker
        return self._zimage

    @property
    def sdxl(self):
        if self._sdxl is None:
            self._sdxl = SDXLModelManager()
            self._sdxl.image_export_worker = self.image_export_worker
        return self._sdxl

    @property
    def x4_upscaler(self):
        if self._x4_upscaler is None:
            self._x4_upscaler = X4UpscaleManager()
            self._x4_upscaler.image_export_worker = self.image_export_worker
        return self._x4_upscaler

    def scan_for_embeddings(self):
        if self.model_manager:
            self.model_manager.scan_for_embeddings()

    def delete_missing_embeddings(self, message):
        if self.model_manager:
            self.model_manager.delete_missing_embeddings(message)

    def get_embeddings(self, message):
        if self.model_manager:
            self.model_manager.get_embeddings(message)

    def on_update_lora_signal(self, data=None):
        print("ON UPDATE LORA SIGNAL")
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
            self.model_manager.settings_changed(data)

    def on_unload_controlnet_signal(self, _data=None):
        if self.model_manager:
            self._unload_controlnet()

    def on_load_art_signal(self, data: Dict = None):
        self.add_to_queue(
            {"action": ModelAction.LOAD, "type": ModelType.SD, "data": data}
        )

    def on_art_model_changed(self, data: Dict = None):
        # CRITICAL: Invalidate the generator settings cache so we pick up
        # the latest precision/dtype settings from the database when the
        # model is reloaded. Without this, the worker uses stale cached
        # settings (e.g., old dtype) because the UI and worker have
        # separate caches.
        self._invalidate_setting_cache(GeneratorSettings)
        self.unload_model_manager()

    def _get_model_path_from_image_request(
        self, image_request: Optional[ImageRequest]
    ) -> Optional[str]:
        model_path = None

        if image_request is not None:
            model_path = image_request.model_path

        if model_path is None:
            custom_path = self.generator_settings.custom_path
            if custom_path is not None and custom_path != "":
                if os.path.exists(custom_path):
                    model_path = custom_path

        if (
            model_path is None or model_path == ""
        ) and self.generator_settings.model is not None:
            aimodel = AIModels.objects.get(self.generator_settings.model)
            if aimodel is not None:
                model_path = aimodel.path

        return model_path

    def _debug_log_model_path_resolution(
        self, image_request: Optional[ImageRequest], model_path: Optional[str]
    ):
        try:
            self.logger.debug(
                "Model path resolution: image_request.model_path=%s generator_settings.model=%s generator_settings.custom_path=%s resolved=%s",
                getattr(image_request, "model_path", None),
                getattr(self.generator_settings, "model", None),
                getattr(self.generator_settings, "custom_path", None),
                model_path,
            )
        except Exception:
            pass

    def _process_image_request(self, data: Dict) -> Dict:
        settings = self.generator_settings
        image_request = data.get("image_request", None)
        model_path = self._get_model_path_from_image_request(image_request)
        # Log resolution for debugging
        try:
            self._debug_log_model_path_resolution(image_request, model_path)
        except Exception:
            pass

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
                images_per_batch=settings.images_per_batch,
                clip_skip=settings.clip_skip,
                crops_coords_top_left=settings.crops_coords_top_left,
                negative_crops_coords_top_left=settings.negative_crops_coords_top_left,
                original_size=settings.original_size,
                target_size=settings.target_size,
                negative_original_size=settings.negative_original_size,
                negative_target_size=settings.negative_target_size,
                lora_scale=settings.lora_scale,
                width=self.application_settings.working_width,
                height=self.application_settings.working_height,
            )
        new_version = StableDiffusionVersion(version)
        if new_version is not self.version:
            self.version = new_version
            # Reset model manager when version changes so the correct one is selected
            self._model_manager = None
        return data

    def load_model_manager(self, data: Dict = None):
        # Ensure data is a dict to avoid TypeError when called without args
        data = data or {}
        data["settings"] = self.generator_settings
        data = self._process_image_request(data)
        do_reload = data.get("do_reload", False)
        # Ensure the model manager is instantiated before we try to set the image_request
        mm = self.model_manager
        self.logger.debug(f"[LOAD DEBUG] load_model_manager: mm={id(mm)}, mm._pipe={getattr(mm, '_pipe', 'N/A')}, model_is_loaded={mm.model_is_loaded if mm else 'N/A'}")
        image_request = data.get("image_request")
        # Attach the image_request to the model manager BEFORE loading so model_path property
        # resolves to the ImageRequest.model_path instead of falling back to stale generator_settings.model
        if mm and image_request is not None:
            try:
                mm.image_request = image_request
            except Exception:
                pass
        if mm:
            if do_reload:
                mm.reload()
            elif not mm.model_is_loaded:
                mm.load()
            # Debug: log which path will be used
            try:
                self.logger.debug(
                    "[LOAD DEBUG] After load: mm._pipe=%s, mm=%s",
                    getattr(mm, "_pipe", "N/A"),
                    id(mm),
                )
            except Exception:
                pass
        # Only call the callback if the model is actually loaded
        # If a download was triggered, the callback will be called after download completes
        if data and mm and mm.model_is_loaded:
            callback = data.get("callback", None)
            if callback is not None:
                self.logger.debug(f"[LOAD DEBUG] Calling callback with mm={id(mm)}, mm._pipe={getattr(mm, '_pipe', 'N/A')}")
                callback(data)

    def unload(self, data: Dict):
        self.add_to_queue(
            {"action": ModelAction.UNLOAD, "type": ModelType.SD, "data": data}
        )

    def unload_model_manager(self, data: Dict = None):
        if self._model_manager is not None:
            # CRITICAL: Store reference before clearing to check which manager it is
            manager_ref = self._model_manager

            # Unload the manager
            self._model_manager.unload()
            self.model_manager = None

            # Clear the specific manager reference to allow garbage collection
            # Without this, the manager stays in memory even after unload()
            if manager_ref is self._flux:
                self.logger.info(">>> Unloading FLUX model manager")
                self._flux.image_export_worker.stop()
                del self._flux.image_export_worker
                self._flux.image_export_worker = None
                del self._flux
                self._flux = None
            elif manager_ref is self._sd:
                self.logger.info(">>> Unloading SD model manager")
                self._sd.image_export_worker.stop()
                del self._sd.image_export_worker
                self._sd.image_export_worker = None
                del self._sd
                self._sd = None
            elif manager_ref is self._sdxl:
                self.logger.info(">>> Unloading SDXL model manager")
                self._sdxl.image_export_worker.stop()
                del self._sdxl.image_export_worker
                self._sdxl.image_export_worker = None
                del self._sdxl
                self._sdxl = None
            elif manager_ref is self._x4_upscaler:
                self.logger.info(">>> Unloading X4 Upscaler model manager")
                self._x4_upscaler.image_export_worker.stop()
                del self._x4_upscaler.image_export_worker
                self._x4_upscaler.image_export_worker = None
                del self._x4_upscaler
                self._x4_upscaler = None

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

    def on_tokenizer_load_signal(self, data: Dict = None):
        if self.model_manager:
            self.model_manager.sd_load_tokenizer(data)

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
        scheduler_name = data["scheduler"]
        self.update_generator_settings(scheduler=scheduler_name)
        
        if self._is_generating:
            # Defer scheduler change until generation completes
            self.logger.debug(
                f"[SCHEDULER] Deferring scheduler change to '{scheduler_name}' until generation completes"
            )
            self._pending_scheduler = scheduler_name
        elif self.model_manager:
            # Apply immediately if not generating
            self.model_manager._load_scheduler(scheduler_name)

    def _apply_scheduler_change(self, scheduler_name: str):
        """Apply a scheduler change. Used for deferred scheduler changes after generation."""
        if self.model_manager:
            self.model_manager._load_scheduler(scheduler_name)

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
            # Messages enqueued for GENERATE use key 'message',
            # while LOAD/UNLOAD paths use key 'data'. Support both.
            data = (
                message.get("message")
                if "message" in message
                else message.get("data", {})
            )
            
            self.logger.debug(f"[HANDLE_MESSAGE] action={action}, model_type={model_type}")
            
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
        mm = self.model_manager
        self.logger.debug(f"[FINALIZE DEBUG] _finalize: mm={id(mm) if mm else None}, mm._pipe={getattr(mm, '_pipe', 'N/A') if mm else 'N/A'}")
        if mm:
            # Don't try to generate if model isn't loaded yet (e.g., download in progress)
            if not mm.model_is_loaded:
                self.logger.info(
                    "Model not loaded yet, skipping generation (download may be in progress)"
                )
                return

            try:
                self._is_generating = True
                mm.handle_generate_signal(message)
            except (PipeNotLoadedException, TypeError) as e:
                error_message = getattr(e, "message", str(e))
                self.handle_error(error_message)
                image_request = message.get("image_request", None)
                err = "Image model failed to load"
                if (
                    image_request is not None
                    and getattr(image_request, "model_path", None) == ""
                ):
                    err = "You must select a model before generating images."
                self.send_missing_model_alert(err)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                error_msg = str(e) if str(e) else f"{type(e).__name__}"
                self.handle_error(f"Unexpected error: {error_msg}\n{tb}")
                self.send_missing_model_alert(
                    "An unexpected error occurred during image generation. Please check logs."
                )
            finally:
                self._is_generating = False
                # Apply any scheduler change that was deferred during generation
                if self._pending_scheduler is not None:
                    pending = self._pending_scheduler
                    self._pending_scheduler = None
                    self.logger.info(f"Applying deferred scheduler change to: {pending}")
                    self._apply_scheduler_change(pending)

    def handle_error(self, error_message):
        self.logger.error(f"SDWorker Error: {error_message}")

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
