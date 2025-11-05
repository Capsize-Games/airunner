"""Video generation loop mixin for iterative frame generation."""

import os
import torch
import numpy as np
from typing import Optional


class VideoGenerationLoopMixin:
    """Mixin for video generation loop and post-processing.

    Handles:
    - Iterative latent generation
    - Progress tracking with callbacks
    - VAE decoding
    - Video file saving

    Dependencies (from parent):
        transformer: Video transformer model
        vae: Video VAE
        high_vram: Boolean for VRAM mode
        use_teacache: Boolean for TeaCache optimization
        gpu_memory_preservation: Memory preservation setting
        mp4_crf: MP4 encoding quality
        outputs_folder: Output directory
        _cancel_requested: Cancellation flag
        logger: Logger instance
        _emit_progress: Progress callback method
        emit_signal: Signal emission method
    """

    def _run_generation_loop(
        self,
        start_latent: torch.Tensor,
        llama_vec: torch.Tensor,
        llama_attention_mask: torch.Tensor,
        llama_vec_n: torch.Tensor,
        llama_attention_mask_n: torch.Tensor,
        clip_l_pooler: torch.Tensor,
        clip_l_pooler_n: torch.Tensor,
        image_encoder_hidden_states: torch.Tensor,
        height: int,
        width: int,
        total_second_length: float,
        cfg_scale: float,
        steps: int,
        seed: int,
        latent_window_size: int,
        gpu: torch.device,
        dtype: torch.dtype,
        **kwargs,
    ) -> Optional[torch.Tensor]:
        """Run the main video generation loop.

        Args:
            start_latent: Initial latent from input image
            llama_vec: Text embeddings from Llama
            llama_attention_mask: Attention mask for Llama
            llama_vec_n: Negative text embeddings
            llama_attention_mask_n: Negative attention mask
            clip_l_pooler: CLIP pooled embeddings
            clip_l_pooler_n: Negative CLIP pooled embeddings
            image_encoder_hidden_states: CLIP vision features
            height: Video height
            width: Video width
            total_second_length: Video duration in seconds
            cfg_scale: Classifier-free guidance scale
            steps: Number of diffusion steps
            seed: Random seed
            latent_window_size: Window size for generation
            gpu: Target device
            dtype: Data type for tensors
            **kwargs: Additional parameters

        Returns:
            Tensor with generated video pixels, or None if cancelled
        """
        from airunner.vendor.framepack.diffusers_helper import (
            hunyuan,
            memory as memory_utils,
        )
        from airunner.vendor.framepack.diffusers_helper.pipelines.k_diffusion_hunyuan import (
            sample_hunyuan,
        )
        from airunner.vendor.framepack.diffusers_helper.utils import (
            soft_append_bcthw,
        )
        from airunner.enums import SignalCode

        self._emit_progress(40, "Starting video generation...")

        rnd = torch.Generator("cpu").manual_seed(seed)
        frames_per_section = latent_window_size * 4 - 3

        # Calculate sections based on video length
        total_latent_sections = int(
            max(
                round((total_second_length * 30) / (latent_window_size * 4)),
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
            latent_paddings = [3] + [2] * (total_latent_sections - 3) + [1, 0]
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
            base_progress = 40 + int(40 * section_idx / len(latent_paddings))
            self._emit_progress(
                base_progress,
                f"Generating section {section_idx + 1}/{len(latent_paddings)}...",
            )

            # Prepare indices
            indices = torch.arange(
                0,
                sum([1, latent_padding_size, latent_window_size, 1, 2, 16]),
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
                memory_utils.offload_model_from_device_for_memory_preservation(
                    self.transformer,
                    target_device=gpu,
                    preserved_memory_gb=8,
                )
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
            total_generated_latent_frames += int(generated_latents.shape[2])
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

        return history_pixels

    def _save_video(
        self, history_pixels: torch.Tensor, job_id: str, fps: int
    ) -> str:
        """Save generated video to file.

        Args:
            history_pixels: Generated video pixels
            job_id: Unique job identifier
            fps: Frames per second

        Returns:
            Path to saved video file
        """
        from airunner.vendor.framepack.diffusers_helper.utils import (
            save_bcthw_as_mp4,
        )

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
