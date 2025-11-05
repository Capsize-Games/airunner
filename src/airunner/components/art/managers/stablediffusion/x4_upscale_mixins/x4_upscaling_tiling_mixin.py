"""
Higher-level tiling helpers for X4 upscaler.

Contains logic to initialize tiling state and process batches; these are
small delegations used by the core manager to keep the orchestration
concise and testable.
"""

from typing import Tuple
from PIL import Image


class X4UpscalingTilingMixin:
    """Helpers around tiling orchestration."""

    def _init_tiling_state(
        self,
        image: Image.Image,
        tile_size: int,
        overlap: int,
        tile_batch_size: int,
    ) -> Tuple:
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

        return (
            output,
            tiles,
            total_tiles,
            current_batch_size,
            current_tile_size,
            reductions_remaining,
        )

    def _process_all_tile_batches(
        self,
        output,
        tiles,
        total_tiles,
        current_batch_size,
        current_tile_size,
        reductions_remaining,
        image,
        overlap,
        prompt,
        negative_prompt,
        steps,
        guidance_scale,
        noise_level,
    ):
        """Process all tile batches, handling OOM and interruptions."""
        processed_tiles = 0

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

                processed_tiles = self._paste_tiles_into_output(
                    output, batch, upscaled_tiles, processed_tiles, total_tiles
                )

            except Exception as exc:
                # Allow interrupted exceptions to bubble
                from airunner.components.application.exceptions import (
                    InterruptedException,
                )

                if isinstance(exc, InterruptedException):
                    self.logger.debug(
                        "Tile batch interrupted at index %d", processed_tiles
                    )
                    raise

                # Handle OOM by delegating to OOM helpers (may return new state)
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
                import gc

                gc.collect()
                self._empty_cache()

        return output

    def _paste_tiles_into_output(
        self, output, batch, upscaled_tiles, processed_tiles, total_tiles
    ):
        """Paste a batch of upscaled tiles into the output canvas and update progress."""
        for idx, tile_dict in enumerate(batch):
            processed_tiles = self._paste_single_tile_and_emit(
                output,
                upscaled_tiles[idx],
                tile_dict["box"],
                processed_tiles,
                total_tiles,
            )

        return processed_tiles

    def _paste_single_tile_and_emit(
        self, output, tile_image, source_box, processed_tiles, total_tiles
    ):
        """Paste a single upscaled tile into output and emit progress."""
        self._paste_tile(output, tile_image, source_box, self.SCALE_FACTOR)
        processed_tiles += 1
        pct = int((processed_tiles / total_tiles) * 100)
        self._emit_progress(pct, 100)
        return processed_tiles

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
        """Process a batch of tiles through the upscaling pipeline."""
        batch_images = [tile["crop"] for tile in batch]

        kwargs = self._build_batch_kwargs(
            batch_images,
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            guidance_scale=guidance_scale,
            noise_level=noise_level,
            processed_tiles=processed_tiles,
            batch_count=len(batch),
            total_tiles=total_tiles,
        )

        upscaled_tiles = self._execute_pipe_and_extract(kwargs)

        if self._is_all_black(upscaled_tiles):
            upscaled_tiles = self._bicubic_fallback(batch_images)

        return upscaled_tiles

    def _build_batch_kwargs(
        self,
        batch_images,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        noise_level: int,
        processed_tiles: int,
        batch_count: int,
        total_tiles: int,
    ):
        """Construct pipeline kwargs for a tile batch and attach callback."""
        kwargs = self._build_pipeline_kwargs(
            image=batch_images,
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            guidance_scale=guidance_scale,
            noise_level=noise_level,
        )

        kwargs["callback"] = self._make_batch_progress_callback(
            steps, processed_tiles, batch_count, total_tiles
        )
        kwargs["callback_steps"] = 1

        return kwargs

    def _create_smaller_tiles_and_output(
        self, image, current_tile_size, overlap
    ):
        tiles = self._build_tiles(image, current_tile_size, overlap)
        total_tiles = len(tiles)
        width, height = image.size
        output = Image.new(
            "RGB",
            (width * self.SCALE_FACTOR, height * self.SCALE_FACTOR),
            (255, 255, 255),
        )
        return tiles, total_tiles, output
