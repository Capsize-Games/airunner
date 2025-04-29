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
from airunner.handlers.musetalk_handler import MuseTalkHandler


class MuseTalkWorker(Worker):
    """
    Worker thread for the MuseTalk lip-sync handler.

    This worker manages loading, unloading, and lip-sync generation requests
    for the MuseTalk lip-sync model.
    """

    queue_type = Worker.queue_type.GET_LAST_ITEM

    def __init__(self):
        """Initialize the MuseTalkWorker."""
        self._musetalk_handler = None
        self.signal_handlers = {
            SignalCode.MUSETALK_LOAD_SIGNAL: self.on_load_musetalk_signal,
            SignalCode.MUSETALK_UNLOAD_SIGNAL: self.on_unload_musetalk_signal,
            SignalCode.MUSETALK_GENERATE_SIGNAL: self.on_musetalk_generate_signal,
            SignalCode.INTERRUPT_MUSETALK_GENERATION_SIGNAL: self.on_interrupt_musetalk_generation_signal,
            SignalCode.QUIT_APPLICATION: self.on_quit_application_signal,
        }
        super().__init__()

    @property
    def model_manager(self):
        """Get the MuseTalk model manager."""
        return self._musetalk_handler

    @model_manager.setter
    def model_manager(self, value):
        """Set the MuseTalk model manager."""
        self._musetalk_handler = value

    def handle_message(self, message):
        """Handle incoming messages for MuseTalk operations."""
        if isinstance(message, dict):
            if "action" in message:
                if message["action"] == ModelAction.LOAD:
                    self.load_model_manager(message.get("data", {}))
                elif message["action"] == ModelAction.UNLOAD:
                    self.unload_model_manager(message.get("data", {}))
                elif message["action"] == ModelAction.GENERATE:
                    self.generate_lip_sync(message.get("data", {}))
        else:
            self.logger.warning(f"Unsupported message type: {type(message)}")

    def on_load_musetalk_signal(self, data: Dict = None):
        """Handle signal to load the MuseTalk model."""
        self.add_to_queue(
            {"action": ModelAction.LOAD, "type": ModelType.VIDEO, "data": data}
        )

    def on_unload_musetalk_signal(self, data: Dict = None):
        """Handle signal to unload the MuseTalk model."""
        self.add_to_queue(
            {
                "action": ModelAction.UNLOAD,
                "type": ModelType.VIDEO,
                "data": data,
            }
        )

    def on_musetalk_generate_signal(self, data: Dict):
        """Handle signal to generate a lip-synced video."""
        self.add_to_queue(
            {
                "action": ModelAction.GENERATE,
                "type": ModelType.VIDEO,
                "data": data,
            }
        )

    def on_interrupt_musetalk_generation_signal(self, _data=None):
        """Handle signal to interrupt lip-sync generation."""
        if self.model_manager:
            self.model_manager.interrupt()

    def on_quit_application_signal(self, _data=None):
        """Handle application quit signal."""
        self.unload_model_manager()

    def load_model_manager(self, data: Dict = None):
        """Load the MuseTalk model manager."""
        data = data or {}

        try:
            if not self._musetalk_handler:
                self.logger.info("Creating new MuseTalkHandler instance")
                self._musetalk_handler = MuseTalkHandler()

                # Immediately load the model and wait for completion
                self.logger.info("Loading MuseTalk models")
                success = self._musetalk_handler.load()

                if not success:
                    self.logger.error("Failed to load MuseTalk models")
                    self.emit_signal(
                        SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                        "Failed to load MuseTalk models",
                    )
                    return False

                # Verify model status after loading
                model_status = self._musetalk_handler.model_status.get(
                    ModelType.VIDEO
                )
                self.logger.info(
                    f"MuseTalk model status after loading: {model_status}"
                )

                if model_status != ModelStatus.READY:
                    self.logger.error(
                        f"MuseTalk models are not ready after loading. Status: {model_status}"
                    )
                    self.emit_signal(
                        SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                        f"MuseTalk models not ready: {model_status}",
                    )
                    return False

            if self._musetalk_handler:
                # Ensure the model is loaded
                if (
                    self._musetalk_handler.model_status.get(ModelType.VIDEO)
                    != ModelStatus.READY
                ):
                    self.logger.info(
                        "MuseTalk models not ready, attempting to load"
                    )
                    success = self._musetalk_handler.load()

                    if not success:
                        self.logger.error("Failed to load MuseTalk models")
                        self.emit_signal(
                            SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                            "Failed to load MuseTalk models",
                        )
                        return False

                    # Double-check model status after loading
                    if (
                        self._musetalk_handler.model_status.get(
                            ModelType.VIDEO
                        )
                        != ModelStatus.READY
                    ):
                        self.logger.error(
                            "MuseTalk models still not ready after loading"
                        )
                        self.emit_signal(
                            SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                            "MuseTalk models are not ready after loading attempt",
                        )
                        return False

                # Run callback if provided
                callback = data.get("callback", None)
                if callback:
                    callback(data)

                self.logger.info("MuseTalk models loaded successfully")
                self.emit_signal(
                    SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
                    "MuseTalk models loaded successfully",
                )
                return True

            return False

        except Exception as e:
            import traceback

            self.logger.error(f"Error loading MuseTalk models: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                f"Error loading MuseTalk models: {str(e)}",
            )
            return False

    def unload_model_manager(self, data: Dict = None):
        """Unload the MuseTalk model manager."""
        data = data or {}

        if self._musetalk_handler:
            self._musetalk_handler.unload()
            self._musetalk_handler = None

            callback = data.get("callback", None)
            if callback:
                callback(data)

    def generate_lip_sync(self, data):
        """Process lip-sync generation request and pass to the handler.

        Args:
            data (dict): The request data containing:
                - video_path: Path to input video file
                - audio_path: Path to input audio file
                - output_path: Optional path where to save the output
                - Additional parameters as needed
        """
        try:
            # Load the model manager on first use
            self.logger.info(f"Starting lip-sync generation with data: {data}")
            self.load_model_manager()

            if not self._musetalk_handler:
                self.logger.error("MuseTalk handler is not initialized")
                self.emit_signal(
                    SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                    "Lip-sync generation failed: MuseTalk not initialized",
                )
                return

            # Report model status
            model_status = self._musetalk_handler.model_status.get(
                ModelType.VIDEO
            )
            self.logger.info(f"MuseTalk model status: {model_status}")

            # Get video and audio paths
            video_path = data.get("video_path")
            if not video_path:
                self.logger.error("No input video provided")
                self.emit_signal(
                    SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                    "No input video provided for lip-sync generation",
                )
                return

            audio_path = data.get("audio_path")
            if not audio_path:
                self.logger.error("No input audio provided")
                self.emit_signal(
                    SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                    "No input audio provided for lip-sync generation",
                )
                return

            # Get other parameters
            output_path = data.get("output_path")
            face_center_x = data.get("face_center_x", 0.5)
            face_center_y = data.get("face_center_y", 0.5)
            version = data.get("version", "v1.5")

            self.logger.info(
                f"Starting lip-sync generation with parameters: video='{video_path}', "
                f"audio='{audio_path}', output='{output_path}', "
                f"face_center=({face_center_x}, {face_center_y}), version={version}"
            )

            # Set up signal connections for progress updates
            # Connect the handler's signals to our own signal emitters
            self._musetalk_handler.frame_ready.connect(
                lambda frame: self.emit_signal(
                    SignalCode.VIDEO_FRAME_UPDATE_SIGNAL, {"frame": frame}
                )
            )
            self._musetalk_handler.video_completed.connect(
                lambda path: self.emit_signal(
                    SignalCode.VIDEO_GENERATION_COMPLETED_SIGNAL,
                    {"path": path},
                )
            )
            self._musetalk_handler.progress_update.connect(
                lambda percent, message: self.emit_signal(
                    SignalCode.VIDEO_GENERATION_PROGRESS_SIGNAL,
                    {"percent": percent, "message": message},
                )
            )

            # Generate lip-synced video
            self.logger.info("Calling MuseTalkHandler.run()")
            job_id = self._musetalk_handler.run(
                video_path=video_path,
                audio_path=audio_path,
                output_path=output_path,
                face_center_x=face_center_x,
                face_center_y=face_center_y,
                version=version,
            )

            # Store job ID for potential cancellation
            self._current_job_id = job_id
            self.logger.info(
                f"Lip-sync generation started with job ID: {job_id}"
            )

            # Send initial response
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
                f"Lip-sync generation started (Job ID: {job_id})",
            )

        except Exception as e:
            import traceback

            self.logger.error(f"Error in lip-sync generation: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                f"Lip-sync generation error: {str(e)}",
            )
