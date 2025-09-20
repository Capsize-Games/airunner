import argparse
import logging
import os
from typing import Optional

from airunner.components.art.trainers import (
    SDLoRATrainer,
    SDTextToImageTrainer,
    TextualInversionTrainer,
    TrainingConfig,
)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train Stable Diffusion: finetune, LoRA, or textual inversion",
    )
    parser.add_argument(
        "mode",
        choices=["finetune", "lora", "textual-inversion"],
        help="Training mode",
    )
    parser.add_argument("--pretrained_model_path", required=True)
    parser.add_argument("--train_data_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument(
        "--logging_dir", default=os.path.join("./logs", "train")
    )
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--train_batch_size", type=int, default=1)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4)
    parser.add_argument("--learning_rate", type=float, default=1e-4)
    parser.add_argument("--max_train_steps", type=int, default=1000)
    parser.add_argument("--checkpointing_steps", type=int, default=500)
    parser.add_argument(
        "--logging_steps",
        type=int,
        default=20,
        help="Log loss/progress every N steps.",
    )
    parser.add_argument(
        "--mixed_precision", choices=["fp16", "bf16", "no"], default="fp16"
    )
    parser.add_argument("--center_crop", action="store_true")
    parser.add_argument("--random_flip", action="store_true")
    parser.add_argument(
        "--resize_mode",
        choices=["crop", "pad"],
        default="crop",
        help="Image resize strategy: crop (default) or pad to square before resize.",
    )
    parser.add_argument(
        "--pad_color",
        type=lambda s: tuple(int(x) for x in s.split(",")),
        default=(255, 255, 255),
        help="Pad color as R,G,B when --resize_mode pad (default 255,255,255).",
    )
    parser.add_argument("--enable_xformers", action="store_true")
    parser.add_argument(
        "--attention_slicing",
        action="store_true",
        help="Enable attention slicing when xFormers is not used.",
    )
    parser.add_argument(
        "--cache_latents",
        action="store_true",
        help="Precompute VAE latents once then free VAE to save memory.",
    )
    parser.add_argument(
        "--unet_gradient_checkpointing",
        action="store_true",
        help="Enable gradient checkpointing on UNet (slower, less memory).",
    )
    parser.add_argument(
        "--channels_last",
        action="store_true",
        help="Convert UNet to channels_last memory format.",
    )
    parser.add_argument(
        "--local_files_only",
        action="store_true",
        help="Do not use network; load weights/config from local cache/files only.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default=None, help="cuda|cpu|auto")
    # LoRA
    parser.add_argument("--lora_rank", type=int, default=4)
    parser.add_argument("--lora_alpha", type=int, default=16)
    parser.add_argument("--lora_dropout", type=float, default=0.0)
    parser.add_argument("--train_text_encoder", action="store_true")
    # Textual inversion
    parser.add_argument("--placeholder_token", default=None)
    parser.add_argument("--initializer_token", default=None)
    parser.add_argument(
        "--num_vectors",
        type=int,
        default=1,
        help="Number of vectors per token for textual inversion. More vectors = larger embedding = better quality but more memory.",
    )
    # Model naming
    parser.add_argument(
        "--model_name",
        default=None,
        help="Custom name for the final model output file (for both LoRA and embeddings).",
    )
    # Trigger words (all modes)
    parser.add_argument(
        "--trigger_word",
        action="append",
        help="Trigger word to inject into each caption. Can be passed multiple times.",
    )
    parser.add_argument(
        "--trigger_mode",
        choices=["prepend", "append", "replace"],
        default="prepend",
        help="How to apply trigger words to captions.",
    )
    # Misc
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def _build_config(args: argparse.Namespace) -> TrainingConfig:
    mp = None if args.mixed_precision == "no" else args.mixed_precision
    device = args.device
    if device in (None, "auto"):
        device = (
            "cuda"
            if os.environ.get("CUDA_VISIBLE_DEVICES", "") != ""
            else "cuda" if _cuda_available() else "cpu"
        )
    # If running on CPU, disable mixed precision to avoid autocast errors
    if device == "cpu" and mp in ("fp16", "bf16"):
        mp = None
    return TrainingConfig(
        pretrained_model_path=args.pretrained_model_path,
        train_data_dir=args.train_data_dir,
        output_dir=args.output_dir,
        logging_dir=args.logging_dir,
        resolution=args.resolution,
        train_batch_size=args.train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        max_train_steps=args.max_train_steps,
        checkpointing_steps=args.checkpointing_steps,
        logging_steps=args.logging_steps,
        mixed_precision=mp,
        center_crop=args.center_crop,
        random_flip=args.random_flip,
        resize_mode=args.resize_mode,
        pad_color=args.pad_color,
        enable_xformers=args.enable_xformers,
        attention_slicing=args.attention_slicing,
        cache_latents=args.cache_latents,
        unet_gradient_checkpointing=args.unet_gradient_checkpointing,
        channels_last=args.channels_last,
        local_files_only=args.local_files_only,
        seed=args.seed,
        device=device,
        lora_rank=args.lora_rank,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        train_text_encoder=args.train_text_encoder,
        placeholder_token=args.placeholder_token,
        initializer_token=args.initializer_token,
        num_vectors=args.num_vectors,
        trigger_words=args.trigger_word,
        trigger_mode=args.trigger_mode,
        model_name=args.model_name,
    )


def _cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


def main() -> None:
    args = _parse_args()
    _setup_logging(args.verbose)
    cfg = _build_config(args)

    if args.mode == "finetune":
        trainer = SDTextToImageTrainer(cfg)
    elif args.mode == "lora":
        trainer = SDLoRATrainer(cfg)
    else:
        if not args.placeholder_token or not args.initializer_token:
            raise SystemExit(
                "textual-inversion requires --placeholder_token and --initializer_token"
            )
        trainer = TextualInversionTrainer(cfg)

    trainer.train()


if __name__ == "__main__":
    main()
