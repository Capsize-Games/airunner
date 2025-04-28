import os
import torch
import numpy as np
from PIL import Image
from typing import Optional, Dict, Any, List
import threading

from PySide6.QtCore import Signal

from airunner.enums import HandlerType, ModelType, ModelStatus, SignalCode
from airunner.handlers.base_model_manager import BaseModelManager

# Import vendored FramePack modules
from airunner.vendor.framepack.diffusers_helper.memory import (
    DynamicSwapInstaller,
)
import airunner.vendor.framepack.diffusers_helper.bucket_tools as bucket_tools
import airunner.vendor.framepack.diffusers_helper.clip_vision as clip_vision
import airunner.vendor.framepack.diffusers_helper.hunyuan as hunyuan
import airunner.vendor.framepack.diffusers_helper.memory as memory_utils
import airunner.vendor.framepack.diffusers_helper.utils as fp_utils


class AsyncFramePackStream:
    """A class to handle the stream of frames from FramePack."""

    def __init__(self):
        self.output_queue = []
        self.listeners = []

    def push(self, item):
        """Push an item to the output queue and notify listeners."""
        self.output_queue.append(item)
        for listener in self.listeners:
            listener(item)

    def add_listener(self, listener):
        """Add a listener to be notified when new items are added to the queue."""
        self.listeners.append(listener)

    def clear(self):
        """Clear the output queue."""
        self.output_queue = []


