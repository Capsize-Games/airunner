import gc
import os
from contextlib import nullcontext
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import torch
from diffusers import StableDiffusionUpscalePipeline
from PIL import Image

from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.components.art.managers.stablediffusion.stable_diffusion_model_manager import (
    StableDiffusionModelManager,
)
from airunner.enums import (
    EngineResponseCode,
    ModelStatus,
    ModelType,
    SignalCode,
    HandlerState,
)
from airunner.components.application.exceptions import InterruptedException
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner.utils.memory import clear_memory


class X4UpscaleManager(StableDiffusionModelManager):
    """Manager for the ``stabilityai/stable-diffusion-x4-upscaler`` pipeline."""

    _pipeline_class = StableDiffusionUpscalePipeline
    model_type: ModelType = ModelType.UPSCALER
    _model_status = {}

    MODEL_REPO = "stabilityai/stable-diffusion-x4-upscaler"
    SCALE_FACTOR = 4
    PREVIEW_FILENAME = "preview_current.png"
    DEFAULT_NUM_STEPS = 30
    DEFAULT_GUIDANCE_SCALE = 7.5
    DEFAULT_NOISE_LEVEL = 20
    LARGE_INPUT_THRESHOLD = 512
    DEFAULT_TILE_SIZE = 256
    DEFAULT_TILE_BATCH_SIZE = 2
    TILE_OVERLAP = 32
    MIN_TILE_SIZE = 128
    MAX_TILE_REDUCTIONS = 3

    def handle_generate_signal(self, message: Optional[Dict] = None):
        """Handle image generation request for upscaling."""
        self.image_request = message.get("image_request", None)
        if not self.image_request:
            raise ValueError("ImageRequest is None for upscale")

        source_image = (
            self.image_request.image
            if hasattr(self.image_request, "image")
            else None
        )

        if source_image is None:
            error_msg = "No source image available for upscaling"
            self.logger.error(error_msg)
            self._emit_failure(error_msg)
            return

        # Mark manager as generating so interrupt requests can set the
        # interrupt flag via interrupt_image_generation().
        prev_state = getattr(self, "_current_state", None)
        try:
            self._current_state = HandlerState.GENERATING
            try:
                result = self.handle_upscale_request(source_image)
                return result
            except InterruptedException:
                # Upscale was interrupted by user action; notify and cleanup.
                self.logger.debug("Upscale interrupted by user")
                try:
                    self.api.worker_response(
                        code=EngineResponseCode.INTERRUPTED,
                        message="Upscale interrupted",
                    )
                except Exception:
                    pass
                return None
            except Exception as exc:
                self.logger.exception("Upscale failed: %s", exc)
                self._emit_failure(str(exc))
                raise
        finally:
            # Clear generating state and reset interrupt flag
            try:
                self._current_state = prev_state or HandlerState.READY
            except Exception:
                self._current_state = HandlerState.READY
            try:
                self.do_interrupt_image_generation = False
            except Exception:
                pass

    @property
    def use_compel(self) -> bool:
        return False

    @property
    def preview_dir(self) -> str:
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "art",
            "upscaled",
        )

    @property
    def preview_path(self) -> str:
        return os.path.join(self.preview_dir, self.PREVIEW_FILENAME)

    @property
    def use_from_single_file(self) -> bool:
        return False

    @property
    def pipeline_map(
        self,
    ) -> Dict[str, Any]:
        return {"x4-upscaler": StableDiffusionUpscalePipeline}

    def is_loaded(self) -> bool:
        return (
            self._pipe is not None and self.model_status == ModelStatus.LOADED
        )

    def load(self):
        if self.is_loaded():
            return
        self.change_model_status(ModelType.UPSCALER, ModelStatus.LOADING)
        try:
            self.logger.info(
                "Loading x4 upscaler pipeline from %s", self.model_path
            )
            # If CUDA is available we can request fp16 variants; on CPU
            # avoid forcing fp16 variant to prevent incorrect weight loading
            # or computation issues.
            file_directory = os.path.dirname(self.model_path)
            data = self._prepare_pipe_data()
            if torch.cuda.is_available():
                self._pipe = StableDiffusionUpscalePipeline.from_pretrained(
                    file_directory, **data
                )
            else:
                self._pipe = StableDiffusionUpscalePipeline.from_pretrained(
                    file_directory, **data
                )
            self._configure_pipeline()
            try:
                # Debug: log pipeline device and some component dtypes
                dev = getattr(self._pipe, "device", None)
                self.logger.info(
                    "x4 upscaler loaded on device=%s dtype=%s",
                    dev,
                    self.data_type,
                )
            except Exception:
                pass
            self.change_model_status(ModelType.UPSCALER, ModelStatus.LOADED)
        except Exception as exc:
            self._pipe = None
            self.change_model_status(ModelType.UPSCALER, ModelStatus.FAILED)
            self.logger.exception("Failed to load x4 upscaler: %s", exc)
            raise

    def _configure_pipeline(self):
        if not self._pipe:
            return
        self._make_memory_efficient()
        try:
            if hasattr(self._pipe, "enable_attention_slicing"):
                self._pipe.enable_attention_slicing()
            if hasattr(
                self._pipe, "enable_xformers_memory_efficient_attention"
            ):
                try:
                    self._pipe.enable_xformers_memory_efficient_attention()
                except Exception:
                    pass
            if hasattr(self._pipe, "enable_model_cpu_offload"):
                try:
                    self._pipe.enable_model_cpu_offload()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self._move_pipe_to_device()
        except Exception:
            pass

    def _prepare_data(self, active_rect=None) -> Dict:
        data = super()._prepare_data(active_rect)
        del data["width"]
        del data["height"]
        del data["clip_skip"]
        data["callback"] = data["callback_on_step_end"]
        del data["callback_on_step_end"]
        data["guidance_scale"] = self.image_request.scale
        data["noise_level"] = self.DEFAULT_NOISE_LEVEL
        return data

    def _prepare_pipe_data(self) -> Dict[str, Any]:
        data = {
            "torch_dtype": self.data_type,
            "use_safetensors": True,
            "variant": "fp16",
            "local_files_only": AIRUNNER_LOCAL_FILES_ONLY,
            "device": self._device,
        }

        return data

    def handle_upscale_request(
        self, source_image: Image.Image
    ) -> Optional[ImageResponse]:
        source_image = self._ensure_image(source_image)

        request = self.image_request
        prompt = request.prompt
        negative_prompt = request.negative_prompt
        steps = max(1, request.steps or self.DEFAULT_NUM_STEPS)
        guidance_scale = request.scale
        noise_level = self.DEFAULT_NOISE_LEVEL

        # Initialize progress at 0 and reset internal last-percent tracker
        # so that progress doesn't appear to go backwards during tiled
        # upscaling when step-based callbacks and per-tile emissions
        # interleave.
        self._last_progress_percent = -1
        self._emit_progress(0, 100)

        try:
            self.load()
            result = self._run_upscale(
                source_image,
                prompt=prompt,
                negative_prompt=negative_prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                noise_level=noise_level,
            )

            saved_path = self._save_result_to_disk(result)
            response_data = self._build_response_data(
                prompt=prompt,
                negative_prompt=negative_prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                saved_path=saved_path,
                noise_level=noise_level,
            )
            images = [result]
            response = ImageResponse(
                images=images,
                data=response_data,
                nsfw_content_detected=False,
                active_rect=self.active_rect,
                is_outpaint=False,
                node_id=request.node_id,
            )

            self._queue_export(images, response_data)
            self._send_to_canvas(response)
            self._notify_worker(EngineResponseCode.IMAGE_GENERATED, response)
            self._emit_completed(saved_path, steps)
            return response
        except InterruptedException as ie:
            # User-initiated interrupt: avoid noisy error logs and worker ERROR
            # emissions. Let the caller/outer handler emit an INTERRUPTED code
            # and perform cleanup.
            self.logger.debug("Upscale operation interrupted by user: %s", ie)
            raise
        except Exception as exc:
            self.logger.exception("Upscale operation failed: %s", exc)
            self._emit_failure(str(exc))
            raise
        finally:
            clear_memory()
            # Reset the progress tracker so future operations start fresh
            try:
                self._last_progress_percent = None
            except Exception:
                pass

    def _run_upscale(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        noise_level: int,
    ) -> Image.Image:
        if not self._pipe:
            raise RuntimeError("Upscale pipeline is not loaded")
        if self._should_tile(image):
            return self._tile_upscale(
                image=image,
                prompt=prompt,
                negative_prompt=negative_prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                noise_level=noise_level,
                tile_size=self.DEFAULT_TILE_SIZE,
                overlap=self.TILE_OVERLAP,
                tile_batch_size=self.DEFAULT_TILE_BATCH_SIZE,
            )
        return self._single_pass_upscale(
            image=image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            guidance_scale=guidance_scale,
            noise_level=noise_level,
        )

    def _single_pass_upscale(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        noise_level: int,
    ) -> Image.Image:
        kwargs = self._build_pipeline_kwargs(
            image=image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            guidance_scale=guidance_scale,
            noise_level=noise_level,
        )
        # Ensure the pipeline receives our interrupt callback so cancel actions
        # set via interrupt_image_generation() are honored during long-running
        # upscaling steps. BaseDiffusersModelManager defines a name-mangled
        # interrupt callback; access it if present.
        interrupt_cb = getattr(
            self, "_BaseDiffusersModelManager__interrupt_callback", None
        )
        if interrupt_cb is not None:
            kwargs["callback"] = interrupt_cb
            # Many diffusers pipelines support callback_steps to control
            # frequency of callback invocation; default to 1 (every step)
            kwargs.setdefault("callback_steps", 1)
        self._empty_cache()
        autocast_ctx = (
            torch.autocast("cuda", dtype=self.data_type)
            if torch.cuda.is_available()
            else nullcontext()
        )
        with torch.inference_mode():
            with autocast_ctx:
                result = self._pipe(**kwargs)
        images = self._extract_images(result)
        final_image = images[0]
        # Composite onto white if image has alpha to avoid black transparency
        try:
            if "A" in final_image.getbands():
                rgba = final_image.convert("RGBA")
                bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                final_image = Image.alpha_composite(bg, rgba).convert("RGB")
            else:
                final_image = final_image.convert("RGB")
        except Exception:
            final_image = final_image.convert("RGB")
        # Report 100% progress on completion
        self._emit_progress(100, 100)
        return final_image

    def _tile_upscale(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        noise_level: int,
        tile_size: int,
        overlap: int,
        tile_batch_size: int,
    ) -> Image.Image:
        """Upscale image using tiled approach to manage VRAM usage."""
        width, height = image.size
        output = Image.new(
            "RGB",
            (width * self.SCALE_FACTOR, height * self.SCALE_FACTOR),
            (255, 255, 255),
        )
        current_tile_size = tile_size
        current_batch_size = tile_batch_size
        reductions_remaining = self.MAX_TILE_REDUCTIONS

        tiles = self._build_tiles(image, current_tile_size, overlap)
        total_tiles = len(tiles)
        processed_tiles = 0
        # Progress: 0-100%, report in percentages
        self._emit_progress(0, 100)

        while processed_tiles < total_tiles:
            batch = tiles[
                processed_tiles : processed_tiles + current_batch_size
            ]
            if not batch:
                break

            batch_images = [tile["crop"] for tile in batch]
            kwargs = self._build_pipeline_kwargs(
                image=batch_images,
                prompt=prompt,
                negative_prompt=negative_prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                noise_level=noise_level,
            )
            self._empty_cache()

            autocast_ctx = (
                torch.autocast("cuda", dtype=self.data_type)
                if torch.cuda.is_available()
                else nullcontext()
            )

            try:
                # Provide a per-batch callback so we can emit continuous
                # progress updates while the pipeline runs. Map the
                # pipeline's step progress into the overall tile progress
                # range covered by this batch.
                start_tiles = processed_tiles
                batch_count = len(batch)

                def _batch_progress_callback(*cb_args, **cb_kwargs):
                    # Honor global interrupt flag used by the application.
                    # If set, raise InterruptedException to abort the pipeline.
                    try:
                        is_interrupt = getattr(
                            self, "do_interrupt_image_generation", False
                        )
                        self.logger.debug(
                            "x4_upscale_manager: batch callback invoked, do_interrupt=%s",
                            is_interrupt,
                        )
                        if is_interrupt:
                            # Resetting the flag is handled by the manager's
                            # higher-level interrupt logic when catching this exception.
                            raise InterruptedException()
                    except InterruptedException:
                        # Re-raise so the outer logic can catch and handle it.
                        self.logger.debug(
                            "x4_upscale_manager: raising InterruptedException from batch callback"
                        )
                        raise
                    except Exception:
                        # Non-fatal check failure; continue to progress handling.
                        pass
                    """Flexible callback wrapper for different diffusers callback signatures.

                    The pipeline may call the callback with signatures like
                    (pipe, i, t, callback_kwargs) or (i, t, callback_kwargs).
                    Accept any form and try to extract the step index.
                    """
                    try:
                        # Prefer common patterns where step index is the second arg
                        step_index = None
                        if len(cb_args) >= 3 and isinstance(cb_args[1], int):
                            step_index = cb_args[1]
                        elif len(cb_args) >= 2 and isinstance(cb_args[0], int):
                            step_index = cb_args[0]
                        else:
                            # try kwargs if present
                            if "step" in cb_kwargs and isinstance(
                                cb_kwargs["step"], int
                            ):
                                step_index = cb_kwargs["step"]

                        if step_index is None:
                            return

                        # step_index is zero-based; map to 1..steps
                        inner_frac = float(step_index + 1) / max(1, steps)
                        overall_frac = (
                            start_tiles + inner_frac * batch_count
                        ) / max(1, total_tiles)
                        pct = int(overall_frac * 100)
                        # Emit normalized progress (0..100)
                        self._emit_progress(pct, 100)
                    except Exception:
                        # Swallow any callback errors to avoid interrupting the
                        # main pipeline; progress is best-effort.
                        return

                # Attach callback to kwargs so diffusers will call it each step
                kwargs["callback"] = _batch_progress_callback
                # Request callback every step to keep updates frequent
                kwargs["callback_steps"] = 1

                with torch.inference_mode():
                    with autocast_ctx:
                        result = self._pipe(**kwargs)

                upscaled_tiles = self._extract_images(result)

                # Fallback to bicubic if all-black output detected
                if self._is_all_black(upscaled_tiles):
                    upscaled_tiles = self._bicubic_fallback(batch_images)

                # Paste tiles into output canvas
                for idx, tile_dict in enumerate(batch):
                    self._paste_tile(
                        output,
                        upscaled_tiles[idx],
                        tile_dict["box"],
                        self.SCALE_FACTOR,
                    )
                    processed_tiles += 1
                    # Report progress as percentage: processed/total * 100
                    progress_percent = int(
                        (processed_tiles / total_tiles) * 100
                    )
                    self._emit_progress(progress_percent, 100)

            except Exception as exc:
                # If this was a user interrupt, avoid logging as an error
                # and simply re-raise so the higher-level handler can
                # translate it into an INTERRUPTED response.
                if isinstance(exc, InterruptedException):
                    self.logger.debug(
                        "Tile batch interrupted at index %d: %s",
                        processed_tiles,
                        exc,
                    )
                    raise

                if self._is_out_of_memory(exc):
                    if current_batch_size > 1:
                        current_batch_size = max(1, current_batch_size // 2)
                        self.logger.warning(
                            "OOM during tiled upscale; reducing batch size to %d",
                            current_batch_size,
                        )
                        continue
                    if (
                        current_tile_size > self.MIN_TILE_SIZE
                        and reductions_remaining > 0
                    ):
                        reductions_remaining -= 1
                        current_tile_size = max(
                            self.MIN_TILE_SIZE, current_tile_size // 2
                        )
                        self.logger.warning(
                            "OOM persists; reducing tile size to %d",
                            current_tile_size,
                        )
                        tiles = self._build_tiles(
                            image, current_tile_size, overlap
                        )
                        total_tiles = len(tiles)
                        processed_tiles = 0
                        output = Image.new(
                            "RGB",
                            (
                                width * self.SCALE_FACTOR,
                                height * self.SCALE_FACTOR,
                            ),
                            (255, 255, 255),
                        )
                        self._emit_progress(0, total_tiles)
                        continue

                self.logger.exception(
                    "Tile batch failed at index %d: %s", processed_tiles, exc
                )
                raise
            finally:
                batch_images.clear()
                gc.collect()
                self._empty_cache()

        # Report 100% completion
        self._emit_progress(100, 100)
        return output.convert("RGB")

    def _is_all_black(self, images: List[Image.Image]) -> bool:
        """Check if all images in a list are completely black."""
        try:
            for img in images:
                arr = np.asarray(img)
                if arr.size and int(arr.max()) > 0:
                    return False
            return True
        except Exception:
            return False

    def _bicubic_fallback(
        self, images: List[Image.Image]
    ) -> List[Image.Image]:
        """Fallback to bicubic upscaling when pipeline produces black output."""
        fallback_tiles = []
        for crop in images:
            try:
                w, h = crop.size
                fw, fh = w * self.SCALE_FACTOR, h * self.SCALE_FACTOR
                up = crop.convert("RGB").resize(
                    (fw, fh), resample=Image.BICUBIC
                )
                fallback_tiles.append(up)
            except Exception:
                # White tile on error
                fallback_tiles.append(
                    Image.new("RGB", (fw, fh), (255, 255, 255))
                )
        return fallback_tiles

    def _build_tiles(
        self, image: Image.Image, tile_size: int, overlap: int
    ) -> List[Dict[str, Union[Tuple[int, int, int, int], Image.Image]]]:
        width, height = image.size
        step = max(1, tile_size - overlap)
        tiles: List[
            Dict[str, Union[Tuple[int, int, int, int], Image.Image]]
        ] = []
        for top in range(0, height, step):
            bottom = min(top + tile_size, height)
            top = max(0, bottom - tile_size)
            for left in range(0, width, step):
                right = min(left + tile_size, width)
                left = max(0, right - tile_size)
                crop = image.crop((left, top, right, bottom))
                tiles.append({"box": (left, top, right, bottom), "crop": crop})
        return tiles

    @staticmethod
    def _paste_tile(
        canvas: Image.Image,
        tile: Image.Image,
        source_box: Tuple[int, int, int, int],
        scale_factor: int,
    ):
        left, top, right, bottom = source_box
        dest_box = (
            left * scale_factor,
            top * scale_factor,
            right * scale_factor,
            bottom * scale_factor,
        )
        try:
            # If tile has an alpha channel, composite it over white first.
            if "A" in tile.getbands():
                try:
                    tile_rgba = tile.convert("RGBA")
                    white_bg = Image.new(
                        "RGBA", tile_rgba.size, (255, 255, 255, 255)
                    )
                    composed = Image.alpha_composite(
                        white_bg, tile_rgba
                    ).convert("RGB")
                    canvas.paste(composed, dest_box)
                except Exception:
                    # Fallback to mask-based paste if alpha_composite fails
                    mask = tile.split()[-1]
                    canvas.paste(tile.convert("RGBA"), dest_box, mask)
            else:
                canvas.paste(tile.convert("RGB"), dest_box)
        except Exception:
            # Best-effort paste; fallback to a naive paste on error.
            try:
                canvas.paste(tile, dest_box)
            except Exception:
                pass

    def _should_tile(self, image: Image.Image) -> bool:
        return max(image.size) >= self.LARGE_INPUT_THRESHOLD

    def _build_pipeline_kwargs(
        self,
        image: Union[Image.Image, Sequence[Image.Image]],
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        noise_level: int,
    ) -> Dict[str, Union[int, float, str, Sequence[Image.Image]]]:
        kwargs: Dict[str, Union[int, float, str, Sequence[Image.Image]]] = {
            "image": image,
            "num_inference_steps": steps,
            "guidance_scale": guidance_scale,
            "noise_level": noise_level,
        }
        if prompt:
            kwargs["prompt"] = (
                [prompt] * len(image)
                if self._is_image_sequence(image)
                else prompt
            )
        if negative_prompt:
            kwargs["negative_prompt"] = (
                [negative_prompt] * len(image)
                if self._is_image_sequence(image)
                else negative_prompt
            )
        return {
            key: value for key, value in kwargs.items() if value is not None
        }

    def _extract_images(
        self, result: Union[Dict, Sequence[Image.Image], Image.Image]
    ) -> List[Image.Image]:
        if isinstance(result, dict) and "images" in result:
            images = result["images"]
        elif hasattr(result, "images"):
            images = result.images
        else:
            images = result
        if isinstance(images, (Image.Image, np.ndarray, torch.Tensor)):
            images = [images]

        return [self._ensure_image(img) for img in images]

    def _ensure_image(
        self, value: Union[Image.Image, np.ndarray, torch.Tensor]
    ) -> Image.Image:
        # Pass-through for PIL images
        if isinstance(value, Image.Image):
            return value

        # Handle torch tensors
        if torch.is_tensor(value):
            tensor = value.detach().cpu()
            # Move channel-first to HWC if necessary
            if tensor.ndim == 3 and tensor.shape[0] in (1, 3, 4):
                tensor = tensor.permute(1, 2, 0)

            # Determine numeric range and convert to uint8 0..255
            if tensor.dtype.is_floating_point:
                try:
                    tmin = float(tensor.min())
                    tmax = float(tensor.max())
                except Exception:
                    tmin, tmax = 0.0, 1.0
                # If values appear to be in [-1,1], shift to [0,1]
                if tmin < 0.0 or tmax <= 1.0:
                    # handle [-1,1] and [0,1]
                    if tmin < 0.0:
                        tensor = (tensor + 1.0) / 2.0
                    tensor = tensor.clamp(0.0, 1.0)
                    array = (tensor * 255.0).round().to(torch.uint8).numpy()
                else:
                    # assume already in 0..255 float
                    array = (
                        tensor.clamp(0.0, 255.0)
                        .round()
                        .to(torch.uint8)
                        .numpy()
                    )
            else:
                array = tensor.to(torch.uint8).numpy()

            # If grayscale, promote to 3 channels
            if array.ndim == 2:
                array = np.stack([array] * 3, axis=-1)
            return Image.fromarray(array)

        # Handle numpy arrays
        array = np.asarray(value)
        if array.ndim == 3 and array.shape[0] in (1, 3, 4):
            # channel-first -> HWC
            array = np.moveaxis(array, 0, -1)

        # If image is float, detect range and normalize
        if np.issubdtype(array.dtype, np.floating):
            a_min = float(np.nanmin(array)) if array.size else 0.0
            a_max = float(np.nanmax(array)) if array.size else 1.0
            if a_min < 0.0:
                # assume range [-1,1]
                array = (array + 1.0) / 2.0
            if a_max <= 1.5:
                array = np.clip(array, 0.0, 1.0) * 255.0
            else:
                array = np.clip(array, 0.0, 255.0)
            array = np.rint(array).astype(np.uint8)

        # If integer but not uint8, convert/clamp
        if np.issubdtype(array.dtype, np.integer) and array.dtype != np.uint8:
            array = np.clip(array, 0, 255).astype(np.uint8)

        # If single channel, expand to RGB
        if array.ndim == 2:
            array = np.stack([array] * 3, axis=-1)

        return Image.fromarray(array)

    def _build_request_from_payload(
        self, data: Dict, image: Image.Image
    ) -> ImageRequest:
        settings = getattr(self, "generator_settings", None)
        defaults = ImageRequest()

        prompt = data.get("prompt", getattr(settings, "prompt", "")) or ""
        negative_prompt = (
            data.get(
                "negative_prompt", getattr(settings, "negative_prompt", "")
            )
            or ""
        )

        steps = getattr(settings, "steps", defaults.steps) or defaults.steps
        try:
            steps = max(1, int(steps))
        except (TypeError, ValueError):
            steps = defaults.steps

        scale_raw = data.get("scale", getattr(settings, "scale", None))
        guidance_scale = self._normalize_guidance_scale(scale_raw)

        seed = getattr(settings, "seed", defaults.seed)
        try:
            seed = int(seed)
        except (TypeError, ValueError):
            seed = defaults.seed

        strength_raw = getattr(settings, "strength", 100)
        try:
            strength = (float(strength_raw) or 100) / 100
        except (TypeError, ValueError):
            strength = defaults.strength

        return ImageRequest(
            pipeline_action="upscale_x4",
            generator_name=getattr(
                settings, "generator_name", defaults.generator_name
            ),
            prompt=prompt,
            negative_prompt=negative_prompt,
            random_seed=getattr(settings, "random_seed", defaults.random_seed),
            model_path=getattr(settings, "model_name", defaults.model_path),
            custom_path=getattr(settings, "custom_path", defaults.custom_path),
            scheduler=getattr(settings, "scheduler", defaults.scheduler),
            version=getattr(settings, "version", defaults.version),
            use_compel=getattr(settings, "use_compel", defaults.use_compel),
            steps=steps,
            ddim_eta=getattr(settings, "ddim_eta", defaults.ddim_eta),
            scale=guidance_scale,
            seed=seed,
            strength=strength,
            n_samples=1,
            images_per_batch=1,
            clip_skip=getattr(settings, "clip_skip", defaults.clip_skip),
            width=image.width,
            height=image.height,
        )

    def _normalize_guidance_scale(
        self, value: Optional[Union[int, float]]
    ) -> float:
        if value is None:
            return self.DEFAULT_GUIDANCE_SCALE
        try:
            scale_value = float(value)
        except (TypeError, ValueError):
            return self.DEFAULT_GUIDANCE_SCALE
        if scale_value > 20:
            scale_value /= 100
        if scale_value <= 0:
            return self.DEFAULT_GUIDANCE_SCALE
        return scale_value

    def _emit_failure(self, message: str):
        self._notify_worker(EngineResponseCode.ERROR, message)
        try:
            self.emit_signal(SignalCode.UPSCALE_FAILED, {"error": message})
        except Exception:
            pass

    def _emit_completed(self, saved_path: Optional[str], steps: int):
        try:
            self.emit_signal(
                SignalCode.UPSCALE_COMPLETED,
                {"image_path": saved_path, "steps": steps},
            )
        except Exception:
            pass

    def _send_to_canvas(self, response: ImageResponse):
        api = getattr(self, "api", None)
        if not api or not getattr(api, "art", None):
            return
        try:
            api.art.canvas.send_image_to_canvas(response)
        except Exception as exc:
            self.logger.exception(
                "Failed to send upscaled image to canvas: %s", exc
            )

    def _notify_worker(self, code: EngineResponseCode, message):
        api = getattr(self, "api", None)
        if not api or not hasattr(api, "worker_response"):
            return
        try:
            api.worker_response(code=code, message=message)
        except Exception as exc:
            self.logger.exception(
                "Failed to notify worker of upscale result: %s", exc
            )

    def _build_response_data(
        self,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        saved_path: Optional[str],
        noise_level: int,
    ) -> Dict:
        try:
            controlnet_settings = self.controlnet_settings
        except Exception:
            controlnet_settings = None

        data = {
            "current_prompt": prompt,
            "current_prompt_2": "",
            "current_negative_prompt": negative_prompt,
            "current_negative_prompt_2": "",
            "image_request": self.image_request,
            "model_path": self.model_path,
            "version": self.MODEL_REPO,
            "scheduler_name": self.image_request.scheduler,
            "guidance_scale": guidance_scale,
            "num_inference_steps": steps,
            "memory_settings_flags": self._memory_settings_flags,
            "application_settings": self.application_settings,
            "path_settings": self.path_settings,
            "metadata_settings": self.metadata_settings,
            "controlnet_settings": controlnet_settings,
            "is_txt2img": False,
            "is_img2img": True,
            "is_inpaint": False,
            "is_outpaint": False,
            "mask_blur": 0,
            "saved_path": saved_path,
            "generator": "x4_upscaler",
            "noise_level": noise_level,
        }
        return data

    def _queue_export(self, images: List[Image.Image], data: Dict):
        try:
            self.image_export_worker.add_to_queue(
                {"images": images, "data": data}
            )
        except Exception as exc:
            self.logger.warning(
                "Failed to queue upscaled image export: %s", exc
            )

    def _save_preview_image(self, image: Image.Image):
        try:
            os.makedirs(self.preview_dir, exist_ok=True)
            # If image has alpha, composite onto a white background to avoid
            # black/transparent saved previews.
            try:
                if "A" in image.getbands():
                    bg = Image.new("RGB", image.size, (255, 255, 255))
                    bg.paste(image, mask=image.split()[-1])
                    bg.save(self.preview_path)
                else:
                    image.convert("RGB").save(self.preview_path)
            except Exception:
                # Fallback generic save
                image.convert("RGB").save(self.preview_path)
        except Exception:
            pass

    def _save_result_to_disk(self, image: Image.Image) -> Optional[str]:
        try:
            os.makedirs(self.preview_dir, exist_ok=True)
            filename = datetime.now().strftime("upscaled_%Y%m%d_%H%M%S.png")
            path = os.path.join(self.preview_dir, filename)
            try:
                if "A" in image.getbands():
                    bg = Image.new("RGB", image.size, (255, 255, 255))
                    bg.paste(image, mask=image.split()[-1])
                    bg.save(path)
                else:
                    image.convert("RGB").save(path)
            except Exception:
                image.convert("RGB").save(path)
            return path
        except Exception as exc:
            self.logger.warning("Unable to save upscaled image: %s", exc)
            return None

    def _emit_progress(self, current: int, total: int):
        try:
            # Normalize to a 0..1 percentage value. callers may pass either
            # a (current, total) where total==100 (percent) or tile counts.
            percent = 0.0 if total == 0 else float(current) / float(total)
            percent = max(0.0, min(1.0, percent))

            # Emit upscale-specific progress for any listeners that expect
            # raw values (current/total and a normalized percent).
            self.emit_signal(
                SignalCode.UPSCALE_PROGRESS,
                {"current": current, "total": total, "percent": percent},
            )

            # Also emit the generic SD progress signal the UI listens to.
            # The UI expects a (step, total) pair and computes step/total to
            # derive a percent. Provide a 0-100 range so it will display as
            # an integer percentage consistently.
            try:
                step = int(percent * 100)
            except Exception:
                step = 0

            # Clamp progress so it never goes backwards during an upscale
            # operation where per-step callbacks and final per-tile
            # emissions can interleave. Use an internal tracker set on
            # upscale start/reset in handle_upscale_request.
            try:
                last = getattr(self, "_last_progress_percent", None)
                if last is None:
                    # not tracking, emit as-is
                    emit_step = step
                else:
                    emit_step = max(int(last), step)
                    # store updated value
                    self._last_progress_percent = emit_step
            except Exception:
                emit_step = step

            self.emit_signal(
                SignalCode.SD_PROGRESS_SIGNAL,
                {"step": emit_step, "total": 100},
            )
        except Exception:
            pass

    def _is_image_sequence(
        self, value: Union[Image.Image, Sequence[Image.Image]]
    ) -> bool:
        return isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        )

    def _empty_cache(self):
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

    @staticmethod
    def _is_out_of_memory(exc: Exception) -> bool:
        message = str(exc).lower()
        return "out of memory" in message or isinstance(
            exc, torch.cuda.OutOfMemoryError
        )
