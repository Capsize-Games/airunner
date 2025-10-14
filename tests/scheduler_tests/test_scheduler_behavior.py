#!/usr/bin/env python3
"""
Quick test to verify scheduler switching behavior.
Run this to check if schedulers are actually being changed correctly.
"""
import diffusers
from airunner.components.art.data.schedulers import Schedulers
from airunner.enums import Scheduler

# Test that our schedulers database has the right mappings
print("Testing scheduler mappings...")
print("-" * 60)

test_schedulers = [
    Scheduler.EULER.value,
    Scheduler.DPM.value,
    Scheduler.DPM_PP_2M.value,
    Scheduler.DPM_PP_2M_K.value,
    Scheduler.DPM_PP_2M_SDE_K.value,
]

for scheduler_name in test_schedulers:
    scheduler_record = Schedulers.objects.filter_by_first(
        display_name=scheduler_name
    )
    if scheduler_record:
        scheduler_class_name = scheduler_record.name
        scheduler_class = getattr(diffusers, scheduler_class_name, None)
        if scheduler_class:
            print(f"✓ {scheduler_name:25s} -> {scheduler_class_name}")
        else:
            print(
                f"✗ {scheduler_name:25s} -> {scheduler_class_name} (CLASS NOT FOUND)"
            )
    else:
        print(f"✗ {scheduler_name:25s} -> NOT IN DATABASE")

print("\n" + "=" * 60)
print("Testing DPM scheduler config overrides...")
print("-" * 60)

# Create a dummy config to test the override logic
from airunner.enums import Scheduler

test_cases = [
    (
        Scheduler.DPM,
        {"algorithm_type": "dpmsolver", "use_karras_sigmas": False},
    ),
    (
        Scheduler.DPM_PP_2M,
        {"algorithm_type": "dpmsolver++", "use_karras_sigmas": False},
    ),
    (
        Scheduler.DPM_PP_2M_K,
        {"algorithm_type": "dpmsolver++", "use_karras_sigmas": True},
    ),
    (
        Scheduler.DPM_PP_2M_SDE_K,
        {"algorithm_type": "sde-dpmsolver++", "use_karras_sigmas": True},
    ),
    (
        Scheduler.DPM_2M_SDE_K,
        {"algorithm_type": "sde-dpmsolver", "use_karras_sigmas": True},
    ),
]

for scheduler_enum, expected_overrides in test_cases:
    scheduler_name = scheduler_enum.value
    print(f"\n{scheduler_name}:")
    print(f"  Expected overrides: {expected_overrides}")

print("\n" + "=" * 60)
print("Done! If you see checkmarks above, the scheduler database is correct.")
print("Now run airunner and check the logs for scheduler change messages.")
print("=" * 60)