class FramePackHandler(BaseModelManager):
    """Handler for FramePack video generation."""

    handler_type = HandlerType.TRANSFORMER
    model_type = ModelType.VIDEO

    # Signal for frame updates
    frame_ready = Signal(object)  # Emits either a QPixmap or np.ndarray
    video_completed = Signal(str)  # Emits the path to the completed video file
    progress_update = Signal(
        int, str
    )  # Emits progress percentage and status message

    def __init__(self):
        super().__init__()
        # Initialize models as None
        self.text_encoder = None
        self.text_encoder_2 = None
        self.image_encoder = None
        self.transformer = None
        self.vae = None
        self.feature_extractor = None

        # Default configuration
        self.config = {
            "high_vram": False,  # If true, models are kept in memory
            "use_teacache": True,  # For speedup
            "gpu_memory_preservation": True,  # For memory management
            "mp4_crf": 23,  # Video quality (lower is better)
            "steps": 20,  # Default diffusion steps
            "cfg": 7.5,  # Default classifier-free guidance scale
            "guidance_scale": 4.0,  # Default guidance scale
            "random_seed": 1.0,  # Default random seed
            "latent_window_size": 4,  # Default window size
        }

        # Output directory
        self.outputs_folder = os.path.join(
            os.path.expanduser("~"), "airunner_outputs", "framepack"
        )
        os.makedirs(self.outputs_folder, exist_ok=True)

        # Stream for async updates
        self.stream = AsyncFramePackStream()
        self.stream.add_listener(self._handle_stream_update)

        # State tracking
        self.is_generating = False
        self.current_job_id = None
        self.generation_thread = None

    def load(self):
        """Load the FramePack models."""
        try:
            self.change_model_status(ModelType.VIDEO, ModelStatus.LOADING)

            # Using the same logic from demo_gradio.py
            # Load models from Hugging Face
            device_string = "cuda:0" if torch.cuda.is_available() else "cpu"

            self.progress_update.emit(10, "Loading text encoders...")
            self.text_encoder = hunyuan.create_text_encoder(
                device=device_string
            )
            self.text_encoder_2 = hunyuan.create_text_encoder_2(
                device=device_string
            )

            self.progress_update.emit(30, "Loading image encoder...")
            self.image_encoder, self.feature_extractor = (
                clip_vision.create_clip_vision(device=device_string)
            )

            self.progress_update.emit(50, "Loading VAE...")
            self.vae = hunyuan.create_vae(device=device_string)

            self.progress_update.emit(70, "Loading transformer...")
            self.transformer = hunyuan.create_hunyuan_transformer(
                device=device_string
            )

            # Initialize teacache if enabled
            if self.config["use_teacache"]:
                self.progress_update.emit(90, "Initializing teacache...")
                self.transformer.initialize_teacache(enable_teacache=True)

            # Set models to eval mode and disable gradients
            self.text_encoder.eval()
            self.text_encoder_2.eval()
            self.image_encoder.eval()
            self.vae.eval()
            self.transformer.eval()

            # Apply DynamicSwap if not high VRAM mode
            if not self.config["high_vram"]:
                DynamicSwapInstaller.install_model(
                    self.transformer, device=device_string
                )

            self.change_model_status(ModelType.VIDEO, ModelStatus.READY)
            return True

        except Exception as e:
            self.change_model_status(ModelType.VIDEO, ModelStatus.FAILED)
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                f"Failed to load FramePack models: {str(e)}",
            )
            return False

    def unload(self):
        """Unload the FramePack models and free resources."""
        try:
            # If generation is in progress, wait for it to finish or cancel
            if (
                self.is_generating
                and self.generation_thread
                and self.generation_thread.is_alive()
            ):
                # TODO: Add cancellation logic if needed
                self.generation_thread.join(timeout=5)

            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Unload models
            self.text_encoder = None
            self.text_encoder_2 = None
            self.image_encoder = None
            self.feature_extractor = None
            self.vae = None
            self.transformer = None

            self.change_model_status(ModelType.VIDEO, ModelStatus.UNLOADED)
            return True

        except Exception as e:
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                f"Failed to unload FramePack models: {str(e)}",
            )
            return False

    def generate_video(
        self, input_image, prompt, n_prompt="", total_second_length=5, **kwargs
    ):
        """
        Generate a video from an input image and prompt.

        Args:
            input_image: PIL Image or numpy array
            prompt: Text prompt describing the desired video
            n_prompt: Negative prompt to avoid certain elements
            total_second_length: Length of the video in seconds
            **kwargs: Additional arguments to override defaults

        Returns:
            str: Path to the generated video file
        """
        if self.model_status.get(ModelType.VIDEO) != ModelStatus.READY:
            raise RuntimeError(
                "FramePack models are not ready. Load models first."
            )

        if self.is_generating:
            raise RuntimeError("A video generation is already in progress.")

        # Create a unique job ID
        import uuid

        self.current_job_id = f"framepack_{uuid.uuid4().hex[:8]}"

        # Update config with any provided kwargs
        config = self.config.copy()
        for key, value in kwargs.items():
            if key in config:
                config[key] = value

        # Start generation in a separate thread
        self.is_generating = True
        self.generation_thread = threading.Thread(
            target=self._generate_video_thread,
            args=(input_image, prompt, n_prompt, total_second_length, config),
        )
        self.generation_thread.start()

        return self.current_job_id

    def _generate_video_thread(
        self, input_image, prompt, n_prompt, total_second_length, config
    ):
        """Thread function for video generation."""
        try:
            # Convert input image to the expected format
            if isinstance(input_image, Image.Image):
                input_image_np = np.array(input_image)
                input_image_pt = (
                    torch.from_numpy(input_image_np)
                    .permute(2, 0, 1)
                    .unsqueeze(0)
                    .float()
                    / 127.5
                    - 1
                )
            else:
                input_image_np = input_image
                input_image_pt = (
                    torch.from_numpy(input_image_np)
                    .permute(2, 0, 1)
                    .unsqueeze(0)
                    .float()
                    / 127.5
                    - 1
                )

            # Set device
            device_string = "cuda:0" if torch.cuda.is_available() else "cpu"
            gpu = torch.device(device_string)

            # Generate starting latent
            self.stream.push(("progress", (None, "", f"VAE encoding...")))
            start_latent = hunyuan.vae_encode(input_image_pt, self.vae)

            # CLIP Vision encoding
            self.stream.push(
                ("progress", (None, "", f"CLIP Vision encoding..."))
            )
            image_encoder_output = clip_vision.hf_clip_vision_encode(
                input_image_np, self.feature_extractor, self.image_encoder
            )
            image_encoder_last_hidden_state = (
                image_encoder_output.last_hidden_state
            )

            # LLAMA text encoding
            self.stream.push(("progress", (None, "", f"Text encoding...")))
            llama_vec = hunyuan.llama_encode_pre_computer(
                prompt, self.text_encoder, self.text_encoder_2
            )
            llama_vec_n = hunyuan.llama_encode_pre_computer(
                n_prompt, self.text_encoder, self.text_encoder_2
            )

            # CLIP pooler
            clip_l_pooler, clip_l_pooler_n = hunyuan.clip_pooler_compute(
                llama_vec, llama_vec_n
            )

            # Prepare for sampling
            self.stream.push(
                ("progress", (None, "", f"Starting video generation..."))
            )

            # Set random seed
            seed = int(config.get("seed", 42))
            rnd = torch.Generator("cpu").manual_seed(seed)

            latent_window_size = config.get("latent_window_size", 4)
            num_frames = latent_window_size * 4 - 3

            # Setup for image dimensions
            height, width = start_latent.shape[-2], start_latent.shape[-1]

            # Initialize history variables
            history_latents = torch.zeros(
                size=(1, 16, 1 + 2 + 16, height, width), dtype=torch.float32
            ).cpu()
            history_pixels = None
            total_generated_latent_frames = 0

            # Calculate sections for long videos
            fps = 30
            total_latent_frames = int(total_second_length * fps / 4)
            total_latent_sections = max(
                1, (total_latent_frames - 1) // latent_window_size + 1
            )

            # Sampling loop (sections)
            for section_idx in range(total_latent_sections):
                is_last_section = section_idx == total_latent_sections - 1

                self.stream.push(
                    (
                        "progress",
                        (
                            None,
                            "",
                            f"Generating section {section_idx+1}/{total_latent_sections}...",
                        ),
                    )
                )

                # Get section latent
                if section_idx == 0:
                    input_latent = start_latent
                else:
                    # Get from history for continuation
                    input_latent = history_latents[:, :, :1]

                # Prepare generation params
                steps = config.get("steps", 20)
                cfg = config.get("cfg", 7.5)
                gs = config.get("guidance_scale", 4.0)
                rs = config.get("random_seed", 1.0)

                # Generate latents
                generated_latents = hunyuan.generate_hunyuan_video_packed(
                    prompt=prompt,
                    n_prompt=n_prompt,
                    llama_vec=llama_vec,
                    llama_vec_n=llama_vec_n,
                    clip_l_pooler=clip_l_pooler,
                    clip_l_pooler_n=clip_l_pooler_n,
                    image_encoder_last_hidden_state=image_encoder_last_hidden_state,
                    input_latent=input_latent,
                    transformer=self.transformer,
                    latent_window_size=latent_window_size,
                    steps=steps,
                    cfg=cfg,
                    gs=gs,
                    rs=rs,
                    is_last_section=is_last_section,
                    callback=self._callback_wrapper,
                )

                # Process generated latents
                if is_last_section:
                    generated_latents = torch.cat(
                        [
                            start_latent.to(generated_latents),
                            generated_latents,
                        ],
                        dim=2,
                    )

                total_generated_latent_frames += int(
                    generated_latents.shape[2]
                )
                history_latents = torch.cat(
                    [generated_latents.to(history_latents), history_latents],
                    dim=2,
                )

                # Preserve memory if needed
                if config.get(
                    "gpu_memory_preservation", True
                ) and not config.get("high_vram", False):
                    memory_utils.offload_model_from_device_for_memory_preservation(
                        self.transformer,
                        target_device=gpu,
                        preserved_memory_gb=8,
                    )
                    memory_utils.load_model_as_complete(
                        self.vae, target_device=gpu
                    )

                # Decode latents to pixels
                real_history_latents = history_latents[
                    :, :, :total_generated_latent_frames
                ]

                if history_pixels is None:
                    history_pixels = hunyuan.vae_decode(
                        real_history_latents, self.vae
                    ).cpu()
                else:
                    section_latent_frames = (
                        (latent_window_size * 2 + 1)
                        if is_last_section
                        else (latent_window_size * 2)
                    )
                    overlapped_frames = latent_window_size * 4 - 3

                    current_pixels = hunyuan.vae_decode(
                        real_history_latents[:, :, :section_latent_frames],
                        self.vae,
                    ).cpu()
                    history_pixels = hunyuan.soft_append_bcthw(
                        current_pixels, history_pixels, overlapped_frames
                    )

                # Save current progress
                output_filename = os.path.join(
                    self.outputs_folder,
                    f"{self.current_job_id}_{total_generated_latent_frames}.mp4",
                )

                fp_utils.save_bcthw_as_mp4(
                    history_pixels,
                    output_filename,
                    fps=30,
                    crf=config.get("mp4_crf", 23),
                )

                # Emit the current video file
                self.stream.push(("file", output_filename))

                # Check if this is the last section
                if is_last_section:
                    break

            # Final output file
            final_output_filename = os.path.join(
                self.outputs_folder, f"{self.current_job_id}_final.mp4"
            )
            fp_utils.save_bcthw_as_mp4(
                history_pixels,
                final_output_filename,
                fps=30,
                crf=config.get("mp4_crf", 23),
            )

            # Emit completion signal
            self.stream.push(("end", final_output_filename))
            self.video_completed.emit(final_output_filename)

            return final_output_filename

        except Exception as e:
            self.stream.push(("error", str(e)))
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                f"FramePack error: {str(e)}",
            )
            return None

        finally:
            self.is_generating = False
            self.current_job_id = None

    def _callback_wrapper(self, d):
        """Callback function for the hunyuan generator."""
        if d is None:
            return

        step = d.get("step", 0)
        total_steps = d.get("total", 1)

        # Calculate percentage
        percentage = int((step / total_steps) * 100)

        # Create a preview image if available
        preview = d.get("preview")
        if preview is not None:
            # Convert to QPixmap and emit
            from PySide6.QtGui import QImage, QPixmap

            height, width, channel = preview.shape
            q_img = QImage(
                preview.data, width, height, width * 3, QImage.Format_RGB888
            )
            pixmap = QPixmap.fromImage(q_img)
            self.frame_ready.emit(pixmap)

        # Update progress
        desc = f"Step {step}/{total_steps} ({percentage}%)"
        self.progress_update.emit(percentage, desc)

    def _handle_stream_update(self, item):
        """Handle updates from the stream."""
        item_type, item_data = item

        if item_type == "progress":
            preview, desc, progress_html = item_data
            if preview is not None:
                # Convert to QPixmap and emit
                from PySide6.QtGui import QImage, QPixmap

                height, width, channel = preview.shape
                q_img = QImage(
                    preview.data,
                    width,
                    height,
                    width * 3,
                    QImage.Format_RGB888,
                )
                pixmap = QPixmap.fromImage(q_img)
                self.frame_ready.emit(pixmap)

            # Extract percentage from HTML if available
            import re

            percentage = 0
            if progress_html:
                match = re.search(r"(\d+)%", progress_html)
                if match:
                    percentage = int(match.group(1))

            self.progress_update.emit(percentage, desc)

        elif item_type == "file":
            # A new video file is available
            self.video_completed.emit(item_data)

        elif item_type == "error":
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                f"FramePack error: {item_data}",
            )

        elif item_type == "end":
            # Final video is complete
            self.is_generating = False
            if item_data:
                self.video_completed.emit(item_data)
