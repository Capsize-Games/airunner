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

        if not self._framepack_handler:
            self._framepack_handler = FramePackHandler()

        if self._framepack_handler:
            self._framepack_handler.state = HandlerState.LOADED
            self._framepack_handler.load()

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

    def generate_video(self, data: Dict):
        """Generate a video using the FramePack handler."""
        if not self._framepack_handler:
            self.load_model_manager()

        if (
            self._framepack_handler
            and self._framepack_handler.state == HandlerState.LOADED
        ):
            input_image = data.get("input_image")
            prompt = data.get("prompt")

            if not input_image:
                self.emit_signal(
                    SignalCode.STATUS_MESSAGE_SIGNAL,
                    {
                        "message": "No input image provided for video generation"
                    },
                )
                return

            if not prompt:
                self.emit_signal(
                    SignalCode.STATUS_MESSAGE_SIGNAL,
                    {"message": "No prompt provided for video generation"},
                )
                return

            try:
                self._framepack_handler.generate_video(
                    input_image=input_image,
                    prompt=prompt,
                    n_prompt=data.get("negative_prompt", ""),
                    total_second_length=data.get("duration", 5.0),
                    steps=data.get("steps", 20),
                    guidance_scale=data.get("guidance_scale", 4.0),
                    cfg=data.get("cfg", 7.5),
                    seed=data.get("seed", 42),
                )
            except Exception as e:
                self.emit_signal(
                    SignalCode.STATUS_MESSAGE_SIGNAL,
                    {"message": f"Error generating video: {str(e)}"},
                )
