#!/usr/bin/env python3
"""Manual test of LLM endpoint to debug timeout issue."""
import os
import requests
import json

# Configure
os.environ["AIRUNNER_HEADLESS"] = "1"
os.environ["AIRUNNER_HTTP_PORT"] = "8188"
os.environ["AIRUNNER_KNOWLEDGE_ON"] = "0"

BASE_URL = "http://127.0.0.1:8188"

print("Testing AI Runner headless server...")
print(f"Base URL: {BASE_URL}\n")

# Test 1: Health check
print("1. Testing /health endpoint...")
try:
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}\n")
except Exception as e:
    print(f"   ERROR: {e}\n")

# Test 2: LLM generation (non-streaming)
print("2. Testing /llm/generate endpoint (non-streaming)...")
try:
    payload = {
        "prompt": "What is 2+2? Answer in one word.",
        "temperature": 0.7,
        "max_tokens": 50,
        "stream": False,
    }
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    print("   Sending request...")

    resp = requests.post(
        f"{BASE_URL}/llm/generate",
        json=payload,
        timeout=10,  # 10 second timeout
    )

    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   Response: {json.dumps(data, indent=2)}")
    else:
        print(f"   Error: {resp.text}")

except requests.Timeout:
    print("   ERROR: Request timed out (10s)")
except Exception as e:
    print(f"   ERROR: {e}")

print("\nDone!")
