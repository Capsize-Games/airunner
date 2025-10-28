#!/usr/bin/env python3
"""
Diagnostic script to check AI Runner headless setup for eval testing.

Run this before running eval tests to verify everything is configured.
"""
import os
import sys


def check_llm_model_configured():
    """Check if an LLM model is configured."""
    print("=" * 60)
    print("1. Checking LLM Model Configuration")
    print("=" * 60)

    try:
        from airunner.components.llm.data.llm_generator_settings import (
            LLMGeneratorSettings,
        )

        settings = LLMGeneratorSettings.objects.first()
        if not settings:
            print("❌ FAIL: No LLM settings found")
            print("   Fix: Run 'airunner' (GUI) to initialize settings")
            return False

        print(f"Model Service: {settings.model_service}")
        print(f"Model Version: {settings.model_version}")
        print(f"Model Path: {settings.model_path}")

        if not settings.model_path or settings.model_path == "":
            print("❌ FAIL: No model path configured")
            print(
                "   Fix: Run 'airunner' (GUI) and select an LLM model in settings"
            )
            print("   Or: Run 'airunner-setup' to download a model")
            return False

        # Check if model file exists
        import os

        if not os.path.exists(settings.model_path):
            print(f"❌ FAIL: Model file not found at: {settings.model_path}")
            print("   Fix: Run 'airunner-setup' to download the model")
            return False

        print(f"✅ PASS: Model configured at {settings.model_path}")

        # Check if it's a directory (HuggingFace model) or file
        if os.path.isdir(settings.model_path):
            # Check for model files in directory
            model_files = [
                f
                for f in os.listdir(settings.model_path)
                if f.endswith((".bin", ".safetensors", ".gguf"))
            ]
            if model_files:
                print(f"   Model files found: {len(model_files)} file(s)")
            else:
                print(f"   WARNING: Directory exists but no model files found")

        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_headless_server():
    """Check if headless server can start."""
    print("\n" + "=" * 60)
    print("2. Checking Headless Server")
    print("=" * 60)

    try:
        import requests

        base_url = "http://127.0.0.1:8188"

        # Try to connect to server
        try:
            resp = requests.get(f"{base_url}/health", timeout=2)
            if resp.status_code == 200:
                print(f"✅ Server already running at {base_url}")
                print(f"   Health check: {resp.json()}")
                return True
        except requests.RequestException:
            pass

        print("ℹ️  Server not running (this is OK for manual testing)")
        print("   To start: airunner-headless --port 8188")
        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def check_qt_availability():
    """Check if Qt is available for worker event loop."""
    print("\n" + "=" * 60)
    print("3. Checking Qt Availability")
    print("=" * 60)

    try:
        from PySide6.QtCore import QCoreApplication

        print("✅ PASS: PySide6 Qt Core available")
        return True
    except ImportError as e:
        print(f"❌ FAIL: PySide6 not available: {e}")
        print("   Fix: pip install PySide6")
        return False


def check_test_dependencies():
    """Check if pytest and test dependencies are installed."""
    print("\n" + "=" * 60)
    print("4. Checking Test Dependencies")
    print("=" * 60)

    missing = []

    try:
        import pytest

        print(f"✅ pytest: {pytest.__version__}")
    except ImportError:
        print("❌ pytest not installed")
        missing.append("pytest")

    try:
        import requests

        print(f"✅ requests: {requests.__version__}")
    except ImportError:
        print("❌ requests not installed")
        missing.append("requests")

    if missing:
        print(f"\n   Fix: pip install {' '.join(missing)}")
        return False

    return True


def main():
    """Run all diagnostic checks."""
    print("\nAI Runner Eval Testing Diagnostic")
    print("=" * 60)

    results = {
        "LLM Model": check_llm_model_configured(),
        "Headless Server": check_headless_server(),
        "Qt Availability": check_qt_availability(),
        "Test Dependencies": check_test_dependencies(),
    }

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = all(results.values())

    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")

    print("=" * 60)

    if all_passed:
        print("\n✅ All checks passed! You can run eval tests:")
        print(
            "   pytest src/airunner/components/eval/tests/test_real_eval.py -v --timeout=300"
        )
    else:
        print(
            "\n❌ Some checks failed. Fix the issues above before running tests."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
