"""
Response and communication mixin for X4UpscaleManager.

This mixin handles progress reporting, completion signaling, image export,
and worker communication for upscaling operations.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

from PIL import Image

from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.enums import EngineResponseCode, SignalCode


class X4ResponseMixin:
    """Response handling and communication for X4UpscaleManager."""

    PREVIEW_FILENAME = "preview_current.png"

    def _emit_failure(self, message: str):
        """Emit failure signals for upscaling operation.

        Args:
            message: Error message to report.
        """
        self._notify_worker(EngineResponseCode.ERROR, message)
        try:
            self.emit_signal(SignalCode.UPSCALE_FAILED, {"error": message})
        except Exception:
            pass

    def _emit_completed(self, saved_path: Optional[str], steps: int):
        """Emit completion signal with result information.

        Args:
            saved_path: Path where upscaled image was saved (if any).
            steps: Number of inference steps used.
        """
        try:
            self.emit_signal(
                SignalCode.UPSCALE_COMPLETED,
                {"image_path": saved_path, "steps": steps},
            )
        except Exception:
            pass

    def _send_to_canvas(self, response: ImageResponse):
        """Send upscaled image to canvas for display.

        Args:
            response: ImageResponse containing upscaled image.
        """
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
        """Notify worker of operation result.

        Args:
            code: Response code indicating success/failure/status.
            message: Response message or data.
        """
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
        """Build response data dictionary with operation metadata.

        Args:
            prompt: Text prompt used.
            negative_prompt: Negative prompt used.
            steps: Number of inference steps.
            guidance_scale: Guidance scale value.
            saved_path: Path where image was saved.
            noise_level: Noise level used.

        Returns:
            Dictionary with comprehensive operation metadata.
        """
        controlnet_settings = self._safe_controlnet_settings()

        return self._compose_response_metadata(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            guidance_scale=guidance_scale,
            saved_path=saved_path,
            noise_level=noise_level,
            controlnet_settings=controlnet_settings,
        )

    def _safe_controlnet_settings(self):
        """Safely retrieve controlnet settings if available.

        Returns:
            The controlnet settings object or None if not present.
        """
        try:
            return self.controlnet_settings
        except Exception:
            return None

    def _compose_response_metadata(
        self,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        saved_path: Optional[str],
        noise_level: int,
        controlnet_settings: Optional[object],
    ) -> Dict:
        """Compose the response metadata dictionary.

        This helper centralizes construction of the response payload so the
        public method remains concise for static analysis tools.
        """
        base = self._base_response_metadata(
            prompt, negative_prompt, steps, guidance_scale, saved_path
        )
        base["controlnet_settings"] = controlnet_settings
        base["noise_level"] = noise_level
        return base

    def _base_response_metadata(
        self,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        saved_path: Optional[str],
    ) -> Dict:
        """Build the core response metadata dict shared across generators."""
        return {
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
            "is_txt2img": False,
            "is_img2img": True,
            "is_inpaint": False,
            "is_outpaint": False,
            "mask_blur": 0,
            "saved_path": saved_path,
            "generator": "x4_upscaler",
        }

    def _queue_export(self, images: List[Image.Image], data: Dict):
        """Queue images for export with metadata.

        Args:
            images: List of PIL Images to export.
            data: Metadata dictionary for export.
        """
        try:
            self.image_export_worker.add_to_queue(
                {"images": images, "data": data}
            )
        except Exception as exc:
            self.logger.warning(
                "Failed to queue upscaled image export: %s", exc
            )

    def _save_preview_image(self, image: Image.Image):
        """Save preview image to disk.

        Composites alpha channels over white background to avoid
        transparency issues.

        Args:
            image: PIL Image to save as preview.
        """
        try:
            os.makedirs(self.preview_dir, exist_ok=True)

            # Handle alpha channel
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
        """Save upscaled result image to disk with timestamped filename.

        Args:
            image: PIL Image to save.

        Returns:
            Path where image was saved, or None if save failed.
        """
        try:
            os.makedirs(self.preview_dir, exist_ok=True)
            filename = datetime.now().strftime("upscaled_%Y%m%d_%H%M%S.png")
            path = os.path.join(self.preview_dir, filename)

            # Handle alpha channel
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
        """Emit progress update signals.

        Normalizes progress to 0-100% and emits both upscale-specific
        and generic SD progress signals. Prevents progress from going
        backwards during tiled operations.

        Args:
            current: Current progress value.
            total: Total progress value (e.g., 100 for percentage).
        """
        try:
            percent = self._normalize_progress(current, total)

            # Emit upscale-specific progress
            self.emit_signal(
                SignalCode.UPSCALE_PROGRESS,
                {"current": current, "total": total, "percent": percent},
            )

            step = self._percent_to_step(percent)
            emit_step = self._prevent_backward_progress(step)

            self.emit_signal(
                SignalCode.SD_PROGRESS_SIGNAL,
                {"step": emit_step, "total": 100},
            )
        except Exception:
            pass

    def _normalize_progress(self, current: int, total: int) -> float:
        """Normalize a current/total pair to a clamped 0.0-1.0 float."""
        try:
            if total == 0:
                return 0.0
            percent = float(current) / float(total)
            return max(0.0, min(1.0, percent))
        except Exception:
            return 0.0

    def _percent_to_step(self, percent: float) -> int:
        """Convert a 0.0-1.0 percent into an integer 0-100 step value."""
        try:
            return int(percent * 100)
        except Exception:
            return 0

    def _prevent_backward_progress(self, step: int) -> int:
        """Ensure progress never moves backward during tiled operations.

        Updates internal _last_progress_percent state and returns the
        step value that should be emitted.
        """
        try:
            last = getattr(self, "_last_progress_percent", None)
            if last is None:
                self._last_progress_percent = step
                return step

            emit_step = max(int(last), step)
            self._last_progress_percent = emit_step
            return emit_step
        except Exception:
            return step
