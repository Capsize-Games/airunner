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
from transformers import (
    AutoTokenizer,
    CLIPTextModel,
    CLIPTextModelWithProjection,
)
from tqdm import tqdm

from airunner.components.art.trainers.base import (
    BaseTrainer,
    TrainingConfig,
    logger,
)
from airunner.components.art.trainers.datasets import FolderWithCaptions


class TextualInversionTrainer(BaseTrainer):
    def cleanup_checkpoints_and_lora(self):
        """Remove all checkpoint and LoRA folders in output_dir after training."""
        import shutil

        out_dir = self.config.output_dir
        for name in os.listdir(out_dir):
            path = os.path.join(out_dir, name)
            if os.path.isdir(path) and (
                name.startswith("checkpoint-") or name.startswith("lora-")
            ):
                shutil.rmtree(path, ignore_errors=True)
                logger.info(f"Deleted folder: {path}")
        # Also remove any leftover 'final' folder from previous runs
        final_dir = os.path.join(out_dir, "final")
        if os.path.isdir(final_dir):
            shutil.rmtree(final_dir, ignore_errors=True)
            logger.info(f"Deleted folder: {final_dir}")

    """Train a learnable embedding for a placeholder token using SD 1.x text encoder.

    Saves learned embeddings to `output_dir/learned_embeds.safetensors`.
    """

    def __init__(self, config: TrainingConfig):
        if not config.placeholder_token or not config.initializer_token:
            raise ValueError(
                "placeholder_token and initializer_token are required for textual inversion"
            )
        super().__init__(config)

    def train(self) -> None:
        cfg = self.config
        device = torch.device(cfg.device)

        logger.info(
            "Loading model components from: %s", cfg.pretrained_model_path
        )
        # Load from folder or single-file
        tokenizer = None
        tokenizer_2 = None
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
            else:
                text_encoder_2 = None
            del pipe
        else:
            tokenizer = AutoTokenizer.from_pretrained(
                cfg.pretrained_model_path,
                subfolder="tokenizer",
                use_fast=False,
            )
            # Detect SDXL (dual encoders)
            is_sdxl = os.path.exists(
                os.path.join(cfg.pretrained_model_path, "tokenizer_2")
            ) or os.path.exists(
                os.path.join(cfg.pretrained_model_path, "text_encoder_2")
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

        vae.requires_grad_(False)
        unet.requires_grad_(False)
        text_encoder.requires_grad_(False)

        if cfg.gradient_checkpointing:
            text_encoder.gradient_checkpointing_enable()
        if cfg.unet_gradient_checkpointing:
            try:
                unet.enable_gradient_checkpointing()
                logger.info("Enabled UNet gradient checkpointing")
            except Exception:
                logger.warning("UNet gradient checkpointing not supported")

        # Move all models to GPU
        vae.to(device)
        unet.to(device)
        text_encoder.to(device)
        if is_sdxl and text_encoder_2 is not None:
            text_encoder_2.to(device)

        # Memory format optimization
        if cfg.channels_last:
            try:
                unet.to(memory_format=torch.channels_last)
                logger.info("Converted UNet to channels_last memory format")
            except Exception:
                logger.warning("channels_last memory format not supported")

        # Enable memory efficient attention / slicing
        from airunner.components.art.trainers.base import BaseTrainer

        BaseTrainer._maybe_enable_xformers(self, unet)  # reuse util

        if cfg.mixed_precision in ("fp16", "bf16"):
            text_encoder = self._prepare_precision(text_encoder)
            if is_sdxl and text_encoder_2 is not None:
                text_encoder_2 = self._prepare_precision(text_encoder_2)
            vae = self._prepare_precision(vae)
            unet = self._prepare_precision(unet)

        # Create a new token and its embedding initialized from an existing token
        num_vectors = cfg.num_vectors
        token = cfg.placeholder_token
        init_token = cfg.initializer_token

        logger.info(f"Creating embedding with {num_vectors} vectors per token")

        # TE1 placeholder
        if token not in tokenizer.get_vocab():
            tokenizer.add_tokens(token)
        token_id = tokenizer.convert_tokens_to_ids(token)
        init_id = tokenizer.convert_tokens_to_ids(init_token)
        text_encoder.resize_token_embeddings(len(tokenizer))
        with torch.no_grad():
            init_embed_te1 = (
                text_encoder.get_input_embeddings()
                .weight[init_id]
                .detach()
                .clone()
            )
        # Create learned embedding on GPU device
        embedder_te1 = text_encoder.get_input_embeddings()
        if num_vectors == 1:
            learned_embed_te1 = torch.nn.Parameter(
                init_embed_te1.to(
                    device=embedder_te1.weight.device,
                    dtype=embedder_te1.weight.dtype,
                )
            )
        else:
            # Create multiple vectors for richer representation
            init_repeated = init_embed_te1.unsqueeze(0).repeat(num_vectors, 1)
            # Add small random noise to each vector to make them different
            noise = torch.randn_like(init_repeated) * 0.01
            learned_embed_te1 = torch.nn.Parameter(
                (init_repeated + noise).to(
                    device=embedder_te1.weight.device,
                    dtype=embedder_te1.weight.dtype,
                )
            )
        # TE2 for SDXL
        learned_embed_te2 = None
        token_id_2 = None
        if is_sdxl and tokenizer_2 is not None and text_encoder_2 is not None:
            if token not in tokenizer_2.get_vocab():
                tokenizer_2.add_tokens(token)

            token_id_2 = tokenizer_2.convert_tokens_to_ids(token)

            init_id_2 = tokenizer_2.convert_tokens_to_ids(init_token)
            text_encoder_2.resize_token_embeddings(len(tokenizer_2))
            with torch.no_grad():
                init_embed_te2 = (
                    text_encoder_2.get_input_embeddings()
                    .weight[init_id_2]
                    .detach()
                    .clone()
                )
            # Create learned embedding on GPU device
            embedder_te2 = text_encoder_2.get_input_embeddings()
            if num_vectors == 1:
                learned_embed_te2 = torch.nn.Parameter(
                    init_embed_te2.to(
                        device=embedder_te2.weight.device,
                        dtype=embedder_te2.weight.dtype,
                    )
                )
            else:
                # Create multiple vectors for richer representation
                init_repeated = init_embed_te2.unsqueeze(0).repeat(
                    num_vectors, 1
                )
                # Add small random noise to each vector to make them different
                noise = torch.randn_like(init_repeated) * 0.01
                learned_embed_te2 = torch.nn.Parameter(
                    (init_repeated + noise).to(
                        device=embedder_te2.weight.device,
                        dtype=embedder_te2.weight.dtype,
                    )
                )

        params = [learned_embed_te1]
        if learned_embed_te2 is not None:
            params.append(learned_embed_te2)
        optimizer = torch.optim.AdamW(
            params,
            lr=cfg.learning_rate,
            betas=(cfg.adam_beta1, cfg.adam_beta2),
            eps=cfg.adam_epsilon,
            weight_decay=0.0,
        )

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

        # Optional: cache latents to save memory/time (single pass VAE encode)
        cached_latents = []
        cached_captions = []
        cached_dataset_size = 0
        if cfg.cache_latents:
            logger.info(
                "Caching VAE latents for the dataset (may take a while)..."
            )
            with torch.no_grad():
                for batch in train_loader:
                    pixel_values = batch["pixel_values"].to(device)
                    vae_dtype = next(vae.parameters()).dtype
                    with torch.amp.autocast(
                        device_type="cuda",
                        enabled=cfg.mixed_precision in ("fp16", "bf16"),
                        dtype=vae_dtype,
                    ):
                        pixel_values = pixel_values.to(vae_dtype)
                        latents = vae.encode(pixel_values).latent_dist.sample()
                        scale = getattr(vae.config, "scaling_factor", 0.18215)
                        latents = latents * scale
                    cached_latents.append(latents.detach().cpu())
                    # batch["caption"] is a str per dataset __getitem__
                    cached_captions.append(batch["caption"])
            cached_dataset_size = len(cached_latents)
            logger.info("Cached %d latent(s)", cached_dataset_size)
            # Free VAE to reclaim memory (not needed after caching)
            del vae
            torch.cuda.empty_cache()

        scaler = torch.amp.GradScaler(
            device="cuda", enabled=(cfg.mixed_precision == "fp16")
        )
        max_steps = cfg.max_train_steps or 1000
        global_step = 0
        start_time = time.time()
        running_loss: float = 0.0
        tokenizer_max_len = tokenizer.model_max_length
        tokenizer2_max_len = (
            tokenizer_2.model_max_length if is_sdxl and tokenizer_2 else None
        )

        logger.info(
            "Starting textual inversion training: max_steps=%d, cache_latents=%s",
            max_steps,
            str(bool(cfg.cache_latents)),
        )
        logger.info(
            "Placeholder token: %s, Initializer token: %s",
            cfg.placeholder_token,
            cfg.initializer_token,
        )
        logger.info("Token ID: %d", token_id)
        if is_sdxl and token_id_2 is not None:
            logger.info("SDXL detected - Token ID 2: %d", token_id_2)
        logger.info("Initial embedding shape: %s", init_embed_te1.shape)
        # Progress bar for steps
        pbar = tqdm(total=max_steps, desc="Training steps", leave=True)
        while global_step < max_steps:
            if cfg.cache_latents:
                # Cycle through cached latents indefinitely until max_steps reached
                idx = global_step % cached_dataset_size
                if cached_dataset_size == 0:
                    raise RuntimeError(
                        "No latents were cached; dataset may be empty."
                    )
                latents = cached_latents[idx].to(device)
                cap = cached_captions[idx]
                # Normalize to a list[str]
                if isinstance(cap, list):
                    captions_batch = cap
                else:
                    captions_batch = [cap]
            else:
                # Fetch a single batch and compute latents on the fly
                for batch in train_loader:
                    pixel_values = batch["pixel_values"].to(device)
                    # Fix: ensure pixel_values dtype matches VAE weights for mixed precision
                    vae_dtype = next(vae.parameters()).dtype
                    with torch.no_grad():
                        with torch.amp.autocast(
                            device_type="cuda",
                            enabled=cfg.mixed_precision in ("fp16", "bf16"),
                            dtype=vae_dtype,
                        ):
                            pixel_values = pixel_values.to(vae_dtype)
                            latents = vae.encode(
                                pixel_values
                            ).latent_dist.sample()
                            scale = getattr(
                                vae.config, "scaling_factor", 0.18215
                            )
                            latents = latents * scale
                    captions_batch = batch["caption"]
                    break  # process one batch per outer loop iteration

            # Common training compute regardless of caching
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

            captions = [
                c.replace("*", token) if isinstance(c, str) else token
                for c in captions_batch
            ]
            # Apply trigger words if configured (combine with placeholder token)
            if cfg.trigger_words:
                if cfg.trigger_mode == "replace":
                    captions = [" ".join(cfg.trigger_words)] * len(captions)
                elif cfg.trigger_mode == "append":
                    captions = [
                        f"{c} {' '.join(cfg.trigger_words)}" for c in captions
                    ]
                else:  # prepend
                    captions = [
                        f"{' '.join(cfg.trigger_words)} {c}" for c in captions
                    ]

            inputs_1 = tokenizer(
                captions,
                padding="max_length",
                max_length=tokenizer_max_len,
                truncation=True,
                return_tensors="pt",
            )
            input_ids_1 = inputs_1.input_ids.to(device)
            attn_1 = inputs_1.attention_mask.to(device)
            if is_sdxl and tokenizer_2 is not None:
                inputs_2 = tokenizer_2(
                    captions,
                    padding="max_length",
                    max_length=tokenizer2_max_len,
                    truncation=True,
                    return_tensors="pt",
                )
                input_ids_2 = inputs_2.input_ids.to(device)
                attn_2 = inputs_2.attention_mask.to(device)

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
                # Temporarily inject learned embeddings into the token embedding weights
                emb_te1 = text_encoder.get_input_embeddings()
                orig_weight_te1 = emb_te1.weight[token_id].clone()

                # Handle both single and multiple vectors
                if num_vectors == 1:
                    emb_te1.weight.data[token_id] = learned_embed_te1.squeeze()
                else:
                    # For multiple vectors, use the mean of all vectors
                    emb_te1.weight.data[token_id] = learned_embed_te1.mean(
                        dim=0
                    )

                enc1 = text_encoder(
                    input_ids=input_ids_1,
                    attention_mask=attn_1,
                    output_hidden_states=True,
                )

                # Restore original weight
                emb_te1.weight.data[token_id] = orig_weight_te1

                if is_sdxl and text_encoder_2 is not None:
                    emb_te2 = text_encoder_2.get_input_embeddings()
                    orig_weight_te2 = emb_te2.weight[token_id_2].clone()

                    # Handle both single and multiple vectors
                    if num_vectors == 1:
                        emb_te2.weight.data[token_id_2] = (
                            learned_embed_te2.squeeze()
                        )
                    else:
                        # For multiple vectors, use the mean of all vectors
                        emb_te2.weight.data[token_id_2] = (
                            learned_embed_te2.mean(dim=0)
                        )

                    enc2 = text_encoder_2(
                        input_ids=input_ids_2,
                        attention_mask=attn_2,
                        output_hidden_states=True,
                    )

                    # Restore original weight
                    emb_te2.weight.data[token_id_2] = orig_weight_te2
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
                    encoder_hidden_states = enc1.last_hidden_state
                    # Important: grads must flow back to inputs
                    model_pred = unet(
                        noisy_latents, timesteps, encoder_hidden_states
                    ).sample

                # Clear GPU cache to free memory instead of moving models
                torch.cuda.empty_cache()
                target = noise
                loss = torch.nn.functional.mse_loss(
                    model_pred, target, reduction="mean"
                )

            # Track loss (pre-accumulation) for logging window
            running_loss += loss.detach().float().item()

            scaler.scale(loss).backward()

            if (global_step + 1) % cfg.gradient_accumulation_steps == 0:
                scaler.unscale_(optimizer)
                clip_params = [learned_embed_te1]
                if learned_embed_te2 is not None:
                    clip_params.append(learned_embed_te2)
                torch.nn.utils.clip_grad_norm_(clip_params, cfg.max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)

            if (
                cfg.checkpointing_steps
                and global_step > 0
                and global_step % cfg.checkpointing_steps == 0
            ):
                self._save_embeddings(
                    learned_embed_te1,
                    tokenizer,
                    token,
                    global_step,
                    learned_embed_te2,
                    tokenizer_2,
                )

            # Periodic logging similar to LoRA trainer
            if (
                cfg.logging_steps
                and global_step > 0
                and global_step % cfg.logging_steps == 0
            ):
                elapsed = time.time() - start_time
                steps_done = max(1, global_step)
                steps_left = max(0, (max_steps - steps_done))
                avg_loss = running_loss / max(1, cfg.logging_steps)
                running_loss = 0.0
                sec_per_step = elapsed / steps_done
                eta_s = int(steps_left * sec_per_step)
                logger.info(
                    "step %d/%d | loss=%.4f | eta=%02d:%02d:%02d",
                    global_step,
                    max_steps,
                    avg_loss,
                    eta_s // 3600,
                    (eta_s % 3600) // 60,
                    eta_s % 60,
                )
                # Log embedding statistics to ensure training is working
                embed_norm = torch.norm(learned_embed_te1).item()
                logger.debug("Embedding norm: %.4f", embed_norm)
                if learned_embed_te2 is not None:
                    embed2_norm = torch.norm(learned_embed_te2).item()
                    logger.debug("Embedding 2 norm: %.4f", embed2_norm)

            # First-step heartbeat
            if global_step == 0:
                logger.info("Step 1 started")
            global_step += 1
            pbar.update(1)
            if global_step >= max_steps:
                break

        pbar.close()
        logger.info(
            "Exited training loop at step %d/%d", global_step, max_steps
        )

        self._save_embeddings(
            learned_embed_te1,
            tokenizer,
            token,
            global_step,
            learned_embed_te2,
            tokenizer_2,
            final=True,
        )
        # Clean up checkpoint and LoRA folders after training
        self.cleanup_checkpoints_and_lora()

    # ...existing code...

    def _save_embeddings(
        self,
        learned_embed_te1: torch.nn.Parameter,
        tokenizer: AutoTokenizer,
        token: str,
        step: int,
        learned_embed_te2: Optional[torch.nn.Parameter] = None,
        tokenizer_2: Optional[AutoTokenizer] = None,
        final: bool = False,
    ) -> None:
        # Prepare tensors and logging
        tensor1 = learned_embed_te1.detach().cpu()

        logger.info(f"TE1 embedding shape: {tensor1.shape}")
        logger.info(f"TE1 embedding dtype: {tensor1.dtype}")
        if learned_embed_te2 is not None:
            tensor2 = learned_embed_te2.detach().cpu()
            logger.info(f"TE2 embedding shape: {tensor2.shape}")
            logger.info(f"TE2 embedding dtype: {tensor2.dtype}")

        model_name = (
            self.config.model_name
            if final and self.config.model_name
            else None
        )

        try:
            from safetensors.torch import save_file

            if final:
                # Final save: single safetensors at output root
                final_filename = f"{model_name or token}.safetensors"

                # Aggregate vectors when multivec
                te1_tensor = (
                    tensor1.squeeze(0)
                    if tensor1.dim() > 1 and self.config.num_vectors == 1
                    else (
                        tensor1.mean(dim=0) if tensor1.dim() > 1 else tensor1
                    )
                )

                data: dict[str, torch.Tensor] = {
                    f"string_to_param/{token}": te1_tensor
                }

                if learned_embed_te2 is not None:
                    te2_cpu = learned_embed_te2.detach().cpu()
                    te2_tensor = (
                        te2_cpu.squeeze(0)
                        if te2_cpu.dim() > 1 and self.config.num_vectors == 1
                        else (
                            te2_cpu.mean(dim=0)
                            if te2_cpu.dim() > 1
                            else te2_cpu
                        )
                    )
                    # SDXL second encoder key
                    data[f"string_to_param_2/{token}"] = te2_tensor

                final_path = os.path.join(
                    self.config.output_dir, final_filename
                )
                save_file(data, final_path)
                logger.info("Saved final embedding to %s", final_path)
                return

            # Not final: checkpoint artifacts (cleaned later)
            out_dir = os.path.join(
                self.config.output_dir, f"checkpoint-{step}"
            )
            os.makedirs(out_dir, exist_ok=True)
            save_file(
                {f"string_to_param/{token}": tensor1},
                os.path.join(out_dir, "learned_embeds_te1.safetensors"),
            )
            if learned_embed_te2 is not None and tokenizer_2 is not None:
                save_file(
                    {
                        f"string_to_param_2/{token}": learned_embed_te2.detach().cpu()
                    },
                    os.path.join(out_dir, "learned_embeds_te2.safetensors"),
                )

        except Exception:
            if final:
                final_filename = f"{(model_name or token)}.pt"
                te1_tensor = (
                    tensor1.squeeze(0)
                    if tensor1.dim() > 1 and self.config.num_vectors == 1
                    else (
                        tensor1.mean(dim=0) if tensor1.dim() > 1 else tensor1
                    )
                )
                if learned_embed_te2 is not None:
                    te2_cpu = learned_embed_te2.detach().cpu()
                    te2_tensor = (
                        te2_cpu.squeeze(0)
                        if te2_cpu.dim() > 1 and self.config.num_vectors == 1
                        else (
                            te2_cpu.mean(dim=0)
                            if te2_cpu.dim() > 1
                            else te2_cpu
                        )
                    )
                    combined = {
                        "string_to_param": {token: te1_tensor},
                        "string_to_param_2": {token: te2_tensor},
                    }
                else:
                    combined = {"string_to_param": {token: te1_tensor}}
                final_path = os.path.join(
                    self.config.output_dir, final_filename
                )
                torch.save(combined, final_path)
                logger.info("Saved final embedding to %s", final_path)
                return

            # Checkpoint fallback
            out_dir = os.path.join(
                self.config.output_dir, f"checkpoint-{step}"
            )
            os.makedirs(out_dir, exist_ok=True)
            torch.save(
                {"string_to_param": {token: tensor1}},
                os.path.join(out_dir, "learned_embeds_te1.pt"),
            )
            if learned_embed_te2 is not None and tokenizer_2 is not None:
                torch.save(
                    {
                        "string_to_param_2": {
                            token: learned_embed_te2.detach().cpu()
                        }
                    },
                    os.path.join(out_dir, "learned_embeds_te2.pt"),
                )

        # For checkpoint saves, write a token file to aid inspection
        if not final:
            os.makedirs(out_dir, exist_ok=True)
            with open(
                os.path.join(out_dir, "token.txt"), "w", encoding="utf-8"
            ) as fh:
                fh.write(token)
            logger.info("Saved textual inversion checkpoint to %s", out_dir)


if __name__ == "__main__":
    # Test configuration
    config = TrainingConfig(
        model_path="/home/joe/Projects/airunner/models/realDream_sdxl1.safetensors",
        dataset_path="/home/joe/Projects/airunner/training_data/joe",
        output_dir="/home/joe/Projects/airunner/test_textual_inversion_output",
        placeholder_token="<joe>",
        initializer_token="person",
        resolution=1024,
        train_batch_size=1,
        learning_rate=1e-4,
        max_train_steps=100,  # Short test
        mixed_precision="fp16",
        save_steps=50,
        checkpointing_steps=50,
        seed=42,
    )

    trainer = TextualInversionTrainer(config)
    trainer.train()
