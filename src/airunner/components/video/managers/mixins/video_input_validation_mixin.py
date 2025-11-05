"""Input validation mixin for video generation."""

from typing import Any
from PIL import Image


class VideoInputValidationMixin:
    """Mixin for validating video generation inputs.

    Handles validation of:
    - Input images (PIL or numpy)
    - Prompts
    - Video parameters (frames, fps)

    Dependencies (from parent):
        logger: Logger instance
    """

    def _validate_generation_inputs(self, **kwargs) -> dict:
        """Validate and extract generation inputs.

        Args:
            **kwargs: Generation parameters

        Returns:
            Dict with validated parameters

        Raises:
            ValueError: If required inputs are missing or invalid
        """
        init_image = kwargs.get("init_image")
        prompt = kwargs.get("prompt", "")
        num_frames = kwargs.get("num_frames", 121)
        fps = kwargs.get("fps", 30)

        if init_image is None:
            self.logger.error("init_image is required for HunyuanVideo")
            raise ValueError("Input image is required")

        if not prompt:
            self.logger.error("prompt is required for HunyuanVideo")
            raise ValueError("Prompt cannot be empty")

        if num_frames < 1:
            self.logger.error(f"Invalid num_frames: {num_frames}")
            raise ValueError("num_frames must be at least 1")

        if fps <= 0:
            self.logger.error(f"Invalid fps: {fps}")
            raise ValueError("fps must be greater than 0")

        return {
            "init_image": init_image,
            "prompt": prompt,
            "num_frames": num_frames,
            "fps": fps,
        }

    def _get_image_dimensions(self, init_image: Any) -> tuple:
        """Get height and width from image.

        Args:
            init_image: PIL Image or numpy array

        Returns:
            Tuple of (height, width)
        """
        if isinstance(init_image, Image.Image):
            return init_image.height, init_image.width
        else:
            # Numpy array
            return init_image.shape[0], init_image.shape[1]
