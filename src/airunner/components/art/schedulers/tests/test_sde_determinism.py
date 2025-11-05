#!/usr/bin/env python3
"""
Test script to verify DPM++ SDE deterministic noise sampler.

This ensures that the DeterministicSDENoiseSampler produces consistent,
reproducible results when given the same seed, matching AUTOMATIC1111's
behavior for batch determinism.
"""
import sys
import os

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src"
    ),
)

import torch
from airunner.components.art.managers.stablediffusion.noise_sampler import (
    DeterministicSDENoiseSampler,
)


def test_deterministic_sde_noise():
    """Test that the deterministic noise sampler produces consistent results."""
    print("=" * 80)
    print("TESTING DETERMINISTIC SDE NOISE SAMPLER")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    seed = 42
    shape = (2, 4, 64, 64)  # batch_size=2, channels=4, 64x64 latent

    # Create two samplers with the same seed
    sampler1 = DeterministicSDENoiseSampler(seed=seed, device=device)
    sampler2 = DeterministicSDENoiseSampler(seed=seed, device=device)

    # Generate noise from both
    noise1_batch1 = sampler1(shape)
    noise1_batch2 = sampler1(shape)  # Second call should be different

    noise2_batch1 = sampler2(shape)
    sampler2(shape)

    print(f"\nDevice: {device}")
    print(f"Seed: {seed}")
    print(f"Shape: {shape}")
    print()

    # Test 1: Same seed should produce same initial noise
    diff_initial = torch.abs(noise1_batch1 - noise2_batch1).max().item()
    print(f"Test 1: Same seed, first batch")
    print(f"  Max difference: {diff_initial:.10f}")
    test1_pass = diff_initial < 1e-6
    if test1_pass:
        print("  ✅ PASS: Identical noise from same seed")
    else:
        print(
            f"  ❌ FAIL: Different noise from same seed! (diff={diff_initial})"
        )

    # Test 2: Sequential calls should produce different noise
    diff_sequential = torch.abs(noise1_batch1 - noise1_batch2).max().item()
    print(f"\nTest 2: Same sampler, sequential batches")
    print(f"  Max difference: {diff_sequential:.10f}")
    test2_pass = diff_sequential > 0.1
    if test2_pass:
        print("  ✅ PASS: Sequential batches are different")
    else:
        print(
            f"  ❌ FAIL: Sequential batches are too similar! (diff={diff_sequential})"
        )

    # Test 3: Different seeds should produce different noise
    sampler3 = DeterministicSDENoiseSampler(seed=seed + 1, device=device)
    noise3 = sampler3(shape)
    diff_seeds = torch.abs(noise1_batch1 - noise3).max().item()
    print(f"\nTest 3: Different seeds")
    print(f"  Max difference: {diff_seeds:.10f}")
    test3_pass = diff_seeds > 0.1
    if test3_pass:
        print("  ✅ PASS: Different seeds produce different noise")
    else:
        print(
            f"  ❌ FAIL: Different seeds produce similar noise! (diff={diff_seeds})"
        )

    # Test 4: Verify noise statistics are reasonable
    mean = noise1_batch1.mean().item()
    std = noise1_batch1.std().item()
    print(f"\nTest 4: Noise statistics")
    print(f"  Mean: {mean:.6f} (should be ~0)")
    print(f"  Std:  {std:.6f} (should be ~1)")
    test4_pass = abs(mean) < 0.1 and abs(std - 1.0) < 0.2
    if test4_pass:
        print("  ✅ PASS: Noise statistics are normal")
    else:
        print(
            f"  ⚠️  WARNING: Noise statistics are unusual (mean={mean:.6f}, std={std:.6f})"
        )

    # Test 5: Verify dtype handling
    print(f"\nTest 5: Different dtype support")
    try:
        noise_fp16 = sampler1(shape, dtype=torch.float16)
        noise_fp32 = sampler1(shape, dtype=torch.float32)
        test5_pass = (
            noise_fp16.dtype == torch.float16
            and noise_fp32.dtype == torch.float32
        )
        if test5_pass:
            print("  ✅ PASS: Dtype handling works correctly")
        else:
            print(
                f"  ❌ FAIL: Dtype not preserved (got {noise_fp16.dtype} and {noise_fp32.dtype})"
            )
    except Exception as e:
        print(f"  ❌ FAIL: Dtype handling failed: {e}")
        test5_pass = False

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    all_pass = (
        test1_pass and test2_pass and test3_pass and test4_pass and test5_pass
    )

    if all_pass:
        print(
            "✅ All tests PASSED - Deterministic SDE noise sampler is working correctly!"
        )
        return 0
    else:
        print("❌ Some tests FAILED - Check implementation")
        failed_tests = []
        if not test1_pass:
            failed_tests.append("Test 1 (same seed determinism)")
        if not test2_pass:
            failed_tests.append("Test 2 (sequential difference)")
        if not test3_pass:
            failed_tests.append("Test 3 (different seeds)")
        if not test4_pass:
            failed_tests.append("Test 4 (noise statistics)")
        if not test5_pass:
            failed_tests.append("Test 5 (dtype handling)")
        print(f"Failed: {', '.join(failed_tests)}")
        return 1


if __name__ == "__main__":
    exit(test_deterministic_sde_noise())
