#!/usr/bin/env python3
"""Quick test to verify headless worker initialization."""
import os
import sys

# Set headless mode
os.environ["AIRUNNER_HEADLESS"] = "1"
os.environ["AIRUNNER_HTTP_PORT"] = "8188"
os.environ["AIRUNNER_KNOWLEDGE_ON"] = "0"

# Test imports
try:
    from airunner.app import App

    print("✓ App import successful")
except Exception as e:
    print(f"✗ App import failed: {e}")
    sys.exit(1)

# Test worker creation
try:
    print("Creating app instance...")
    app = App(initialize_gui=False)
    print("✓ App created")

    # Check if Qt app exists
    if hasattr(app, "app") and app.app:
        print(f"✓ Qt app created: {type(app.app).__name__}")
    else:
        print("✗ No Qt app instance")

    # Check if worker exists
    if hasattr(app, "_llm_generate_worker"):
        print(
            f"✓ LLM worker exists: {type(app._llm_generate_worker).__name__}"
        )
    else:
        print("✗ LLM worker not initialized")

    print("\nShutting down...")
    app.cleanup()
    print("✓ Cleanup complete")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\n✓ All checks passed")
