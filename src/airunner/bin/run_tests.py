#!/usr/bin/env python3
"""
Test runner script for AI Runner project.

This script provides a unified interface for running different test suites:
- Unit tests: Safe component tests excluding GUI/widget-only suites
- Eval tests: Evaluation framework tests in src/airunner/components/llm/tests/eval/
- LLM runtime smoke tests: safe route/runtime checks with no app startup
- STT runtime smoke tests: safe route/worker checks with no app startup
- Art runtime smoke tests: safe daemon-backed art checks with no app startup
- TTS runtime smoke tests: safe daemon-backed TTS checks with no app startup

Usage:
    python run_tests.py --unit              # Run unit tests only
    python run_tests.py --eval              # Run eval tests only
    python run_tests.py --all               # Run unit + runtime smoke + eval
    python run_tests.py --unit --verbose    # Run unit tests with verbose output
    python run_tests.py --component llm     # Run tests for specific component
    python run_tests.py --llm-runtime-smoke # Run safe LLM runtime smoke tests
    python run_tests.py --stt-runtime-smoke # Run safe STT runtime smoke tests
    python run_tests.py --art-runtime-smoke # Run safe art runtime smoke tests
    python run_tests.py --tts-runtime-smoke # Run safe TTS runtime smoke tests

Note: Eval tests use pytest fixtures to automatically manage the headless server.
      The server will start/stop automatically when tests run.
    The default unit suite skips GUI-only tests and blocks GUI app startup.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def _pytest_command(*args: str) -> list[str]:
    """Build a pytest command bound to the active Python interpreter."""
    return [sys.executable, "-m", "pytest", *args]


def _component_targets(
    base_path: Path,
    component: str,
) -> tuple[list[Path], str] | None:
    """Resolve one component name or alias into pytest targets."""
    alias_targets = {
        "chat": [
            base_path
            / "chat"
            / "gui"
            / "widgets"
            / "tests"
            / "test_chat_prompt_widget_show_event.py",
            base_path
            / "chat"
            / "gui"
            / "widgets"
            / "tests"
            / "test_chat_request_mode.py",
            base_path
            / "chat"
            / "gui"
            / "widgets"
            / "tests"
            / "test_conversation_widget_streaming.py",
        ],
        "documents": [
            base_path
            / "documents"
            / "gui"
            / "widgets"
            / "tests"
            / "test_knowledge_base_panel_widget.py",
        ],
    }
    if component in alias_targets:
        return alias_targets[component], (
            f"Focused validation suite for {component}"
        )
    test_path = base_path / component / "tests"
    if test_path.exists():
        return [test_path], f"Safe unit tests for {component} component"
    return None


def _build_pytest_env(skip_gui: bool = False) -> dict[str, str]:
    """Return environment guards for pytest subprocesses."""
    env = {"AIRUNNER_TEST_NO_GUI_LAUNCH": "1"}
    if skip_gui:
        env["AIRUNNER_SKIP_GUI_TESTS"] = "1"
        env["AIRUNNER_SKIP_EVAL_TESTS"] = "1"
        env["AIRUNNER_SKIP_FUNCTIONAL_TESTS"] = "1"
    return env


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
        resolved = _component_targets(base_path, component)
        if resolved is None:
            print(
                "Error: Component or alias "
                f"'{component}' is not configured for test execution"
            )
            return 1
        test_targets, description = resolved
    else:
        test_targets = [base_path]
        description = "Safe unit tests (GUI suites excluded)"

    include_gui_tests = component in {"chat", "documents"}

    cmd = _pytest_command(*[str(path) for path in test_targets])

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("--tb=short")

    # Add useful pytest options
    cmd.extend(
        [
            "--color=yes",
            "-ra",  # Show summary of all test outcomes
            "-m",
            (
                "not eval and not benchmark and not integration"
                if include_gui_tests
                else "not gui and not eval and not benchmark and not integration"
            ),
            "--ignore=src/airunner/components/eval",  # Exclude eval tests
            "--ignore=src/airunner/components/server/tests/functional",
        ]
    )

    return run_command(
        cmd,
        description,
        env=_build_pytest_env(skip_gui=not include_gui_tests),
    )


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
        cmd = _pytest_command(str(test_target))
    else:
        cmd = _pytest_command(str(test_path))

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
    env = _build_pytest_env()
    if model:
        env["AIRUNNER_TEST_MODEL_PATH"] = model
        # Also pass to pytest as --model flag
        cmd.extend(["--model", model])
        print(f"Using model: {model}")

    description = (
        f"Evaluation framework tests{' - ' + test_file if test_file else ''}"
    )
    return run_command(cmd, description, env=env)


def run_llm_runtime_smoke_tests(verbose: bool = False) -> int:
    """Run the safe llama.cpp runtime smoke suite."""
    test_path = Path("src/airunner/api/tests")
    cmd = _pytest_command(
        str(test_path),
        "-m",
        "llm_runtime_smoke",
    )

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("--tb=short")

    cmd.extend(["--color=yes", "-ra"])
    return run_command(
        cmd,
        "LLM runtime smoke tests",
        env=_build_pytest_env(),
    )


def run_stt_runtime_smoke_tests(verbose: bool = False) -> int:
    """Run the safe STT runtime smoke suite."""
    test_path = Path("src/airunner/api/tests")
    cmd = _pytest_command(
        str(test_path),
        "-m",
        "stt_runtime_smoke",
    )

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("--tb=short")

    cmd.extend(["--color=yes", "-ra"])
    return run_command(
        cmd,
        "STT runtime smoke tests",
        env=_build_pytest_env(),
    )


def run_art_runtime_smoke_tests(verbose: bool = False) -> int:
    """Run the safe art runtime smoke suite."""
    test_path = Path("src/airunner/api/tests")
    cmd = _pytest_command(
        str(test_path),
        "-m",
        "art_runtime_smoke",
    )

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("--tb=short")

    cmd.extend(["--color=yes", "-ra"])
    return run_command(
        cmd,
        "Art runtime smoke tests",
        env=_build_pytest_env(),
    )


def run_tts_runtime_smoke_tests(verbose: bool = False) -> int:
    """Run the safe TTS runtime smoke suite."""
    test_path = Path("src/airunner/api/tests")
    cmd = _pytest_command(
        str(test_path),
        "-m",
        "tts_runtime_smoke",
    )

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("--tb=short")

    cmd.extend(["--color=yes", "-ra"])
    return run_command(
        cmd,
        "TTS runtime smoke tests",
        env=_build_pytest_env(),
    )


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Run AI Runner test suites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --unit                    Run all unit tests
    %(prog)s --eval                    Run eval tests only
    %(prog)s --llm-runtime-smoke       Run safe llama.cpp runtime smoke tests
    %(prog)s --stt-runtime-smoke       Run safe STT runtime smoke tests
    %(prog)s --art-runtime-smoke       Run safe art runtime smoke tests
    %(prog)s --tts-runtime-smoke       Run safe TTS runtime smoke tests
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
        "--llm-runtime-smoke",
        action="store_true",
        help="Run safe llama.cpp runtime smoke tests",
    )

    parser.add_argument(
        "--stt-runtime-smoke",
        action="store_true",
        help="Run safe STT runtime smoke tests",
    )

    parser.add_argument(
        "--art-runtime-smoke",
        action="store_true",
        help="Run safe art runtime smoke tests",
    )

    parser.add_argument(
        "--tts-runtime-smoke",
        action="store_true",
        help="Run safe TTS runtime smoke tests",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests (unit + runtime smoke + eval)",
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
    if not (
        args.unit
        or args.eval
        or args.llm_runtime_smoke
        or args.stt_runtime_smoke
        or args.art_runtime_smoke
        or args.tts_runtime_smoke
        or args.all
    ):
        args.unit = True

    exit_codes = []

    # Run unit tests
    if args.unit or args.all:
        exit_code = run_unit_tests(
            component=args.component, verbose=args.verbose
        )
        exit_codes.append(exit_code)

    if args.llm_runtime_smoke or args.all:
        exit_code = run_llm_runtime_smoke_tests(verbose=args.verbose)
        exit_codes.append(exit_code)

    if args.stt_runtime_smoke or args.all:
        exit_code = run_stt_runtime_smoke_tests(verbose=args.verbose)
        exit_codes.append(exit_code)

    if args.art_runtime_smoke or args.all:
        exit_code = run_art_runtime_smoke_tests(verbose=args.verbose)
        exit_codes.append(exit_code)

    if args.tts_runtime_smoke or args.all:
        exit_code = run_tts_runtime_smoke_tests(verbose=args.verbose)
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
