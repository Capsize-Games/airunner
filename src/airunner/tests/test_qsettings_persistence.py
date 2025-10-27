#!/usr/bin/env python
"""
Test script to diagnose QSettings persistence for adapter checkboxes.
Run this to verify QSettings is working correctly.
"""
import json
from airunner.utils.settings.get_qsettings import get_qsettings


def test_qsettings_persistence():
    """Test reading and writing adapter settings."""
    print("=" * 60)
    print("Testing QSettings Persistence for Adapters")
    print("=" * 60)

    qs = get_qsettings()
    print(f"\nQSettings file location: {qs.fileName()}")
    print(f"Organization: {qs.organizationName()}")
    print(f"Application: {qs.applicationName()}")

    # Read current value
    print("\n1. Reading current value:")
    current = qs.value("llm_settings/enabled_adapters", "[]")
    print(f"   Raw value: {current}")
    print(f"   Type: {type(current)}")

    try:
        parsed = json.loads(current)
        print(f"   Parsed: {parsed}")
    except json.JSONDecodeError as e:
        print(f"   ERROR parsing: {e}")

    # Write test value
    print("\n2. Writing test value:")
    test_adapters = ["test_adapter_1", "test_adapter_2"]
    test_json = json.dumps(test_adapters)
    print(f"   Writing: {test_json}")
    qs.setValue("llm_settings/enabled_adapters", test_json)
    qs.sync()

    # Read back immediately
    print("\n3. Reading back immediately:")
    readback = qs.value("llm_settings/enabled_adapters", "[]")
    print(f"   Raw value: {readback}")
    print(f"   Type: {type(readback)}")

    try:
        parsed = json.loads(readback)
        print(f"   Parsed: {parsed}")
        print(f"   Match: {parsed == test_adapters}")
    except json.JSONDecodeError as e:
        print(f"   ERROR parsing: {e}")

    # List all keys in llm_settings group
    print("\n4. All keys in llm_settings group:")
    qs.beginGroup("llm_settings")
    keys = qs.allKeys()
    for key in keys:
        value = qs.value(key)
        print(f"   {key}: {value} (type: {type(value).__name__})")
    qs.endGroup()

    print("\n" + "=" * 60)
    print("Test complete. Check if values persist after restart.")
    print("=" * 60)


if __name__ == "__main__":
    test_qsettings_persistence()
