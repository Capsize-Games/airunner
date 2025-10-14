#!/usr/bin/env python3
"""
Test script to verify schedulers are actually different.
This creates minimal scheduler instances and compares their behavior.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import torch
from diffusers import (
    EulerDiscreteScheduler,
    EulerAncestralDiscreteScheduler,
    DPMSolverMultistepScheduler,
    DDIMScheduler,
)

print("=" * 80)
print("SCHEDULER BEHAVIOR TEST")
print("=" * 80)

# Create a simple config (typical SD 1.5 settings)
base_config = {
    "num_train_timesteps": 1000,
    "beta_start": 0.00085,
    "beta_end": 0.012,
    "beta_schedule": "scaled_linear",
    "trained_betas": None,
    "prediction_type": "epsilon",
}

print("\n1. Creating schedulers with base config...")
print("-" * 80)

euler = EulerDiscreteScheduler.from_config(base_config)
print(f"✓ Euler: {euler.__class__.__name__}")

euler_a = EulerAncestralDiscreteScheduler.from_config(base_config)
print(f"✓ Euler Ancestral: {euler_a.__class__.__name__}")

dpm_config = base_config.copy()
dpm = DPMSolverMultistepScheduler.from_config(dpm_config)
print(f"✓ DPM++ (default): {dpm.__class__.__name__}")

dpm_karras_config = base_config.copy()
dpm_karras = DPMSolverMultistepScheduler.from_config(dpm_karras_config)
dpm_karras.config.use_karras_sigmas = True
dpm_karras.config.algorithm_type = "dpmsolver++"
print(f"✓ DPM++ Karras: {dpm_karras.__class__.__name__}")

ddim = DDIMScheduler.from_config(base_config)
print(f"✓ DDIM: {ddim.__class__.__name__}")

print("\n2. Setting timesteps (50 steps)...")
print("-" * 80)

num_steps = 50
for scheduler, name in [
    (euler, "Euler"),
    (euler_a, "Euler Ancestral"),
    (dpm, "DPM++"),
    (dpm_karras, "DPM++ Karras"),
    (ddim, "DDIM"),
]:
    scheduler.set_timesteps(num_steps)
    timesteps = scheduler.timesteps
    print(
        f"{name:20s}: {len(timesteps)} timesteps, first={timesteps[0]:.1f}, last={timesteps[-1]:.1f}"
    )

print("\n3. Testing step behavior...")
print("-" * 80)

# Create a dummy latent and model output
latent = torch.randn(1, 4, 64, 64)
model_output = torch.randn_like(latent)

print(f"Input latent shape: {latent.shape}")
print(f"Model output shape: {model_output.shape}")
print()

results = {}
for scheduler, name in [
    (euler, "Euler"),
    (euler_a, "Euler Ancestral"),
    (dpm, "DPM++"),
    (dpm_karras, "DPM++ Karras"),
    (ddim, "DDIM"),
]:
    scheduler.set_timesteps(num_steps)
    # Use the first timestep from the scheduler's timesteps
    timestep = scheduler.timesteps[0]
    print(f"Testing {name} with timestep {timestep}")
    output = scheduler.step(model_output, timestep, latent)
    prev_sample = output.prev_sample
    results[name] = prev_sample

    # Calculate some statistics
    mean = prev_sample.mean().item()
    std = prev_sample.std().item()
    min_val = prev_sample.min().item()
    max_val = prev_sample.max().item()

    print(
        f"{name:20s}: mean={mean:8.4f}, std={std:7.4f}, min={min_val:8.4f}, max={max_val:8.4f}"
    )

print("\n4. Comparing outputs...")
print("-" * 80)

# Compare each scheduler's output
names = list(results.keys())
for i, name1 in enumerate(names):
    for name2 in names[i + 1 :]:
        diff = (results[name1] - results[name2]).abs().mean().item()
        print(f"{name1:20s} vs {name2:20s}: mean abs diff = {diff:.6f}")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("-" * 80)
if len(set(names)) > 1:
    # Check if all outputs are identical (they shouldn't be!)
    all_same = all(
        torch.allclose(results[names[0]], results[name], atol=1e-5)
        for name in names[1:]
    )
    if all_same:
        print("❌ ERROR: All schedulers produced IDENTICAL outputs!")
        print("   This means schedulers are NOT behaving differently.")
    else:
        print("✅ SUCCESS: Schedulers produced DIFFERENT outputs!")
        print("   Schedulers are working correctly in isolation.")
else:
    print("⚠ Only tested one scheduler")

print("=" * 80)
print("\nIf schedulers are different here but same in airunner,")
print("the problem is in how airunner loads/uses the scheduler.")
print("=" * 80)
