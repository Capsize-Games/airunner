"""
Example: Using Batch Processing for Faster Eval Tests

This example demonstrates how to use the new batch processing features
to run eval tests much faster by processing multiple requests in parallel.

Runnable both as a standalone script and as a pytest module:

    # Standalone (requires a running daemon on the default port):
    python examples/batch_processing_example.py

    # As pytest (the airunner_client fixture is defined below):
    pytest examples/batch_processing_example.py -v

The default endpoint is http://localhost:8188, which matches the daemon's
default HTTP port (airunner_services.runtimes.daemon_config.DaemonConfig).
Override it with the AIRUNNER_EXAMPLE_BASE_URL environment variable when your
daemon listens elsewhere.
"""

import os
import time

# pytest is optional: the standalone __main__ path must run without it, so
# the import is guarded and the pytest fixture is only registered when pytest
# is actually available.
try:
    import pytest
except ImportError:  # pragma: no cover - standalone runs without pytest
    pytest = None  # type: ignore[assignment]

from airunner_services.eval.client import AIRunnerClient


DEFAULT_BASE_URL = os.environ.get(
    "AIRUNNER_EXAMPLE_BASE_URL", "http://localhost:8188"
)


def make_client(base_url: str = DEFAULT_BASE_URL) -> AIRunnerClient:
    """Return an AIRunnerClient for the example daemon endpoint."""
    return AIRunnerClient(base_url=base_url)


if pytest is not None:

    @pytest.fixture
    def airunner_client() -> AIRunnerClient:
        """Fixture providing a client for pytest-based eval tests.

        Simple client factory; override AIRUNNER_EXAMPLE_BASE_URL (or edit
        DEFAULT_BASE_URL) to point the fixture at a different daemon.
        """
        return make_client()


def example_sequential_requests():
    """Traditional sequential approach - SLOW for many requests."""
    client = make_client()

    prompts = [
        "What is 2+2?",
        "What is 3+3?",
        "What is 5+5?",
        "What is 7+7?",
        "What is 9+9?",
    ]

    print("Sequential requests (SLOW):")
    start = time.time()

    responses = []
    for prompt in prompts:
        response = client.generate(prompt, stream=False)
        responses.append(response["text"])
        print(f"  - {prompt} → {response['text']}")

    duration = time.time() - start
    print(f"Total time: {duration:.2f}s\n")

    return responses


def example_batch_requests():
    """New batch approach - FAST with parallel processing."""
    client = make_client()

    prompts = [
        "What is 2+2?",
        "What is 3+3?",
        "What is 5+5?",
        "What is 7+7?",
        "What is 9+9?",
    ]

    print("Batch requests (FAST):")
    start = time.time()

    # All requests processed in parallel!
    responses = client.generate_batch(prompts)

    for response in responses:
        print(f"  - {response['prompt']} → {response['text']}")

    duration = time.time() - start
    print(f"Total time: {duration:.2f}s\n")

    return [r["text"] for r in responses]


def example_async_batch_requests():
    """Async batch for fire-and-forget scenarios."""
    client = make_client()

    prompts = ["Question " + str(i) for i in range(100)]

    print("Async batch requests:")

    # Submit batch and get batch_id
    batch_id = client.generate_batch_async(prompts)
    print(f"Submitted batch: {batch_id}")

    # Poll for results (in real code, do this periodically)
    while True:
        result = client.get_batch_results(batch_id)
        status = result.get("status")
        print(f"Status: {status}")

        if status == "completed":
            responses = result.get("responses", [])
            print(f"Completed {len(responses)} responses")
            break
        elif status == "failed":
            print("Batch failed")
            break

        time.sleep(1)


# Example pytest usage for eval tests
def test_math_eval_batched(airunner_client):
    """Example: Batch eval test for math problems."""
    # Prepare all test cases
    test_cases = [
        {"prompt": "What is 2+2?", "expected": "4"},
        {"prompt": "What is 10-5?", "expected": "5"},
        {"prompt": "What is 3*4?", "expected": "12"},
        {"prompt": "What is 15/3?", "expected": "5"},
        # ... hundreds more test cases ...
    ]

    prompts = [tc["prompt"] for tc in test_cases]

    # Process all in parallel - MUCH faster!
    responses = airunner_client.generate_batch(
        prompts,
        temperature=0.1,  # Low temp for consistent answers
        max_tokens=50,
    )

    # Check results
    passed = 0
    for tc, response in zip(test_cases, responses):
        if tc["expected"] in response["text"]:
            passed += 1

    accuracy = passed / len(test_cases)
    print(f"Accuracy: {accuracy:.2%}")
    assert accuracy > 0.8  # Require 80% accuracy


if __name__ == "__main__":
    # Compare sequential vs batch
    print("=" * 60)
    print("COMPARISON: Sequential vs Batch Processing")
    print("=" * 60)

    print("\n1. Sequential (old way - slow):")
    print("-" * 60)
    seq_responses = example_sequential_requests()

    print("\n2. Batch (new way - fast):")
    print("-" * 60)
    batch_responses = example_batch_requests()

    print("\n3. Results match:")
    print("-" * 60)
    for seq, batch in zip(seq_responses, batch_responses):
        match = "✓" if seq == batch else "✗"
        print(f"  {match} Same result")
