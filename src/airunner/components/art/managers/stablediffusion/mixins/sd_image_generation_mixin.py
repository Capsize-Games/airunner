"""
Mixin providing image generation execution for Stable Diffusion.

This mixin handles the actual image generation process including signal
handling, generation loop, interruption, and result processing.
"""

from typing import Dict, Optional

import torch

from airunner.components.application.exceptions import (
    PipeNotLoadedException,
    InterruptedException,
)
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.enums import (
    HandlerState,
    EngineResponseCode,
)
from airunner.settings import (
    CUDA_ERROR,
    AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE,
)
from airunner.utils.memory import clear_memory


class SDImageGenerationMixin:
    """Mixin providing image generation execution for Stable Diffusion."""

    def handle_generate_signal(self, message: Optional[Dict] = None):
        """
        Handle image generation request signal.

        Args:
            message: Signal message containing image_request.

        Main entry point for image generation. Handles scheduler changes,
        state management, and delegates to _generate().
        """
        self.image_request = message.get("image_request", None)

        if not self.image_request:
            raise ValueError("ImageRequest is None")

        # Always (re)apply the requested scheduler to avoid lingering config
        requested_scheduler = self.image_request.scheduler
        current_scheduler = self.scheduler_name
        self.logger.debug(
            f"[SCHEDULER CHECK] Requested: '{requested_scheduler}', Current: '{current_scheduler}'"
        )
        if requested_scheduler != current_scheduler:
            self.logger.info(
                f"[SCHEDULER CHANGE] Switching from '{current_scheduler}' to '{requested_scheduler}'"
            )
        # Reload even if names match to guarantee fresh config/flags
        if requested_scheduler:
            self._load_scheduler(requested_scheduler)

        self._clear_cached_properties()

        if self._current_state not in (
            HandlerState.GENERATING,
            HandlerState.PREPARING_TO_GENERATE,
        ):
            self._generate()
            self._current_state = HandlerState.READY
            clear_memory()
        self.handle_requested_action()

        # Clear the image request so that we no longer
        # use its values in the next request.
        self.image_request = None

    def interrupt_image_generation(self):
        """
        Request interruption of ongoing image generation.

        Sets flag that will be checked during generation loop to stop early.
        """
        if self._current_state in (
            HandlerState.PREPARING_TO_GENERATE,
            HandlerState.GENERATING,
        ):
            self.do_interrupt_image_generation = True
            try:
                self.logger.debug(
                    "interrupt_image_generation called: setting do_interrupt_image_generation=True for %s",
                    getattr(self, "model_type", None),
                )
            except Exception:
                pass

    def _generate(self):
        """
        Execute image generation process.

        Main generation loop that:
        1. Prepares data and loads prompt embeddings
        2. Runs pipeline inference
        3. Exports images
        4. Sends responses

        Handles interruption and errors gracefully.
        """
        self.logger.debug(f"[GEN DEBUG] _generate called: self._pipe={self._pipe}, self={id(self)}")
        if self._pipe is None:
            raise PipeNotLoadedException()

        self._load_prompt_embeds()
        clear_memory()
        data = self._prepare_data(self.active_rect)
        self._current_state = HandlerState.GENERATING

        try:
            for results in self._get_results(data):

                # Benchmark getting images from results
                images = results.get("images", [])

                nsfw_flags = []

                if images is not None:
                    if images:
                        processed_images, nsfw_flags = (
                            self._check_and_mark_nsfw_images(images)
                        )
                        if any(nsfw_flags):
                            self.logger.info(
                                "NSFW content detected in generated batch; marked images will be returned"
                            )
                        images = processed_images
                    else:
                        nsfw_flags = []

                    self.api.art.final_progress_update(
                        total=self.image_request.steps
                    )

                    data.update(
                        {
                            "current_prompt": self._current_prompt,
                            "current_prompt_2": self._current_prompt_2,
                            "current_negative_prompt": self._current_negative_prompt,
                            "current_negative_prompt_2": self._current_negative_prompt_2,
                            "image_request": self.image_request,
                            "model_path": self.model_path,
                            "version": self.version,
                            "scheduler_name": self.scheduler_name,
                            "loaded_lora": self._loaded_lora,
                            "loaded_embeddings": self._loaded_embeddings,
                            "controlnet_enabled": self.controlnet_enabled,
                            "is_txt2img": self.is_txt2img,
                            "is_img2img": self.is_img2img,
                            "is_inpaint": self.is_inpaint,
                            "is_outpaint": self.is_outpaint,
                            "mask_blur": self.mask_blur,
                            "memory_settings_flags": self._memory_settings_flags,
                            "application_settings": self.application_settings,
                            "path_settings": self.path_settings,
                            "metadata_settings": self.metadata_settings,
                            "controlnet_settings": self.controlnet_settings,
                            "nsfw_detected": nsfw_flags,
                            "nsfw_filter_active": self.use_safety_checker,
                        }
                    )

                    self.image_export_worker.add_to_queue(
                        {
                            "images": images,
                            "data": data,
                        }
                    )
                else:
                    images = images or []
                    nsfw_flags = [False] * len(images)

                self._current_state = HandlerState.PREPARING_TO_GENERATE
                response = None
                code = EngineResponseCode.NONE
                try:
                    response = ImageResponse(
                        images=images,
                        data=data,
                        active_rect=self.active_rect,
                        is_outpaint=self.is_outpaint,
                        node_id=self.image_request.node_id,
                    )
                    code = EngineResponseCode.IMAGE_GENERATED

                    # Send image to canvas for layer support (if not a node-based generation)
                    if response.node_id is None and hasattr(self.api, "art"):
                        try:
                            self.api.art.canvas.send_image_to_canvas(response)
                        except Exception as e:
                            self.logger.debug(
                                f"Failed to send image to canvas: {e}"
                            )
                except PipeNotLoadedException as e:
                    self.logger.error(e)
                except InterruptedException:
                    code = EngineResponseCode.INTERRUPTED
                except Exception as e:
                    code = EngineResponseCode.ERROR
                    error_message = f"Error generating image: {e}"
                    response = error_message
                    if CUDA_ERROR in str(e):
                        code = EngineResponseCode.INSUFFICIENT_GPU_MEMORY
                        response = AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE
                    self.logger.error(error_message)
                if self.image_request.callback:
                    self.image_request.callback(response)
                self.api.worker_response(code=code, message=response)
        except InterruptedException:
            self.logger.debug("Image generation interrupted")
            self._current_state = HandlerState.READY
            self.api.worker_response(
                code=EngineResponseCode.INTERRUPTED,
                message="Image generation interrupted",
            )
            self.do_interrupt_image_generation = False

        clear_memory()

    def _get_results(self, data):
        """
        Run pipeline inference and yield results.

        Args:
            data: Generation parameters dictionary.

        Yields:
            Pipeline results for each batch.

        Handles infinite generation mode and interruption checks.
        """
        with torch.no_grad(), torch.amp.autocast(
            "cuda", dtype=self.data_type, enabled=True
        ):
            total = 0
            while total < self.image_request.n_samples:
                if self.do_interrupt_image_generation:
                    raise InterruptedException()
                results = self._pipe(**data)

                # Debug: Check what we got from the pipeline
                import numpy as np
                from PIL import Image

                if "images" in results and len(results["images"]) > 0:
                    img = results["images"][0]
                    if isinstance(img, Image.Image):
                        img_array = np.array(img)
                        self.logger.info(
                            f"[PIPELINE DEBUG] Image type: PIL Image"
                        )
                        self.logger.info(
                            f"[PIPELINE DEBUG] Image shape: {img_array.shape}"
                        )
                        self.logger.info(
                            f"[PIPELINE DEBUG] Image dtype: {img_array.dtype}"
                        )
                        self.logger.info(
                            f"[PIPELINE DEBUG] Image min: {img_array.min()}, max: {img_array.max()}"
                        )
                        self.logger.info(
                            f"[PIPELINE DEBUG] Unique values: {len(np.unique(img_array))}"
                        )
                    else:
                        self.logger.info(
                            f"[PIPELINE DEBUG] Image type: {type(img)}"
                        )

                yield results
                if not self.image_request.generate_infinite_images:
                    total += 1

    def _callback(self, _pipe, _i, _t, callback_kwargs):
        """
        Progress callback during generation.

        Args:
            _pipe: Pipeline instance.
            _i: Current step index.
            _t: Current timestep.
            callback_kwargs: Additional callback parameters.

        Returns:
            Updated callback_kwargs.
        """
        self.api.art.progress_update(step=_i, total=self.image_request.steps)
        return callback_kwargs

    def _interrupt_callback(self, _pipe, _i, _t, callback_kwargs):
        """
        Interrupt-aware callback during generation.

        Args:
            _pipe: Pipeline instance.
            _i: Current step index.
            _t: Current timestep.
            callback_kwargs: Additional callback parameters.

        Returns:
            Updated callback_kwargs.

        Raises:
            InterruptedException: If interruption was requested.
        """
        if self.do_interrupt_image_generation:
            self.do_interrupt_image_generation = False
            raise InterruptedException()
        else:
            self._callback(_pipe, _i, _t, callback_kwargs)
        return callback_kwargs
