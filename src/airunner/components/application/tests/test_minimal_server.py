#!/usr/bin/env python3
"""Minimal test to isolate server hang issue."""

import os
import subprocess
import sys
import time
import requests

# Start headless server
print("=" * 70)
print("Starting headless server...")
print("=" * 70)

env = os.environ.copy()
env["AIRUNNER_HTTP_PORT"] = "8188"
env["AIRUNNER_HTTP_HOST"] = "127.0.0.1"
env["AIRUNNER_TEST_MODEL_PATH"] = (
    "~/.local/share/airunner/text/models/llm/causallm/Qwen2.5-7B-Instruct"
)

# Capture ALL server output
server_log = open("/tmp/minimal_server.log", "w", buffering=1)

server_proc = subprocess.Popen(
    [sys.executable, "-m", "airunner.bin.airunner_headless"],
    env=env,
    stdout=server_log,
    stderr=subprocess.STDOUT,
)

# Wait for server to start
print("Waiting for server to be ready...")
for i in range(120):
    try:
        response = requests.get("http://127.0.0.1:8188/health", timeout=1)
        if response.status_code == 200:
            print("✓ Server is ready!")
            break
    except (
        requests.RequestException,
        requests.ConnectionError,
        requests.Timeout,
    ):
        # Server not ready yet, continue waiting
        pass

    time.sleep(0.5)
    if i % 20 == 0:
        print(f"  Still waiting... ({i}s)")
else:
    print("✗ Server failed to start")
    server_proc.terminate()
    server_log.close()
    print("\n=== SERVER LOG ===")
    with open("/tmp/minimal_server.log") as f:
        print(f.read())
    sys.exit(1)

# Now test simple generation WITHOUT tool filtering
print("\n" + "=" * 70)
print("Test 1: Simple generation WITHOUT tool filtering")
print("=" * 70)

try:
    print("Sending request to /llm/generate...")
    response = requests.post(
        "http://127.0.0.1:8188/llm/generate",
        json={
            "prompt": "What is 2+2?",
            "max_tokens": 50,
        },
        timeout=10,
    )
    print(f"✓ Response received! Status: {response.status_code}")
    data = response.json()
    print(f"Response preview: {str(data)[:200]}")
except requests.Timeout:
    print("✗ TIMEOUT: Request timed out after 10 seconds")
except Exception as e:
    print(f"✗ Error: {e}")

# Now test WITH tool filtering
print("\n" + "=" * 70)
print("Test 2: Generation WITH tool_categories=['SYSTEM']")
print("=" * 70)

try:
    print("Sending request with tool_categories=['SYSTEM']...")
    response = requests.post(
        "http://127.0.0.1:8188/llm/generate",
        json={
            "prompt": "Create a calendar event tomorrow at 2pm",
            "max_tokens": 50,
            "tool_categories": ["SYSTEM"],
        },
        timeout=10,
    )
    print(f"✓ Response received! Status: {response.status_code}")
    data = response.json()
    print(f"Response preview: {str(data)[:200]}")
except requests.Timeout:
    print("✗ TIMEOUT: Request timed out after 10 seconds")
except Exception as e:
    print(f"✗ Error: {e}")

# Terminate server
print("\n" + "=" * 70)
print("Terminating server...")
print("=" * 70)
server_proc.terminate()

try:
    server_proc.wait(timeout=5)
except subprocess.TimeoutExpired:
    server_proc.kill()

server_log.close()

print("\n=== SERVER LOG (last 100 lines) ===")
with open("/tmp/minimal_server.log") as f:
    lines = f.readlines()
    for line in lines[-100:]:
        print(line.rstrip())

print("\nDone!")
