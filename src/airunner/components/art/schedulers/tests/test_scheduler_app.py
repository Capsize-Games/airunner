"""
Test script to verify scheduler behavior in airunner.
This will help identify if schedulers are being configured correctly.
"""

import os
import sys

# Add airunner to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import logging

# Set up logging to see all debug output
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(name)s - %(message)s",
)


def test_scheduler_loading():
    """Test that different schedulers are loaded with different configs."""
    print("=" * 80)
    print("TESTING SCHEDULER LOADING IN AIRUNNER")
    print("=" * 80)

    # This test would require a full airunner setup with database, settings, etc.
    # For now, just print instructions for manual testing
    print("\nTo test scheduler behavior manually:")
    print("1. Run airunner application")
    print("2. Load a Stable Diffusion model")
    print("3. Set a fixed seed (e.g., 42)")
    print("4. Generate an image with 'Euler' scheduler")
    print("5. Change scheduler to 'DPM++ 2M Karras'")
    print("6. Generate another image with the SAME seed")
    print("7. Check the logs for scheduler config details")
    print("8. Images should be DIFFERENT if schedulers are working correctly")
    print("\nLook for these log lines:")
    print(
        "  - '📄 Loaded scheduler config from disk' or '⚙️ Using scheduler class default config'"
    )
    print("  - '🔧 Final scheduler config after instantiation'")
    print("  - '✓ Loaded scheduler' with algorithm_type and use_karras_sigmas")
    print("  - '🎨 Starting generation with scheduler'")
    print(
        "\nIf all schedulers show the same config values, that's the problem!"
    )
    print("=" * 80)


if __name__ == "__main__":
    test_scheduler_loading()
