import os
from typing import Optional

import torch
from diffusers import (
    AutoencoderKL,
    DDPMScheduler,
    UNet2DConditionModel,
    StableDiffusionPipeline,
    StableDiffusionXLPipeline,
)
from transformers import (
    AutoTokenizer,
    CLIPTextModel,
    CLIPTextModelWithProjection,
)

from airunner.components.art.trainers.base import (
    BaseTrainer,
    TrainingConfig,
    logger,
)
from airunner.components.art.trainers.datasets import FolderWithCaptions


class SDTextToImageTrainer(BaseTrainer):
    """Full/UNet-only fine-tuning for SD 1.x style pipelines.

    This class keeps scope minimal for local training:
    - Loads UNet, VAE, and text encoder/tokenizer from a local model folder.
    - Trains UNet on folder images + captions.
    - Saves full pipeline snapshot (UNet + original components references) or
      at least the UNet checkpoint to `output_dir`.
    """

    def __init__(self, config: TrainingConfig):
        super().__init__(config)

    def train(self) -> None:
        cfg = self.config
        device = torch.device(cfg.device)

        # Load components from local model path or single-file checkpoint
        logger.info(
            "Loading model components from: %s", cfg.pretrained_model_path
        )
        tokenizer = None
        tokenizer_2 = None
        text_encoder = None
        text_encoder_2 = None
        is_sdxl = False
        if os.path.isfile(cfg.pretrained_model_path):
            try:
                pipe = StableDiffusionXLPipeline.from_single_file(
                    cfg.pretrained_model_path,
                    torch_dtype=(
                        torch.float16
                        if cfg.mixed_precision == "fp16"
                        else None
                    ),
                    local_files_only=cfg.local_files_only,
                    use_safetensors=True,
                )
                is_sdxl = True
            except Exception:
                pipe = StableDiffusionPipeline.from_single_file(
                    cfg.pretrained_model_path,
                    torch_dtype=(
                        torch.float16
                        if cfg.mixed_precision == "fp16"
                        else None
                    ),
                    local_files_only=cfg.local_files_only,
                    use_safetensors=True,
                )
            tokenizer = pipe.tokenizer
            text_encoder = pipe.text_encoder
            vae = pipe.vae
            unet = pipe.unet
            try:
                noise_scheduler = DDPMScheduler.from_config(
                    pipe.scheduler.config
                )
            except Exception:
                noise_scheduler = DDPMScheduler(num_train_timesteps=1000)
            if is_sdxl:
                tokenizer_2 = pipe.tokenizer_2
                text_encoder_2 = pipe.text_encoder_2
            del pipe
        else:
            # Auto-detect SDXL by presence of the second tokenizer/encoder
            is_sdxl = os.path.exists(
                os.path.join(cfg.pretrained_model_path, "tokenizer_2")
            ) or os.path.exists(
                os.path.join(cfg.pretrained_model_path, "text_encoder_2")
            )

            tokenizer = AutoTokenizer.from_pretrained(
                cfg.pretrained_model_path,
                subfolder="tokenizer",
                use_fast=False,
            )
            text_encoder = CLIPTextModel.from_pretrained(
                cfg.pretrained_model_path, subfolder="text_encoder"
            )
            tokenizer_2 = None
            text_encoder_2 = None
            if is_sdxl:
                tokenizer_2 = AutoTokenizer.from_pretrained(
                    cfg.pretrained_model_path,
                    subfolder="tokenizer_2",
                    use_fast=False,
                )
                text_encoder_2 = CLIPTextModelWithProjection.from_pretrained(
                    cfg.pretrained_model_path, subfolder="text_encoder_2"
                )
            vae = AutoencoderKL.from_pretrained(
                cfg.pretrained_model_path, subfolder="vae"
            )
            unet = UNet2DConditionModel.from_pretrained(
                cfg.pretrained_model_path, subfolder="unet"
            )
            noise_scheduler = DDPMScheduler.from_pretrained(
                cfg.pretrained_model_path, subfolder="scheduler"
            )

        # Freeze VAE and text encoder
        vae.requires_grad_(False)
        text_encoder.requires_grad_(False)

        if cfg.gradient_checkpointing:
            unet.enable_gradient_checkpointing()

        if cfg.mixed_precision in ("fp16", "bf16"):
            unet = self._prepare_precision(unet)
            text_encoder = self._prepare_precision(text_encoder)
            if is_sdxl and text_encoder_2 is not None:
                text_encoder_2 = self._prepare_precision(text_encoder_2)
            vae = self._prepare_precision(vae)

        unet.to(device)
        text_encoder.to(device)
        if is_sdxl and text_encoder_2 is not None:
            text_encoder_2.to(device)
        vae.to(device)

        self._maybe_enable_xformers(unet)

        # Data
        dataset = FolderWithCaptions(
            image_dir=cfg.train_data_dir,
            resolution=cfg.resolution,
            center_crop=cfg.center_crop,
            random_flip=cfg.random_flip,
            caption_key=cfg.caption_column,
            resize_mode=cfg.resize_mode,
            pad_color=cfg.pad_color,
        )
        train_loader = self._compile_dataloader(dataset)

        # Optimizer
        optimizer = torch.optim.AdamW(
            unet.parameters(),
            lr=cfg.learning_rate,
            betas=(cfg.adam_beta1, cfg.adam_beta2),
            eps=cfg.adam_epsilon,
            weight_decay=cfg.weight_decay,
        )

        # Scheduler via torch.optim.lr_scheduler if needed - keep it simple (constant)
        lr_scheduler: Optional[torch.optim.lr_scheduler._LRScheduler]
        lr_scheduler = None

        max_steps = cfg.max_train_steps or 1000
        global_step = 0
        unet.train()
        tokenizer_max_len = tokenizer.model_max_length
        tokenizer2_max_len = (
            tokenizer_2.model_max_length if is_sdxl and tokenizer_2 else None
        )

        scaler = torch.cuda.amp.GradScaler(
            enabled=(cfg.mixed_precision == "fp16")
        )

        while global_step < max_steps:
            for batch in train_loader:
                pixel_values = batch["pixel_values"].to(device)
                with torch.no_grad():
                    latents = vae.encode(pixel_values).latent_dist.sample()
                    scale = getattr(vae.config, "scaling_factor", 0.18215)
                    latents = latents * scale

                noise = torch.randn_like(latents)
                timesteps = torch.randint(
                    0,
                    noise_scheduler.config.num_train_timesteps,
                    (latents.shape[0],),
                    device=device,
                    dtype=torch.long,
                )
                noisy_latents = noise_scheduler.add_noise(
                    latents, noise, timesteps
                )

                captions = batch["caption"]
                # Apply trigger words if configured
                if cfg.trigger_words:
                    if cfg.trigger_mode == "replace":
                        captions = [" ".join(cfg.trigger_words)] * len(
                            captions
                        )
                    elif cfg.trigger_mode == "append":
                        captions = [
                            f"{c} {' '.join(cfg.trigger_words)}"
                            for c in captions
                        ]
                    else:  # prepend
                        captions = [
                            f"{' '.join(cfg.trigger_words)} {c}"
                            for c in captions
                        ]
                if is_sdxl:
                    # SDXL: dual encoders + pooled embeds + time ids
                    inputs_1 = tokenizer(
                        list(captions),
                        padding="max_length",
                        max_length=tokenizer_max_len,
                        truncation=True,
                        return_tensors="pt",
                    )
                    inputs_2 = tokenizer_2(
                        list(captions),
                        padding="max_length",
                        max_length=tokenizer2_max_len,
                        truncation=True,
                        return_tensors="pt",
                    )
                    input_ids_1 = inputs_1.input_ids.to(device)
                    attn_1 = inputs_1.attention_mask.to(device)
                    input_ids_2 = inputs_2.input_ids.to(device)
                    attn_2 = inputs_2.attention_mask.to(device)
                    with torch.no_grad():
                        enc1 = text_encoder(
                            input_ids=input_ids_1,
                            attention_mask=attn_1,
                            output_hidden_states=True,
                            return_dict=True,
                        )
                        enc2 = text_encoder_2(
                            input_ids=input_ids_2,
                            attention_mask=attn_2,
                            output_hidden_states=True,
                            return_dict=True,
                        )
                        prompt_embeds = torch.cat(
                            [enc1.last_hidden_state, enc2.last_hidden_state],
                            dim=-1,
                        )
                        pooled = (
                            enc2.text_embeds
                            if hasattr(enc2, "text_embeds")
                            else (
                                enc2.pooler_output
                                if hasattr(enc2, "pooler_output")
                                else enc2.last_hidden_state.mean(dim=1)
                            )
                        )
                    # SDXL time ids (orig_w, orig_h, crop_w, crop_h, tgt_w, tgt_h)
                    res = cfg.resolution
                    add_time_ids = (
                        torch.tensor(
                            [res, res, 0, 0, res, res],
                            device=device,
                            dtype=prompt_embeds.dtype,
                        )
                        .unsqueeze(0)
                        .repeat(prompt_embeds.size(0), 1)
                    )
                else:
                    inputs = tokenizer(
                        list(captions),
                        padding="max_length",
                        max_length=tokenizer_max_len,
                        truncation=True,
                        return_tensors="pt",
                    )
                    input_ids = inputs.input_ids.to(device)
                    attention_mask = inputs.attention_mask.to(device)
                    with torch.no_grad():
                        encoder_hidden_states = text_encoder(
                            input_ids, attention_mask=attention_mask
                        )[0]

                # Predict the noise
                with torch.autocast(
                    device_type=device.type,
                    dtype=(
                        torch.float16
                        if cfg.mixed_precision == "fp16"
                        else (
                            torch.bfloat16
                            if cfg.mixed_precision == "bf16"
                            else torch.float32
                        )
                    ),
                    enabled=cfg.mixed_precision in ("fp16", "bf16"),
                ):
                    if is_sdxl:
                        model_pred = unet(
                            noisy_latents,
                            timesteps,
                            prompt_embeds,
                            added_cond_kwargs={
                                "text_embeds": pooled,
                                "time_ids": add_time_ids,
                            },
                        ).sample
                    else:
                        model_pred = unet(
                            noisy_latents, timesteps, encoder_hidden_states
                        ).sample
                    target = noise
                    loss = torch.nn.functional.mse_loss(
                        model_pred, target, reduction="mean"
                    )

                scaler.scale(loss).backward()

                if (global_step + 1) % cfg.gradient_accumulation_steps == 0:
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        unet.parameters(), cfg.max_grad_norm
                    )
                    scaler.step(optimizer)
                    scaler.update()
                    optimizer.zero_grad(set_to_none=True)
                    if lr_scheduler is not None:
                        lr_scheduler.step()

                if (
                    cfg.checkpointing_steps
                    and global_step > 0
                    and global_step % cfg.checkpointing_steps == 0
                ):
                    self._save_unet_checkpoint(unet, global_step)

                global_step += 1
                if global_step >= max_steps:
                    break

        # Final save
        self._save_unet_checkpoint(unet, global_step, final=True)

    def _save_unet_checkpoint(
        self, unet: UNet2DConditionModel, step: int, final: bool = False
    ):
        out_dir = os.path.join(
            self.config.output_dir,
            f"checkpoint-{step}" if not final else "final",
        )
        os.makedirs(out_dir, exist_ok=True)
        # Save UNet weights in a subfolder to mirror diffusers layout
        save_dir = os.path.join(out_dir, "unet")
        unet.save_pretrained(
            save_dir, safe_serialization=self._save_safetensors()
        )
        logger.info("Saved UNet checkpoint to %s", save_dir)
