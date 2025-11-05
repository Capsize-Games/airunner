#!/usr/bin/env python3
"""
Test script for HunyuanVideo generation.

Tests the complete end-to-end video generation pipeline.
"""

import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PIL import Image
import numpy as np

from airunner.components.video.managers.hunyuan_video_manager import (
    HunyuanVideoManager,
)
from airunner.enums import SignalCode


def test_hunyuan_video_generation():
    """Test HunyuanVideo end-to-end generation."""
    print("=" * 70)
    print("HunyuanVideo Generation Test")
    print("=" * 70)

    # Initialize manager
    print("\n1. Initializing HunyuanVideoManager...")
    manager = HunyuanVideoManager()

    # Create test input image
    print("\n2. Creating test input image...")
    width, height = 640, 384
    test_image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    test_image_pil = Image.fromarray(test_image)

    # Test parameters
    prompt = "A beautiful sunset over the ocean"
    negative_prompt = "blurry, low quality"
    num_frames = 129  # ~4 seconds at 30fps
    seed = 42

    print("\n3. Loading models...")
    try:
        manager._load_model()
        print("✅ Models loaded successfully")
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False

    # Generate video
    print("\n4. Generating video...")
    print(f"   Prompt: {prompt}")
    print(f"   Frames: {num_frames}")
    print(f"   Seed: {seed}")

    # Register progress callback
    def progress_callback(data):
        progress = data.get("progress", 0)
        message = data.get("message", "")
        print(f"   Progress: {progress}% - {message}")

    manager.register(SignalCode.VIDEO_PROGRESS_SIGNAL, progress_callback)

    try:
        output_path = manager.generate_video(
            prompt=prompt,
            negative_prompt=negative_prompt,
            init_image=test_image_pil,
            num_frames=num_frames,
            seed=seed,
            steps=20,  # Reduced for faster testing
            cfg_scale=7.0,
        )

        if output_path and os.path.exists(output_path):
            print(f"\n✅ Video generated successfully!")
            print(f"   Output: {output_path}")
            print(
                f"   Size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB"
            )
            return True
        else:
            print(f"\n❌ Video generation failed - no output file")
            return False

    except Exception as e:
        print(f"\n❌ Video generation failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        print("\n5. Cleaning up...")
        manager._unload_model()
        print("✅ Models unloaded")


def test_model_loading_only():
    """Test just the model loading/unloading."""
    print("=" * 70)
    print("HunyuanVideo Model Loading Test")
    print("=" * 70)

    print("\n1. Initializing manager...")
    manager = HunyuanVideoManager()

    print("\n2. Loading models...")
    try:
        manager._load_model()
        print("✅ Models loaded successfully")

        # Check all components
        components = [
            ("Text Encoder (Llama)", manager.text_encoder),
            ("Text Encoder 2 (CLIP)", manager.text_encoder_2),
            ("Tokenizer (Llama)", manager.tokenizer),
            ("Tokenizer 2 (CLIP)", manager.tokenizer_2),
            ("VAE", manager.vae),
            ("Transformer", manager.transformer),
            ("Image Encoder", manager.image_encoder),
            ("Feature Extractor", manager.feature_extractor),
        ]

        print("\n3. Verifying components:")
        all_loaded = True
        for name, component in components:
            status = "✅" if component is not None else "❌"
            print(f"   {status} {name}")
            if component is None:
                all_loaded = False

        if all_loaded:
            print("\n✅ All components loaded successfully")
        else:
            print("\n❌ Some components failed to load")
            return False

    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        print("\n4. Unloading models...")
        manager._unload_model()
        print("✅ Models unloaded")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test HunyuanVideo generation"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full generation test (slow, requires GPU)",
    )
    parser.add_argument(
        "--load-only",
        action="store_true",
        help="Only test model loading/unloading",
    )

    args = parser.parse_args()

    if args.full:
        success = test_hunyuan_video_generation()
    elif args.load_only:
        success = test_model_loading_only()
    else:
        print("Usage:")
        print("  --load-only   : Test model loading only (fast)")
        print(
            "  --full        : Test complete generation (slow, requires GPU)"
        )
        sys.exit(1)

    sys.exit(0 if success else 1)
