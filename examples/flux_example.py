"""
FLUX Model Example - Low VRAM Text-to-Image Generation

This example demonstrates how to use the FLUX model manager to generate
images with automatic VRAM optimization for your RTX 5080.

The script will:
1. Initialize the FLUX model manager
2. Automatically apply CPU offload optimizations for 16GB VRAM
3. Generate a high-quality image from a text prompt
4. Save the result

Requirements:
- RTX 5080 (16GB VRAM) or similar
- diffusers >= 0.30.0
- transformers >= 4.40.0
- torch >= 2.1.0

Usage:
    python examples/flux_example.py
"""

from airunner.components.art.managers.stablediffusion.flux_model_manager import (
    FluxModelManager,
)
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.enums import StableDiffusionVersion


def main():
    """
    Generate an image using FLUX.1-schnell for fast generation.

    FLUX.1-schnell is recommended for RTX 5080 as it:
    - Generates high-quality images in 1-4 steps
    - Uses less VRAM than FLUX.1-dev
    - Completes generation in 8-12 seconds at 1024x1024
    """
    print("Initializing FLUX Model Manager...")
    print(
        "This will automatically detect your RTX 5080 and apply optimizations."
    )

    # Create the manager
    manager = FluxModelManager()

    # Create an image request
    request = ImageRequest()
    request.version = StableDiffusionVersion.FLUX_SCHNELL.value
    request.prompt = "A majestic lion standing on a cliff at sunset, highly detailed, cinematic lighting"
    request.negative_prompt = ""  # FLUX doesn't really use negative prompts
    request.width = 1024
    request.height = 1024
    request.steps = 4  # FLUX.1-schnell works well with just 4 steps
    request.guidance_scale = 0.0  # schnell doesn't use guidance
    request.seed = 42  # For reproducible results

    # Set the request on the manager
    manager._image_request = request

    print("\nLoading FLUX.1-schnell model...")
    print("This may take a minute the first time (downloading model)...")

    # Load the model (automatically applies CPU offload for 16GB VRAM)
    manager.load()

    print("\nGenerating image...")
    print(f"Prompt: {request.prompt}")
    print(f"Resolution: {request.width}x{request.height}")
    print(f"Steps: {request.steps}")

    # Generate the image
    try:
        manager.generate()
        print("\n✅ Image generated successfully!")
        print("Check your output directory for the result.")
    except Exception as e:
        print(f"\n❌ Error generating image: {e}")
        print("\nTroubleshooting:")
        print("- Ensure you have 16GB VRAM available")
        print("- Close other GPU-intensive applications")
        print("- Try FLUX.1-schnell instead of dev for lower VRAM")
    finally:
        # Clean up
        manager.unload()
        print("\n✅ Model unloaded, VRAM released")


def flux_dev_example():
    """
    Generate an image using FLUX.1-dev for highest quality.

    FLUX.1-dev provides better quality than schnell but:
    - Requires 50 steps (slower)
    - Uses slightly more VRAM
    - Takes 45-60 seconds at 1024x1024
    """
    print("Initializing FLUX.1-dev (highest quality)...")

    manager = FluxModelManager()

    request = ImageRequest()
    request.version = StableDiffusionVersion.FLUX_DEV.value
    request.prompt = "A serene Japanese garden with cherry blossoms, koi pond, and traditional architecture, photorealistic, 8k"
    request.width = 1024
    request.height = 1024
    request.steps = 50  # dev model needs more steps
    request.guidance_scale = 3.5  # dev uses guidance
    request.seed = 42

    manager._image_request = request

    print("Loading model with CPU offload optimization...")
    manager.load()

    print("Generating high-quality image (this will take ~60 seconds)...")
    manager.generate()

    manager.unload()
    print("✅ Done!")


def low_vram_tips():
    """
    Print tips for running FLUX on systems with less VRAM.
    """
    print("\n" + "=" * 60)
    print("FLUX Low VRAM Tips for RTX 5080 (16GB)")
    print("=" * 60)
    print()
    print("✅ Your RTX 5080 is fully supported!")
    print()
    print("Automatic Optimizations Applied:")
    print("  • CPU Offload: Model components moved between CPU/GPU")
    print("  • bfloat16: Reduces VRAM usage by ~50%")
    print("  • VAE Slicing: Processes images in tiles")
    print("  • Attention Slicing: Reduces attention memory")
    print()
    print("Performance on RTX 5080:")
    print("  • FLUX.1-schnell @ 1024x1024: ~8-12 seconds")
    print("  • FLUX.1-dev @ 1024x1024: ~45-60 seconds")
    print("  • VRAM Usage: ~12-14GB")
    print()
    print("If you experience OOM errors:")
    print("  1. Use FLUX.1-schnell instead of dev")
    print("  2. Reduce resolution to 768x768")
    print("  3. Close other GPU applications")
    print("  4. Ensure no other models are loaded")
    print()
    print("Model Recommendations:")
    print("  • RTX 5080/4080 (16GB): FLUX.1-schnell or dev ✅")
    print("  • RTX 4070 Ti (12GB): FLUX.1-schnell only")
    print("  • RTX 3080 (12GB): FLUX.1-schnell with reduced resolution")
    print("=" * 60)
    print()


if __name__ == "__main__":
    # Show low VRAM tips
    low_vram_tips()

    # Run the fast example (FLUX.1-schnell)
    print("\n🚀 Running FLUX.1-schnell example (fast, 4 steps)...\n")
    main()

    # Uncomment to try FLUX.1-dev (slower but higher quality)
    # print("\n🎨 Running FLUX.1-dev example (highest quality, 50 steps)...\n")
    # flux_dev_example()
