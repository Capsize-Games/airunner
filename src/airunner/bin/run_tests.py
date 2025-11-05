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
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> int:
    """
    Run a command and return the exit code.

    Args:
        cmd: Command and arguments to run
        description: Description of what's being run

    Returns:
        Exit code from the command
    """
    print(f"\n{'=' * 80}")
    print(f"Running: {description}")
    print(f"{'=' * 80}")
    print(f"Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd)
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
        ]
    )

    return run_command(cmd, description)


def run_eval_tests(verbose: bool = False) -> int:
    """
    Run evaluation framework tests.

    Args:
        verbose: Whether to show verbose output

    Returns:
        Exit code from pytest
    """
    test_path = Path("src/airunner/components/llm/tests/eval")

    if not test_path.exists():
        print(f"Error: Eval tests directory not found at {test_path}")
        return 1

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

    return run_command(cmd, "Evaluation framework tests")


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Run AI Runner test suites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --unit                    Run all unit tests
  %(prog)s --eval                    Run eval tests only
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
        exit_code = run_eval_tests(verbose=args.verbose)
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
