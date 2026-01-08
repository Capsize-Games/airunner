# Copyright 2025 Alibaba Z-Image Team and The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This file is adapted from the diffusers library for airunner.
# Based on SanaSprintImg2ImgPipeline and ZImagePipeline.

import inspect
from typing import Any, Callable, Dict, List, Optional, Union

import torch
import torch.nn.functional as F
from PIL import Image
from transformers import Qwen2Tokenizer, Qwen2VLForConditionalGeneration

from diffusers.image_processor import PipelineImageInput, VaeImageProcessor
from diffusers.loaders import FromSingleFileMixin
from diffusers.models import AutoencoderKL
from diffusers.pipelines.pipeline_utils import DiffusionPipeline
from diffusers.schedulers import FlowMatchEulerDiscreteScheduler
from diffusers.utils import logging
from diffusers.utils.torch_utils import randn_tensor

from airunner.components.art.pipelines.z_image.pipeline_output import ZImagePipelineOutput
from airunner.components.art.pipelines.z_image.transformer_z_image import ZImageTransformer2DModel
from airunner.components.art.pipelines.z_image.lora_loader import ZImageLoraLoaderMixin


logger = logging.get_logger(__name__)


def calculate_shift(
    image_seq_len,
    base_seq_len: int = 256,
    max_seq_len: int = 4096,
    base_shift: float = 0.5,
    max_shift: float = 1.16,
):
    m = (max_shift - base_shift) / (max_seq_len - base_seq_len)
    b = base_shift - m * base_seq_len
    mu = image_seq_len * m + b
    return mu


def retrieve_timesteps(
    scheduler,
    num_inference_steps: Optional[int] = None,
    device: Optional[Union[str, torch.device]] = None,
    timesteps: Optional[List[int]] = None,
    sigmas: Optional[List[float]] = None,
    **kwargs,
):
    """
    Calls the scheduler's `set_timesteps` method and retrieves timesteps from the scheduler after the call.
    """
    # Filter kwargs to only include parameters accepted by the scheduler's set_timesteps method
    accepted_params = set(inspect.signature(scheduler.set_timesteps).parameters.keys())
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in accepted_params}

    # Propagate sampler behavioral flags from scheduler.config into set_timesteps when supported
    config = getattr(scheduler, "config", {}) or {}
    for flag in ("use_karras_sigmas", "stochastic_sampling"):
        if flag in accepted_params and flag not in filtered_kwargs and flag in config:
            filtered_kwargs[flag] = config.get(flag)
    
    if timesteps is not None and sigmas is not None:
        raise ValueError("Only one of `timesteps` or `sigmas` can be passed.")
    if timesteps is not None:
        accepts_timesteps = "timesteps" in accepted_params
        if not accepts_timesteps:
            raise ValueError(
                f"The current scheduler class {scheduler.__class__}'s `set_timesteps` does not support custom"
                f" timestep schedules."
            )
        scheduler.set_timesteps(timesteps=timesteps, device=device, **filtered_kwargs)
        timesteps = scheduler.timesteps
        num_inference_steps = len(timesteps)
    elif sigmas is not None:
        accept_sigmas = "sigmas" in accepted_params
        if not accept_sigmas:
            raise ValueError(
                f"The current scheduler class {scheduler.__class__}'s `set_timesteps` does not support custom"
                f" sigmas schedules."
            )
        scheduler.set_timesteps(sigmas=sigmas, device=device, **filtered_kwargs)
        timesteps = scheduler.timesteps
        num_inference_steps = len(timesteps)
    else:
        scheduler.set_timesteps(num_inference_steps, device=device, **filtered_kwargs)
        timesteps = scheduler.timesteps
    return timesteps, num_inference_steps


