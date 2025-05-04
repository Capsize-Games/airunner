import os
import torch
import numpy as np
from PIL import Image
from typing import Optional, Dict, Any, List
import threading

# --- Use the correct imports based on FramePack implementation ---
from transformers import (
    LlamaModel,
    CLIPTextModel,
    LlamaTokenizerFast,
    CLIPTokenizer,
    SiglipImageProcessor,
    SiglipVisionModel,
)
from diffusers import AutoencoderKLHunyuanVideo

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
from airunner.vendor.framepack.diffusers_helper.models.hunyuan_video_packed import (
    HunyuanVideoTransformer3DModelPacked,
)
from airunner.vendor.framepack.diffusers_helper.pipelines.k_diffusion_hunyuan import (
    sample_hunyuan,
)
from airunner.vendor.framepack.diffusers_helper.utils import (
    save_bcthw_as_mp4,
    crop_or_pad_yield_mask,
    soft_append_bcthw,
    resize_and_center_crop,
    generate_timestamp,
)


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
        self._model_status = {
            ModelType.VIDEO: ModelStatus.UNLOADED,
        }
        super().__init__()
        # Initialize models and tokenizers as None
        self.text_encoder = None
        self.text_encoder_2 = None
        self.tokenizer = None
        self.tokenizer_2 = None
        self.image_encoder = None
        self.feature_extractor = None
        self.transformer = None
        self.vae = None

        # Default configuration
        self.config = {
            "high_vram": False,  # If true, models are kept in memory
            "use_teacache": True,  # For speedup
            "gpu_memory_preservation": 6.0,  # For memory management
            "mp4_crf": 23,  # Video quality (lower is better)
            "steps": 25,  # Default diffusion steps
            "cfg": 1.0,  # Default classifier-free guidance scale
            "guidance_scale": 10.0,  # Default guidance scale
            "random_seed": 1.0,  # Default random seed
            "latent_window_size": 9,  # Default window size
        }

        # Output directory
        self.outputs_folder = os.path.join(
            os.path.expanduser("~"), self.path_settings.base_path, "framepack"
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
            self.logger.info("Starting FramePack model loading...")
            self.change_model_status(ModelType.VIDEO, ModelStatus.LOADING)
            self.logger.info(
                f"Status set to LOADING: {self.model_status.get(ModelType.VIDEO)}"
            )

            device_string = "cuda:0" if torch.cuda.is_available() else "cpu"
            gpu = torch.device(device_string)
            free_mem_gb = memory_utils.get_cuda_free_memory_gb(gpu)
            high_vram = free_mem_gb > 60
            self.config["high_vram"] = high_vram

            self.logger.info(f"Free VRAM: {free_mem_gb} GB")
            self.logger.info(f"High-VRAM Mode: {high_vram}")

            # Based on demo_gradio.py, use the correct model identifiers
            hunyuan_model_id = "hunyuanvideo-community/HunyuanVideo"
            flux_model_id = "lllyasviel/flux_redux_bfl"
            transformer_model_id = "lllyasviel/FramePackI2V_HY"

            # Progress updates
            self.progress_update.emit(10, "Loading Text Encoders...")
            self.logger.info("Loading Text Encoders...")

            # Load Text Encoder (Llama model)
            self.text_encoder = LlamaModel.from_pretrained(
                hunyuan_model_id,
                subfolder="text_encoder",
                torch_dtype=torch.float16,
            ).cpu()
            self.logger.info("Text Encoder 1 loaded.")

            # Load Text Encoder 2 (CLIP)
            self.text_encoder_2 = CLIPTextModel.from_pretrained(
                hunyuan_model_id,
                subfolder="text_encoder_2",
                torch_dtype=torch.float16,
            ).cpu()
            self.logger.info("Text Encoder 2 loaded.")

            # Load Tokenizers
            self.tokenizer = LlamaTokenizerFast.from_pretrained(
                hunyuan_model_id, subfolder="tokenizer"
            )
            self.logger.info("Tokenizer 1 loaded.")

            self.tokenizer_2 = CLIPTokenizer.from_pretrained(
                hunyuan_model_id, subfolder="tokenizer_2"
            )
            self.logger.info("Tokenizer 2 loaded.")

            self.progress_update.emit(30, "Loading VAE...")
            self.logger.info("Loading VAE...")

            # Load VAE
            self.vae = AutoencoderKLHunyuanVideo.from_pretrained(
                hunyuan_model_id, subfolder="vae", torch_dtype=torch.float16
            ).cpu()
            self.logger.info("VAE loaded.")

            self.progress_update.emit(60, "Loading Vision Encoder...")
            self.logger.info("Loading Vision Encoder...")

            # Load Image Encoder (SiGLIP)
            self.feature_extractor = SiglipImageProcessor.from_pretrained(
                flux_model_id, subfolder="feature_extractor"
            )
            self.logger.info("Feature Extractor loaded.")

            self.image_encoder = SiglipVisionModel.from_pretrained(
                flux_model_id,
                subfolder="image_encoder",
                torch_dtype=torch.float16,
            ).cpu()
            self.logger.info("Image Encoder loaded.")

            self.progress_update.emit(80, "Loading Transformer...")
            self.logger.info("Loading Transformer...")

            # Load Transformer (HunyuanDiT)
            self.transformer = (
                HunyuanVideoTransformer3DModelPacked.from_pretrained(
                    transformer_model_id, torch_dtype=torch.bfloat16
                ).cpu()
            )
            self.logger.info("Transformer loaded.")

            # Set models to eval mode
            self.vae.eval()
            self.text_encoder.eval()
            self.text_encoder_2.eval()
            self.image_encoder.eval()
            self.transformer.eval()
            self.logger.info("Models set to eval mode.")

            # Apply optimization settings
            if not high_vram:
                self.vae.enable_slicing()
                self.vae.enable_tiling()
                self.logger.info("VAE slicing/tiling enabled for low VRAM.")

            # High quality output setting
            self.transformer.high_quality_fp32_output_for_inference = True
            self.logger.info("Transformer high quality output enabled.")

            # Convert models to the right dtypes
            self.transformer.to(dtype=torch.bfloat16)
            self.vae.to(dtype=torch.float16)
            self.image_encoder.to(dtype=torch.float16)
            self.text_encoder.to(dtype=torch.float16)
            self.text_encoder_2.to(dtype=torch.float16)
            self.logger.info("Models converted to target dtypes.")

            # Disable gradients
            self.vae.requires_grad_(False)
            self.text_encoder.requires_grad_(False)
            self.text_encoder_2.requires_grad_(False)
            self.image_encoder.requires_grad_(False)
            self.transformer.requires_grad_(False)
            self.logger.info("Gradients disabled for all models.")

            # Initialize teacache if enabled
            if self.config["use_teacache"]:
                self.progress_update.emit(90, "Initializing teacache...")
                self.logger.info("Initializing teacache...")
                self.transformer.initialize_teacache(enable_teacache=True)
                self.logger.info("Teacache initialized.")

            # Move models to GPU if high VRAM mode
            if high_vram:
                self.logger.info("Moving models to GPU (High VRAM mode)...")
                self.text_encoder.to(gpu)
                self.text_encoder_2.to(gpu)
                self.image_encoder.to(gpu)
                self.vae.to(gpu)
                self.transformer.to(gpu)
                self.logger.info("Models moved to GPU.")
            else:
                # Use DynamicSwap for better memory efficiency
                self.logger.info("Installing DynamicSwap for low VRAM mode...")
                DynamicSwapInstaller.install_model(
                    self.transformer, device=gpu
                )
                DynamicSwapInstaller.install_model(
                    self.text_encoder, device=gpu
                )
                self.logger.info("DynamicSwap installed.")

            self.change_model_status(ModelType.VIDEO, ModelStatus.READY)
            self.logger.info(
                f"Status set to READY: {self.model_status.get(ModelType.VIDEO)}"
            )
            self.logger.info("FramePack models loaded successfully.")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to load FramePack models: {str(e)}", exc_info=True
            )
            self.change_model_status(ModelType.VIDEO, ModelStatus.FAILED)
            self.logger.error(
                f"Status set to FAILED: {self.model_status.get(ModelType.VIDEO)}"
            )
            # Clean up partially loaded models
            self.unload()
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

            # Unload models and tokenizers
            self.text_encoder = None
            self.text_encoder_2 = None
            self.tokenizer = None
            self.tokenizer_2 = None
            self.image_encoder = None
            self.feature_extractor = None
            self.vae = None
            self.transformer = None

            # Explicitly delete to help GC, especially with CUDA tensors
            import gc

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self.change_model_status(ModelType.VIDEO, ModelStatus.UNLOADED)
            self.logger.info("FramePack models unloaded.")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to unload FramePack models: {e}", exc_info=True
            )
            self.api.application_error(
                f"Failed to unload FramePack models: {str(e)}"
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
        import uuid
        import traceback

        self.logger.info("generate_video called")

        if self.model_status.get(ModelType.VIDEO) != ModelStatus.READY:
            error_msg = f"FramePack models are not ready. Current status: {self.model_status.get(ModelType.VIDEO)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        if self.is_generating:
            error_msg = "A video generation is already in progress."
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Create a unique job ID
        self.current_job_id = f"framepack_{uuid.uuid4().hex[:8]}"
        self.logger.info(f"Created job ID: {self.current_job_id}")

        # Update config with any provided kwargs
        config = self.config.copy()
        for key, value in kwargs.items():
            if key in config:
                config[key] = value

        self.logger.info(f"Configuration updated with kwargs: {kwargs}")
        self.logger.info(f"Final config: {config}")

        # Start generation in a separate thread
        try:
            self.is_generating = True
            self.logger.info(
                f"Creating video generation thread for job {self.current_job_id}"
            )

            self.generation_thread = threading.Thread(
                target=self._generate_video_thread,
                args=(
                    input_image,
                    prompt,
                    n_prompt,
                    total_second_length,
                    config,
                ),
            )

            self.logger.info("Starting video generation thread")
            self.generation_thread.daemon = True  # Make thread daemonic so it doesn't block application exit
            self.generation_thread.start()
            self.logger.info(
                f"Generation thread started: {self.generation_thread.ident}"
            )

            # Report that the thread has started
            self.api.application_status(
                f"Video generation started: {self.current_job_id}"
            )

            return self.current_job_id

        except Exception as e:
            self.is_generating = False
            self.logger.error(f"Failed to start generation thread: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to start video generation: {str(e)}")

    def _generate_video_thread(
        self, input_image, prompt, n_prompt, total_second_length, config
    ):
        """Thread function for video generation."""
        job_id = generate_timestamp()
        self.stream.push(
            ("progress", (None, "", f"Starting video generation..."))
        )

        try:
            # --- Ensure all models are loaded ---
            if not all(
                [
                    self.text_encoder,
                    self.text_encoder_2,
                    self.tokenizer,
                    self.tokenizer_2,
                    self.vae,
                    self.transformer,
                    self.image_encoder,
                    self.feature_extractor,
                ]
            ):
                raise RuntimeError("FramePack models are not fully loaded.")

            # Clean GPU memory if using low VRAM mode
            if not self.config.get("high_vram", False):
                memory_utils.unload_complete_models(
                    self.text_encoder,
                    self.text_encoder_2,
                    self.image_encoder,
                    self.vae,
                    self.transformer,
                )

            # --- Process input image ---
            device_string = "cuda:0" if torch.cuda.is_available() else "cpu"
            gpu = torch.device(device_string)

            # Get image data
            if isinstance(input_image, Image.Image):
                H, W = input_image.height, input_image.width
                input_image_np = np.array(input_image)
            else:
                H, W, _ = input_image.shape
                input_image_np = input_image

            # Find nearest dimension bucket for optimal processing
            height, width = bucket_tools.find_nearest_bucket(
                H, W, resolution=640
            )
            input_image_np = resize_and_center_crop(
                input_image_np, target_width=width, target_height=height
            )

            # Save input image for reference
            Image.fromarray(input_image_np).save(
                os.path.join(self.outputs_folder, f"{job_id}.png")
            )

            # Convert to tensor format
            input_image_pt = (
                torch.from_numpy(input_image_np).float() / 127.5 - 1
            )
            input_image_pt = input_image_pt.permute(2, 0, 1)[None, :, None]

            # --- Text encoding ---
            self.stream.push(("progress", (None, "", f"Text encoding...")))

            if not self.config.get("high_vram", False):
                memory_utils.fake_diffusers_current_device(
                    self.text_encoder, gpu
                )
                memory_utils.load_model_as_complete(
                    self.text_encoder_2, target_device=gpu
                )

            # Encode prompt
            llama_vec, clip_l_pooler = hunyuan.encode_prompt_conds(
                prompt,
                self.text_encoder,
                self.text_encoder_2,
                self.tokenizer,
                self.tokenizer_2,
            )

            # Encode negative prompt
            cfg_scale = config.get("cfg", 1.0)
            if cfg_scale == 1:
                llama_vec_n, clip_l_pooler_n = torch.zeros_like(
                    llama_vec
                ), torch.zeros_like(clip_l_pooler)
            else:
                llama_vec_n, clip_l_pooler_n = hunyuan.encode_prompt_conds(
                    n_prompt,
                    self.text_encoder,
                    self.text_encoder_2,
                    self.tokenizer,
                    self.tokenizer_2,
                )

            # Process text embeddings
            llama_vec, llama_attention_mask = crop_or_pad_yield_mask(
                llama_vec, length=512
            )
            llama_vec_n, llama_attention_mask_n = crop_or_pad_yield_mask(
                llama_vec_n, length=512
            )

            # --- VAE encoding ---
            self.stream.push(("progress", (None, "", f"VAE encoding...")))

            if not self.config.get("high_vram", False):
                memory_utils.load_model_as_complete(
                    self.vae, target_device=gpu
                )

            start_latent = hunyuan.vae_encode(input_image_pt.to(gpu), self.vae)

            # --- CLIP Vision encoding ---
            self.stream.push(("progress", (None, "", f"Vision encoding...")))

            if not self.config.get("high_vram", False):
                memory_utils.load_model_as_complete(
                    self.image_encoder, target_device=gpu
                )

            image_encoder_output = clip_vision.hf_clip_vision_encode(
                input_image_np, self.feature_extractor, self.image_encoder
            )
            image_encoder_hidden_states = (
                image_encoder_output.last_hidden_state
            )

            # --- Convert all tensors to the same dtype ---
            dtype = self.transformer.dtype
            llama_vec = llama_vec.to(dtype)
            llama_vec_n = llama_vec_n.to(dtype)
            clip_l_pooler = clip_l_pooler.to(dtype)
            clip_l_pooler_n = clip_l_pooler_n.to(dtype)
            image_encoder_hidden_states = image_encoder_hidden_states.to(dtype)

            # --- Video generation settings ---
            self.stream.push(
                ("progress", (None, "", f"Starting video generation..."))
            )

            seed = int(config.get("seed", 42))
            rnd = torch.Generator("cpu").manual_seed(seed)
            latent_window_size = int(config.get("latent_window_size", 9))
            num_frames = latent_window_size * 4 - 3

            # Calculate sections based on video length
            total_latent_sections = int(
                max(
                    round(
                        (total_second_length * 30) / (latent_window_size * 4)
                    ),
                    1,
                )
            )

            # Setup history arrays
            history_latents = torch.zeros(
                size=(1, 16, 1 + 2 + 16, height // 8, width // 8),
                dtype=torch.float32,
            ).cpu()
            history_pixels = None
            total_generated_latent_frames = 0

            # Determine latent padding sequence
            if total_latent_sections > 4:
                # Use padding trick from the original code
                latent_paddings = (
                    [3] + [2] * (total_latent_sections - 3) + [1, 0]
                )
            else:
                latent_paddings = list(reversed(range(total_latent_sections)))

            # Process each section of the video
            for latent_padding in latent_paddings:
                is_last_section = latent_padding == 0
                latent_padding_size = latent_padding * latent_window_size

                self.logger.info(
                    f"Processing section: padding={latent_padding_size}, is_last={is_last_section}"
                )

                # Calculate indices for frame processing
                indices = torch.arange(
                    0,
                    sum(
                        [1, latent_padding_size, latent_window_size, 1, 2, 16]
                    ),
                ).unsqueeze(0)

                (
                    clean_latent_indices_pre,
                    blank_indices,
                    latent_indices,
                    clean_latent_indices_post,
                    clean_latent_2x_indices,
                    clean_latent_4x_indices,
                ) = indices.split(
                    [1, latent_padding_size, latent_window_size, 1, 2, 16],
                    dim=1,
                )

                clean_latent_indices = torch.cat(
                    [clean_latent_indices_pre, clean_latent_indices_post],
                    dim=1,
                )

                # Prepare clean latents
                clean_latents_pre = start_latent.to(history_latents)
                clean_latents_post, clean_latents_2x, clean_latents_4x = (
                    history_latents[:, :, : 1 + 2 + 16, :, :].split(
                        [1, 2, 16], dim=2
                    )
                )
                clean_latents = torch.cat(
                    [clean_latents_pre, clean_latents_post], dim=2
                )

                # Load transformer for this section if using low VRAM mode
                if not self.config.get("high_vram", False):
                    memory_utils.unload_complete_models()
                    memory_utils.move_model_to_device_with_memory_preservation(
                        self.transformer,
                        target_device=gpu,
                        preserved_memory_gb=self.config.get(
                            "gpu_memory_preservation", 6.0
                        ),
                    )

                # Initialize TeaCache for optimization
                if self.config.get("use_teacache", True):
                    self.transformer.initialize_teacache(
                        enable_teacache=True, num_steps=config.get("steps", 25)
                    )
                else:
                    self.transformer.initialize_teacache(enable_teacache=False)

                # Define callback function for progress updates
                def callback(d):
                    preview = d["denoised"]
                    preview = hunyuan.vae_decode_fake(preview)

                    # Convert to viewable format
                    preview = (
                        (preview * 255.0)
                        .detach()
                        .cpu()
                        .numpy()
                        .clip(0, 255)
                        .astype(np.uint8)
                    )
                    # Corrected einsum string: bcthu -> bhtuc
                    preview_sequence = np.einsum(
                        "bcthu->bhtuc", preview
                    ).squeeze(0)

                    # Select the last frame for preview (shape: h, u, c)
                    # Assuming time is the second dimension (index 1) after squeeze
                    last_frame_preview = preview_sequence[:, -1, :, :]

                    current_step = d["i"] + 1
                    steps = config.get("steps", 25)
                    percentage = int(100.0 * current_step / steps)
                    hint = f"Sampling {current_step}/{steps}"
                    desc = (
                        f"Generated frames: {int(max(0, total_generated_latent_frames * 4 - 3))}, "
                        f"Length: {max(0, (total_generated_latent_frames * 4 - 3) / 30):.2f}s"
                    )

                    self.stream.push(
                        (
                            "progress",
                            # Send only the last frame
                            (
                                last_frame_preview,
                                desc,
                                f"{percentage}% - {hint}",
                            ),
                        )
                    )
                    return

                # Run the diffusion sampling
                generated_latents = sample_hunyuan(
                    transformer=self.transformer,
                    sampler="unipc",
                    width=width,
                    height=height,
                    frames=num_frames,
                    real_guidance_scale=config.get("cfg", 1.0),
                    distilled_guidance_scale=config.get(
                        "guidance_scale", 10.0
                    ),
                    guidance_rescale=config.get("random_seed", 0.0),
                    num_inference_steps=config.get("steps", 25),
                    generator=rnd,
                    prompt_embeds=llama_vec,
                    prompt_embeds_mask=llama_attention_mask,
                    prompt_poolers=clip_l_pooler,
                    negative_prompt_embeds=llama_vec_n,
                    negative_prompt_embeds_mask=llama_attention_mask_n,
                    negative_prompt_poolers=clip_l_pooler_n,
                    device=gpu,
                    dtype=dtype,
                    image_embeddings=image_encoder_hidden_states,
                    latent_indices=latent_indices,
                    clean_latents=clean_latents,
                    clean_latent_indices=clean_latent_indices,
                    clean_latents_2x=clean_latents_2x,
                    clean_latent_2x_indices=clean_latent_2x_indices,
                    clean_latents_4x=clean_latents_4x,
                    clean_latent_4x_indices=clean_latent_4x_indices,
                    callback=callback,
                )

                # If last section, prepend the start latent
                if is_last_section:
                    generated_latents = torch.cat(
                        [
                            start_latent.to(generated_latents),
                            generated_latents,
                        ],
                        dim=2,
                    )

                # Update counters and history
                total_generated_latent_frames += int(
                    generated_latents.shape[2]
                )
                history_latents = torch.cat(
                    [generated_latents.to(history_latents), history_latents],
                    dim=2,
                )

                # Load VAE for decoding if using low VRAM mode
                if not self.config.get("high_vram", False):
                    memory_utils.offload_model_from_device_for_memory_preservation(
                        self.transformer,
                        target_device=gpu,
                        preserved_memory_gb=8,
                    )
                    memory_utils.load_model_as_complete(
                        self.vae, target_device=gpu
                    )

                # Get latents for this section and decode
                real_history_latents = history_latents[
                    :, :, :total_generated_latent_frames, :, :
                ]

                # Decode latents to pixels
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
                    history_pixels = soft_append_bcthw(
                        current_pixels, history_pixels, overlapped_frames
                    )

                # Unload models if using low VRAM mode
                if not self.config.get("high_vram", False):
                    memory_utils.unload_complete_models()

                # Save the video for this section
                output_filename = os.path.join(
                    self.outputs_folder,
                    f"{job_id}_{total_generated_latent_frames}.mp4",
                )

                save_bcthw_as_mp4(
                    history_pixels,
                    output_filename,
                    fps=30,
                    crf=config.get("mp4_crf", 23),
                )

                self.logger.info(
                    f"Decoded section. Latent shape {real_history_latents.shape}; pixel shape {history_pixels.shape}"
                )

                # Send update for this section
                self.stream.push(("file", output_filename))

                if is_last_section:
                    break

            # Final video with all sections
            final_output_filename = os.path.join(
                self.outputs_folder, f"{job_id}_final.mp4"
            )
            save_bcthw_as_mp4(
                history_pixels,
                final_output_filename,
                fps=30,
                crf=config.get("mp4_crf", 23),
            )

            self.stream.push(("end", final_output_filename))
            self.video_completed.emit(final_output_filename)

            return final_output_filename

        except Exception as e:
            self.logger.error(
                f"Error during video generation: {str(e)}", exc_info=True
            )
            self.stream.push(("error", str(e)))
            self.api.application_error(f"FramePack error: {str(e)}")
            return None

        finally:
            self.is_generating = False
            self.current_job_id = None

            # Clean up CUDA memory
            if torch.cuda.is_available():
                if not self.config.get("high_vram", False):
                    memory_utils.unload_complete_models(
                        self.text_encoder,
                        self.text_encoder_2,
                        self.image_encoder,
                        self.vae,
                        self.transformer,
                    )
                import gc

                gc.collect()
                torch.cuda.empty_cache()

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

                # Ensure the array is C-contiguous before creating QImage
                if not preview.flags["C_CONTIGUOUS"]:
                    preview = np.ascontiguousarray(preview)

                height, width, channel = preview.shape
                q_img = QImage(
                    preview.data,  # Use the data buffer of the contiguous array
                    width,
                    height,
                    width * 3,  # Bytes per line
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
            self.api.application_error(f"FramePack error: {item_data}")

        elif item_type == "end":
            # Final video is complete
            self.is_generating = False
            if item_data:
                self.video_completed.emit(item_data)
