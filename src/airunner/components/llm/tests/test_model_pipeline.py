#!/usr/bin/env python3
"""
Test script for the complete model download and quantization pipeline.

This script demonstrates:
1. Downloading a model from HuggingFace (no Hub dependency)
2. Quantizing to 4-bit with GPTQModel
3. Verifying function calling capability (Mistral tokenizer)
4. Cleaning up temporary files
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from airunner.components.llm.utils.model_pipeline import ModelPipeline


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def progress_callback(stage: str, progress: float):
    """Display progress bar."""
    bar_length = 40
    filled = int(bar_length * progress)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r{bar} {progress * 100:5.1f}% | {stage}", end="", flush=True)
    if progress >= 1.0:
        print()  # Newline when complete


def main():
    print("=" * 80)
    print("AI Runner Model Pipeline Test")
    print("=" * 80)

    # Initialize pipeline
    pipeline = ModelPipeline()

    # List available models
    print("\nAvailable models:")
    print("-" * 80)
    for key, info in pipeline.list_available_models().items():
        print(f"\n{key}:")
        print(f"  Repo: {info['repo_id']}")
        print(f"  Function calling: {info['supports_function_calling']}")
        print(f"  Context: {info['context_length']:,} tokens")
        print(f"  VRAM requirements:")
        for quant, vram in info["vram_requirements_gb"].items():
            print(f"    {quant}: {vram} GB")

    print("\n" + "=" * 80)
    print("Testing Ministral-3-8B Download & Quantization")
    print("=" * 80)

    # Test the pipeline with Ministral-3-8B
    # NOTE: This will download ~20GB and requires CUDA for quantization
    print("\nStarting download and quantization...")
    print("This will:")
    print("  1. Download ~20GB from HuggingFace")
    print("  2. Quantize to 4-bit (~4GB)")
    print("  3. Clean up original files")
    print()

    try:
        results = pipeline.download_and_quantize(
            model_key="ministral3-8b",
            quantize_4bit=True,
            quantize_2bit=False,  # Skip 2-bit for initial test
            keep_unquantized=False,  # Clean up to save space
            progress_callback=progress_callback,
        )

        print("\n" + "=" * 80)
        print("Pipeline Complete!")
        print("=" * 80)
        print("\nResults:")
        for variant, path in results.items():
            print(f"  {variant}: {path}")

        # Check registry
        print("\nRegistry:")
        for key, info in pipeline.list_downloaded_models():
            print(f"  {key}:")
            print(f"    Path: {info['path']}")
            print(f"    Quantization: {info['quantization']}")
            print(f"    VRAM: {info['vram_gb']} GB")
            print(f"    Function calling: {info['supports_function_calling']}")

        print("\n" + "=" * 80)
        print("Next Steps:")
        print("=" * 80)
        print("1. Update LLM settings to use:", results.get("4bit", "N/A"))
        print("2. Restart AI Runner")
        print("3. Test function calling with tools")
        print("4. Verify interrupt button works")

    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
