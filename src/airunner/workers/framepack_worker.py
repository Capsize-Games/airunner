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
        print("FRAMEPACK WORKER ON VIDEO GENERATE SIGNAL")
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
        print("LOAD MODEL MANAGER", self._framepack_handler)

        if not self._framepack_handler:
            print("n" * 100)
            print("setting framepack handler")
            self._framepack_handler = FramePackHandler()
            self._framepack_handler.load()

        if self._framepack_handler:
            callback = data.get("callback", None)
            if callback:
                callback(data)

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
            self.load_model_manager()

            # Get image path or data
            image_path = data.get("image")
            if not image_path:
                self.emit_signal(
                    SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                    "No input image provided for video generation",
                )
                return

            # Load image
            from PIL import Image
            import base64
            import io

            if isinstance(image_path, str) and image_path.startswith(
                "data:image"
            ):
                # Base64 encoded image
                image_data = image_path.split(",")[1]
                image = Image.open(io.BytesIO(base64.b64decode(image_data)))
            elif isinstance(image_path, str) and os.path.exists(image_path):
                # File path
                image = Image.open(image_path)
            else:
                self.emit_signal(
                    SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                    "Invalid image format for video generation",
                )
                return

            # Convert image to RGB if needed
            if image.mode != "RGB":
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

            # Generate video
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

            # Send initial response
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
                f"Video generation started (Job ID: {job_id})",
            )

        except Exception as e:
            self.logger.error(f"Error in video generation: {str(e)}")
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                f"Video generation error: {str(e)}",
            )
