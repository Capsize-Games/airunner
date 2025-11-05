"""Video encoding mixin for text and image processing."""

import torch
import numpy as np
from PIL import Image
from typing import Tuple, Any


class VideoEncodingMixin:
    """Mixin for encoding text and images for video generation.

    Handles:
    - Text prompt encoding (Llama + CLIP)
    - Image preprocessing and encoding
    - VAE encoding
    - CLIP Vision encoding

    Dependencies (from parent):
        text_encoder: Llama text encoder
        text_encoder_2: CLIP text encoder
        tokenizer: Llama tokenizer
        tokenizer_2: CLIP tokenizer
        vae: Video VAE
        image_encoder: CLIP vision encoder
        feature_extractor: CLIP feature extractor
        high_vram: Boolean for VRAM mode
        logger: Logger instance
        _emit_progress: Progress callback method
    """

    def _encode_text_prompts(
        self,
        prompt: str,
        negative_prompt: str,
        cfg_scale: float,
        gpu: torch.device,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Encode text prompts using Llama and CLIP.

        Args:
            prompt: Main text prompt
            negative_prompt: Negative prompt
            cfg_scale: Classifier-free guidance scale
            gpu: Target device

        Returns:
            Tuple of (llama_vec, llama_attention_mask, llama_vec_n, llama_attention_mask_n,
                     clip_l_pooler, clip_l_pooler_n)
        """
        from airunner.vendor.framepack.diffusers_helper import (
            hunyuan,
            memory as memory_utils,
        )
        from airunner.vendor.framepack.diffusers_helper.utils import (
            crop_or_pad_yield_mask,
        )

        self._emit_progress(10, "Encoding text prompts...")

        if not self.high_vram:
            memory_utils.fake_diffusers_current_device(self.text_encoder, gpu)
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

        return (
            llama_vec,
            llama_attention_mask,
            llama_vec_n,
            llama_attention_mask_n,
            clip_l_pooler,
            clip_l_pooler_n,
        )

    def _process_and_encode_image(
        self, init_image: Any, height: int, width: int, gpu: torch.device
    ) -> Tuple[torch.Tensor, torch.Tensor, np.ndarray]:
        """Process input image and encode with VAE and CLIP Vision.

        Args:
            init_image: Input PIL Image or numpy array
            height: Target height
            width: Target width
            gpu: Target device

        Returns:
            Tuple of (start_latent, image_encoder_hidden_states, input_image_np)
        """
        from airunner.vendor.framepack.diffusers_helper import (
            hunyuan,
            clip_vision,
            memory as memory_utils,
        )
        from airunner.vendor.framepack.diffusers_helper.utils import (
            resize_and_center_crop,
        )

        self._emit_progress(5, "Processing input image...")

        # Convert to numpy if needed
        if isinstance(init_image, Image.Image):
            input_image_np = np.array(init_image)
        else:
            input_image_np = init_image

        # Resize and crop
        input_image_np = resize_and_center_crop(
            input_image_np, target_width=width, target_height=height
        )

        # Convert to tensor
        input_image_pt = torch.from_numpy(input_image_np).float() / 127.5 - 1
        input_image_pt = input_image_pt.permute(2, 0, 1)[None, :, None]

        # VAE encoding
        self._emit_progress(20, "VAE encoding...")

        if not self.high_vram:
            memory_utils.load_model_as_complete(self.vae, target_device=gpu)

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
        image_encoder_hidden_states = image_encoder_output.last_hidden_state

        return start_latent, image_encoder_hidden_states, input_image_np