class ZImageImg2ImgPipeline(DiffusionPipeline, FromSingleFileMixin, ZImageLoraLoaderMixin):
    r"""
    The Z-Image pipeline for image-to-image generation.

    This pipeline takes an input image and a text prompt, and generates a new image
    based on both. The `strength` parameter controls how much the output differs from
    the input image.

    Args:
        transformer ([`ZImageTransformer2DModel`]):
            Conditional Transformer (DiT) architecture to denoise the encoded image latents.
        scheduler ([`FlowMatchEulerDiscreteScheduler`]):
            A scheduler to be used in combination with `transformer` to denoise the encoded image latents.
        vae ([`AutoencoderKL`]):
            Variational Auto-Encoder (VAE) Model to encode and decode images to and from latent representations.
        text_encoder ([`Qwen2VLForConditionalGeneration`]):
            [Qwen2-VL](https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct) text encoder.
        tokenizer (`Qwen2Tokenizer`):
            Tokenizer of class Qwen2Tokenizer.
    """

    model_cpu_offload_seq = "text_encoder->transformer->vae"
    _callback_tensor_inputs = ["latents", "prompt_embeds"]

    def __init__(
        self,
        transformer: ZImageTransformer2DModel,
        scheduler: FlowMatchEulerDiscreteScheduler,
        vae: AutoencoderKL,
        text_encoder: Qwen2VLForConditionalGeneration,
        tokenizer: Qwen2Tokenizer,
    ):
        super().__init__()
        self.register_modules(
            transformer=transformer,
            scheduler=scheduler,
            vae=vae,
            text_encoder=text_encoder,
            tokenizer=tokenizer,
        )
        self.vae_scale_factor = 2 ** (len(self.vae.config.block_out_channels) - 1) if getattr(self, "vae", None) else 8
        self.image_processor = VaeImageProcessor(vae_scale_factor=self.vae_scale_factor)
        self.tokenizer_max_length = (
            self.tokenizer.model_max_length if hasattr(self, "tokenizer") and self.tokenizer is not None else 256
        )

    def encode_prompt(
        self,
        prompt: Union[str, List[str]],
        num_images_per_prompt: int = 1,
        device: Optional[torch.device] = None,
        prompt_embeds: Optional[torch.Tensor] = None,
        max_sequence_length: int = 512,
    ):
        """Encodes the prompt into text encoder hidden states."""
        if device is None:
            device = self._execution_device

        if prompt_embeds is not None:
            prompt_embeds = prompt_embeds.to(device=device)
            prompt_embeds = [embed.squeeze(0) for embed in prompt_embeds]
            prompt_embeds = prompt_embeds * num_images_per_prompt
            return prompt_embeds

        if isinstance(prompt, str):
            prompt = [prompt]

        # Apply chat template to prompts (official Z-Image format)
        for i, prompt_item in enumerate(prompt):
            messages = [
                {"role": "user", "content": prompt_item},
            ]
            try:
                prompt_item = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=True,
                )
            except TypeError:
                prompt_item = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            prompt[i] = prompt_item

        all_prompt_embeds = []
        for p in prompt:
            text_inputs = self.tokenizer(
                p,
                padding="max_length",
                max_length=max_sequence_length,
                truncation=True,
                return_tensors="pt",
            )

            text_input_ids = text_inputs.input_ids.to(device)
            attention_mask = text_inputs.attention_mask.to(device).bool()

            with torch.no_grad():
                outputs = self.text_encoder(
                    text_input_ids,
                    attention_mask=attention_mask,
                    output_hidden_states=True,
                    return_dict=True,
                )
                prompt_embed = outputs.hidden_states[-2][0][attention_mask[0]]
                all_prompt_embeds.append(prompt_embed)

        # Repeat for num_images_per_prompt
        all_prompt_embeds = [pe for pe in all_prompt_embeds for _ in range(num_images_per_prompt)]

        return all_prompt_embeds

    def check_inputs(
        self,
        prompt,
        image,
        strength,
        height,
        width,
        callback_on_step_end_tensor_inputs=None,
        prompt_embeds=None,
        max_sequence_length=None,
    ):
        if height % (self.vae_scale_factor * 2):
            raise ValueError(
                f"`height` must be divisible by {self.vae_scale_factor * 2} but is {height}."
            )

        if width % (self.vae_scale_factor * 2):
            raise ValueError(
                f"`width` must be divisible by {self.vae_scale_factor * 2} but is {width}."
            )

        if strength < 0 or strength > 1:
            raise ValueError(f"The value of strength should be in [0.0, 1.0] but is {strength}")

        if callback_on_step_end_tensor_inputs is not None and not all(
            k in self._callback_tensor_inputs for k in callback_on_step_end_tensor_inputs
        ):
            raise ValueError(
                f"`callback_on_step_end_tensor_inputs` has to be in {self._callback_tensor_inputs}"
            )

        if prompt is not None and prompt_embeds is not None:
            raise ValueError(
                f"Cannot forward both `prompt`: {prompt} and `prompt_embeds`: {prompt_embeds}."
            )
        elif prompt is None and prompt_embeds is None:
            raise ValueError(
                "Provide either `prompt` or `prompt_embeds`."
            )
        elif prompt is not None and (not isinstance(prompt, str) and not isinstance(prompt, list)):
            raise ValueError(f"`prompt` has to be of type `str` or `list` but is {type(prompt)}")

        if image is None:
            raise ValueError("Image input is required for img2img pipeline.")

    def prepare_image(
        self,
        image: PipelineImageInput,
        width: int,
        height: int,
        device: torch.device,
        dtype: torch.dtype,
    ):
        """Preprocess and prepare the input image."""
        if isinstance(image, torch.Tensor):
            if image.ndim == 3:
                image = image.unsqueeze(0)
            # Resize if current dimensions do not match target dimensions
            if image.shape[2] != height or image.shape[3] != width:
                image = F.interpolate(image, size=(height, width), mode="bilinear", align_corners=False)
            image = self.image_processor.preprocess(image, height=height, width=width)
        else:
            image = self.image_processor.preprocess(image, height=height, width=width)

        image = image.to(device=device, dtype=dtype)
        return image

    def get_timesteps(self, num_inference_steps: int, strength: float, device: torch.device):
        """Get the timesteps for img2img based on strength."""
        # Calculate the initial timestep based on strength
        init_timestep = min(int(num_inference_steps * strength), num_inference_steps)
        t_start = max(num_inference_steps - init_timestep, 0)
        timesteps = self.scheduler.timesteps[t_start:]
        return timesteps, num_inference_steps - t_start

    def prepare_latents(
        self,
        image: torch.Tensor,
        timestep: torch.Tensor,
        batch_size: int,
        num_channels_latents: int,
        height: int,
        width: int,
        dtype: torch.dtype,
        device: torch.device,
        generator: Optional[torch.Generator] = None,
        latents: Optional[torch.Tensor] = None,
    ):
        """Prepare latents for img2img generation."""
        if latents is not None:
            return latents.to(device=device, dtype=dtype)

        # VAE applies 8x compression, account for packing
        latent_height = 2 * (int(height) // (self.vae_scale_factor * 2))
        latent_width = 2 * (int(width) // (self.vae_scale_factor * 2))
        shape = (batch_size, num_channels_latents, latent_height, latent_width)

        # Encode input image to latents
        if image.shape[1] != num_channels_latents:
            image_latents = self.vae.encode(image).latent_dist.sample(generator)
            image_latents = (image_latents - self.vae.config.shift_factor) * self.vae.config.scaling_factor
        else:
            image_latents = image

        # Expand for batch
        if batch_size > image_latents.shape[0] and batch_size % image_latents.shape[0] == 0:
            additional_image_per_prompt = batch_size // image_latents.shape[0]
            image_latents = torch.cat([image_latents] * additional_image_per_prompt, dim=0)
        elif batch_size > image_latents.shape[0] and batch_size % image_latents.shape[0] != 0:
            raise ValueError(
                f"Cannot duplicate `image` of batch size {image_latents.shape[0]} to {batch_size} text prompts."
            )
        else:
            image_latents = torch.cat([image_latents], dim=0)

        # Add noise to image latents based on timestep
        noise = randn_tensor(shape, generator=generator, device=device, dtype=dtype)
        
        # Scale timestep for noise addition (Z-Image uses 0-1 timesteps)
        t = timestep.item() / 1000.0 if timestep.dim() == 0 else timestep[0].item() / 1000.0
        
        # Interpolate between image latents and noise based on timestep
        # At t=0 (end), we want image_latents; at t=1 (start), we want noise
        latents = (1 - t) * image_latents + t * noise
        
        return latents.to(dtype=torch.float32)

    @property
    def guidance_scale(self):
        return self._guidance_scale

    @property
    def num_timesteps(self):
        return self._num_timesteps

    @property
    def interrupt(self):
        return self._interrupt

    @torch.no_grad()
    def __call__(
        self,
        prompt: Union[str, List[str]] = None,
        image: PipelineImageInput = None,
        strength: float = 0.8,
        height: Optional[int] = None,
        width: Optional[int] = None,
        num_inference_steps: int = 50,
        sigmas: Optional[List[float]] = None,
        guidance_scale: float = 5.0,
        num_images_per_prompt: Optional[int] = 1,
        generator: Optional[Union[torch.Generator, List[torch.Generator]]] = None,
        latents: Optional[torch.Tensor] = None,
        prompt_embeds: Optional[torch.Tensor] = None,
        output_type: Optional[str] = "pil",
        return_dict: bool = True,
        callback_on_step_end: Optional[Callable[[int, int, Dict], None]] = None,
        callback_on_step_end_tensor_inputs: List[str] = ["latents"],
        max_sequence_length: int = 128,
    ):
        r"""
        Function invoked when calling the pipeline for image-to-image generation.

        Args:
            prompt (`str` or `List[str]`, *optional*):
                The prompt or prompts to guide the image generation.
            image (`PipelineImageInput`):
                The input image to transform. Can be a PIL Image, numpy array, or torch Tensor.
            strength (`float`, *optional*, defaults to 0.8):
                Indicates extent to transform the reference `image`. Must be between 0 and 1. A value of 1
                essentially ignores the input image.
            height (`int`, *optional*):
                The height in pixels of the generated image. If None, uses the input image height.
            width (`int`, *optional*):
                The width in pixels of the generated image. If None, uses the input image width.
            num_inference_steps (`int`, *optional*, defaults to 50):
                The number of denoising steps.
            sigmas (`List[float]`, *optional*):
                Custom sigmas for the denoising process.
            guidance_scale (`float`, *optional*, defaults to 5.0):
                Guidance scale for classifier-free guidance.
            num_images_per_prompt (`int`, *optional*, defaults to 1):
                The number of images to generate per prompt.
            generator (`torch.Generator`, *optional*):
                A torch generator for reproducibility.
            latents (`torch.Tensor`, *optional*):
                Pre-generated noisy latents.
            prompt_embeds (`torch.Tensor`, *optional*):
                Pre-generated text embeddings.
            output_type (`str`, *optional*, defaults to `"pil"`):
                Output format: "pil", "np", or "latent".
            return_dict (`bool`, *optional*, defaults to `True`):
                Whether to return a ZImagePipelineOutput.
            callback_on_step_end (`Callable`, *optional*):
                Callback function called at each denoising step.
            callback_on_step_end_tensor_inputs (`List`, *optional*):
                Tensor inputs for the callback.
            max_sequence_length (`int`, *optional*, defaults to 128):
                Maximum sequence length for the prompt.

        Returns:
            [`~pipelines.z_image.ZImagePipelineOutput`] or `tuple`:
                The generated images.
        """
        # Get image dimensions if not provided
        if isinstance(image, Image.Image):
            if height is None:
                height = image.height
            if width is None:
                width = image.width
        elif isinstance(image, torch.Tensor):
            if height is None:
                height = image.shape[-2]
            if width is None:
                width = image.shape[-1]
        
        # Ensure dimensions are divisible by vae_scale_factor * 2
        height = height - (height % (self.vae_scale_factor * 2))
        width = width - (width % (self.vae_scale_factor * 2))

        # 1. Check inputs
        self.check_inputs(
            prompt,
            image,
            strength,
            height,
            width,
            callback_on_step_end_tensor_inputs=callback_on_step_end_tensor_inputs,
            prompt_embeds=prompt_embeds,
            max_sequence_length=max_sequence_length,
        )

        self._guidance_scale = guidance_scale
        self._interrupt = False

        # 2. Define call parameters
        if prompt is not None:
            if isinstance(prompt, str):
                batch_size = 1
            else:
                batch_size = len(prompt)
        else:
            batch_size = prompt_embeds.shape[0]

        device = self._execution_device

        # 3. Preprocess image
        init_image = self.prepare_image(image, width, height, device, self.vae.dtype)

        # 4. Encode prompt
        prompt_embeds = self.encode_prompt(
            prompt=prompt,
            num_images_per_prompt=num_images_per_prompt,
            device=device,
            prompt_embeds=prompt_embeds,
            max_sequence_length=max_sequence_length,
        )

        # 5. Prepare timesteps
        # Calculate image sequence length for shift calculation
        latent_height = 2 * (int(height) // (self.vae_scale_factor * 2))
        latent_width = 2 * (int(width) // (self.vae_scale_factor * 2))
        image_seq_len = (latent_height // 2) * (latent_width // 2)
        
        mu = calculate_shift(
            image_seq_len,
            self.scheduler.config.get("base_image_seq_len", 256),
            self.scheduler.config.get("max_image_seq_len", 4096),
            self.scheduler.config.get("base_shift", 0.5),
            self.scheduler.config.get("max_shift", 1.15),
        )
        self.scheduler.sigma_min = 0.0
        timesteps, num_inference_steps = retrieve_timesteps(
            self.scheduler,
            num_inference_steps,
            device,
            sigmas=sigmas,
            mu=mu,
        )

        # Adjust timesteps based on strength
        timesteps, num_inference_steps = self.get_timesteps(num_inference_steps, strength, device)
        if num_inference_steps < 1:
            raise ValueError(
                f"After adjusting by strength={strength}, num_inference_steps={num_inference_steps} which is < 1."
            )
        latent_timestep = timesteps[:1]

        # 6. Prepare latents
        num_channels_latents = self.transformer.config.in_channels
        actual_batch_size = batch_size * num_images_per_prompt
        latents = self.prepare_latents(
            init_image,
            latent_timestep,
            actual_batch_size,
            num_channels_latents,
            height,
            width,
            torch.float32,
            device,
            generator,
            latents,
        )

        num_warmup_steps = max(len(timesteps) - num_inference_steps * self.scheduler.order, 0)
        self._num_timesteps = len(timesteps)

        # 7. CFG preparation
        if guidance_scale > 1.0:
            uncond_prompt_embeds = self.encode_prompt(
                prompt=[""] * batch_size,
                num_images_per_prompt=num_images_per_prompt,
                device=device,
                max_sequence_length=max_sequence_length,
            )

        # 8. Denoising loop
        with self.progress_bar(total=num_inference_steps) as progress_bar:
            for i, t in enumerate(timesteps):
                if self.interrupt:
                    continue

                # Broadcast to batch dimension
                timestep = t.expand(latents.shape[0])
                timestep = (1000 - timestep) / 1000

                # Run CFG if guidance_scale > 1.0
                apply_cfg = guidance_scale > 1.0
                if apply_cfg:
                    latents_typed = latents.to(self.transformer.dtype)
                    latent_model_input = latents_typed.repeat(2, 1, 1, 1)
                    prompt_embeds_model_input = prompt_embeds + uncond_prompt_embeds
                    timestep_model_input = timestep.repeat(2)
                else:
                    latent_model_input = latents.to(self.transformer.dtype)
                    prompt_embeds_model_input = prompt_embeds
                    timestep_model_input = timestep

                # Add temporal dimension for transformer (5D input)
                latent_model_input = latent_model_input.unsqueeze(2)
                latent_model_input_list = list(latent_model_input.unbind(dim=0))

                # Transformer forward pass
                model_out_list = self.transformer(
                    latent_model_input_list,
                    timestep_model_input,
                    prompt_embeds_model_input,
                )[0]

                if apply_cfg:
                    # Perform CFG
                    pos_out = model_out_list[:actual_batch_size]
                    neg_out = model_out_list[actual_batch_size:]
                    noise_pred = []
                    for j in range(actual_batch_size):
                        pos = pos_out[j].float()
                        neg = neg_out[j].float()
                        pred = pos + guidance_scale * (pos - neg)
                        noise_pred.append(pred)
                    noise_pred = torch.stack(noise_pred, dim=0)
                else:
                    noise_pred = torch.stack([out.float() for out in model_out_list], dim=0)

                # Remove temporal dimension from output
                noise_pred = noise_pred.squeeze(2)
                noise_pred = -noise_pred

                # Compute the previous noisy sample x_t -> x_t-1
                latents = self.scheduler.step(noise_pred.to(torch.float32), t, latents, return_dict=False)[0]
                assert latents.dtype == torch.float32

                if callback_on_step_end is not None:
                    callback_kwargs = {}
                    for k in callback_on_step_end_tensor_inputs:
                        callback_kwargs[k] = locals()[k]
                    callback_outputs = callback_on_step_end(self, i, t, callback_kwargs)

                    latents = callback_outputs.pop("latents", latents)
                    prompt_embeds = callback_outputs.pop("prompt_embeds", prompt_embeds)
                    if apply_cfg:
                        uncond_prompt_embeds = callback_outputs.pop("negative_prompt_embeds", uncond_prompt_embeds)

                # Call the callback, if provided
                if i == len(timesteps) - 1 or ((i + 1) > num_warmup_steps and (i + 1) % self.scheduler.order == 0):
                    progress_bar.update()

        if output_type == "latent":
            if not return_dict:
                return (latents,)
            return ZImagePipelineOutput(images=latents)

        # 9. Decode latents
        latents = latents.to(self.vae.dtype)
        latents = (latents / self.vae.config.scaling_factor) + self.vae.config.shift_factor
        image = self.vae.decode(latents, return_dict=False)[0]
        images = self.image_processor.postprocess(image, output_type=output_type)

        # Offload all models
        self.maybe_free_model_hooks()

        if not return_dict:
            return (images,)

        return ZImagePipelineOutput(images=images)
