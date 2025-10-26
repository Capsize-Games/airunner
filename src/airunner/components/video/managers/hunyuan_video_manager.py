"""
HunyuanVideo model manager for image-to-video generation.

This manager handles loading and running the HunyuanVideo model with FramePack
for high-quality image-to-video generation.
"""

import os
import uuid
from typing import Dict, Optional, Any
import logging

import torch
import numpy as np
from PIL import Image
from transformers import (
    LlamaModel,
    CLIPTextModel,
    LlamaTokenizerFast,
    CLIPTokenizer,
    SiglipImageProcessor,
    SiglipVisionModel,
)
from diffusers import AutoencoderKLHunyuanVideo

from airunner.components.video.managers.base_video_manager import (
    BaseVideoManager,
)
from airunner.enums import ModelType, SignalCode
from airunner.vendor.framepack.diffusers_helper import (
    bucket_tools,
    clip_vision,
    hunyuan,
    memory as memory_utils,
    utils as general,
)
from airunner.vendor.framepack.diffusers_helper.utils import (
    crop_or_pad_yield_mask,
    resize_and_center_crop,
    soft_append_bcthw,
    save_bcthw_as_mp4,
    generate_timestamp,
)
from airunner.vendor.framepack.diffusers_helper.models.hunyuan_video_packed import (
    HunyuanVideoTransformer3DModelPacked,
)
from airunner.vendor.framepack.diffusers_helper.pipelines.k_diffusion_hunyuan import (
    sample_hunyuan,
)

# Import vendored FramePack modules
from airunner.vendor.framepack.diffusers_helper.memory import (
    DynamicSwapInstaller,
)
import airunner.vendor.framepack.diffusers_helper.bucket_tools as bucket_tools
import airunner.vendor.framepack.diffusers_helper.clip_vision as clip_vision
import airunner.vendor.framepack.diffusers_helper.hunyuan as hunyuan
import airunner.vendor.framepack.diffusers_helper.memory as memory_utils
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


