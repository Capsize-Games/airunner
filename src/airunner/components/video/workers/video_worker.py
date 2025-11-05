"""
Video generation worker for handling video generation requests.

This worker processes video generation signals and manages the generation
pipeline asynchronously.
"""

from typing import Any, Dict, Optional

from airunner.components.application.workers.worker import Worker
from airunner.enums import SignalCode, QueueType


class VideoWorker(Worker):
    """
    Worker for processing video generation requests.

    Listens for VIDEO_GENERATE_SIGNAL and handles video generation
    asynchronously using the appropriate video model manager.

    Signals:
        VIDEO_GENERATE_SIGNAL: Trigger video generation
        VIDEO_CANCEL_SIGNAL: Cancel current generation

    Example:
        >>> # Emit signal to generate video
        >>> self.emit_signal(SignalCode.VIDEO_GENERATE_SIGNAL, {
        ...     "model_type": "HunyuanVideo",
        ...     "prompt": "A beautiful sunset over the ocean",
        ...     "num_frames": 16,
        ...     "fps": 8,
        ...     "callback": self.on_progress
        ... })
    """

    queue_type = QueueType.GET_LAST_ITEM  # Only process latest request
    prefix = "VideoWorker"

    def __init__(self, *args, **kwargs):
        """Initialize the video worker."""
        super().__init__(*args, **kwargs)

        # Will be populated with video managers
        self._managers: Dict[str, Any] = {}
        self._current_manager: Optional[Any] = None
        self._cancel_requested = False

        # Register signal handlers
        self.register(SignalCode.VIDEO_GENERATE_SIGNAL, self.queue_message)
        self.register(
            SignalCode.INTERRUPT_VIDEO_GENERATION_SIGNAL, self.handle_cancel
        )
        self.register(
            SignalCode.VIDEO_MODEL_CHANGED_SIGNAL, self.handle_model_change
        )

    def handle_message(self, message: Dict[str, Any]):
        """
        Handle incoming video generation requests.

        Args:
            message: Dictionary containing:
                - model_type: Name of video model to use
                - prompt: Text prompt
                - negative_prompt: Negative prompt
                - num_frames: Number of frames
                - fps: Frames per second
                - width: Video width
                - height: Video height
                - guidance_scale: CFG scale
                - num_inference_steps: Denoising steps
                - seed: Random seed
                - init_image: Optional initial image
                - strength: Strength for I2V
                - callback: Progress callback
        """
        if self._cancel_requested:
            self.logger.info("Generation cancelled, skipping message")
            self._cancel_requested = False
            return

        model_type = message.get("model_type", "HunyuanVideo")

        # Get or create manager for this model type
        manager = self._get_manager(model_type)
        if not manager:
            self.logger.error(f"No manager found for model type: {model_type}")
            self.emit_signal(
                SignalCode.VIDEO_GENERATION_FAILED_SIGNAL,
                {"error": f"Unknown model type: {model_type}"},
            )
            return

        self._current_manager = manager

        # Emit generation started signal
        self.emit_signal(
            SignalCode.VIDEO_GENERATION_STARTED_SIGNAL,
            {"model_type": model_type},
        )

        try:
            # Generate video
            output_path = manager.generate_video(**message)

            if output_path and not self._cancel_requested:
                # Emit completion signal
                self.emit_signal(
                    SignalCode.VIDEO_GENERATED_SIGNAL,
                    {
                        "output_path": output_path,
                        "model_type": model_type,
                        "prompt": message.get("prompt", ""),
                    },
                )
                self.logger.info(
                    f"Video generated successfully: {output_path}"
                )
            elif self._cancel_requested:
                self.logger.info("Video generation cancelled")
                self._cancel_requested = False
            else:
                self.emit_signal(
                    SignalCode.VIDEO_GENERATION_FAILED_SIGNAL,
                    {"error": "Generation failed"},
                )

        except Exception as e:
            self.logger.error(f"Error generating video: {e}", exc_info=True)
            self.emit_signal(
                SignalCode.VIDEO_GENERATION_FAILED_SIGNAL, {"error": str(e)}
            )
        finally:
            self._current_manager = None

    def handle_cancel(self, message: Dict[str, Any]):
        """
        Handle video generation cancellation request.

        Args:
            message: Cancellation request (currently unused)
        """
        self.logger.info("Cancel requested")
        self._cancel_requested = True

        if self._current_manager:
            self._current_manager.cancel_generation()

    def handle_model_change(self, message: Dict[str, Any]):
        """
        Handle video model change request.

        Args:
            message: Dictionary containing:
                - model_type: New model type to use
        """
        model_type = message.get("model_type")
        if not model_type:
            return

        self.logger.info(f"Switching to video model: {model_type}")

        # Get or create new manager
        manager = self._get_manager(model_type)
        if manager:
            self._current_manager = manager

    def _get_manager(self, model_type: str) -> Optional[Any]:
        """
        Get or create a manager for the specified model type.

        Args:
            model_type: Name of the video model

        Returns:
            Video manager instance, or None if not found
        """
        # Import and instantiate managers based on model_type
        if model_type == "HunyuanVideo":
            if "HunyuanVideo" not in self._managers:
                from airunner.components.video.managers.hunyuan_video_manager import (
                    HunyuanVideoManager,
                )

                self._managers["HunyuanVideo"] = HunyuanVideoManager()
                # Load the model if not already loaded
                if not self._managers["HunyuanVideo"].load_model():
                    self.logger.error("Failed to load HunyuanVideo model")
                    return None
            return self._managers["HunyuanVideo"]

        # TODO: Add CogVideoX and AnimateDiff managers
        # elif model_type == "CogVideoX":
        #     ...
        # elif model_type == "AnimateDiff":
        #     ...

        self.logger.warning(f"Manager for {model_type} not yet implemented")
        return None

    def stop(self, _=None):
        """Stop the worker and clean up resources."""
        self.logger.info("Stopping video worker...")

        # Cancel any ongoing generation
        if self._current_manager:
            self._current_manager.cancel_generation()

        # Unload all managers
        for manager in self._managers.values():
            try:
                manager.unload_model()
            except Exception as e:
                self.logger.error(f"Error unloading manager: {e}")

        self._managers.clear()
        super().stop()
