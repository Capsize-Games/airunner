#!/usr/bin/env python
"""Simple eval test to debug hanging issue."""

import sys
import time
from airunner.components.eval.client import AIRunnerClient


def test_basic_generation():
    """Test basic generation without tools."""
    print("Testing basic generation...")
    client = AIRunnerClient(base_url="http://127.0.0.1:8188")

    try:
        client.health_check()
        print("✓ Server is healthy")
    except Exception as e:
        print(f"✗ Server health check failed: {e}")
        return False

    start = time.time()
    try:
        response = client.generate(
            "What is 2+2?",
            max_tokens=50,
            temperature=0.1,
        )
        elapsed = time.time() - start
        print(f"✓ Basic generation completed in {elapsed:.2f}s")
        print(f"  Response: {response.get('text', '')[:100]}")
        return True
    except Exception as e:
        print(f"✗ Basic generation failed: {e}")
        return False


def test_with_rag_category():
    """Test generation with RAG tool category."""
    print("\nTesting with RAG tool category...")
    client = AIRunnerClient(base_url="http://127.0.0.1:8188")

    start = time.time()
    try:
        # Set a timeout for this test
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Request timed out after 30s")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 second timeout

        response = client.generate(
            "What is 2+2?",
            max_tokens=50,
            temperature=0.1,
            tool_categories=["rag"],  # This might cause hanging
        )

        signal.alarm(0)  # Cancel timeout
        elapsed = time.time() - start
        print(f"✓ RAG category generation completed in {elapsed:.2f}s")
        print(f"  Response: {response.get('text', '')[:100]}")
        return True
    except TimeoutError as e:
        print(f"✗ RAG category generation timed out: {e}")
        return False
    except Exception as e:
        print(f"✗ RAG category generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("EVAL TEST DEBUGGING")
    print("=" * 70)

    basic_ok = test_basic_generation()
    rag_ok = test_with_rag_category()

    print("\n" + "=" * 70)
    print("RESULTS:")
    print(f"  Basic generation: {'✓ PASS' if basic_ok else '✗ FAIL'}")
    print(f"  RAG category:     {'✓ PASS' if rag_ok else '✗ FAIL'}")
    print("=" * 70)

    sys.exit(0 if (basic_ok and rag_ok) else 1)
