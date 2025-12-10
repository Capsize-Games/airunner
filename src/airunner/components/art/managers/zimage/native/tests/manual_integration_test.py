#!/usr/bin/env python3
"""
Manual integration test for Z-Image Native FP8 Pipeline.

This script tests the complete pipeline with an actual FP8 checkpoint.
Run manually to verify memory usage and image generation quality.

Usage:
    python manual_integration_test.py [--checkpoint PATH] [--text-encoder PATH] [--vae PATH]
"""

import argparse
import gc
import os
import sys
import time
from pathlib import Path

import torch
from airunner.components.art.managers.zimage.native import (
    ZImageNativePipeline,
    NativePipelineWrapper,
)
import psutil


def get_memory_stats() -> dict:
    """Get current memory usage statistics."""
    stats = {}
    
    # CPU memory
    if psutil is not None:
        process = psutil.Process(os.getpid())
        stats["cpu_rss_gb"] = process.memory_info().rss / 1024**3
        stats["cpu_vms_gb"] = process.memory_info().vms / 1024**3
    else:
        stats["cpu_rss_gb"] = 0
        stats["cpu_vms_gb"] = 0
    
    # GPU memory
    if torch.cuda.is_available():
        stats["gpu_allocated_gb"] = torch.cuda.memory_allocated() / 1024**3
        stats["gpu_reserved_gb"] = torch.cuda.memory_reserved() / 1024**3
        stats["gpu_max_allocated_gb"] = torch.cuda.max_memory_allocated() / 1024**3
    else:
        stats["gpu_allocated_gb"] = 0
        stats["gpu_reserved_gb"] = 0
        stats["gpu_max_allocated_gb"] = 0
    
    return stats


