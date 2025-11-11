#!/usr/bin/env python3
"""
Kill zombie airunner_headless processes.

This script finds and kills all running airunner_headless processes.
Use this if headless servers didn't shut down properly and are hogging GPU memory.

Usage:
    python src/airunner/bin/kill_zombie_processes.py
"""

import subprocess
import sys


def kill_zombie_processes():
    """Find and kill all airunner_headless processes."""
    try:
        # Find all airunner_headless processes
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            check=True,
        )

        lines = result.stdout.split("\n")
        pids = []

        for line in lines:
            if "airunner_headless" in line and "grep" not in line:
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        # Don't kill the current script process
                        if pid != subprocess.os.getpid():
                            pids.append(pid)
                    except ValueError:
                        continue

        if not pids:
            print("✓ No zombie airunner_headless processes found")
            return 0

        print(f"Found {len(pids)} zombie airunner_headless process(es)")
        print(f"PIDs: {', '.join(map(str, pids))}")

        # Kill all found processes
        for pid in pids:
            try:
                print(f"Killing process {pid}...")
                subprocess.run(["kill", "-9", str(pid)], check=True)
                print(f"✓ Killed process {pid}")
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to kill process {pid}: {e}")

        print(f"\n✓ Killed {len(pids)} zombie process(es)")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(kill_zombie_processes())
