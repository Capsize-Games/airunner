import os
import subprocess
import torch
import shutil
from typing import Optional, Dict, Any, List
import threading
from pathlib import Path

from PySide6.QtCore import Signal

from airunner.enums import HandlerType, ModelType, ModelStatus, SignalCode
from airunner.handlers.base_model_manager import BaseModelManager
from airunner.utils.application.get_logger import get_logger
from airunner.settings import AIRUNNER_LOG_LEVEL


class MuseTalkHandler(BaseModelManager):
    """Handler for MuseTalk lip-syncing model.

    This handler manages the loading and execution of the MuseTalk lip-syncing model,
    which generates synchronized lip movements for a video based on an audio input.
    """

    handler_type = HandlerType.TRANSFORMER
    model_type = ModelType.VIDEO

    # Signals for progress updates and completion
    frame_ready = Signal(object)  # Emits either a QPixmap or np.ndarray frame
    video_completed = Signal(str)  # Emits the path to the completed video file
    progress_update = Signal(
        int, str
    )  # Emits progress percentage and status message

    _model_status = {
        ModelType.VIDEO: ModelStatus.UNLOADED,
    }

    def __init__(self, model_root: str = None, device: str = "cuda"):
        super().__init__()
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self.logger.info("Initializing MuseTalkHandler")

        # Model paths and configuration
        self.model_root = model_root or os.path.join(
            os.path.expanduser("~"), self.path_settings.models_path, "MuseTalk"
        )
        self.device = device if torch.cuda.is_available() else "cpu"

        # Initialize model components as None
        self.unet = None
        self.vae = None
        self.whisper = None
        self.face_parser = None
        self.dw_pose = None
        self.sync_net = None

        # Find FFmpeg path
        self.ffmpeg_path = self._find_ffmpeg()
        if not self.ffmpeg_path:
            self.logger.error(
                "FFmpeg executable not found. Please install FFmpeg and ensure it is in PATH."
            )

        # Output directory
        self.outputs_folder = os.path.join(
            os.path.expanduser("~"), self.path_settings.base_path, "musetalk"
        )
        os.makedirs(self.outputs_folder, exist_ok=True)

        # State tracking
        self.is_generating = False
        self.current_job_id = None
        self.generation_thread = None

    def _find_ffmpeg(self) -> str:
        """Find the FFmpeg executable path.

        Checks PATH, common installation locations, and bundled locations.

        Returns:
            str: Path to the FFmpeg executable or None if not found.
        """
        # Check if FFmpeg is in PATH
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            self.logger.info(f"Found FFmpeg in PATH: {ffmpeg_path}")
            return ffmpeg_path

        # Check common installation locations
        common_locations = [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/opt/homebrew/bin/ffmpeg",  # macOS Homebrew
            "C:\\ffmpeg\\bin\\ffmpeg.exe",  # Windows
        ]

        for location in common_locations:
            if os.path.exists(location):
                self.logger.info(f"Found FFmpeg at: {location}")
                return location

        # Check if bundled with the application
        bundled_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "bin",
            "ffmpeg",
        )
        if os.path.exists(bundled_path):
            self.logger.info(f"Found bundled FFmpeg: {bundled_path}")
            return bundled_path

        self.logger.error("FFmpeg executable not found")
        return None

    def load(self):
        """Load the MuseTalk models.

        Returns:
            bool: True if loading was successful, False otherwise.
        """
        try:
            self.logger.info("Starting MuseTalk model loading...")
            self.change_model_status(ModelType.VIDEO, ModelStatus.LOADING)

            # Check if FFmpeg is available
            if not self.ffmpeg_path:
                raise RuntimeError(
                    "FFmpeg executable is required but not found"
                )

            # Progress updates
            self.progress_update.emit(10, "Loading UNet model...")

            # Load UNet model
            unet_path = os.path.join(self.model_root, "unet")
            self.logger.info(f"Loading UNet model from {unet_path}")

            # Import MuseTalk modules from vendored code
            from airunner.vendor.musetalk.musetalk.models import (
                load_unet_model,
            )

            self.unet = load_unet_model(unet_path)
            if self.unet:
                self.unet.to(self.device)
                self.unet.eval()
                self.logger.info("UNet model loaded successfully")

            # Load VAE
            self.progress_update.emit(30, "Loading VAE model...")
            vae_path = os.path.join(self.model_root, "sd-vae")
            self.logger.info(f"Loading VAE model from {vae_path}")

            # Use HuggingFace diffusers for loading VAE
            from diffusers import AutoencoderKL

            try:
                self.vae = AutoencoderKL.from_pretrained(
                    vae_path, torch_dtype=torch.float16
                )
                self.vae.to(self.device)
                self.vae.eval()
                self.logger.info("VAE model loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load VAE model: {str(e)}")
                raise

            # Load Whisper
            self.progress_update.emit(50, "Loading Whisper model...")
            whisper_path = os.path.join(self.model_root, "whisper")
            self.logger.info(f"Loading Whisper model from {whisper_path}")

            # Use HuggingFace transformers for loading Whisper
            from transformers import WhisperModel

            try:
                self.whisper = WhisperModel.from_pretrained(
                    whisper_path, torch_dtype=torch.float16
                )
                self.whisper.to(self.device)
                self.whisper.eval()
                self.logger.info("Whisper model loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load Whisper model: {str(e)}")
                raise

            # Load Face Parser
            self.progress_update.emit(70, "Loading face parsing model...")
            face_parser_path = os.path.join(self.model_root, "face_parser")
            self.logger.info(f"Loading face parser from {face_parser_path}")

            # Import face parser module from vendored code
            from airunner.vendor.musetalk.musetalk.face_parsing import (
                FaceParser,
            )

            try:
                self.face_parser = FaceParser(
                    face_parser_path, device=self.device
                )
                self.logger.info("Face parser loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load face parser: {str(e)}")
                raise

            # Load DWPose
            self.progress_update.emit(85, "Loading DWPose model...")
            dwpose_path = os.path.join(self.model_root, "dwpose")
            self.logger.info(f"Loading DWPose model from {dwpose_path}")

            # Import DWPose module from vendored code
            from airunner.vendor.musetalk.musetalk.dwpose import (
                DWPoseEstimator,
            )

            try:
                self.dw_pose = DWPoseEstimator(dwpose_path, device=self.device)
                self.logger.info("DWPose model loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load DWPose model: {str(e)}")
                raise

            # Change status to READY
            self.change_model_status(ModelType.VIDEO, ModelStatus.READY)
            self.logger.info("MuseTalk models loaded successfully")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to load MuseTalk models: {str(e)}", exc_info=True
            )
            self.change_model_status(ModelType.VIDEO, ModelStatus.FAILED)
            # Clean up partially loaded models
            self.unload()
            return False

    def unload(self):
        """Unload the MuseTalk models and free resources.

        Returns:
            bool: True if unloading was successful, False otherwise.
        """
        try:
            # If generation is in progress, wait for it to finish or cancel
            if (
                self.is_generating
                and self.generation_thread
                and self.generation_thread.is_alive()
            ):
                self.generation_thread.join(timeout=5)

            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Unload models
            self.unet = None
            self.vae = None
            self.whisper = None
            self.face_parser = None
            self.dw_pose = None
            self.sync_net = None

            # Explicitly delete to help GC, especially with CUDA tensors
            import gc

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self.change_model_status(ModelType.VIDEO, ModelStatus.UNLOADED)
            self.logger.info("MuseTalk models unloaded.")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to unload MuseTalk models: {e}", exc_info=True
            )
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                f"Failed to unload MuseTalk models: {str(e)}",
            )
            return False

    def run(
        self,
        video_path: str,
        audio_path: str,
        output_path: str = None,
        **kwargs,
    ):
        """Run the MuseTalk lip-syncing process.

        Args:
            video_path (str): Path to the input video file
            audio_path (str): Path to the input audio file
            output_path (str, optional): Path for the output video file. If not provided,
                                         a default path will be generated.
            **kwargs: Additional arguments for MuseTalk processing

        Returns:
            str: Job ID for the process
        """
        import uuid
        import traceback

        self.logger.info("MuseTalk run called")

        # Check if models are ready
        if self.model_status.get(ModelType.VIDEO) != ModelStatus.READY:
            error_msg = f"MuseTalk models are not ready. Current status: {self.model_status.get(ModelType.VIDEO)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Check if a process is already running
        if self.is_generating:
            error_msg = "A lip-sync generation is already in progress."
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Verify input files
        if not os.path.exists(video_path):
            error_msg = f"Input video file not found: {video_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        if not os.path.exists(audio_path):
            error_msg = f"Input audio file not found: {audio_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Create job ID
        self.current_job_id = f"musetalk_{uuid.uuid4().hex[:8]}"
        self.logger.info(f"Created job ID: {self.current_job_id}")

        # Set default output path if not provided
        if not output_path:
            output_filename = f"musetalk_output_{self.current_job_id}.mp4"
            output_path = os.path.join(self.outputs_folder, output_filename)

        self.logger.info(f"Output will be saved to: {output_path}")

        # Start generation in a separate thread
        try:
            self.is_generating = True
            self.logger.info(
                f"Creating lip-sync generation thread for job {self.current_job_id}"
            )

            self.generation_thread = threading.Thread(
                target=self._run_thread,
                args=(video_path, audio_path, output_path, kwargs),
            )

            self.logger.info("Starting lip-sync generation thread")
            self.generation_thread.daemon = True  # Make thread daemonic so it doesn't block application exit
            self.generation_thread.start()
            self.logger.info(
                f"Generation thread started: {self.generation_thread.ident}"
            )

            # Report that the thread has started
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
                f"Lip-sync generation started: {self.current_job_id}",
            )

            return self.current_job_id

        except Exception as e:
            self.is_generating = False
            self.logger.error(
                f"Failed to start lip-sync generation thread: {str(e)}"
            )
            self.logger.error(traceback.format_exc())
            raise RuntimeError(
                f"Failed to start lip-sync generation: {str(e)}"
            )

    def _run_thread(self, video_path, audio_path, output_path, options):
        """Thread function for lip-sync generation.

        Args:
            video_path (str): Path to the input video file
            audio_path (str): Path to the input audio file
            output_path (str): Path for the output video file
            options (dict): Additional options for processing
        """
        try:
            self.logger.info(
                f"Starting lip-sync processing for video: {video_path}"
            )
            self.progress_update.emit(5, "Starting lip-sync processing...")

            # Step 1: Validate inputs and prepare environment
            if not all(
                [
                    self.unet,
                    self.vae,
                    self.whisper,
                    self.face_parser,
                    self.dw_pose,
                ]
            ):
                raise RuntimeError("MuseTalk models are not fully loaded.")

            # Step 2: Extract frames from video using FFmpeg
            temp_dir = os.path.join(
                self.outputs_folder, f"temp_{self.current_job_id}"
            )
            os.makedirs(temp_dir, exist_ok=True)

            frames_dir = os.path.join(temp_dir, "frames")
            os.makedirs(frames_dir, exist_ok=True)

            self.logger.info("Extracting frames from video")
            self.progress_update.emit(10, "Extracting frames from video...")

            extract_cmd = [
                self.ffmpeg_path,
                "-i",
                video_path,
                "-qscale:v",
                "1",
                "-qmin",
                "1",
                "-qmax",
                "1",
                "-vsync",
                "0",
                os.path.join(frames_dir, "%04d.png"),
            ]

            process = subprocess.Popen(
                extract_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                self.logger.error(f"FFmpeg error: {stderr.decode()}")
                raise RuntimeError(
                    f"Failed to extract frames: {stderr.decode()}"
                )

            # Count extracted frames
            frame_files = sorted(
                [f for f in os.listdir(frames_dir) if f.endswith(".png")]
            )
            if not frame_files:
                raise RuntimeError("No frames were extracted from the video")

            self.logger.info(f"Extracted {len(frame_files)} frames from video")

            # Step 3: Process audio with Whisper
            self.logger.info("Processing audio with Whisper model")
            self.progress_update.emit(25, "Processing audio features...")

            # Import necessary modules from vendored code
            from airunner.vendor.musetalk.musetalk.audio_processing import (
                extract_audio_features,
            )

            audio_features = extract_audio_features(
                audio_path, self.whisper, device=self.device
            )

            # Step 4: Process video frames with face detection and parsing
            self.logger.info("Processing video frames for face detection")
            self.progress_update.emit(40, "Detecting and parsing faces...")

            # Import face processing modules
            from airunner.vendor.musetalk.musetalk.face_processing import (
                process_video_frames,
            )

            processed_frames = process_video_frames(
                frames_dir,
                self.face_parser,
                self.dw_pose,
                progress_callback=lambda i, total: self.progress_update.emit(
                    40 + int((i / total) * 20),
                    f"Processing face data: {i}/{total} frames",
                ),
            )

            # Step 5: Run MuseTalk inference
            self.logger.info("Running MuseTalk inference")
            self.progress_update.emit(60, "Generating lip-synced frames...")

            # Import inference modules
            from airunner.vendor.musetalk.musetalk.inference import (
                run_inference,
            )

            output_frames_dir = os.path.join(temp_dir, "output_frames")
            os.makedirs(output_frames_dir, exist_ok=True)

            # Run the actual inference
            run_inference(
                processed_frames,
                audio_features,
                self.unet,
                self.vae,
                output_frames_dir,
                device=self.device,
                progress_callback=lambda i, total: self.progress_update.emit(
                    60 + int((i / total) * 30), f"Generating frame {i}/{total}"
                ),
            )

            # Step 6: Assemble output video with FFmpeg
            self.logger.info("Assembling output video")
            self.progress_update.emit(90, "Assembling final video...")

            # Extract original video's frame rate
            fps_cmd = [self.ffmpeg_path, "-i", video_path, "-hide_banner"]

            process = subprocess.Popen(
                fps_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            # Parse frame rate from output
            import re

            fps_match = re.search(r"(\d+(?:\.\d+)?) fps", stderr.decode())
            fps = fps_match.group(1) if fps_match else "30"

            # Assemble final video
            assemble_cmd = [
                self.ffmpeg_path,
                "-r",
                str(fps),
                "-i",
                os.path.join(output_frames_dir, "%04d.png"),
                "-i",
                audio_path,
                "-c:v",
                "libx264",
                "-preset",
                "slow",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-pix_fmt",
                "yuv420p",
                "-y",
                output_path,
            ]

            process = subprocess.Popen(
                assemble_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                self.logger.error(
                    f"FFmpeg error while assembling video: {stderr.decode()}"
                )
                raise RuntimeError(
                    f"Failed to assemble output video: {stderr.decode()}"
                )

            self.logger.info(f"Lip-sync video generated: {output_path}")
            self.progress_update.emit(100, "Lip-sync video completed")

            # Clean up temporary files
            try:
                import shutil

                shutil.rmtree(temp_dir)
            except Exception as e:
                self.logger.warning(
                    f"Failed to clean up temporary files: {str(e)}"
                )

            # Emit completion signal
            self.video_completed.emit(output_path)

            return output_path

        except Exception as e:
            self.logger.error(
                f"Error during lip-sync generation: {str(e)}", exc_info=True
            )
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                f"MuseTalk error: {str(e)}",
            )
            return None

        finally:
            self.is_generating = False
            self.current_job_id = None

            # Clean up CUDA memory
            if torch.cuda.is_available():
                import gc

                gc.collect()
                torch.cuda.empty_cache()

    def interrupt(self):
        """Interrupt the current lip-sync generation process."""
        if (
            self.is_generating
            and self.generation_thread
            and self.generation_thread.is_alive()
        ):
            # We don't have a direct way to interrupt the thread,
            # but we can set a flag to signal interruption
            self.is_generating = False
            self.logger.info(f"Interrupting job {self.current_job_id}")
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
                f"Lip-sync generation interrupted for job {self.current_job_id}",
            )
