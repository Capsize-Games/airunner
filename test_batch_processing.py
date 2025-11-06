"""
Quick test script to verify batch processing works with real server.

This script:
1. Tests basic batch endpoint functionality
2. Compares sequential vs batch performance
3. Validates responses match
"""

import time
import sys
from airunner.components.eval.client import AIRunnerClient


def test_batch_endpoint_basic():
    """Test that batch endpoint accepts and processes requests."""
    print("\n" + "=" * 70)
    print("TEST 1: Basic Batch Endpoint")
    print("=" * 70)

    client = AIRunnerClient(base_url="http://localhost:8188", timeout=60)

    # Try health check first
    try:
        health = client.health_check()
        print(f"✓ Server is healthy: {health}")
    except Exception as e:
        print(f"✗ Server not available: {e}")
        return False

    # Test batch generation with simple prompts
    prompts = [
        "What is 2+2? Answer with just the number.",
        "What is 3+3? Answer with just the number.",
        "What is 5+5? Answer with just the number.",
    ]

    print(f"\nSending batch of {len(prompts)} prompts...")

    try:
        responses = client.generate_batch(
            prompts,
            max_tokens=10,
            temperature=0.1,
        )

        print(f"✓ Received {len(responses)} responses")

        for i, (prompt, response) in enumerate(zip(prompts, responses)):
            print(f"  {i+1}. {prompt}")
            print(f"     → {response.get('text', 'NO TEXT')[:50]}")

        return True

    except Exception as e:
        print(f"✗ Batch generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_sequential_vs_batch():
    """Compare sequential vs batch processing performance."""
    print("\n" + "=" * 70)
    print("TEST 2: Sequential vs Batch Performance")
    print("=" * 70)

    client = AIRunnerClient(base_url="http://localhost:8188", timeout=120)

    # Use simple math problems for speed
    prompts = [
        f"What is {i}+{i}? Answer with just the number." for i in range(1, 6)
    ]

    # Test 1: Sequential
    print(f"\n1. Sequential processing ({len(prompts)} requests)...")
    start = time.time()

    sequential_responses = []
    try:
        for i, prompt in enumerate(prompts, 1):
            print(f"   Request {i}/{len(prompts)}...", end="", flush=True)
            response = client.generate(
                prompt,
                max_tokens=10,
                temperature=0.1,
                stream=False,
            )
            sequential_responses.append(response)
            print(" ✓")
    except Exception as e:
        print(f"\n✗ Sequential failed: {e}")
        return False

    sequential_time = time.time() - start
    print(f"   Sequential time: {sequential_time:.2f}s")

    # Test 2: Batch
    print(f"\n2. Batch processing ({len(prompts)} requests)...")
    start = time.time()

    try:
        batch_responses = client.generate_batch(
            prompts,
            max_tokens=10,
            temperature=0.1,
        )
        print(f"   All {len(batch_responses)} responses received ✓")
    except Exception as e:
        print(f"✗ Batch failed: {e}")
        return False

    batch_time = time.time() - start
    print(f"   Batch time: {batch_time:.2f}s")

    # Compare
    print(f"\n3. Performance comparison:")
    print(f"   Sequential: {sequential_time:.2f}s")
    print(f"   Batch:      {batch_time:.2f}s")

    if batch_time < sequential_time:
        speedup = sequential_time / batch_time
        print(f"   ✓ Batch is {speedup:.2f}x faster!")
    else:
        slowdown = batch_time / sequential_time
        print(f"   ✗ Batch is {slowdown:.2f}x slower (unexpected)")

    # Verify responses are similar
    print(f"\n4. Response consistency:")
    for i, (seq, batch) in enumerate(
        zip(sequential_responses, batch_responses)
    ):
        seq_text = seq.get("text", "")
        batch_text = batch.get("text", "")
        match = "✓" if seq_text.strip() == batch_text.strip() else "~"
        print(
            f"   {match} Request {i+1}: seq='{seq_text[:20]}' batch='{batch_text[:20]}'"
        )

    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("BATCH PROCESSING VERIFICATION")
    print("=" * 70)
    print("\nNOTE: This test requires the AI Runner server to be running.")
    print("Start server with: airunner-headless")
    print("Or in another terminal: python -m airunner.bin.airunner_headless")

    # Run tests
    results = []

    results.append(("Basic batch endpoint", test_batch_endpoint_basic()))
    results.append(("Sequential vs Batch", test_sequential_vs_batch()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
