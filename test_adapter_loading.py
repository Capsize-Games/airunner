#!/usr/bin/env python
"""
Test script to check if LoRA adapters are loaded properly.
This helps diagnose if the adapter knowledge is being applied to the model.
"""
import json
from airunner.utils.settings.get_qsettings import get_qsettings
from airunner.components.llm.data.fine_tuned_model import FineTunedModel


def test_adapter_loading():
    """Test adapter configuration and availability."""
    print("=" * 60)
    print("Testing Adapter Loading Configuration")
    print("=" * 60)

    # Check QSettings for enabled adapters
    print("\n1. QSettings Configuration:")
    qs = get_qsettings()
    enabled_json = qs.value("llm_settings/enabled_adapters", "[]")
    print(f"   Enabled adapters JSON: {enabled_json}")

    try:
        enabled_names = json.loads(enabled_json)
        print(f"   Enabled adapter names: {enabled_names}")
    except json.JSONDecodeError as e:
        print(f"   ERROR: Failed to parse JSON: {e}")
        return

    # Check database for adapters
    print("\n2. Database Adapters:")
    try:
        all_adapters = FineTunedModel.objects.all()
        print(f"   Total adapters in database: {len(all_adapters)}")

        for adapter in all_adapters:
            enabled = "✓" if adapter.name in enabled_names else "✗"
            print(f"   {enabled} {adapter.name}")
            print(f"      Path: {adapter.adapter_path}")
            if adapter.adapter_path:
                import os

                exists = os.path.exists(adapter.adapter_path)
                print(f"      Exists: {exists}")
                if exists:
                    # Check if adapter_config.json exists
                    config_path = os.path.join(
                        adapter.adapter_path, "adapter_config.json"
                    )
                    config_exists = os.path.exists(config_path)
                    print(f"      Has adapter_config.json: {config_exists}")
                    if config_exists:
                        with open(config_path, "r") as f:
                            config = json.load(f)
                            print(
                                f"      Adapter type: {config.get('peft_type', 'unknown')}"
                            )
                            print(
                                f"      Task type: {config.get('task_type', 'unknown')}"
                            )
    except Exception as e:
        print(f"   ERROR: {e}")

    # Check which adapters will be loaded
    print("\n3. Adapters That Will Be Loaded:")
    if enabled_names:
        try:
            all_adapters = FineTunedModel.objects.all()
            adapters_to_load = [
                a for a in all_adapters if a.name in enabled_names
            ]
            print(
                f"   Found {len(adapters_to_load)} adapter(s) matching enabled names"
            )
            for adapter in adapters_to_load:
                import os

                if adapter.adapter_path and os.path.exists(
                    adapter.adapter_path
                ):
                    print(f"   ✓ {adapter.name} will be loaded")
                else:
                    print(
                        f"   ✗ {adapter.name} WILL NOT load (path missing or invalid)"
                    )
        except Exception as e:
            print(f"   ERROR: {e}")
    else:
        print("   No adapters enabled")

    print("\n" + "=" * 60)
    print("Test complete.")
    print("\nTo test if adapter knowledge is loaded:")
    print("1. Enable your book-trained adapter in LLM settings")
    print("2. Reload the model (unload and load again)")
    print("3. Check logs for: '✓ Successfully loaded adapter'")
    print("4. Ask the LLM specific questions about your book")
    print("5. Compare responses with/without adapter enabled")
    print("=" * 60)


if __name__ == "__main__":
    test_adapter_loading()
