"""
Base abstract class for video generation model managers.

This module provides the base interface that all video model managers must implement,
following the same pattern as BaseDiffusersModelManager for Stable Diffusion.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any


from airunner.components.application.managers.base_model_manager import (
    BaseModelManager,
)
from airunner.enums import ModelType, ModelStatus, SignalCode


class BaseVideoManager(BaseModelManager, ABC):
    """
    Abstract base class for video generation model managers.

    All video model managers (HunyuanVideo, CogVideoX, AnimateDiff) must inherit
    from this class and implement the abstract methods.

    Attributes:
        model_type: Type of model (set by subclass)
        pipeline: The loaded diffusers pipeline
        model_status: Current status of the model

    Example:
        >>> class HunyuanVideoManager(BaseVideoManager):
        ...     model_type = ModelType.HUNYUAN_VIDEO
        ...
        ...     def _load_model(self, options):
        ...         # Load HunyuanVideo pipeline
        ...         pass
    """

    model_type = ModelType.VIDEO  # Subclasses should override

    def __init__(self, *args, **kwargs):
        """Initialize the video manager."""
        super().__init__(*args, **kwargs)
        self.pipeline = None
        self._current_project: Optional[Dict[str, Any]] = None

    @abstractmethod
    def _load_model(self, options: Dict[str, Any]) -> bool:
        """
        Load the video generation model.

        Args:
            options: Configuration options for model loading
                - model_path: Path to model
                - torch_dtype: PyTorch dtype (float16, bfloat16, etc.)
                - device: Target device (cuda, cpu, etc.)

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def _unload_model(self) -> bool:
        """
        Unload the video generation model and free resources.

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def generate_video(self, **kwargs) -> Optional[str]:
        """
        Generate a video from the given parameters.

        Args:
            prompt: Text prompt for generation
            negative_prompt: Negative text prompt
            num_frames: Number of frames to generate
            fps: Frames per second
            width: Video width in pixels
            height: Video height in pixels
            guidance_scale: CFG scale
            num_inference_steps: Number of denoising steps
            seed: Random seed for reproducibility
            init_image: Optional initial image for I2V
            strength: Strength for I2V (0.0-1.0)
            callback: Progress callback function

        Returns:
            Path to generated video file, or None if failed
        """

    def load_model(self, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Public method to load the model with status updates.

        Args:
            options: Configuration options

        Returns:
            True if successful
        """
        self.logger.info(f"Loading {self.model_type} model...")
        self.set_model_status(ModelStatus.LOADING)

        try:
            success = self._load_model(options or {})
            if success:
                self.set_model_status(ModelStatus.LOADED)
                self.emit_signal(
                    SignalCode.VIDEO_LOAD_SIGNAL,
                    {"model_type": self.model_type},
                )
                self.logger.info(
                    f"{self.model_type} model loaded successfully"
                )
            else:
                self.set_model_status(ModelStatus.FAILED)
                self.logger.error(f"Failed to load {self.model_type} model")
            return success
        except Exception as e:
            self.set_model_status(ModelStatus.FAILED)
            self.logger.error(f"Error loading {self.model_type} model: {e}")
            return False

    def unload_model(self) -> bool:
        """
        Public method to unload the model with status updates.

        Returns:
            True if successful
        """
        self.logger.info(f"Unloading {self.model_type} model...")
        self.set_model_status(ModelStatus.UNLOADING)

        try:
            success = self._unload_model()
            if success:
                self.set_model_status(ModelStatus.UNLOADED)
                self.emit_signal(
                    SignalCode.VIDEO_UNLOAD_SIGNAL,
                    {"model_type": self.model_type},
                )
                self.logger.info(
                    f"{self.model_type} model unloaded successfully"
                )
            else:
                self.set_model_status(ModelStatus.FAILED)
                self.logger.error(f"Failed to unload {self.model_type} model")
            return success
        except Exception as e:
            self.set_model_status(ModelStatus.FAILED)
            self.logger.error(f"Error unloading {self.model_type} model: {e}")
            return False

    def _prepare_generation_data(self, **kwargs) -> Dict[str, Any]:
        """
        Prepare and validate generation parameters.

        Args:
            **kwargs: Raw generation parameters

        Returns:
            Validated and processed parameters
        """
        return {
            "prompt": kwargs.get("prompt", ""),
            "negative_prompt": kwargs.get("negative_prompt", ""),
            "num_frames": kwargs.get("num_frames", 16),
            "fps": kwargs.get("fps", 8),
            "width": kwargs.get("width", 512),
            "height": kwargs.get("height", 512),
            "guidance_scale": kwargs.get("guidance_scale", 7.5),
            "num_inference_steps": kwargs.get("num_inference_steps", 50),
            "seed": kwargs.get("seed", -1),
            "init_image": kwargs.get("init_image"),
            "strength": kwargs.get("strength", 0.8),
            "callback": kwargs.get("callback"),
        }

    def cancel_generation(self):
        """Cancel the current video generation."""
        self.logger.info("Cancelling video generation...")
        self.emit_signal(
            SignalCode.INTERRUPT_VIDEO_GENERATION_SIGNAL,
            {"model_type": self.model_type},
        )
