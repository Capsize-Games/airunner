#!/usr/bin/env python3
"""
Test script for downloading models from HuggingFace (no quantization).

This script demonstrates:
1. Downloading a model from HuggingFace (no Hub dependency)
2. Verifying function calling capability (Mistral tokenizer)

Note: Quantization will happen at runtime using bitsandbytes (already integrated).
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from airunner.components.llm.utils.model_downloader import (
    HuggingFaceDownloader,
)


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
    print("AI Runner Model Download Test")
    print("=" * 80)

    print("\nThis will download Ministral-3-8B-Instruct-2512 (~20GB)")
    print(
        "Quantization will happen at runtime using bitsandbytes (already installed)"
    )
    print()

    # Initialize downloader
    downloader = HuggingFaceDownloader()

    print("Downloading Ministral-3-8B-Instruct-2512...")
    print("-" * 80)

    try:
        model_path = downloader.download_model(
            repo_id="mistralai/Ministral-3-8B-Instruct-2512",
            model_type="ministral3",
            include_patterns=["*.safetensors", "*.json"],
            exclude_patterns=["*.bin", "*.msgpack", "*consolidated*"],
            progress_callback=lambda f, d, t: progress_callback(
                f"Downloading {f}", d / t if t > 0 else 0.0
            ),
        )

        print("\n" + "=" * 80)
        print("Download Complete!")
        print("=" * 80)
        print(f"\nModel downloaded to: {model_path}")

        # Verify critical files exist
        print("\nVerifying files...")
        critical_files = [
            "config.json",
            "params.json",
            "tekken.json",  # Critical for function calling!
        ]

        all_good = True
        for filename in critical_files:
            file_path = model_path / filename
            exists = file_path.exists()
            status = "✓" if exists else "✗"
            print(f"  {status} {filename}")
            if not exists:
                all_good = False

        # Check for safetensors files
        safetensors = list(model_path.glob("*.safetensors"))
        print(f"  ✓ {len(safetensors)} safetensors file(s)")

        if all_good and safetensors:
            print("\n" + "=" * 80)
            print("SUCCESS!")
            print("=" * 80)
            print("\nNext steps:")
            print(f"1. Update LLM settings to use: {model_path}")
            print("2. Restart AI Runner")
            print("3. bitsandbytes will quantize to 4-bit at runtime")
            print("4. Test function calling with tools")
            print("5. Verify interrupt button works")

            # Verify tokenizer
            print("\n" + "=" * 80)
            print("Verifying Tokenizer...")
            print("=" * 80)

            try:
                from transformers import AutoTokenizer

                tokenizer = AutoTokenizer.from_pretrained(str(model_path))
                vocab_size = len(tokenizer)
                special_tokens = tokenizer.all_special_tokens

                print(f"\nVocab size: {vocab_size:,}")
                print(f"Special tokens: {len(special_tokens)}")

                # Check for function calling support
                has_tool_tokens = any(
                    "tool" in str(token).lower() for token in special_tokens
                )

                if vocab_size == 131072:
                    print("✓ Mistral V3-Tekken tokenizer detected!")
                    print("✓ Function calling should work")
                elif has_tool_tokens:
                    print("✓ Tool tokens found - function calling supported")
                else:
                    print("⚠ Function calling tokens not detected")
                    print(
                        "  This model may not support native function calling"
                    )

            except Exception as e:
                print(f"⚠ Could not verify tokenizer: {e}")
        else:
            print("\n" + "=" * 80)
            print("WARNING: Some files missing!")
            print("=" * 80)
            print("Download may be incomplete. Try running again.")
            return 1

    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
