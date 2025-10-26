"""
Upscaling core mixin for X4UpscaleManager.

This mixin contains the main upscaling logic including single-pass
and tiled upscaling approaches with interrupt handling and memory
management.
"""

import gc
from contextlib import nullcontext
from typing import Optional

import torch
from PIL import Image

from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.components.application.exceptions import InterruptedException
from airunner.enums import EngineResponseCode
from airunner.utils.memory import clear_memory


class X4UpscalingCoreMixin:
    """Core upscaling logic for X4UpscaleManager."""

    DEFAULT_NUM_STEPS = 30
    DEFAULT_NOISE_LEVEL = 20
    LARGE_INPUT_THRESHOLD = 512
    DEFAULT_TILE_SIZE = 256
    DEFAULT_TILE_BATCH_SIZE = 2
    MIN_TILE_SIZE = 128
    MAX_TILE_REDUCTIONS = 3
    TILE_OVERLAP = 32
    SCALE_FACTOR = 4

    def handle_upscale_request(
        self, source_image: Image.Image
    ) -> Optional[ImageResponse]:
        """Handle upscale request from start to finish.

        Coordinates loading pipeline, running upscale (single-pass or tiled),
        saving results, and emitting responses.

        Args:
            source_image: PIL Image to upscale.

        Returns:
            ImageResponse with upscaled image and metadata, or None on failure.

        Raises:
            InterruptedException: If user interrupts the operation.
        """
        source_image = self._ensure_image(source_image)
        request = self.image_request

        # Extract request parameters
        prompt = request.prompt
        negative_prompt = request.negative_prompt
        steps = max(1, request.steps or self.DEFAULT_NUM_STEPS)
        guidance_scale = request.scale
        noise_level = self.DEFAULT_NOISE_LEVEL

        # Initialize progress tracking
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
            # User interrupt - let caller handle notification
            self.logger.debug("Upscale operation interrupted by user: %s", ie)
            raise
        except Exception as exc:
            self.logger.exception("Upscale operation failed: %s", exc)
            self._emit_failure(str(exc))
            raise
        finally:
            clear_memory()
            # Reset progress tracker
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
        """Run upscale operation (tiled or single-pass).

        Chooses between tiled upscaling (for large images) and single-pass
        upscaling based on image size.

        Args:
            image: Source PIL Image.
            prompt: Text prompt.
            negative_prompt: Negative prompt.
            steps: Number of inference steps.
            guidance_scale: Guidance scale value.
            noise_level: Noise level for upscaling.

        Returns:
            Upscaled PIL Image.

        Raises:
            RuntimeError: If pipeline is not loaded.
        """
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
        """Upscale image in single pass through pipeline.

        Args:
            image: Source PIL Image.
            prompt: Text prompt.
            negative_prompt: Negative prompt.
            steps: Number of inference steps.
            guidance_scale: Guidance scale value.
            noise_level: Noise level.

        Returns:
            Upscaled PIL Image.
        """
        kwargs = self._build_pipeline_kwargs(
            image=image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            guidance_scale=guidance_scale,
            noise_level=noise_level,
        )

        # Add interrupt callback
        interrupt_cb = getattr(
            self, "_BaseDiffusersModelManager__interrupt_callback", None
        )
        if interrupt_cb is not None:
            kwargs["callback"] = interrupt_cb
            kwargs.setdefault("callback_steps", 1)

        self._empty_cache()

        # Run pipeline with autocast
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

        # Composite alpha over white background
        final_image = self._composite_alpha(final_image)

        # Report 100% progress
        self._emit_progress(100, 100)
        return final_image

    def _composite_alpha(self, image: Image.Image) -> Image.Image:
        """Composite alpha channel over white background.

        Args:
            image: PIL Image (may have alpha).

        Returns:
            RGB PIL Image.
        """
        try:
            if "A" in image.getbands():
                rgba = image.convert("RGBA")
                bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                return Image.alpha_composite(bg, rgba).convert("RGB")
            else:
                return image.convert("RGB")
        except Exception:
            return image.convert("RGB")

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
        """Upscale large image using tiled approach.

        Processes image in overlapping tiles to manage VRAM usage.
        Automatically reduces tile size and batch size on OOM errors.

        Args:
            image: Source PIL Image.
            prompt: Text prompt.
            negative_prompt: Negative prompt.
            steps: Number of inference steps.
            guidance_scale: Guidance scale.
            noise_level: Noise level.
            tile_size: Initial tile size.
            overlap: Overlap between tiles.
            tile_batch_size: Initial batch size.

        Returns:
            Upscaled PIL Image.

        Raises:
            InterruptedException: If user interrupts.
        """
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

        self._emit_progress(0, 100)

        while processed_tiles < total_tiles:
            batch = tiles[
                processed_tiles : processed_tiles + current_batch_size
            ]
            if not batch:
                break

            try:
                upscaled_tiles = self._process_tile_batch(
                    batch=batch,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    steps=steps,
                    guidance_scale=guidance_scale,
                    noise_level=noise_level,
                    processed_tiles=processed_tiles,
                    total_tiles=total_tiles,
                )

                # Paste tiles into output
                for idx, tile_dict in enumerate(batch):
                    self._paste_tile(
                        output,
                        upscaled_tiles[idx],
                        tile_dict["box"],
                        self.SCALE_FACTOR,
                    )
                    processed_tiles += 1

                    # Report progress
                    progress_percent = int(
                        (processed_tiles / total_tiles) * 100
                    )
                    self._emit_progress(progress_percent, 100)

            except Exception as exc:
                if isinstance(exc, InterruptedException):
                    self.logger.debug(
                        "Tile batch interrupted at index %d: %s",
                        processed_tiles,
                        exc,
                    )
                    raise

                # Handle OOM by reducing batch/tile size
                if self._is_out_of_memory(exc):
                    result = self._handle_oom(
                        current_batch_size=current_batch_size,
                        current_tile_size=current_tile_size,
                        reductions_remaining=reductions_remaining,
                        image=image,
                        overlap=overlap,
                    )

                    if result:
                        (
                            current_batch_size,
                            current_tile_size,
                            reductions_remaining,
                            tiles,
                            total_tiles,
                            processed_tiles,
                            output,
                        ) = result
                        continue

                self.logger.exception(
                    "Tile batch failed at index %d: %s", processed_tiles, exc
                )
                raise
            finally:
                gc.collect()
                self._empty_cache()

        self._emit_progress(100, 100)
        return output.convert("RGB")

    def _process_tile_batch(
        self,
        batch,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        noise_level: int,
        processed_tiles: int,
        total_tiles: int,
    ):
        """Process a batch of tiles through the upscaling pipeline.

        Args:
            batch: List of tile dictionaries.
            prompt: Text prompt.
            negative_prompt: Negative prompt.
            steps: Number of steps.
            guidance_scale: Guidance scale.
            noise_level: Noise level.
            processed_tiles: Number of tiles already processed.
            total_tiles: Total number of tiles.

        Returns:
            List of upscaled PIL Images.

        Raises:
            InterruptedException: If user interrupts.
        """
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

        # Create progress callback for this batch
        start_tiles = processed_tiles
        batch_count = len(batch)

        def _batch_progress_callback(*cb_args, **cb_kwargs):
            """Progress callback with interrupt handling."""
            # Check for interrupt
            try:
                if getattr(self, "do_interrupt_image_generation", False):
                    raise InterruptedException()
            except InterruptedException:
                raise
            except Exception:
                pass

            # Update progress
            self._update_batch_progress(
                cb_args,
                cb_kwargs,
                steps,
                start_tiles,
                batch_count,
                total_tiles,
            )

        kwargs["callback"] = _batch_progress_callback
        kwargs["callback_steps"] = 1

        # Run pipeline
        autocast_ctx = (
            torch.autocast("cuda", dtype=self.data_type)
            if torch.cuda.is_available()
            else nullcontext()
        )

        with torch.inference_mode():
            with autocast_ctx:
                result = self._pipe(**kwargs)

        upscaled_tiles = self._extract_images(result)

        # Fallback to bicubic if all black
        if self._is_all_black(upscaled_tiles):
            upscaled_tiles = self._bicubic_fallback(batch_images)

        return upscaled_tiles

    def _update_batch_progress(
        self, cb_args, cb_kwargs, steps, start_tiles, batch_count, total_tiles
    ):
        """Update progress during batch processing.

        Args:
            cb_args: Callback positional arguments.
            cb_kwargs: Callback keyword arguments.
            steps: Total steps.
            start_tiles: Starting tile index for this batch.
            batch_count: Number of tiles in batch.
            total_tiles: Total tiles in operation.
        """
        try:
            # Extract step index from callback args
            step_index = None
            if len(cb_args) >= 3 and isinstance(cb_args[1], int):
                step_index = cb_args[1]
            elif len(cb_args) >= 2 and isinstance(cb_args[0], int):
                step_index = cb_args[0]
            elif "step" in cb_kwargs and isinstance(cb_kwargs["step"], int):
                step_index = cb_kwargs["step"]

            if step_index is None:
                return

            # Map step progress to overall progress
            inner_frac = float(step_index + 1) / max(1, steps)
            overall_frac = (start_tiles + inner_frac * batch_count) / max(
                1, total_tiles
            )
            pct = int(overall_frac * 100)
            self._emit_progress(pct, 100)
        except Exception:
            pass

    def _handle_oom(
        self,
        current_batch_size,
        current_tile_size,
        reductions_remaining,
        image,
        overlap,
    ):
        """Handle out-of-memory error by reducing batch/tile size.

        Args:
            current_batch_size: Current batch size.
            current_tile_size: Current tile size.
            reductions_remaining: Remaining reduction attempts.
            image: Source image.
            overlap: Tile overlap.

        Returns:
            Tuple of updated parameters, or None if cannot reduce further.
        """
        # Try reducing batch size first
        if current_batch_size > 1:
            current_batch_size = max(1, current_batch_size // 2)
            self.logger.warning(
                "OOM during tiled upscale; reducing batch size to %d",
                current_batch_size,
            )
            return (
                current_batch_size,
                current_tile_size,
                reductions_remaining,
                self._build_tiles(image, current_tile_size, overlap),
                None,  # tiles will be recalculated
                0,  # reset processed_tiles
                None,  # output will be recreated
            )

        # Try reducing tile size
        if current_tile_size > self.MIN_TILE_SIZE and reductions_remaining > 0:
            reductions_remaining -= 1
            current_tile_size = max(self.MIN_TILE_SIZE, current_tile_size // 2)
            self.logger.warning(
                "OOM persists; reducing tile size to %d", current_tile_size
            )

            tiles = self._build_tiles(image, current_tile_size, overlap)
            total_tiles = len(tiles)
            width, height = image.size
            output = Image.new(
                "RGB",
                (width * self.SCALE_FACTOR, height * self.SCALE_FACTOR),
                (255, 255, 255),
            )

            return (
                self.DEFAULT_TILE_BATCH_SIZE,  # reset batch size
                current_tile_size,
                reductions_remaining,
                tiles,
                total_tiles,
                0,  # reset processed_tiles
                output,
            )

        return None

    def _should_tile(self, image: Image.Image) -> bool:
        """Determine if image should use tiled upscaling.

        Args:
            image: Source PIL Image.

        Returns:
            True if largest dimension >= threshold.
        """
        return max(image.size) >= self.LARGE_INPUT_THRESHOLD
