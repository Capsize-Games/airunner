#!/usr/bin/env python3
"""Debug script to test LLM request correlation manually."""
import os
import sys
import time
import requests

# Set env vars
os.environ["AIRUNNER_HEADLESS"] = "1"
os.environ["AIRUNNER_HTTP_PORT"] = "8188"
os.environ["AIRUNNER_KNOWLEDGE_ON"] = "0"

print("Starting headless server for debugging...")
print("Waiting for server to start (5 seconds)...")
time.sleep(5)

# Check health
try:
    resp = requests.get("http://127.0.0.1:8188/health", timeout=2)
    print(f"✓ Health check: {resp.status_code} - {resp.json()}")
except Exception as e:
    print(f"✗ Health check failed: {e}")
    sys.exit(1)

# Test LLM generation
print("\nTesting LLM generation...")
print("Sending: What is 2+2?")

try:
    resp = requests.post(
        "http://127.0.0.1:8188/llm/generate",
        json={
            "prompt": "What is 2+2? Answer in one word.",
            "temperature": 0.7,
            "max_tokens": 50,
        },
        timeout=60,
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except requests.Timeout:
    print("✗ Request timed out after 60 seconds")
    print("\nThis means the callback is not being invoked.")
    print("Check server logs for SignalMediator routing issues.")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

print("\n✓ Test successful!")
