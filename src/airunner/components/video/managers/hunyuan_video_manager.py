"""
HunyuanVideo model manager for image-to-video generation.

This manager handles loading and running the HunyuanVideo model with FramePack
for high-quality image-to-video generation.
"""

import gc
import os
from typing import Dict, Optional, Any

import torch
import numpy as np
from PIL import Image

from airunner.components.video.managers.base_video_manager import (
    BaseVideoManager,
)
from airunner.components.video.managers.mixins import (
    VideoInputValidationMixin,
    VideoEncodingMixin,
    VideoGenerationLoopMixin,
    ModelLifecycleMixin,
)
from airunner.enums import ModelType, SignalCode
from airunner.vendor.framepack.diffusers_helper import (
    bucket_tools,
    memory as memory_utils,
)
from airunner.vendor.framepack.diffusers_helper.utils import (
    resize_and_center_crop,
    generate_timestamp,
)

# Import vendored FramePack modules
import airunner.vendor.framepack.diffusers_helper.bucket_tools as bucket_tools
import airunner.vendor.framepack.diffusers_helper.memory as memory_utils
from airunner.vendor.framepack.diffusers_helper.utils import (
    resize_and_center_crop,
    generate_timestamp,
)


class HunyuanVideoManager(
    VideoInputValidationMixin,
    VideoEncodingMixin,
    VideoGenerationLoopMixin,
    ModelLifecycleMixin,
    BaseVideoManager,
):
    """Manager for HunyuanVideo image-to-video generation.

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

    def __init__(
        self, config: Optional[Dict[str, Any]] = None, *args, **kwargs
    ):
        """Initialize the HunyuanVideo manager.

        Args:
            config: Optional configuration dictionary to override defaults:
                - high_vram: Keep models in GPU memory (default: auto-detect)
                - use_teacache: Enable teacache for speedup (default: True)
                - gpu_memory_preservation: GB to preserve (default: 6.0)
                - mp4_crf: Video quality, lower is better (default: 23)
                - num_inference_steps: Denoising steps (default: 50)
                - guidance_scale: CFG scale (default: 6.0)
        """
        super().__init__(*args, **kwargs)

        # Apply config overrides if provided
        config = config or {}

        # Model components
        self.text_encoder = None
        self.text_encoder_2 = None
        self.tokenizer = None
        self.tokenizer_2 = None
        self.vae = None
        self.image_encoder = None
        self.feature_extractor = None
        self.transformer = None

        # Configuration (with config overrides)
        self.high_vram = config.get("high_vram", False)
        self.use_teacache = config.get("use_teacache", True)
        self.gpu_memory_preservation = config.get(
            "gpu_memory_preservation", 6.0
        )
        self.mp4_crf = config.get("mp4_crf", 23)
        self.num_inference_steps = config.get("num_inference_steps", 50)
        self.guidance_scale = config.get("guidance_scale", 6.0)

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

    def generate_video(self, **kwargs) -> Optional[str]:
        """Generate a video from an input image and prompt.

        Uses mixins to organize the generation pipeline:
        - VideoInputValidationMixin: Input validation
        - VideoEncodingMixin: Text and image encoding
        - VideoGenerationLoopMixin: Iterative generation and saving

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
        # Validate inputs (from VideoInputValidationMixin)
        validated = self._validate_generation_inputs(**kwargs)
        init_image = validated["init_image"]
        prompt = validated["prompt"]
        num_frames = validated["num_frames"]
        fps = validated["fps"]

        # Prepare generation data
        data = self._prepare_generation_data(**kwargs)

        # Set defaults specific to HunyuanVideo
        negative_prompt = data.get("negative_prompt", "")
        cfg_scale = data.get("guidance_scale", 1.0)
        steps = data.get("num_inference_steps", 25)
        seed = data.get("seed", 42)
        latent_window_size = data.get("latent_window_size", 9)

        # Calculate video length
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

            # Get image dimensions (from VideoInputValidationMixin)
            H, W = self._get_image_dimensions(init_image)

            # Find nearest dimension bucket
            height, width = bucket_tools.find_nearest_bucket(
                H, W, resolution=640
            )

            # Save input image
            job_id = generate_timestamp()
            if isinstance(init_image, Image.Image):
                input_image_np = np.array(init_image)
            else:
                input_image_np = init_image

            input_image_resized = resize_and_center_crop(
                input_image_np, target_width=width, target_height=height
            )
            Image.fromarray(input_image_resized).save(
                os.path.join(self.outputs_folder, f"{job_id}.png")
            )

            # Process and encode image (from VideoEncodingMixin)
            start_latent, image_encoder_hidden_states, _ = (
                self._process_and_encode_image(init_image, height, width, gpu)
            )

            # Encode text prompts (from VideoEncodingMixin)
            (
                llama_vec,
                llama_attention_mask,
                llama_vec_n,
                llama_attention_mask_n,
                clip_l_pooler,
                clip_l_pooler_n,
            ) = self._encode_text_prompts(
                prompt, negative_prompt, cfg_scale, gpu
            )

            # Convert all tensors to the same dtype
            dtype = self.transformer.dtype
            llama_vec = llama_vec.to(dtype)
            llama_vec_n = llama_vec_n.to(dtype)
            clip_l_pooler = clip_l_pooler.to(dtype)
            clip_l_pooler_n = clip_l_pooler_n.to(dtype)
            image_encoder_hidden_states = image_encoder_hidden_states.to(dtype)

            # Run generation loop (from VideoGenerationLoopMixin)
            history_pixels = self._run_generation_loop(
                start_latent=start_latent,
                llama_vec=llama_vec,
                llama_attention_mask=llama_attention_mask,
                llama_vec_n=llama_vec_n,
                llama_attention_mask_n=llama_attention_mask_n,
                clip_l_pooler=clip_l_pooler,
                clip_l_pooler_n=clip_l_pooler_n,
                image_encoder_hidden_states=image_encoder_hidden_states,
                height=height,
                width=width,
                total_second_length=total_second_length,
                cfg_scale=cfg_scale,
                steps=steps,
                seed=seed,
                latent_window_size=latent_window_size,
                gpu=gpu,
                dtype=dtype,
                **kwargs,
            )

            if history_pixels is None:
                # Generation was cancelled
                return None

            # Save video (from VideoGenerationLoopMixin)
            return self._save_video(history_pixels, job_id, fps)

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
                "progress": percent,
                "message": message,
                "model_type": self.model_type,
            },
        )
