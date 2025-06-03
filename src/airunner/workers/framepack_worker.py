import os
from typing import Dict, Optional

from airunner.enums import (
    SignalCode,
    ModelAction,
    ModelType,
    ModelStatus,
    HandlerState,
)
from airunner.workers.worker import Worker
from airunner.handlers.framepack_handler import FramePackHandler


class FramePackWorker(Worker):
    """
    Worker thread for the FramePack video generation handler.

    This worker manages loading, unloading, and video generation requests
    for the FramePack video generation library.
    """

    queue_type = Worker.queue_type.GET_LAST_ITEM

    def __init__(self):
        """Initialize the FramePackWorker."""
        self._framepack_handler = None
        self.signal_handlers = {
            SignalCode.VIDEO_LOAD_SIGNAL: self.on_load_video_signal,
            SignalCode.VIDEO_UNLOAD_SIGNAL: self.on_unload_video_signal,
            SignalCode.VIDEO_GENERATE_SIGNAL: self.on_video_generate_signal,
            SignalCode.INTERRUPT_VIDEO_GENERATION_SIGNAL: self.on_interrupt_video_generation_signal,
            SignalCode.QUIT_APPLICATION: self.on_quit_application_signal,
        }
        super().__init__()

    @property
    def model_manager(self):
        """Get the FramePack model manager."""
        return self._framepack_handler

    @model_manager.setter
    def model_manager(self, value):
        """Set the FramePack model manager."""
        self._framepack_handler = value

    def handle_message(self, message):
        """Handle incoming messages for FramePack operations."""
        if isinstance(message, dict):
            if "action" in message:
                if message["action"] == ModelAction.LOAD:
                    self.load_model_manager(message.get("data", {}))
                elif message["action"] == ModelAction.UNLOAD:
                    self.unload_model_manager(message.get("data", {}))
                elif message["action"] == ModelAction.GENERATE:
                    self.generate_video(message.get("data", {}))
        else:
            self.logger.warning(f"Unsupported message type: {type(message)}")

    def on_load_video_signal(self, data: Dict = None):
        """Handle signal to load the video model."""
        self.add_to_queue(
            {"action": ModelAction.LOAD, "type": ModelType.VIDEO, "data": data}
        )

    def on_unload_video_signal(self, data: Dict = None):
        """Handle signal to unload the video model."""
        self.add_to_queue(
            {
                "action": ModelAction.UNLOAD,
                "type": ModelType.VIDEO,
                "data": data,
            }
        )

    def on_video_generate_signal(self, data: Dict):
        """Handle signal to generate a video."""
        self.add_to_queue(
            {
                "action": ModelAction.GENERATE,
                "type": ModelType.VIDEO,
                "data": data,
            }
        )

    def on_interrupt_video_generation_signal(self, _data=None):
        """Handle signal to interrupt video generation."""
        if self.model_manager:
            self.model_manager.interrupt()

    def on_quit_application_signal(self, _data=None):
        """Handle application quit signal."""
        self.unload_model_manager()

    def load_model_manager(self, data: Dict = None):
        """Load the FramePack model manager."""
        data = data or {}

        try:
            if not self._framepack_handler:
                self.logger.info("Creating new FramePackHandler instance")
                self._framepack_handler = FramePackHandler()

                # Immediately load the model and wait for completion
                self.logger.info("Loading FramePack models")
                success = self._framepack_handler.load()

                if not success:
                    self.api.application_error(
                        "Failed to load FramePack models"
                    )
                    return False

                # Verify model status after loading
                model_status = self._framepack_handler.model_status.get(
                    ModelType.VIDEO
                )
                self.logger.info(
                    f"FramePack model status after loading: {model_status}"
                )

                if model_status != ModelStatus.READY:
                    self.api.application_error(
                        f"FramePack models not ready: {model_status}"
                    )
                    return False

            if self._framepack_handler:
                # Ensure the model is loaded
                if (
                    self._framepack_handler.model_status.get(ModelType.VIDEO)
                    != ModelStatus.READY
                ):
                    self.logger.info(
                        "FramePack models not ready, attempting to load"
                    )
                    success = self._framepack_handler.load()

                    if not success:
                        self.api.application_error(
                            "Failed to load FramePack models",
                        )
                        return False

                    # Double-check model status after loading
                    if (
                        self._framepack_handler.model_status.get(
                            ModelType.VIDEO
                        )
                        != ModelStatus.READY
                    ):
                        self.api.application_error(
                            "FramePack models are not ready after loading attempt",
                        )
                        return False

                # Run callback if provided
                callback = data.get("callback", None)
                if callback:
                    callback(data)
                self.api.application_status(
                    "FramePack models loaded successfully",
                )
                return True

            return False

        except Exception as e:
            self.api.application_error(
                f"Error loading FramePack models: {str(e)}",
            )
            return False

    def unload_model_manager(self, data: Dict = None):
        """Unload the FramePack model manager."""
        data = data or {}

        if self._framepack_handler:
            self._framepack_handler.unload()
            self._framepack_handler = None

            callback = data.get("callback", None)
            if callback:
                callback(data)

    def generate_video(self, data):
        """Process video generation request and pass to the handler.

        Args:
            data (dict): The request data containing:
                - image: Path to input image or base64 encoded image
                - prompt: Text prompt for video generation
                - n_prompt: Optional negative prompt
                - duration: Video duration in seconds
                - Additional parameters as needed
        """
        try:
            # Load the model manager on first use
            self.logger.info(f"Starting video generation with data: {data}")
            self.load_model_manager()

            if not self._framepack_handler:
                self.api.application_error(
                    "Video generation failed: FramePack not initialized",
                )
                return

            # Report model status
            model_status = self._framepack_handler.model_status.get(
                ModelType.VIDEO
            )
            self.logger.info(f"FramePack model status: {model_status}")

            # Get image path or data
            image = data.get("input_image")
            if not image:
                self.api.application_error(
                    "No input image provided for video generation",
                )
                return

            # Convert image to RGB if needed
            if image.mode != "RGB":
                self.logger.info(f"Converting image from {image.mode} to RGB")
                image = image.convert("RGB")

            # Get parameters
            prompt = data.get("prompt", "")
            n_prompt = data.get("n_prompt", "")
            duration = float(data.get("duration", 5.0))

            # Additional parameters
            steps = int(data.get("steps", 20))
            guidance_scale = float(data.get("guidance_scale", 4.0))
            cfg_scale = float(data.get("cfg_scale", 7.5))
            seed = int(data.get("seed", 42))

            self.logger.info(
                f"Starting video generation with parameters: prompt='{prompt}', duration={duration}, steps={steps}, guidance_scale={guidance_scale}, cfg_scale={cfg_scale}, seed={seed}"
            )

            # Set up signal connections for progress updates
            # Connect the handler's signals to our own signal emitters
            self._framepack_handler.frame_ready.connect(
                lambda frame: self.api.video.frame_update(frame)
            )
            self._framepack_handler.video_completed.connect(
                lambda path: self.api.video.generation_complete(path)
            )
            self._framepack_handler.progress_update.connect(
                lambda percent, message: self.api.video.video_generate_step(
                    percent, message
                )
            )

            # Generate video
            self.logger.info("Calling FramePackHandler.generate_video()")
            job_id = self._framepack_handler.generate_video(
                input_image=image,
                prompt=prompt,
                n_prompt=n_prompt,
                total_second_length=duration,
                steps=steps,
                guidance_scale=guidance_scale,
                cfg=cfg_scale,
                seed=seed,
                random_seed=1.0,  # Default value
            )

            # Store job ID for potential cancellation
            self._current_job_id = job_id
            self.api.application_status(
                f"Video generation started (Job ID: {job_id})",
            )

        except Exception as e:
            self.api.application_error(
                f"Video generation error: {str(e)}",
            )
