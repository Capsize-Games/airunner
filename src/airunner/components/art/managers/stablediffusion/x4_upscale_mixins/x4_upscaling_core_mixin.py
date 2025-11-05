"""Minimal, import-light core mixin for X4 upscaling tests.

This file intentionally defines a small class surface so mixin-level
tests can import and assert the expected method names without pulling
heavy runtime dependencies.
"""

from typing import Any, Optional


class X4UpscalingCoreMixin:
    """Core orchestration mixin for the X4 upscaler.

    This mixin keeps high-level flow (request handling, decision between
    single-pass and tiled upscaling, finalization) while delegating
    implementation details to other mixins (execution, tiling, OOM,
    response I/O, image processing).
    """

    DEFAULT_NUM_STEPS = 30
    DEFAULT_NOISE_LEVEL = 20
    LARGE_INPUT_THRESHOLD = 512
    DEFAULT_TILE_SIZE = 256
    DEFAULT_TILE_BATCH_SIZE = 2
    MIN_TILE_SIZE = 128
    MAX_TILE_REDUCTIONS = 3
    TILE_OVERLAP = 32
    SCALE_FACTOR = 4

    def handle_upscale_request(self, source_image: Any) -> Optional[Any]:
        """Top-level entrypoint for an upscale request.

        This method is intentionally lightweight and uses internal
        helpers from other mixins. Imports that would pull heavy
        runtime dependencies are done lazily to keep module import
        time cheap for tests.
        """
        # Local imports to avoid heavy import-time dependencies

        from airunner.components.application.exceptions import (
            InterruptedException,
        )
        from airunner.utils.memory import clear_memory

        # Normalize image and extract request
        source_image = self._ensure_image(source_image)
        request = self.image_request

        prompt = request.prompt
        negative_prompt = request.negative_prompt
        steps = max(1, request.steps or self.DEFAULT_NUM_STEPS)
        guidance_scale = request.scale
        noise_level = self.DEFAULT_NOISE_LEVEL

        # Initialize progress tracking
        self._last_progress_percent = -1
        self._emit_progress(0, 100)

        try:
            # Ensure pipeline is loaded
            self.load()

            result = self._run_upscale(
                source_image,
                prompt=prompt,
                negative_prompt=negative_prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                noise_level=noise_level,
            )

            # Finalize response (save, queue, notify)
            return self._finalize_response(
                result=result,
                request=request,
                prompt=prompt,
                negative_prompt=negative_prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                noise_level=noise_level,
            )

        except InterruptedException:
            # Re-raise user interrupts after logging
            self.logger.debug("Upscale operation interrupted by user")
            raise
        except Exception as exc:  # pragma: no cover - integration path
            # Emit failure and re-raise so callers can handle errors
            self.logger.exception("Upscale operation failed: %s", exc)
            try:
                self._emit_failure(str(exc))
            except Exception:
                pass
            raise
        finally:
            # Best-effort memory cleanup
            try:
                clear_memory()
            except Exception:
                pass
            try:
                self._last_progress_percent = None
            except Exception:
                pass

    def _run_upscale(
        self,
        image: Any,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        noise_level: int,
    ) -> Any:
        """Dispatch to tiled or single-pass upscaling based on image size.

        The decision delegates to `_should_tile` which may be provided by
        a tiling mixin.
        """
        # Ensure pipeline loaded and available
        self._ensure_pipe_loaded()

        if self._should_tile(image):
            params = self._tile_parameters()
            return self._tile_upscale(
                image=image,
                prompt=prompt,
                negative_prompt=negative_prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                noise_level=noise_level,
                **params,
            )

        return self._single_pass_upscale(
            image=image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            guidance_scale=guidance_scale,
            noise_level=noise_level,
        )

    def _ensure_pipe_loaded(self) -> None:
        """Raise a helpful error if the pipeline is not loaded."""
        if not getattr(self, "_pipe", None):
            raise RuntimeError("Upscale pipeline is not loaded")

    def _tile_parameters(self):
        """Return default tile parameters for tiled upscaling."""
        return {
            "tile_size": self.DEFAULT_TILE_SIZE,
            "overlap": self.TILE_OVERLAP,
            "tile_batch_size": self.DEFAULT_TILE_BATCH_SIZE,
        }

    def _finalize_response(
        self,
        result,
        request,
        prompt,
        negative_prompt,
        steps,
        guidance_scale,
        noise_level,
    ):
        """Finalize pipeline result into an ImageResponse and perform I/O.

        Saves preview/result, queues export, builds response metadata,
        emits completion, and sends image to canvas if available.
        """

        from airunner.components.art.managers.stablediffusion.image_response import (
            ImageResponse,
        )

        # Save result and preview (best-effort)
        saved_path = None
        try:
            saved_path = self._save_result_to_disk(result)
        except Exception:
            saved_path = None

        try:
            self._save_preview_image(result)
        except Exception:
            pass

        # Build response data and ImageResponse
        try:
            data = self._build_response_data(
                prompt=prompt,
                negative_prompt=negative_prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                saved_path=saved_path,
                noise_level=noise_level,
            )

            response = ImageResponse(
                images=[result],
                data=data,
                nsfw_content_detected=False,
                active_rect=getattr(self, "active_rect", None),
                is_outpaint=False,
            )

            # Queue export and notify
            try:
                self._queue_export([result], data)
            except Exception:
                pass

            try:
                self._emit_completed(saved_path, steps)
            except Exception:
                pass

            try:
                self._send_to_canvas(response)
            except Exception:
                pass

            return response
        except Exception as exc:  # pragma: no cover - integration path
            self.logger.exception(
                "Failed to finalize upscale response: %s", exc
            )
            try:
                self._emit_failure(str(exc))
            except Exception:
                pass
            return None

    def _handle_oom(self, *args, **kwargs):
        """Fallback handler for OOM conditions.

        Delegates to OOM mixin helpers which may return a new tiling state.
        """
        # Prefer OOM helpers provided by dedicated mixin
        # Signature forwarded to keep compatibility with older code
        try:
            # Try batch reduction first
            batch_result = self._reduce_batch_size_if_possible(*args, **kwargs)
            if batch_result is not None:
                return batch_result

            # Try tile size reduction
            tile_result = self._reduce_tile_size_if_possible(*args, **kwargs)
            if tile_result is not None:
                return tile_result

        except Exception:
            pass

        return None

    def _should_tile(self, image: Any) -> bool:
        """Decide whether to use tiling.

        Default heuristic: largest dimension >= threshold. Individual mixins
        may override this logic.
        """
        try:
            return max(image.size) >= self.LARGE_INPUT_THRESHOLD
        except Exception:
            return False

    # The following methods are intentionally provided as lightweight
    # stubs so that importing `X4UpscalingCoreMixin` at test-collection
    # time does not require heavy runtime dependencies. Concrete
    # implementations are provided by other mixins (e.g. execution,
    # tiling, OOM). The manager's MRO should place those mixins before
    # this core mixin so their methods override these stubs.

    def _single_pass_upscale(self, *args, **kwargs):
        """Stub for single-pass upscaling; overridden by execution mixin.

        Raises:
            NotImplementedError: If no overriding mixin provides an
            implementation at runtime.
        """
        raise NotImplementedError()

    def _tile_upscale(self, *args, **kwargs):
        """Stub for tiled upscaling; overridden by tiling mixin."""
        raise NotImplementedError()

    def _execute_pipe_and_extract(self, *args, **kwargs):
        """Stub for pipeline execution; overridden by execution mixin."""
        raise NotImplementedError()

    def _reduce_batch_size_if_possible(self, *args, **kwargs):
        """Stub for batch-size reduction on OOM; overridden by OOM mixin."""
        raise NotImplementedError()

    def _reduce_tile_size_if_possible(self, *args, **kwargs):
        """Stub for tile-size reduction on OOM; overridden by OOM mixin."""
        raise NotImplementedError()
