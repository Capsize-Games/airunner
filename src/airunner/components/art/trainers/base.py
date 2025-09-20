"""Common training primitives for Diffusers-based trainers.

This module defines the shared TrainingConfig and BaseTrainer used by
fine-tuning, LoRA, and textual inversion trainers.
"""

import logging
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import torch
from torch.utils.data import DataLoader


logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Generic training configuration for all trainers.

    Args:
        pretrained_model_path: Local path to a Diffusers-compatible model folder.
        train_data_dir: Folder containing training images (and optional captions).
        output_dir: Directory to write checkpoints and final outputs.
        logging_dir: Directory for trainer logs.
        device: Compute device, e.g. "cuda" or "cpu".
        mixed_precision: One of None, "fp16", or "bf16".
        gradient_checkpointing: Enable gradient checkpointing on supported modules.
        enable_xformers: Enable xFormers/SDPA attention where available.
        resolution: Target image resolution (square).
        center_crop: If True and resize_mode=="crop", apply CenterCrop.
        random_flip: Random horizontal flip augmentation.
        image_column: Key name for image field in dataset records.
        caption_column: Key name for caption field in dataset records.
        resize_mode: "crop" to resize (and optional center crop) or "pad" to
            pad-to-square then resize.
        pad_color: RGB pad color used when resize_mode == "pad".
        train_batch_size: Per-step batch size.
        gradient_accumulation_steps: Steps to accumulate gradients before update.
        learning_rate: Optimizer learning rate.
        weight_decay: AdamW weight decay.
        max_grad_norm: Gradient clipping value.
        lr_scheduler: LR scheduler name (kept simple/constant by default).
        lr_warmup_steps: Warmup steps for schedulers that support it.
        adam_beta1: Adam beta1.
        adam_beta2: Adam beta2.
        adam_epsilon: Adam epsilon.
        num_train_epochs: Optional epoch budget (alternative to max_train_steps).
        max_train_steps: Max optimization steps.
        checkpointing_steps: Frequency (in steps) to checkpoint.
        seed: Random seed for reproducibility.
        lora_rank: LoRA rank.
        lora_alpha: LoRA alpha.
        lora_dropout: LoRA dropout.
        lora_target_modules: Optional list of target module names for LoRA.
        train_text_encoder: Whether to train text encoder adapters (LoRA).
        placeholder_token: Placeholder token for textual inversion.
        initializer_token: Initializer token whose embedding seeds the placeholder.
        num_vectors: Number of vectors for textual inversion (kept 1 here).
        save_precision: Precision to use when saving weights (None uses model dtype).
        trigger_words: Optional list of trigger words to apply to captions.
        trigger_mode: How to apply trigger words: "prepend"|"append"|"replace".
    """

    # IO
    pretrained_model_path: str
    train_data_dir: str
    output_dir: str
    logging_dir: str = field(default_factory=lambda: os.path.join("./logs"))

    # Compute
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    mixed_precision: Optional[str] = "fp16"  # None|"fp16"|"bf16"
    gradient_checkpointing: bool = True
    enable_xformers: bool = False
    local_files_only: bool = False  # for from_single_file() loads
    # Memory / performance tweaks
    cache_latents: bool = False  # precompute VAE latents & drop VAE
    unet_gradient_checkpointing: bool = False  # reduce UNet activation memory
    attention_slicing: bool = False  # use attention slicing
    channels_last: bool = False  # convert UNet to channels_last

    # Data
    resolution: int = 512
    center_crop: bool = False
    random_flip: bool = False
    image_column: str = "image"
    caption_column: str = "text"
    resize_mode: str = "crop"  # crop|pad
    pad_color: Tuple[int, int, int] = (255, 255, 255)

    # Optim
    train_batch_size: int = 1
    gradient_accumulation_steps: int = 4
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0
    lr_scheduler: str = "constant"
    lr_warmup_steps: int = 0
    adam_beta1: float = 0.9
    adam_beta2: float = 0.999
    adam_epsilon: float = 1e-8

    # Training duration
    num_train_epochs: Optional[int] = None
    max_train_steps: Optional[int] = 1000
    checkpointing_steps: Optional[int] = 500
    logging_steps: int = 20

    # Seed
    seed: Optional[int] = 42

    # Extra knobs for specific trainers
    # LoRA
    lora_rank: int = 4
    lora_alpha: int = 16
    lora_dropout: float = 0.0
    lora_target_modules: Optional[List[str]] = None
    train_text_encoder: bool = False

    # Textual inversion
    placeholder_token: Optional[str] = None
    initializer_token: Optional[str] = None
    num_vectors: int = 1

    # Save
    save_precision: Optional[str] = None  # "fp16"|"bf16"|None uses model dtype

    # Prompt augmentation
    trigger_words: Optional[List[str]] = None  # words to inject into captions
    trigger_mode: str = "prepend"  # prepend|append|replace
    model_name: Optional[str] = None  # Custom name for final output file


class BaseTrainer:
    """Base class for trainers.

    Provides small utilities used by child classes. Subclasses must implement
    train().
    """

    def __init__(self, config: TrainingConfig):
        self.config = config
        if os.path.isfile(self.config.pretrained_model_path):
            logger.info(
                "Using single-file checkpoint: %s",
                self.config.pretrained_model_path,
            )
        os.makedirs(self.config.output_dir, exist_ok=True)
        os.makedirs(self.config.logging_dir, exist_ok=True)

    def _compile_dataloader(self, dataset, shuffle: bool = True) -> DataLoader:
        """Build a default DataLoader.

        Args:
            dataset: PyTorch dataset instance.
            shuffle: Whether to shuffle the dataset.

        Returns:
            A PyTorch DataLoader configured with sensible defaults.
        """
        return DataLoader(
            dataset,
            batch_size=self.config.train_batch_size,
            shuffle=shuffle,
            num_workers=min(8, os.cpu_count() or 1),
            pin_memory=True,
        )

    def _maybe_enable_xformers(self, unet):
        """Enable memory-efficient attention when available.

        Silently continues if xFormers/SDPA is unavailable in the environment.
        """
        if self.config.enable_xformers:
            try:
                unet.enable_xformers_memory_efficient_attention()
                logger.info("Enabled xFormers memory efficient attention")
            except Exception as e:  # pragma: no cover - environment specific
                logger.warning("xFormers not available: %s", e)
        elif self.config.attention_slicing:
            # Fall back to diffusers built-in attention slicing if requested
            try:
                unet.enable_attention_slicing()
                logger.info("Enabled attention slicing")
            except Exception as e:
                logger.warning("Attention slicing not available: %s", e)

    def _prepare_precision(self, module: torch.nn.Module) -> torch.nn.Module:
        """Cast module to the configured dtype for mixed precision.

        Args:
            module: The module to cast.

        Returns:
            The same module cast to half/bfloat16 or left untouched.
        """
        if self.config.mixed_precision == "fp16":
            return module.half()
        if self.config.mixed_precision == "bf16":
            return module.bfloat16()
        return module

    def _global_step_to_epoch(self, step: int, steps_per_epoch: int) -> float:
        """Convert a global step to fractional epoch index.

        Args:
            step: Global optimization step (0-indexed).
            steps_per_epoch: Steps in one epoch.

        Returns:
            A float representing the epoch number.
        """
        return step / max(1, steps_per_epoch)

    def _save_safetensors(self) -> bool:
        """Return True if safetensors is available in the environment."""
        try:
            import safetensors  # noqa: F401

            return True
        except Exception:
            return False

    def train(self) -> None:  # pragma: no cover - abstract
        """Run training. Must be implemented by subclasses."""
        raise NotImplementedError
