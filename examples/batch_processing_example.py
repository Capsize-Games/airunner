"""
Example: Using Batch Processing for Faster Eval Tests

This example demonstrates how to use the new batch processing features
to run eval tests much faster by processing multiple requests in parallel.
"""

import time
from airunner.components.eval.client import AIRunnerClient


def example_sequential_requests():
    """Traditional sequential approach - SLOW for many requests."""
    client = AIRunnerClient(base_url="http://localhost:8188")

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
    client = AIRunnerClient(base_url="http://localhost:8188")

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
    client = AIRunnerClient(base_url="http://localhost:8188")

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
