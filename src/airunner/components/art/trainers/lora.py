import os
import time
from typing import Optional

import torch
from diffusers import (
    AutoencoderKL,
    DDPMScheduler,
    UNet2DConditionModel,
    StableDiffusionPipeline,
    StableDiffusionXLPipeline,
)
from diffusers.optimization import get_scheduler as get_diffusers_scheduler
from diffusers.models.attention_processor import AttnProcessor2_0
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


class SDLoRATrainer(BaseTrainer):
    """LoRA training for Stable Diffusion UNet (optionally text encoder).

    Saves LoRA attention processor weights to `output_dir`.
    """

    def __init__(self, config: TrainingConfig):
        super().__init__(config)

    def train(self) -> None:
        cfg = self.config
        device = torch.device(cfg.device)

        logger.info(
            "Loading model components from: %s", cfg.pretrained_model_path
        )

        tokenizer = None
        tokenizer_2 = None
        text_encoder = None
        text_encoder_2 = None
        vae = None
        unet = None
        noise_scheduler = None
        is_sdxl = False

        if os.path.isfile(cfg.pretrained_model_path):
            # Single-file checkpoint; try SDXL first, then SD1.x
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
            # Extract submodules
            tokenizer = pipe.tokenizer
            text_encoder = pipe.text_encoder
            unet = pipe.unet
            vae = pipe.vae
            if is_sdxl:
                tokenizer_2 = pipe.tokenizer_2
                text_encoder_2 = pipe.text_encoder_2
            # Build a scheduler compatible with training
            try:
                noise_scheduler = DDPMScheduler.from_config(
                    pipe.scheduler.config
                )
            except Exception:
                noise_scheduler = DDPMScheduler(num_train_timesteps=1000)
            del pipe
        else:
            # Diffusers directory layout
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

        vae.requires_grad_(False)
        if not cfg.train_text_encoder:
            text_encoder.requires_grad_(False)
            if is_sdxl and text_encoder_2 is not None:
                text_encoder_2.requires_grad_(False)

        if cfg.gradient_checkpointing:
            unet.enable_gradient_checkpointing()

        # Prepare precision and device
        unet.to(device)
        text_encoder.to(device)
        vae.to(device)
        if is_sdxl and text_encoder_2 is not None:
            text_encoder_2.to(device)
        if cfg.mixed_precision in ("fp16", "bf16"):
            unet = self._prepare_precision(unet)
            text_encoder = self._prepare_precision(text_encoder)
            if is_sdxl and text_encoder_2 is not None:
                text_encoder_2 = self._prepare_precision(text_encoder_2)
            vae = self._prepare_precision(vae)

        self._maybe_enable_xformers(unet)

        # Apply LoRA using diffusers native LoRA adapter system
        if cfg.lora_rank and cfg.lora_rank > 0:
            try:
                # Add LoRA adapter to UNet using diffusers native system
                from peft import LoraConfig

                lora_config = LoraConfig(
                    r=cfg.lora_rank,
                    lora_alpha=cfg.lora_alpha,
                    target_modules=["to_k", "to_q", "to_v", "to_out.0"],
                    lora_dropout=cfg.lora_dropout,
                )

                # Add LoRA layers to UNet using diffusers method
                unet.add_adapter(lora_config, adapter_name="default")

                logger.info(
                    "Applied LoRA adapter to UNet with rank %d, alpha %d.",
                    cfg.lora_rank,
                    cfg.lora_alpha,
                )
            except Exception as e:
                logger.error("LoRA adapter setup failed: %s", e)
                raise RuntimeError(f"Cannot create LoRA adapter: {e}") from e

        # Optional: LoRA on text encoder via PEFT (guarded for CLIP compatibility)
        train_te = cfg.train_text_encoder
        if cfg.train_text_encoder:
            import inspect

            # Some transformers versions for CLIPTextModel do NOT accept `inputs_embeds`.
            # PEFT may route through inputs_embeds, causing runtime errors. Detect and skip.
            te_sig = inspect.signature(text_encoder.forward)
            if "inputs_embeds" not in te_sig.parameters:
                logger.warning(
                    "Disabling text-encoder LoRA: CLIPTextModel.forward lacks 'inputs_embeds' in this env."
                )
                train_te = False
            else:
                try:
                    from peft import LoraConfig, get_peft_model

                    peft_cfg = LoraConfig(
                        r=cfg.lora_rank,
                        lora_alpha=cfg.lora_alpha,
                        lora_dropout=cfg.lora_dropout,
                        bias="none",
                        task_type="FEATURE_EXTRACTION",
                        target_modules=[
                            "q_proj",
                            "k_proj",
                            "v_proj",
                            "out_proj",
                        ],
                    )
                    text_encoder = get_peft_model(text_encoder, peft_cfg)
                    train_te = True
                except Exception as e:
                    logger.warning("Text encoder PEFT LoRA unavailable: %s", e)
                    train_te = False

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

        # Optimizer only LoRA params
        lora_params = [p for p in unet.parameters() if p.requires_grad]
        if train_te:
            lora_params += [
                p for p in text_encoder.parameters() if p.requires_grad
            ]

        optimizer = torch.optim.AdamW(
            lora_params,
            lr=cfg.learning_rate,
            betas=(cfg.adam_beta1, cfg.adam_beta2),
            eps=cfg.adam_epsilon,
            weight_decay=cfg.weight_decay,
        )

        num_update_steps_per_epoch = max(
            1, len(train_loader) // cfg.gradient_accumulation_steps
        )
        max_steps = (
            cfg.max_train_steps
            or cfg.num_train_epochs * num_update_steps_per_epoch
        )
        lr_scheduler = get_diffusers_scheduler(
            name=cfg.lr_scheduler,
            optimizer=optimizer,
            num_warmup_steps=cfg.lr_warmup_steps,
            num_training_steps=max_steps,
        )

        tokenizer_max_len = tokenizer.model_max_length
        tokenizer2_max_len = (
            tokenizer_2.model_max_length if is_sdxl and tokenizer_2 else None
        )
        # AMP/scaler config
        use_fp16 = cfg.mixed_precision == "fp16" and device.type == "cuda"
        use_bf16 = cfg.mixed_precision == "bf16"
        try:
            scaler = torch.amp.GradScaler("cuda", enabled=use_fp16)
        except Exception:
            scaler = torch.cuda.amp.GradScaler(enabled=use_fp16)

        from tqdm import tqdm

        global_step = 0
        running_loss = 0.0
        start_time = time.time()

        logger.info(
            "Training started: steps=%s, batch_size=%s, grad_accum=%s, device=%s, precision=%s",
            max_steps,
            cfg.train_batch_size,
            cfg.gradient_accumulation_steps,
            device.type,
            cfg.mixed_precision or "fp32",
        )

        unet.train()
        if train_te:
            text_encoder.train()
        else:
            text_encoder.eval()

        pbar = tqdm(total=max_steps, desc="LoRA Training Steps", leave=True)
        while global_step < max_steps:
            for batch in train_loader:
                pixel_values = batch["pixel_values"].to(device)
                # Ensure input dtype matches VAE weights to avoid float/half mismatch
                if hasattr(vae, "dtype"):
                    pixel_values = pixel_values.to(dtype=vae.dtype)
                with torch.no_grad():
                    latents = vae.encode(pixel_values).latent_dist.sample()
                    latents = latents * 0.18215

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
                    encoder_hidden_states = text_encoder(
                        input_ids, attention_mask=attention_mask
                    )[0]

                with torch.autocast(
                    device_type=device.type,
                    dtype=(
                        torch.float16
                        if use_fp16
                        else (torch.bfloat16 if use_bf16 else torch.float32)
                    ),
                    enabled=(use_fp16 or use_bf16),
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

                if use_fp16:
                    scaler.scale(loss).backward()
                else:
                    loss.backward()
                running_loss += loss.detach().float().item()

                if (global_step + 1) % cfg.gradient_accumulation_steps == 0:
                    # Gradient clipping
                    if use_fp16:
                        try:
                            scaler.unscale_(optimizer)
                            torch.nn.utils.clip_grad_norm_(
                                lora_params, cfg.max_grad_norm
                            )
                        except Exception as e:
                            logger.warning(
                                "GradScaler unscale/clip skipped: %s", e
                            )
                    else:
                        try:
                            torch.nn.utils.clip_grad_norm_(
                                lora_params, cfg.max_grad_norm
                            )
                        except Exception:
                            pass

                    # Optimizer step
                    if use_fp16:
                        try:
                            scaler.step(optimizer)
                            scaler.update()
                        except Exception as e:
                            logger.warning(
                                "GradScaler step failed (%s); using non-scaled step.",
                                e,
                            )
                            optimizer.step()
                    else:
                        optimizer.step()
                    optimizer.zero_grad(set_to_none=True)
                    lr_scheduler.step()

                if (
                    cfg.checkpointing_steps
                    and global_step > 0
                    and global_step % cfg.checkpointing_steps == 0
                ):
                    self._save_lora_weights(unet, text_encoder, global_step)

                # Periodic logging
                if (
                    cfg.logging_steps
                    and global_step > 0
                    and global_step % cfg.logging_steps == 0
                ):
                    elapsed = time.time() - start_time
                    steps_done = max(1, global_step)
                    steps_left = max(0, (max_steps - steps_done))
                    # Estimate time per step over recent window if possible
                    avg_loss = running_loss / max(1, cfg.logging_steps)
                    running_loss = 0.0
                    # Rough ETA using global avg sec/step
                    sec_per_step = elapsed / steps_done
                    eta_s = int(steps_left * sec_per_step)
                    lr_val = (
                        optimizer.param_groups[0]["lr"]
                        if optimizer.param_groups
                        else cfg.learning_rate
                    )
                    logger.info(
                        "step %d/%d | loss=%.4f | lr=%.6f | eta=%02d:%02d:%02d",
                        global_step,
                        max_steps,
                        avg_loss,
                        lr_val,
                        eta_s // 3600,
                        (eta_s % 3600) // 60,
                        eta_s % 60,
                    )

                global_step += 1
                pbar.update(1)
                if global_step >= max_steps:
                    break

        pbar.close()
        self._save_lora_weights(unet, text_encoder, global_step, final=True)
        total_time = time.time() - start_time
        logger.info(
            "Training complete: steps=%d, time=%dm %ds",
            global_step,
            int(total_time // 60),
            int(total_time % 60),
        )

    def _save_lora_weights(
        self,
        unet: UNet2DConditionModel,
        text_encoder: CLIPTextModel,
        step: int,
        final: bool = False,
    ) -> None:
        out_dir = os.path.join(
            self.config.output_dir,
            f"checkpoint-{step}" if not final else "final",
        )
        os.makedirs(out_dir, exist_ok=True)
        # Save UNet LoRA adapter with proper prefixes for diffusers compatibility
        try:
            import safetensors.torch
            import json

            # First save using UNet's method
            unet.save_lora_adapter(
                out_dir,
                adapter_name="default",
                safe_serialization=self._save_safetensors(),
            )

            # Now read the saved file and add prefixes
            weights_path = os.path.join(
                out_dir, "pytorch_lora_weights.safetensors"
            )
            if os.path.exists(weights_path):
                # Load the raw LoRA weights
                lora_state_dict = safetensors.torch.load_file(weights_path)

                # Add "unet." prefix to all keys for diffusers compatibility
                prefixed_state_dict = {}
                for key, value in lora_state_dict.items():
                    prefixed_key = f"unet.{key}"
                    prefixed_state_dict[prefixed_key] = value

                # Save with proper prefixes
                safetensors.torch.save_file(prefixed_state_dict, weights_path)

            # Create adapter_config.json for diffusers compatibility
            adapter_config = {
                "base_model_name_or_path": self.config.pretrained_model_path,
                "lora_alpha": self.config.lora_alpha,
                "lora_dropout": self.config.lora_dropout,
                "r": self.config.lora_rank,
                "target_modules": ["to_k", "to_q", "to_v", "to_out.0"],
                "task_type": "DIFFUSION",
                "peft_type": "LORA",
            }

            config_path = os.path.join(out_dir, "adapter_config.json")
            with open(config_path, "w") as f:
                json.dump(adapter_config, f, indent=2)

            logger.info("Saved LoRA adapter and config to %s", out_dir)
        except Exception as e:
            logger.error("Failed to save LoRA adapter: %s", e)
            raise
        # Save text encoder adapter if wrapped by PEFT
        if self.config.train_text_encoder:
            try:
                from peft import PeftModel

                if isinstance(text_encoder, PeftModel):
                    text_encoder.save_pretrained(out_dir)
            except Exception:
                pass
        logger.info("Saved LoRA weights to %s", out_dir)

        # Flatten final export for inference convenience
        if final:
            try:
                # Determine the final filename
                if self.config.model_name:
                    flat_name = self.config.model_name
                elif self.config.trigger_words:
                    flat_name = self.config.trigger_words[0]
                else:
                    flat_name = f"lora_{step}"

                flat_file = os.path.join(
                    self.config.output_dir, f"{flat_name}.safetensors"
                )
                # Prefer adapter_model.safetensors if present
                candidate = os.path.join(out_dir, "adapter_model.safetensors")
                copy_source = None
                if os.path.exists(candidate):
                    copy_source = candidate
                else:
                    # Pick any safetensors file in out_dir
                    for f in os.listdir(out_dir):
                        if f.endswith(".safetensors"):
                            copy_source = os.path.join(out_dir, f)
                            break
                if copy_source:
                    if copy_source != flat_file:
                        import shutil

                        shutil.copy2(copy_source, flat_file)
                        logger.info(
                            "Flattened LoRA adapter to %s for inference.",
                            flat_file,
                        )
                        # Also copy adapter_config.json if present so diffusers can load config
                        cfg_src = os.path.join(out_dir, "adapter_config.json")
                        if os.path.exists(cfg_src):
                            cfg_dst = os.path.join(
                                self.config.output_dir, "adapter_config.json"
                            )
                            try:
                                shutil.copy2(cfg_src, cfg_dst)
                                logger.info(
                                    "Copied adapter_config.json alongside flattened adapter."
                                )
                            except Exception as e:  # noqa: BLE001
                                logger.warning(
                                    "Failed copying adapter_config.json: %s", e
                                )
                else:
                    logger.warning(
                        "No safetensors file found in final LoRA directory %s to flatten.",
                        out_dir,
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Failed to flatten final LoRA export for inference: %s", e
                )
