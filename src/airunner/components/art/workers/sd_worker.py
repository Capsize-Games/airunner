import base64
import io
import os
from functools import partial
from typing import Dict, Optional

import torch
from PIL import Image

from airunner.enums import (
    EngineResponseCode,
    GeneratorSection,
    QueueType,
    SignalCode,
    ModelType,
    ModelAction,
    ModelStatus,
)
from airunner.components.application.workers.worker import Worker
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner_model.models.ai_models import AIModels
from airunner_model.models.generator_settings import GeneratorSettings
from airunner.enums import StableDiffusionVersion, normalize_art_version
from airunner.utils.image import convert_image_to_binary
from airunner.utils.memory import apply_cudnn_benchmark


torch.backends.cuda.matmul.allow_tf32 = True


class SDWorker(Worker):
    queue_type = QueueType.GET_LAST_ITEM

    def __init__(self, image_export_worker):
        self.image_export_worker = image_export_worker
        self._version: StableDiffusionVersion = StableDiffusionVersion.NONE
        self._current_model = None
        self._current_version = None
        self._current_pipeline = None
        self._requested_model = None
        self._requested_version = None
        self._requested_pipeline = None
        self._pending_scheduler: Optional[str] = None  # Deferred scheduler change
        self._is_generating: bool = False  # Track generation state
        self._active_daemon_job_id: Optional[str] = None
        self._pending_daemon_unload_after_cancel: bool = False
        super().__init__()
        apply_cudnn_benchmark(self.memory_settings)
        self.__requested_action = ModelAction.NONE
        self._threads = []
        self._workers = []

    @property
    def version(self) -> StableDiffusionVersion:
        version = self._version
        if version is StableDiffusionVersion.NONE:
            version = StableDiffusionVersion(
                normalize_art_version(self.generator_settings.version)
            )
        # Historical setting name: `sd_enabled`.
        # AIRunner's art worker now supports multiple backends (SDXL, Z-Image).
        # Disabling SD should not prevent Z-Image from running.
        if (
            self._version is StableDiffusionVersion.NONE
            and not self.application_settings.sd_enabled
        ):
            if version in (
                StableDiffusionVersion.Z_IMAGE_TURBO,
            ):
                return version
            return StableDiffusionVersion.NONE
        return version

    @version.setter
    def version(self, value: StableDiffusionVersion):
        self._version = value

    def scan_for_embeddings(self):
        # if self.model_manager:
        #     self.model_manager.scan_for_embeddings()
        pass

    def delete_missing_embeddings(self, message):
        # if self.model_manager:
        #     self.model_manager.delete_missing_embeddings(message)
        pass

    def get_embeddings(self, message):
        # if self.model_manager:
        #     self.model_manager.get_embeddings(message)
        pass

    def on_update_lora_signal(self, data=None):
        print("ON UPDATE LORA SIGNAL")
        self._reload_lora()

    def _reload_lora(self):
        # if self.model_manager:
        #     self.model_manager.reload_lora()
        pass

    def on_update_embeddings_signal(self):
        # if self.model_manager:
        #     self.model_manager.reload_embeddings()
        pass

    def on_add_lora_signal(self, message):
        # if self.model_manager:
        #     self.model_manager.on_add_lora_signal(message)
        pass

    def on_load_controlnet_signal(self, data=None):
        self.add_to_queue(
            {
                "action": ModelAction.LOAD,
                "type": ModelType.CONTROLNET,
                "data": data,
            }
        )

    def on_input_image_settings_changed_signal(self, data: Dict):
        # if self.model_manager:
        #     self.model_manager.settings_changed(data)
        pass

    def on_unload_controlnet_signal(self, _data=None):
        # if self.model_manager:
        #     self._unload_controlnet()
        pass

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

    def _requested_model_signature(
        self,
        image_request: Optional[ImageRequest],
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Return the requested model signature for one generation."""
        model_path = self._get_model_path_from_image_request(image_request)
        if image_request is not None:
            version = getattr(image_request, "version", None)
            pipeline_action = getattr(
                image_request,
                "pipeline_action",
                None,
            )
        else:
            version = getattr(self.generator_settings, "version", None)
            pipeline_action = getattr(
                self.generator_settings,
                "pipeline_action",
                None,
            )
        return model_path, version, pipeline_action

    def _record_loaded_model_signature(
        self,
        image_request: Optional[ImageRequest],
    ) -> None:
        """Record the active model signature after a successful load."""
        (
            self._current_model,
            self._current_version,
            self._current_pipeline,
        ) = self._requested_model_signature(image_request)

    def _clear_loaded_model_signature(self) -> None:
        """Forget the active model signature after unload."""
        self._current_model = None
        self._current_version = None
        self._current_pipeline = None

    def _get_model_path_from_image_request(
        self, image_request: Optional[ImageRequest]
    ) -> Optional[str]:
        model_path = None

        if image_request is not None:
            model_path = image_request.model_path

        if model_path is None:
            custom_path = getattr(self.generator_settings, "custom_path", None)
            if custom_path is not None and custom_path != "":
                if os.path.exists(custom_path):
                    model_path = custom_path

        generator_model = getattr(self.generator_settings, "model", None)
        if (
            model_path is None or model_path == ""
        ) and generator_model is not None:
            aimodel = AIModels.objects.get(generator_model)
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
            version = normalize_art_version(image_request.version)
            image_request.version = version
        else:
            version = normalize_art_version(settings.version)
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
                version=version,
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
                lora_scale=1.0,
                width=self.application_settings.working_width,
                height=self.application_settings.working_height,
            )
        new_version = StableDiffusionVersion(version)
        if new_version is not self.version:
            self.version = new_version
        return data

    def load_model_manager(self, data: Dict = None):
        # Ensure data is a dict to avoid TypeError when called without args
        data = data or {}
        data["settings"] = self.generator_settings
        data = self._process_image_request(data)
        do_reload = data.get("do_reload", False)
        # Ensure the model manager is instantiated before we try to set the image_request
        # mm = self.model_manager
        self.logger.debug(f"[LOAD DEBUG] load_model_manager: mm={id(mm)}, mm._pipe={getattr(mm, '_pipe', 'N/A')}, model_is_loaded={mm.model_is_loaded if mm else 'N/A'}")
        image_request = data.get("image_request")
        requested_signature = self._requested_model_signature(image_request)
        # if mm and mm.model_is_loaded and requested_signature != (
        #     self._current_model,
        #     self._current_version,
        #     self._current_pipeline,
        # ):
        #     do_reload = True
        # Attach the image_request to the model manager BEFORE loading so model_path property
        # resolves to the ImageRequest.model_path instead of falling back to stale generator_settings.model
        # if mm and image_request is not None:
        #     try:
        #         mm.image_request = image_request
        #     except Exception:
        #         pass
        # if mm:
        #     if do_reload:
        #         mm.reload()
        #     elif not mm.model_is_loaded:
        #         mm.load()
        #     # Debug: log which path will be used
        #     try:
        #         self.logger.debug(
        #             "[LOAD DEBUG] After load: mm._pipe=%s, mm=%s",
        #             getattr(mm, "_pipe", "N/A"),
        #             id(mm),
        #         )
        #     except Exception:
        #         pass
        #     if mm.model_is_loaded:
        #         self._record_loaded_model_signature(image_request)
        # # Only call the callback if the model is actually loaded
        # # If a download was triggered, the callback will be called after download completes
        # if data and mm and mm.model_is_loaded:
        #     callback = data.get("callback", None)
        #     if callback is not None:
        #         self.logger.debug(f"[LOAD DEBUG] Calling callback with mm={id(mm)}, mm._pipe={getattr(mm, '_pipe', 'N/A')}")
        #         callback(data)
        # elif data and mm and self._has_terminal_model_load_failure(mm):
        #     callback = data.get("callback", None)
        #     if callback is not None:
        #         callback(data)

    @staticmethod
    def _has_terminal_model_load_failure(model_manager) -> bool:
        try:
            return (
                model_manager.model_status.get(model_manager.model_type)
                is ModelStatus.FAILED
            )
        except Exception:
            return False

    def _notify_failed_model_load(
        self,
        image_request: Optional[ImageRequest],
    ) -> None:
        err = "Image model failed to load"
        if image_request is not None:
            if getattr(image_request, "model_path", None) == "":
                err = "You must select a model before generating images."
            if image_request.callback:
                image_request.callback(err)
        self.send_missing_model_alert(err)

    def unload(self, data: Dict):
        self.add_to_queue(
            {"action": ModelAction.UNLOAD, "type": ModelType.SD, "data": data}
        )

    def unload_model_manager(self, data: Dict = None):
        self.logger.info(">>> Stopping image export worker")
        self.image_export_worker.stop()            

        if data:
            callback = data.get("callback", None)
            if callback is not None:
                callback(data)

    def _load_controlnet(self):
        # if self.model_manager:
        #     self.model_manager.load_controlnet()
        pass

    def _unload_controlnet(self):
        # if self.model_manager:
        #     self.model_manager.unload_controlnet()
        pass

    def on_tokenizer_load_signal(self, data: Dict = None):
        # if self.model_manager:
        #     self.model_manager.sd_load_tokenizer(data)
        pass

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

    def request_daemon_unload_after_cancel(self) -> bool:
        """Unload the daemon art runtime after the active job finishes."""
        if self._active_daemon_job_id is None:
            return False
        self._pending_daemon_unload_after_cancel = True
        return True

    def _emit_pending_daemon_unload_if_requested(self) -> None:
        """Emit one deferred unload after a daemon art job exits."""
        if not self._pending_daemon_unload_after_cancel:
            return
        self._pending_daemon_unload_after_cancel = False
        self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL, {})

    def on_interrupt_image_generation_signal(self, _data=None):
        client = self._daemon_client()
        if client is not None and self._active_daemon_job_id is not None:
            try:
                client.cancel_art_job(
                    self._active_daemon_job_id,
                    auto_start=False,
                )
            except RuntimeError:
                pass
            return
        # if self.model_manager:
        #     self.model_manager.interrupt_image_generation()

    def on_change_scheduler_signal(self, data: Dict):
        scheduler_name = data["scheduler"]
        self.update_generator_settings(scheduler=scheduler_name)
        
        if self._is_generating:
            # Defer scheduler change until generation completes
            self.logger.debug(
                f"[SCHEDULER] Deferring scheduler change to '{scheduler_name}' until generation completes"
            )
            self._pending_scheduler = scheduler_name
        # elif self.model_manager:
        #     # Apply immediately if not generating
        #     self.model_manager._load_scheduler(scheduler_name)

    def _apply_scheduler_change(self, scheduler_name: str):
        """Apply a scheduler change. Used for deferred scheduler changes after generation."""
        # if self.model_manager:
        #     self.model_manager._load_scheduler(scheduler_name)
        pass

    def on_model_status_changed_signal(self, message: Dict):
        if message.get("model") != ModelType.SD:
            return
        if self.__requested_action is ModelAction.CLEAR:
            self.on_unload_art_signal()
        self.__requested_action = ModelAction.NONE

    def start_worker_thread(self):
        if not self.application_settings.sd_enabled:
            return
        # model_manager = self.model_manager
        # if model_manager is not None:
        #     model_manager.load()

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
        image_request = message.get("image_request")
        client = self._daemon_client()
        self.logger.info(
            "SDWorker::_generate_image using %s path for version=%s model=%s",
            "daemon" if client is not None else "local",
            getattr(image_request, "version", None),
            getattr(image_request, "model_path", None),
        )
        if client is not None:
            self._generate_image_via_daemon(message)
            return
        message["callback"] = self._finalize_do_generate_signal
        self.load_model_manager(message)

    def _daemon_client(self):
        api = getattr(self, "api", None)
        if api is None or getattr(api, "headless", False):
            return None
        return getattr(api, "daemon_client", None)

    @staticmethod
    def _encode_daemon_image(image: Optional[Image.Image]) -> Optional[str]:
        """Return one PNG base64 payload for daemon art requests."""
        if image is None:
            return None
        binary = convert_image_to_binary(image.convert("RGB"))
        if not binary:
            return None
        return base64.b64encode(binary).decode("ascii")

    def _generate_image_via_daemon(self, message: Dict) -> None:
        client = self._daemon_client()
        image_request = message.get("image_request")
        if client is None or not isinstance(image_request, ImageRequest):
            self.handle_error("No image request available for daemon art generation")
            return

        total_steps = max(int(image_request.steps or 1), 1)
        pipeline = getattr(
            image_request.generator_section,
            "value",
            GeneratorSection.TXT2IMG.value,
        )
        image_b64 = SDWorker._encode_daemon_image(image_request.image)
        error_message: Optional[str] = None
        image_bytes: Optional[bytes] = None

        def on_progress(status: Dict) -> None:
            try:
                progress = float(status.get("progress") or 0.0)
            except (TypeError, ValueError):
                return
            self.logger.debug(
                "SDWorker daemon art progress: status=%s progress=%.1f",
                status.get("status"),
                progress,
            )
            step = int(round((progress / 100.0) * total_steps))
            step = max(0, min(total_steps, step))
            if hasattr(self.api, "art"):
                self.api.art.progress_update(step=step, total=total_steps)

        try:
            self.logger.info(
                "Submitting daemon art job for version=%s scheduler=%s model=%s",
                image_request.version,
                image_request.scheduler,
                image_request.model_path,
            )
            job = client.start_art_generation(
                prompt=image_request.prompt,
                negative_prompt=image_request.negative_prompt or "",
                width=image_request.width,
                height=image_request.height,
                steps=image_request.steps,
                cfg_scale=image_request.scale,
                seed=(
                    None if image_request.random_seed else image_request.seed
                ),
                num_images=image_request.n_samples,
                model=image_request.model_path or None,
                version=image_request.version or None,
                scheduler=image_request.scheduler or None,
                pipeline=pipeline,
                strength=image_request.strength,
                image_b64=image_b64,
                skip_auto_export=True,
            )
            job_id = str(job.get("job_id", "") or "")
            if not job_id:
                raise RuntimeError("Art generation did not return a job id")
            self._active_daemon_job_id = job_id
            self.logger.info("Daemon art job accepted: job_id=%s", job_id)
            image_bytes = client.wait_art_job(
                job_id,
                auto_start=False,
                progress_callback=on_progress,
            )
            self.logger.info(
                "Daemon art job completed: job_id=%s bytes=%s",
                job_id,
                len(image_bytes),
            )
        except RuntimeError as exc:
            error_message = str(exc)
        finally:
            self._active_daemon_job_id = None

        if error_message is not None:
            self._handle_daemon_art_error(error_message)
            self._emit_pending_daemon_unload_if_requested()
            return

        if image_bytes is None:
            return

        print("*"*100)
        print("Daemon art generation succeeded, publishing result")
        try:
            self._publish_daemon_art_result(
                message,
                image_request,
                image_bytes,
            )
        finally:
            self._emit_pending_daemon_unload_if_requested()

    def _handle_daemon_art_error(self, message: str) -> None:
        self.handle_error(message)
        if "cancelled" in message.lower():
            self.api.worker_response(
                code=EngineResponseCode.INTERRUPTED,
                message="Image generation interrupted",
            )
            return
        self.send_missing_model_alert(message)
        self.api.worker_response(
            code=EngineResponseCode.ERROR,
            message=message,
        )

    def _publish_daemon_art_result(
        self,
        message: Dict,
        image_request: ImageRequest,
        image_bytes: bytes,
    ) -> None:
        print("*"*100)
        print("Publishing daemon art result to canvas and callbacks")
        image = Image.open(io.BytesIO(image_bytes)).copy()
        data = self._daemon_result_data(image_request)
        export_callback = partial(
            SDWorker._queue_post_display_export,
            self,
            image,
            data,
        )
        print("*"*100)
        print("Constructing ImageResponse for canvas and callbacks")
        response = ImageResponse(
            images=[image],
            data=data,
            active_rect=message.get("active_rect"),
            is_outpaint=(
                image_request.generator_section is GeneratorSection.OUTPAINT
            ),
            node_id=image_request.node_id,
            post_display_callback=export_callback,
        )
        sent_to_canvas = False
        if response.node_id is None and hasattr(self.api, "art"):
            print("*"*100)
            print("No node_id in response, sending image to canvas")
            try:
                self.api.art.canvas.send_image_to_canvas(response)
                sent_to_canvas = True
                print("*"*100)
                print("Image sent to canvas successfully")
            except Exception as exc:
                print("*"*100)
                print("Failed to send image to canvas:", exc)
                self.logger.warning(
                    "Failed to send image to canvas: %s",
                    exc,
                )
        else:
            print("*"*100)
            print("Node_id present in response or no canvas available, skipping canvas delivery")
            self.logger.info(
                "Skipping canvas delivery: node_id=%s has_art=%s",
                response.node_id,
                hasattr(self.api, "art"),
            )
        if not sent_to_canvas:
            export_callback()
        if image_request.callback:
            image_request.callback(response)
        self.api.worker_response(
            code=EngineResponseCode.IMAGE_GENERATED,
            message=response,
        )

    def _queue_post_display_export(
        self,
        image: Image.Image,
        data: Dict,
    ) -> None:
        """Queue auto export after the canvas handoff has been posted."""
        self.image_export_worker.add_to_queue(
            {"images": [image.copy()], "data": data}
        )

    def _daemon_result_data(self, image_request: ImageRequest) -> Dict:
        generator_section = image_request.generator_section
        return {
            "current_prompt": image_request.prompt,
            "current_negative_prompt": image_request.negative_prompt,
            "image_request": image_request,
            "guidance_scale": image_request.scale,
            "num_inference_steps": image_request.steps,
            "model_path": image_request.model_path,
            "version": image_request.version,
            "scheduler_name": image_request.scheduler,
            "strength": image_request.strength,
            "loaded_lora": [],
            "loaded_embeddings": [],
            "controlnet_enabled": bool(image_request.controlnet_enabled),
            "is_txt2img": generator_section is GeneratorSection.TXT2IMG,
            "is_img2img": generator_section is GeneratorSection.IMG2IMG,
            "is_inpaint": generator_section is GeneratorSection.INPAINT,
            "is_outpaint": generator_section is GeneratorSection.OUTPAINT,
            "mask_blur": image_request.outpaint_mask_blur,
            "memory_settings_flags": {},
            "application_settings": self.application_settings,
            "path_settings": self.path_settings,
            "metadata_settings": self.metadata_settings,
            "controlnet_settings": self.controlnet_settings,
        }

    def _finalize_do_generate_signal(self, message: Dict):
        # mm = self.model_manager
        # self.logger.debug(f"[FINALIZE DEBUG] _finalize: mm={id(mm) if mm else None}, mm._pipe={getattr(mm, '_pipe', 'N/A') if mm else 'N/A'}")
        # if mm:
        #     # Don't try to generate if model isn't loaded yet (e.g., download in progress)
        #     if not mm.model_is_loaded:
        #         if self._has_terminal_model_load_failure(mm):
        #             self._notify_failed_model_load(
        #                 message.get("image_request", None)
        #             )
        #             return
        #         self.logger.info(
        #             "Model not loaded yet, skipping generation (download may be in progress)"
        #         )
        #         return

        #     try:
        #         self._is_generating = True
        #         mm.handle_generate_signal(message)
        #     except (PipeNotLoadedException, TypeError) as e:
        #         error_message = getattr(e, "message", str(e))
        #         self.handle_error(error_message)
        #         image_request = message.get("image_request", None)
        #         err = "Image model failed to load"
        #         if (
        #             image_request is not None
        #             and getattr(image_request, "model_path", None) == ""
        #         ):
        #             err = "You must select a model before generating images."
        #         if image_request is not None and image_request.callback:
        #             image_request.callback(err)
        #         self.send_missing_model_alert(err)
        #     except Exception as e:
        #         import traceback
        #         tb = traceback.format_exc()
        #         error_msg = str(e) if str(e) else f"{type(e).__name__}"
        #         self.handle_error(f"Unexpected error: {error_msg}\n{tb}")
        #         image_request = message.get("image_request", None)
        #         failure_message = (
        #             "An unexpected error occurred during image generation. "
        #             "Please check logs."
        #         )
        #         if image_request is not None and image_request.callback:
        #             image_request.callback(failure_message)
        #         self.send_missing_model_alert(
        #             failure_message
        #         )
        #     finally:
        #         self._is_generating = False
        #         # Apply any scheduler change that was deferred during generation
        #         if self._pending_scheduler is not None:
        #             pending = self._pending_scheduler
        #             self._pending_scheduler = None
        #             self.logger.info(f"Applying deferred scheduler change to: {pending}")
        #             self._apply_scheduler_change(pending)
        pass

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