class HunyuanVideoManager(BaseVideoManager):
    """
    Manager for HunyuanVideo image-to-video generation.

    Uses FramePack implementation for high-quality video generation from
    a single input image with text guidance.

    Model Components:
        - Text Encoder: Llama model for text embedding
        - Text Encoder 2: CLIP for additional text features
        - VAE: AutoencoderKLHunyuanVideo for latent encoding/decoding
        - Image Encoder: SiGLIP for vision encoding
        - Transformer: HunyuanVideoTransformer3DModelPacked (main model)

    Attributes:
        model_type: Set to ModelType.HUNYUAN_VIDEO
        text_encoder: Llama text encoder
        text_encoder_2: CLIP text encoder
        tokenizer: Llama tokenizer
        tokenizer_2: CLIP tokenizer
        vae: Video VAE
        image_encoder: SiGLIP image encoder
        feature_extractor: SiGLIP feature extractor
        transformer: Main video transformer model

    Example:
        >>> manager = HunyuanVideoManager()
        >>> manager.load_model()
        >>> output_path = manager.generate_video(
        ...     prompt="A beautiful sunset over the ocean",
        ...     init_image=input_image,
        ...     num_frames=121,  # 4 seconds at 30fps
        ...     callback=progress_callback
        ... )
    """

    model_type = ModelType.HUNYUAN_VIDEO

    # Model identifiers
    HUNYUAN_MODEL_ID = "hunyuanvideo-community/HunyuanVideo"
    FLUX_MODEL_ID = "lllyasviel/flux_redux_bfl"
    TRANSFORMER_MODEL_ID = "lllyasviel/FramePackI2V_HY"

    def __init__(self, *args, **kwargs):
        """Initialize the HunyuanVideo manager."""
        super().__init__(*args, **kwargs)

        # Model components
        self.text_encoder = None
        self.text_encoder_2 = None
        self.tokenizer = None
        self.tokenizer_2 = None
        self.vae = None
        self.image_encoder = None
        self.feature_extractor = None
        self.transformer = None

        # Configuration
        self.high_vram = False
        self.use_teacache = True
        self.gpu_memory_preservation = 6.0
        self.mp4_crf = 23  # Video quality (lower is better)

        # Output directory
        self.outputs_folder = os.path.join(
            os.path.expanduser("~"),
            self.path_settings.base_path,
            "video",
            "hunyuanvideo",
        )
        os.makedirs(self.outputs_folder, exist_ok=True)

        # Cancellation flag
        self._cancel_requested = False

    def _load_model(self, options: Dict[str, Any]) -> bool:
        """
        Load the HunyuanVideo model and all components.

        Args:
            options: Configuration options
                - high_vram: If True, keep models in GPU memory (default: auto-detect)
                - use_teacache: Enable teacache for speedup (default: True)

        Returns:
            True if successful
        """
        try:
            self.logger.info("Loading HunyuanVideo model...")

            # Determine device and memory mode
            device_string = "cuda:0" if torch.cuda.is_available() else "cpu"
            gpu = torch.device(device_string)

            free_mem_gb = memory_utils.get_cuda_free_memory_gb(gpu)
            self.high_vram = options.get("high_vram", free_mem_gb > 60)
            self.use_teacache = options.get("use_teacache", True)

            self.logger.info(f"Free VRAM: {free_mem_gb} GB")
            self.logger.info(f"High-VRAM Mode: {self.high_vram}")

            # Load Text Encoders
            self._emit_progress(10, "Loading text encoders...")
            self.logger.info("Loading text encoders...")

            self.text_encoder = LlamaModel.from_pretrained(
                self.HUNYUAN_MODEL_ID,
                subfolder="text_encoder",
                torch_dtype=torch.float16,
            ).cpu()

            self.text_encoder_2 = CLIPTextModel.from_pretrained(
                self.HUNYUAN_MODEL_ID,
                subfolder="text_encoder_2",
                torch_dtype=torch.float16,
            ).cpu()

            # Load Tokenizers
            self.tokenizer = LlamaTokenizerFast.from_pretrained(
                self.HUNYUAN_MODEL_ID, subfolder="tokenizer"
            )

            self.tokenizer_2 = CLIPTokenizer.from_pretrained(
                self.HUNYUAN_MODEL_ID, subfolder="tokenizer_2"
            )

            # Load VAE
            self._emit_progress(30, "Loading VAE...")
            self.logger.info("Loading VAE...")

            self.vae = AutoencoderKLHunyuanVideo.from_pretrained(
                self.HUNYUAN_MODEL_ID,
                subfolder="vae",
                torch_dtype=torch.float16,
            ).cpu()

            # Load Image Encoder (SiGLIP)
            self._emit_progress(60, "Loading vision encoder...")
            self.logger.info("Loading vision encoder...")

            self.feature_extractor = SiglipImageProcessor.from_pretrained(
                self.FLUX_MODEL_ID, subfolder="feature_extractor"
            )

            self.image_encoder = SiglipVisionModel.from_pretrained(
                self.FLUX_MODEL_ID,
                subfolder="image_encoder",
                torch_dtype=torch.float16,
            ).cpu()

            # Load Transformer
            self._emit_progress(80, "Loading transformer...")
            self.logger.info("Loading transformer...")

            self.transformer = (
                HunyuanVideoTransformer3DModelPacked.from_pretrained(
                    self.TRANSFORMER_MODEL_ID, torch_dtype=torch.bfloat16
                ).cpu()
            )

            # Set models to eval mode
            self.vae.eval()
            self.text_encoder.eval()
            self.text_encoder_2.eval()
            self.image_encoder.eval()
            self.transformer.eval()

            # Apply optimizations
            if not self.high_vram:
                self.vae.enable_slicing()
                self.vae.enable_tiling()
                self.logger.info("VAE slicing/tiling enabled for low VRAM")

            # High quality output
            self.transformer.high_quality_fp32_output_for_inference = True

            # Convert to target dtypes
            self.transformer.to(dtype=torch.bfloat16)
            self.vae.to(dtype=torch.float16)
            self.image_encoder.to(dtype=torch.float16)
            self.text_encoder.to(dtype=torch.float16)
            self.text_encoder_2.to(dtype=torch.float16)

            # Disable gradients
            self.vae.requires_grad_(False)
            self.text_encoder.requires_grad_(False)
            self.text_encoder_2.requires_grad_(False)
            self.image_encoder.requires_grad_(False)
            self.transformer.requires_grad_(False)

            # Initialize teacache if enabled
            if self.use_teacache:
                self._emit_progress(90, "Initializing teacache...")
                self.logger.info("Initializing teacache...")
                self.transformer.initialize_teacache(enable_teacache=True)

            # Move models to GPU if high VRAM mode
            if self.high_vram:
                self.logger.info("Moving models to GPU (High VRAM mode)...")
                self.text_encoder.to(gpu)
                self.text_encoder_2.to(gpu)
                self.image_encoder.to(gpu)
                self.vae.to(gpu)
                self.transformer.to(gpu)
            else:
                # Use DynamicSwap for better memory efficiency
                self.logger.info("Installing DynamicSwap for low VRAM mode...")
                DynamicSwapInstaller.install_model(
                    self.transformer, device=gpu
                )
                DynamicSwapInstaller.install_model(
                    self.text_encoder, device=gpu
                )

            self._emit_progress(100, "Model loaded successfully")
            self.logger.info("HunyuanVideo model loaded successfully")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to load HunyuanVideo model: {e}", exc_info=True
            )
            self._unload_model()
            return False

    def _unload_model(self) -> bool:
        """
        Unload the HunyuanVideo model and free resources.

        Returns:
            True if successful
        """
        try:
            self.logger.info("Unloading HunyuanVideo model...")

            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Unload all components
            self.text_encoder = None
            self.text_encoder_2 = None
            self.tokenizer = None
            self.tokenizer_2 = None
            self.image_encoder = None
            self.feature_extractor = None
            self.vae = None
            self.transformer = None

            # Force garbage collection
            import gc

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self.logger.info("HunyuanVideo model unloaded successfully")
            return True

        except Exception as e:
            self.logger.error(
                f"Error unloading HunyuanVideo model: {e}", exc_info=True
            )
            return False

    def generate_video(self, **kwargs) -> Optional[str]:
        """
        Generate a video from an input image and prompt.

        Args:
            init_image: PIL Image or numpy array (required)
            prompt: Text prompt describing the desired video (required)
            negative_prompt: Negative prompt to avoid certain elements
            num_frames: Total number of frames to generate (default: 121 for 4s @ 30fps)
            fps: Frames per second (default: 30)
            guidance_scale: CFG scale (default: 1.0)
            num_inference_steps: Diffusion steps (default: 25)
            seed: Random seed (default: 42)
            latent_window_size: Window size for generation (default: 9)
            callback: Progress callback function

        Returns:
            Path to generated video file, or None if failed
        """
        # Validate inputs
        init_image = kwargs.get("init_image")
        prompt = kwargs.get("prompt", "")

        if init_image is None:
            self.logger.error("init_image is required for HunyuanVideo")
            return None

        if not prompt:
            self.logger.error("prompt is required for HunyuanVideo")
            return None

        # Prepare generation data
        data = self._prepare_generation_data(**kwargs)

        # Set defaults specific to HunyuanVideo
        negative_prompt = data.get("negative_prompt", "")
        cfg_scale = data.get("guidance_scale", 1.0)
        steps = data.get("num_inference_steps", 25)
        seed = data.get("seed", 42)
        latent_window_size = data.get("latent_window_size", 9)
        num_frames = data.get("num_frames", 121)
        callback = data.get("callback")

        # Calculate video length
        fps = data.get("fps", 30)
        total_second_length = num_frames / fps

        self.logger.info(
            f"Generating {num_frames} frames ({total_second_length}s @ {fps}fps)"
        )
        self.logger.info(f"Prompt: {prompt}")

        # Reset cancellation flag
        self._cancel_requested = False

        try:
            # Device setup
            device_string = "cuda:0" if torch.cuda.is_available() else "cpu"
            gpu = torch.device(device_string)

            # Verify models are loaded
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
                raise RuntimeError("HunyuanVideo models are not fully loaded")

            # Clean GPU memory if using low VRAM mode
            if not self.high_vram:
                memory_utils.unload_complete_models(
                    self.text_encoder,
                    self.text_encoder_2,
                    self.image_encoder,
                    self.vae,
                    self.transformer,
                )

            # Process input image
            self._emit_progress(5, "Processing input image...")

            if isinstance(init_image, Image.Image):
                H, W = init_image.height, init_image.width
                input_image_np = np.array(init_image)
            else:
                H, W, _ = init_image.shape
                input_image_np = init_image

            # Find nearest dimension bucket
            height, width = bucket_tools.find_nearest_bucket(
                H, W, resolution=640
            )
            input_image_np = resize_and_center_crop(
                input_image_np, target_width=width, target_height=height
            )

            # Save input image
            job_id = generate_timestamp()
            Image.fromarray(input_image_np).save(
                os.path.join(self.outputs_folder, f"{job_id}.png")
            )

            # Convert to tensor
            input_image_pt = (
                torch.from_numpy(input_image_np).float() / 127.5 - 1
            )
            input_image_pt = input_image_pt.permute(2, 0, 1)[None, :, None]

            # Text encoding
            self._emit_progress(10, "Encoding text prompts...")

            if not self.high_vram:
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
            if cfg_scale == 1:
                llama_vec_n, clip_l_pooler_n = torch.zeros_like(
                    llama_vec
                ), torch.zeros_like(clip_l_pooler)
            else:
                llama_vec_n, clip_l_pooler_n = hunyuan.encode_prompt_conds(
                    negative_prompt,
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

            # VAE encoding
            self._emit_progress(20, "VAE encoding...")

            if not self.high_vram:
                memory_utils.load_model_as_complete(
                    self.vae, target_device=gpu
                )

            start_latent = hunyuan.vae_encode(input_image_pt.to(gpu), self.vae)

            # CLIP Vision encoding
            self._emit_progress(30, "Vision encoding...")

            if not self.high_vram:
                memory_utils.load_model_as_complete(
                    self.image_encoder, target_device=gpu
                )

            image_encoder_output = clip_vision.hf_clip_vision_encode(
                input_image_np, self.feature_extractor, self.image_encoder
            )
            image_encoder_hidden_states = (
                image_encoder_output.last_hidden_state
            )

            # Convert all tensors to the same dtype
            dtype = self.transformer.dtype
            llama_vec = llama_vec.to(dtype)
            llama_vec_n = llama_vec_n.to(dtype)
            clip_l_pooler = clip_l_pooler.to(dtype)
            clip_l_pooler_n = clip_l_pooler_n.to(dtype)
            image_encoder_hidden_states = image_encoder_hidden_states.to(dtype)

            # Video generation settings
            self._emit_progress(40, "Starting video generation...")

            rnd = torch.Generator("cpu").manual_seed(seed)
            frames_per_section = latent_window_size * 4 - 3

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
                latent_paddings = (
                    [3] + [2] * (total_latent_sections - 3) + [1, 0]
                )
            else:
                latent_paddings = list(reversed(range(total_latent_sections)))

            # Process each section
            for section_idx, latent_padding in enumerate(latent_paddings):
                if self._cancel_requested:
                    self.logger.info("Generation cancelled by user")
                    return None

                is_last_section = latent_padding == 0
                latent_padding_size = latent_padding * latent_window_size

                self.logger.info(
                    f"Processing section {section_idx + 1}/{len(latent_paddings)}: "
                    f"padding={latent_padding_size}, is_last={is_last_section}"
                )

                # Calculate progress
                base_progress = 40 + int(
                    40 * section_idx / len(latent_paddings)
                )
                self._emit_progress(
                    base_progress,
                    f"Generating section {section_idx + 1}/{len(latent_paddings)}...",
                )

                # Prepare indices
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

                # Load transformer if using low VRAM mode
                if not self.high_vram:
                    memory_utils.unload_complete_models()
                    memory_utils.move_model_to_device_with_memory_preservation(
                        self.transformer,
                        target_device=gpu,
                        preserved_memory_gb=self.gpu_memory_preservation,
                    )

                # Initialize TeaCache
                if self.use_teacache:
                    self.transformer.initialize_teacache(
                        enable_teacache=True, num_steps=steps
                    )
                else:
                    self.transformer.initialize_teacache(enable_teacache=False)

                # Define progress callback
                def progress_callback(d):
                    if self._cancel_requested:
                        return

                    current_step = d["i"] + 1
                    step_progress = base_progress + int(
                        30 * current_step / steps / len(latent_paddings)
                    )

                    frames_generated = int(
                        max(0, total_generated_latent_frames * 4 - 3)
                    )
                    time_generated = max(0, frames_generated / 30)

                    self._emit_progress(
                        step_progress,
                        f"Section {section_idx + 1}/{len(latent_paddings)}, "
                        f"Step {current_step}/{steps} - "
                        f"{frames_generated} frames ({time_generated:.2f}s)",
                    )

                    # Emit frame update if available
                    if "denoised" in d:
                        preview = d["denoised"]
                        preview = hunyuan.vae_decode_fake(preview)
                        preview = (
                            (preview * 255.0)
                            .detach()
                            .cpu()
                            .numpy()
                            .clip(0, 255)
                            .astype(np.uint8)
                        )
                        preview_sequence = np.einsum(
                            "bcthu->bhtuc", preview
                        ).squeeze(0)
                        last_frame = preview_sequence[:, -1, :, :]

                        self.emit_signal(
                            SignalCode.VIDEO_FRAME_UPDATE_SIGNAL,
                            {
                                "frame": last_frame,
                                "step": current_step,
                                "total_steps": steps,
                            },
                        )

                # Run diffusion sampling
                distilled_guidance_scale = kwargs.get(
                    "distilled_guidance_scale", 10.0
                )
                generated_latents = sample_hunyuan(
                    transformer=self.transformer,
                    sampler="unipc",
                    width=width,
                    height=height,
                    frames=frames_per_section,
                    real_guidance_scale=cfg_scale,
                    distilled_guidance_scale=distilled_guidance_scale,
                    guidance_rescale=0.0,
                    num_inference_steps=steps,
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
                    callback=progress_callback,
                )

                # Prepend start latent if last section
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

                # Load VAE for decoding
                if not self.high_vram:
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
                    :, :, :total_generated_latent_frames, :, :
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
                    history_pixels = soft_append_bcthw(
                        current_pixels, history_pixels, overlapped_frames
                    )

                # Unload models if using low VRAM mode
                if not self.high_vram:
                    memory_utils.unload_complete_models()

                if is_last_section:
                    break

            # Save final video
            self._emit_progress(90, "Encoding video...")

            final_output_filename = os.path.join(
                self.outputs_folder, f"{job_id}_final.mp4"
            )
            save_bcthw_as_mp4(
                history_pixels,
                final_output_filename,
                fps=fps,
                crf=self.mp4_crf,
            )

            self._emit_progress(100, "Video generation complete!")
            self.logger.info(f"Video saved to: {final_output_filename}")

            return final_output_filename

        except Exception as e:
            self.logger.error(f"Video generation failed: {e}", exc_info=True)
            self.emit_signal(
                SignalCode.VIDEO_GENERATION_FAILED_SIGNAL, {"error": str(e)}
            )
            return None

        finally:
            # Clean up CUDA memory
            if torch.cuda.is_available():
                if not self.high_vram:
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

    def cancel_generation(self):
        """Cancel the current video generation."""
        super().cancel_generation()
        self._cancel_requested = True

    def _emit_progress(self, percent: int, message: str):
        """
        Emit progress update signal.

        Args:
            percent: Progress percentage (0-100)
            message: Status message
        """
        self.emit_signal(
            SignalCode.VIDEO_PROGRESS_SIGNAL,
            {
                "percent": percent,
                "message": message,
                "model_type": self.model_type,
            },
        )
