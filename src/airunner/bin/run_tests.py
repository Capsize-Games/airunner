#!/usr/bin/env python3
"""
Test runner script for AI Runner project.

This script provides a unified interface for running different test suites:
- Unit tests: Component-level tests in src/airunner/components/*/tests/
- Eval tests: Evaluation framework tests in src/airunner/components/llm/tests/eval/

Usage:
    python run_tests.py --unit              # Run unit tests only
    python run_tests.py --eval              # Run eval tests only
    python run_tests.py --all               # Run all tests
    python run_tests.py --unit --verbose    # Run unit tests with verbose output
    python run_tests.py --component llm     # Run tests for specific component

Note: Eval tests use pytest fixtures to automatically manage the headless server.
      The server will start/stop automatically when tests run.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def kill_stale_servers():
    """
    Kill any stale airunner-headless processes from previous runs.

    This ensures we start with a clean state. Pytest fixtures will
    start a fresh server for the test session.
    """
    print("\n" + "=" * 80)
    print("Cleaning up stale server processes...")
    print("=" * 80)

    # Find airunner-headless processes
    try:
        result = subprocess.run(
            ["pgrep", "-f", "airunner-headless"],
            capture_output=True,
            text=True,
        )

        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            print(f"Found {len(pids)} stale process(es): {', '.join(pids)}")

            # Kill each process
            for pid in pids:
                subprocess.run(["kill", "-9", pid])
                print(f"Killed process {pid}")

            # Give processes time to die
            time.sleep(2)
            print("✅ Cleaned up stale processes")
        else:
            print("No stale processes found")
    except Exception as e:
        print(f"Warning: Error checking for processes: {e}")

    print()


def run_command(cmd: list[str], description: str, env: dict = None) -> int:
    """
    Run a command and return the exit code.

    Args:
        cmd: Command and arguments to run
        description: Description of what's being run
        env: Optional environment variables to set

    Returns:
        Exit code from the command
    """
    import os

    print(f"\n{'=' * 80}")
    print(f"Running: {description}")
    print(f"{'=' * 80}")
    print(f"Command: {' '.join(cmd)}\n")

    process_env = os.environ.copy()
    if env:
        process_env.update(env)
        for key, value in env.items():
            print(f"Environment: {key}={value}")
        print()

    result = subprocess.run(cmd, env=process_env)
    return result.returncode


def run_unit_tests(component: str = None, verbose: bool = False) -> int:
    """
    Run unit tests.

    Args:
        component: Optional component name to test (e.g., 'llm', 'art')
        verbose: Whether to show verbose output

    Returns:
        Exit code from pytest
    """
    base_path = Path("src/airunner/components")

    if component:
        test_path = base_path / component / "tests"
        if not test_path.exists():
            print(
                f"Error: Component '{component}' has no tests directory at {test_path}"
            )
            return 1
        description = f"Unit tests for {component} component"
    else:
        test_path = base_path
        description = "All unit tests"

    cmd = ["pytest", str(test_path)]

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("--tb=short")

    # Add useful pytest options
    cmd.extend(
        [
            "--color=yes",
            "-ra",  # Show summary of all test outcomes
            "--ignore=src/airunner/components/eval",  # Exclude eval tests
        ]
    )

    return run_command(cmd, description)


def run_eval_tests(
    verbose: bool = False,
    model: str = None,
    skip_slow: bool = False,
    test_file: str = None,
) -> int:
    """
    Run evaluation framework tests.

    Args:
        verbose: Whether to show verbose output
        model: Model path to use for testing (e.g., '/path/to/Qwen2.5-7B-Instruct')
        skip_slow: Skip slow integration tests, run only fast tests
        test_file: Optional specific test file to run (e.g., 'test_calendar_tool_eval.py')

    Returns:
        Exit code from pytest
    """
    test_path = Path("src/airunner/components/eval/tests")

    if not test_path.exists():
        print(f"Error: Eval tests directory not found at {test_path}")
        return 1

    # If specific test file provided, use it
    if test_file:
        test_target = test_path / test_file
        if not test_target.exists():
            print(f"Error: Test file not found at {test_target}")
            return 1
        cmd = ["pytest", str(test_target)]
    else:
        cmd = ["pytest", str(test_path)]

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("--tb=short")

    cmd.extend(
        [
            "--color=yes",
            "-ra",
        ]
    )

    # Add marker filters
    if skip_slow:
        cmd.extend(["-m", "not slow"])

    # Pass model argument to pytest if specified
    env = {}
    if model:
        env["AIRUNNER_TEST_MODEL_PATH"] = model
        # Also pass to pytest as --model flag
        cmd.extend(["--model", model])
        print(f"Using model: {model}")

    description = (
        f"Evaluation framework tests{' - ' + test_file if test_file else ''}"
    )
    return run_command(cmd, description, env=env)


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Run AI Runner test suites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --unit                    Run all unit tests
  %(prog)s --eval                    Run eval tests only
  %(prog)s --eval --model /path/to/model    Test with specific model
  %(prog)s --eval --file test_calendar_tool_eval.py --model /path/to/model    Run specific eval test file
  %(prog)s --eval --skip-slow        Run only fast eval tests
  %(prog)s --all                     Run all tests
  %(prog)s --unit --component llm    Run LLM component tests only
  %(prog)s --unit -v                 Run unit tests with verbose output
        """,
    )

    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests (component-level tests)",
    )

    parser.add_argument(
        "--eval", action="store_true", help="Run evaluation framework tests"
    )

    parser.add_argument(
        "--all", action="store_true", help="Run all tests (unit + eval)"
    )

    parser.add_argument(
        "--component",
        type=str,
        help="Run tests for specific component only (e.g., 'llm', 'art', 'tts')",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show verbose output"
    )

    parser.add_argument(
        "--model",
        type=str,
        help="Model path to use for eval tests (e.g., '/home/user/.local/share/airunner/text/models/llm/causallm/Qwen2.5-7B-Instruct')",
    )

    parser.add_argument(
        "--skip-slow",
        action="store_true",
        help="Skip slow integration tests in eval suite",
    )

    parser.add_argument(
        "--file",
        type=str,
        help="Run specific test file (e.g., 'test_calendar_tool_eval.py')",
    )

    args = parser.parse_args()

    # Default to running unit tests if no flags specified
    if not (args.unit or args.eval or args.all):
        args.unit = True

    exit_codes = []

    # Run unit tests
    if args.unit or args.all:
        exit_code = run_unit_tests(
            component=args.component, verbose=args.verbose
        )
        exit_codes.append(exit_code)

    # Run eval tests
    if args.eval or args.all:
        if args.component:
            print("\nWarning: --component flag ignored for eval tests")

        # Clean up any stale server processes from previous runs
        # Pytest fixtures will start a fresh server automatically
        kill_stale_servers()

        exit_code = run_eval_tests(
            verbose=args.verbose,
            model=args.model,
            skip_slow=args.skip_slow,
            test_file=args.file,
        )
        exit_codes.append(exit_code)

    # Print summary
    print(f"\n{'=' * 80}")
    print("Test Summary")
    print(f"{'=' * 80}")

    if all(code == 0 for code in exit_codes):
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