def print_memory(label: str):
    """Print current memory usage."""
    stats = get_memory_stats()
    print(f"\n=== Memory ({label}) ===")
    print(f"  CPU RSS: {stats['cpu_rss_gb']:.2f} GB")
    print(f"  GPU Allocated: {stats['gpu_allocated_gb']:.2f} GB")
    print(f"  GPU Reserved: {stats['gpu_reserved_gb']:.2f} GB")
    print(f"  GPU Max Allocated: {stats['gpu_max_allocated_gb']:.2f} GB")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the manual test."""
    parser = argparse.ArgumentParser(description="Test Z-Image Native FP8 Pipeline")
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="/home/joe/.local/share/airunner/art/models/Z-Image Turbo/txt2img/zImageTurboQuantized_fp8ScaledE4m3fnKJ.safetensors",
        help="Path to FP8 checkpoint",
    )
    parser.add_argument(
        "--text-encoder",
        type=str,
        default="/home/joe/.local/share/airunner/art/models/Z-Image Turbo/txt2img/text_encoder",
        help="Path to text encoder",
    )
    parser.add_argument(
        "--vae",
        type=str,
        default="/home/joe/.local/share/airunner/art/models/Z-Image Turbo/txt2img/vae",
        help="Path to VAE directory",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="A beautiful sunset over mountains, photorealistic, detailed",
        help="Prompt for image generation",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=6,
        help="Number of inference steps (turbo model works with few steps)",
    )
    parser.add_argument("--width", type=int, default=1024, help="Image width")
    parser.add_argument("--height", type=int, default=1024, help="Image height")
    parser.add_argument("--output", type=str, default="test_output.png", help="Output image path")
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Skip image generation, just test loading",
    )
    return parser.parse_args()


def validate_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    """Validate user-supplied paths and exit early on failure."""
    checkpoint_path = Path(args.checkpoint)
    text_encoder_path = Path(args.text_encoder)
    vae_path = Path(args.vae)

    if not checkpoint_path.exists():
        print(f"ERROR: Checkpoint not found: {checkpoint_path}")
        sys.exit(1)

    if not text_encoder_path.exists():
        print(f"ERROR: Text encoder not found: {text_encoder_path}")
        sys.exit(1)

    return checkpoint_path, text_encoder_path, vae_path


def log_run_header(args: argparse.Namespace, checkpoint_path: Path, text_encoder_path: Path, vae_path: Path):
    """Print initial run metadata and memory stats."""
    print("=" * 60)
    print("Z-Image Native FP8 Pipeline Integration Test")
    print("=" * 60)
    print(f"\nCheckpoint: {checkpoint_path}")
    print(f"Text Encoder: {text_encoder_path}")
    print(f"VAE: {vae_path}")
    device_label = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device_label}")

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

    print_memory("Before loading")


def reset_cuda_counters():
    """Reset CUDA memory tracking if available."""
    if torch.cuda.is_available():
        torch.cuda.reset_max_memory_allocated()


def create_pipeline(device: str) -> ZImageNativePipeline:
    """Instantiate the native pipeline and log timing."""
    print("\n>>> Creating pipeline...")
    start_time = time.time()
    pipeline = ZImageNativePipeline(device=device, dtype=torch.bfloat16)
    print(f"    Creation time: {time.time() - start_time:.2f}s")
    print_memory("After pipeline creation")
    return pipeline


def load_components(
    pipeline: ZImageNativePipeline,
    checkpoint_path: Path,
    text_encoder_path: Path,
    vae_path: Path,
):
    """Load transformer, text encoder, and VAE with timing logs."""
    print("\n>>> Loading FP8 transformer...")
    start_time = time.time()
    pipeline.load_transformer(str(checkpoint_path))
    print(f"    Load time: {time.time() - start_time:.2f}s")
    print_memory("After transformer load")

    print("\n>>> Loading text encoder...")
    start_time = time.time()
    pipeline.load_text_encoder(
        str(text_encoder_path),
        use_4bit=True,
    )
    print(f"    Load time: {time.time() - start_time:.2f}s")
    print_memory("After text encoder load")

    if vae_path.exists() and vae_path.is_dir():
        print("\n>>> Loading VAE...")
        start_time = time.time()
        pipeline.load_vae(str(vae_path))
        print(f"    Load time: {time.time() - start_time:.2f}s")
        print_memory("After VAE load")
    else:
        print(f"\nWARNING: VAE directory not found at {vae_path}, skipping VAE load")


def build_wrapper(pipeline: ZImageNativePipeline) -> NativePipelineWrapper:
    """Create a diffusers-style wrapper around the native pipeline."""
    print("\n>>> Creating pipeline wrapper...")
    wrapper = NativePipelineWrapper(pipeline)
    print(f"    Wrapper created: {wrapper}")
    print(f"    Is native FP8: {wrapper.is_native_fp8}")
    print(f"    Device: {wrapper.device}")
    return wrapper


def maybe_generate(wrapper: NativePipelineWrapper, args: argparse.Namespace) -> None:
    """Optionally generate an image using the wrapper."""
    if args.skip_generation:
        print("\n>>> Skipping generation (--skip-generation flag set)")
        return

    print(f"\n>>> Generating image...")
    print(f"    Prompt: {args.prompt}")
    print(f"    Steps: {args.steps}")
    print(f"    Size: {args.width}x{args.height}")

    start_time = time.time()
    result = wrapper(
        prompt=args.prompt,
        num_inference_steps=args.steps,
        width=args.width,
        height=args.height,
        guidance_scale=1.0,
    )

    generation_time = time.time() - start_time
    print(f"    Generation time: {generation_time:.2f}s")
    print_memory("After generation")

    if hasattr(result, "images") and result.images:
        image = result.images[0]
        output_path = Path(args.output)
        image.save(output_path)
        print(f"\n>>> Image saved to: {output_path}")
        print(f"    Image size: {image.size}")
    else:
        print("\nWARNING: No image in result")


def log_final_stats():
    """Log final memory stats including peak GPU usage."""
    print("\n" + "=" * 60)
    print("FINAL MEMORY STATISTICS")
    print("=" * 60)
    print_memory("Final")
    if torch.cuda.is_available():
        max_mem = torch.cuda.max_memory_allocated() / 1024**3
        print(f"\n  Peak GPU Memory: {max_mem:.2f} GB")


def cleanup(pipeline: ZImageNativePipeline, wrapper: NativePipelineWrapper):
    """Release resources and clear GPU memory."""
    print("\n>>> Cleaning up...")
    del wrapper
    del pipeline
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print_memory("After cleanup")
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


def main():
    """Run the manual FP8 pipeline integration test."""
    args = parse_args()
    checkpoint_path, text_encoder_path, vae_path = validate_paths(args)
    log_run_header(args, checkpoint_path, text_encoder_path, vae_path)
    reset_cuda_counters()
    pipeline = create_pipeline("cuda" if torch.cuda.is_available() else "cpu")
    load_components(pipeline, checkpoint_path, text_encoder_path, vae_path)
    wrapper = build_wrapper(pipeline)
    maybe_generate(wrapper, args)
    log_final_stats()
    cleanup(pipeline, wrapper)


if __name__ == "__main__":
    main()
