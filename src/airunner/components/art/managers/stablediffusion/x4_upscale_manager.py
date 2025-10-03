import gc
import os
from contextlib import nullcontext
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import torch
from diffusers import StableDiffusionUpscalePipeline
from PIL import Image

from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.enums import (
    EngineResponseCode,
    ModelStatus,
    ModelType,
    SignalCode,
)
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner.utils.memory import clear_memory


class X4UpscaleManager(BaseDiffusersModelManager):
    """Manager for the ``stabilityai/stable-diffusion-x4-upscaler`` pipeline."""

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_type = ModelType.UPSCALER
        if ModelType.UPSCALER not in self._model_status:
            self._model_status[ModelType.UPSCALER] = ModelStatus.UNLOADED
        self._pipe: Optional[StableDiffusionUpscalePipeline] = None

    @property
    def model_path(self) -> str:
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "art/models/x4-upscaler",
        )

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
            if torch.cuda.is_available():
                self._pipe = StableDiffusionUpscalePipeline.from_pretrained(
                    self.model_path,
                    torch_dtype=self.data_type,
                    use_safetensors=True,
                    variant="fp16",
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                )
            else:
                self._pipe = StableDiffusionUpscalePipeline.from_pretrained(
                    self.model_path,
                    torch_dtype=self.data_type,
                    use_safetensors=True,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
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

    def unload(self):
        if self._pipe is not None:
            try:
                if hasattr(self._pipe, "to"):
                    self._pipe.to("cpu")
            except Exception:
                pass
        self._pipe = None
        self.change_model_status(ModelType.UPSCALER, ModelStatus.UNLOADED)
        clear_memory()

    def is_loaded(self) -> bool:
        return (
            self._pipe is not None
            and self.model_status.get(ModelType.UPSCALER) is ModelStatus.LOADED
        )

    def handle_upscale_request(
        self, data: Optional[Dict] = None
    ) -> Optional[ImageResponse]:
        data = data or {}
        source_image = data.get("image")
        if source_image is None:
            message = "No image provided for x4 upscale request"
            self.logger.error(message)
            self._emit_failure(message)
            return None

        source_image = self._ensure_image(source_image)
        # Save the input image to the preview directory for debugging/comparison
        try:
            os.makedirs(self.preview_dir, exist_ok=True)
            in_fname = datetime.now().strftime(
                "input_for_upscale_%Y%m%d_%H%M%S.png"
            )
            in_path = os.path.join(self.preview_dir, in_fname)
            try:
                source_image.convert("RGB").save(in_path)
            except Exception:
                source_image.save(in_path)
        except Exception:
            pass

        request = data.get("image_request")
        if request is not None and not isinstance(request, ImageRequest):
            try:
                request = ImageRequest(**request)
            except Exception:
                request = None
        if request is None:
            request = self._build_request_from_payload(data, source_image)
        self.image_request = request

        prompt = request.prompt or data.get("prompt", "")
        negative_prompt = request.negative_prompt or data.get(
            "negative_prompt", ""
        )
        steps = max(1, request.steps or self.DEFAULT_NUM_STEPS)
        guidance_scale = request.scale or self.DEFAULT_GUIDANCE_SCALE
        noise_level = data.get("noise_level", self.DEFAULT_NOISE_LEVEL)

        self._emit_progress(0, steps)

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
        except Exception as exc:
            self.logger.exception("Upscale operation failed: %s", exc)
            self._emit_failure(str(exc))
            raise
        finally:
            clear_memory()

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
        self._emit_progress(steps, steps)
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
        width, height = image.size
        # Use white background so transparent regions don't appear black
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
        self._emit_progress(0, max(total_tiles, steps))

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
                with torch.inference_mode():
                    with autocast_ctx:
                        result = self._pipe(**kwargs)
                # Extract images (PIL) from pipeline result
                upscaled_tiles = self._extract_images(result)

                # If pipeline returned all-black tiles, fall back to bicubic
                # upscaling of the input crops and log model dir for debugging.
                try:
                    all_black = True
                    for img in upscaled_tiles:
                        arr = np.asarray(img)
                        if arr.size and int(arr.max()) > 0:
                            all_black = False
                            break
                except Exception:
                    all_black = False

                if all_black:
                    try:
                        # Log model directory to help diagnose missing/corrupt files
                        try:
                            files = os.listdir(self.model_path)
                        except Exception:
                            files = []
                        dbg_txt = os.path.join(
                            self.preview_dir, "preview_debug.txt"
                        )
                        with open(dbg_txt, "a") as f:
                            f.write(
                                f"{datetime.now().isoformat()} all_black_output_detected model_path={self.model_path} files={files}\n"
                            )
                    except Exception:
                        pass

                    # Use bicubic resize fallback for each input crop
                    try:
                        fallback_tiles = []
                        for crop in batch_images:
                            try:
                                w, h = crop.size
                                fw, fh = (
                                    w * self.SCALE_FACTOR,
                                    h * self.SCALE_FACTOR,
                                )
                                up = crop.convert("RGB").resize(
                                    (fw, fh), resample=Image.BICUBIC
                                )
                                fallback_tiles.append(up)
                            except Exception:
                                # give a white tile if anything fails
                                fallback_tiles.append(
                                    Image.new(
                                        "RGB",
                                        (
                                            w * self.SCALE_FACTOR,
                                            h * self.SCALE_FACTOR,
                                        ),
                                        (255, 255, 255),
                                    )
                                )
                        upscaled_tiles = fallback_tiles
                        # Save a note and the fallback tiles
                        try:
                            for i, t in enumerate(upscaled_tiles[:4]):
                                t.save(
                                    os.path.join(
                                        self.preview_dir,
                                        f"dbg_fallback_tile_{processed_tiles + i}.png",
                                    )
                                )
                        except Exception:
                            pass
                    except Exception:
                        pass

                # Debug: save raw pipeline outputs and corresponding input crops
                try:
                    os.makedirs(self.preview_dir, exist_ok=True)
                    raw_images = None
                    try:
                        with open(
                            os.path.join(
                                self.preview_dir, "preview_debug.txt"
                            ),
                            "a",
                        ) as f:
                            f.write(
                                f"{datetime.now().isoformat()} pipeline_result_type={type(result)} repr={repr(result)[:200]}\n"
                            )
                    except Exception:
                        pass
                    if isinstance(result, dict) and "images" in result:
                        raw_images = result["images"]
                    elif hasattr(result, "images"):
                        raw_images = result.images
                    else:
                        raw_images = result
                    # Log detailed info about raw_images elements
                    try:
                        dbg_txt = os.path.join(
                            self.preview_dir, "preview_debug.txt"
                        )
                        with open(dbg_txt, "a") as f:
                            for i, item in enumerate(
                                raw_images
                                if hasattr(raw_images, "__len__")
                                else [raw_images]
                            ):
                                try:
                                    if torch.is_tensor(item):
                                        t = item.detach().cpu()
                                        f.write(
                                            f"{datetime.now().isoformat()} raw[{i}]=torch tensor shape={tuple(t.shape)} dtype={t.dtype} min={float(t.min()):.6f} max={float(t.max()):.6f}\n"
                                        )
                                    else:
                                        arr = np.asarray(item)
                                        f.write(
                                            f"{datetime.now().isoformat()} raw[{i}]=np/ndarray shape={arr.shape} dtype={arr.dtype} min={arr.min() if arr.size else 'NA'} max={arr.max() if arr.size else 'NA'}\n"
                                        )
                                except Exception:
                                    try:
                                        f.write(
                                            f"{datetime.now().isoformat()} raw[{i}]=repr={repr(item)[:200]}\n"
                                        )
                                    except Exception:
                                        pass
                    except Exception:
                        pass
                    # Save up to the first 4 tiles of this batch for inspection
                    for dbg_idx in range(min(4, len(upscaled_tiles))):
                        try:
                            tile_img = upscaled_tiles[dbg_idx]
                            tile_fname = datetime.now().strftime(
                                f"dbg_upscaled_tile_%Y%m%d_%H%M%S_{processed_tiles + dbg_idx}.png"
                            )
                            tile_path = os.path.join(
                                self.preview_dir, tile_fname
                            )
                            tile_img.convert("RGB").save(tile_path)
                        except Exception:
                            try:
                                # try saving raw image via ensure
                                img = self._ensure_image(raw_images[dbg_idx])
                                img.convert("RGB").save(tile_path)
                            except Exception:
                                pass
                    # Save the input crops for the batch as well
                    for crop_idx, crop_img in enumerate(batch_images[:4]):
                        try:
                            crop_fname = datetime.now().strftime(
                                f"dbg_input_crop_%Y%m%d_%H%M%S_{processed_tiles + crop_idx}.png"
                            )
                            crop_path = os.path.join(
                                self.preview_dir, crop_fname
                            )
                            crop_img.convert("RGB").save(crop_path)
                        except Exception:
                            pass
                    # Write min/max/dtype info for tiles
                    try:
                        dbg_txt = os.path.join(
                            self.preview_dir, "preview_debug.txt"
                        )
                        with open(dbg_txt, "a") as f:
                            for info_idx, img in enumerate(upscaled_tiles[:8]):
                                try:
                                    arr = np.asarray(img)
                                    f.write(
                                        f"{datetime.now().isoformat()} tile_index={processed_tiles + info_idx} shape={arr.shape} dtype={arr.dtype} min={arr.min()} max={arr.max()}\n"
                                    )
                                except Exception:
                                    pass
                    except Exception:
                        pass
                except Exception:
                    pass
                for idx, tile_dict in enumerate(batch):
                    # Preserve the tile's alpha if present; _paste_tile will
                    # handle compositing/masking.
                    tile_image = upscaled_tiles[idx]
                    self._paste_tile(
                        output,
                        tile_image,
                        tile_dict["box"],
                        self.SCALE_FACTOR,
                    )
                    processed_tiles += 1
                    self._emit_progress(processed_tiles, total_tiles)
                self._save_preview_image(output)
            except Exception as exc:
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

        self._save_preview_image(output)
        self._emit_progress(steps, steps)
        return output.convert("RGB")

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
            percent = 0.0 if total == 0 else current / total
            self.emit_signal(
                SignalCode.UPSCALE_PROGRESS,
                {"current": current, "total": total, "percent": percent},
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
