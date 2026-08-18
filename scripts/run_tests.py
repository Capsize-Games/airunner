#!/usr/bin/env python3
"""
Test runner script for AI Runner project.

This script provides a unified interface for running different test suites:
- Unit tests: Safe component tests excluding GUI/widget-only suites
- Eval tests: Daemon-backed LLM eval tests in services/tests/eval/
- LLM runtime smoke tests: safe route/runtime checks with no app startup
- STT runtime smoke tests: safe route/worker checks with no app startup
- Art runtime smoke tests: safe daemon-backed art checks with no app startup
- Art service runtime tests: direct service-surface art checks with real models
- TTS runtime smoke tests: safe daemon-backed TTS checks with no app startup

Usage:
    python run_tests.py --unit              # Run unit tests only
    python run_tests.py --eval              # Run eval tests only
    python run_tests.py --eval --service groq --llm groq-model
                                          # Run judged evals with Groq
    python run_tests.py --all               # Run unit + runtime smoke + eval
    python run_tests.py --unit --verbose    # Run unit tests with verbose output
    python run_tests.py --component llm     # Run tests for specific component
    python run_tests.py --llm-runtime-smoke # Run safe LLM runtime smoke tests
    python run_tests.py --stt-runtime-smoke # Run safe STT runtime smoke tests
    python run_tests.py --art-runtime-smoke # Run safe art runtime smoke tests
    python run_tests.py --art-service-runtime # Run direct art service tests
    python run_tests.py --tts-runtime-smoke # Run safe TTS runtime smoke tests

Note: Eval tests start a fresh daemon process inside the test harness.
        The default unit suite skips GUI-only tests and blocks GUI app startup.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
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


def _process_exists(pid: int) -> bool:
    """Return whether one process id is still alive (portable POSIX probe)."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _loopback_token() -> str:
    """Return the per-user daemon loopback token, or "" when unavailable."""
    try:
        from airunner_services.api.loopback_token import (
            get_or_create_loopback_token,
        )

        return get_or_create_loopback_token()
    except Exception:
        try:
            from airunner_common.settings import AIRUNNER_BASE_PATH

            token_path = (
                Path(AIRUNNER_BASE_PATH) / "config" / "loopback_token"
            )
            return token_path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""


def _request_graceful_shutdown(pid: int, ports: list[int], token: str) -> bool:
    """Ask one daemon to shut itself down via its /admin/shutdown endpoint.

    Loopback auth (issue #2033) requires the ``X-Airunner-Token`` header;
    without a token the request would 401, so we fall back to SIGTERM.
    """
    if not token:
        return False
    for port in ports:
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/admin/shutdown",
                method="POST",
                headers={"X-Airunner-Token": token},
            )
            with urllib.request.urlopen(request, timeout=5):
                return True
        except Exception:
            continue
    return False


def _wait_for_exit(pid: int, timeout_seconds: float = 5.0) -> bool:
    """Poll until one process exits or the timeout elapses."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _process_exists(pid):
            return True
        time.sleep(0.25)
    return False


def _terminate_with_sigterm(pid: int) -> None:
    """Send SIGTERM (never SIGKILL) to one process id."""
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def kill_stale_servers():
    """
    Gracefully shut down any stale airunner-headless processes.

    This ensures we start with a clean state. Pytest fixtures will start a
    fresh server for the test session.

    Cleanup is graceful (issue #2056): first POST /admin/shutdown (with the
    per-user loopback token) and wait, then fall back to SIGTERM only -- never
    SIGKILL. Process discovery prefers ``psutil`` (a declared dependency of
    both the GUI and services packages); ``pgrep -f`` is used only when
    psutil is unavailable.
    """
    print("\n" + "=" * 80)
    print("Cleaning up stale server processes...")
    print("=" * 80)

    try:
        import psutil
    except ImportError:
        psutil = None

    pids: list[int] = []
    if psutil is not None:
        for proc in psutil.process_iter(["pid", "cmdline"]):
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if "airunner-headless" in cmdline:
                pids.append(proc.pid)
    else:
        # Portable fallback when psutil is not installed: pgrep + SIGTERM
        # only (the old code used SIGKILL here, issue #2056).
        try:
            result = subprocess.run(
                ["pgrep", "-f", "airunner-headless"],
                capture_output=True,
                text=True,
                check=False,
            )
            pids = [
                int(pid)
                for pid in result.stdout.strip().split()
                if pid.isdigit()
            ]
        except (FileNotFoundError, subprocess.SubprocessError):
            pids = []

    if not pids:
        print("No stale processes found")
        print()
        return

    print(f"Found {len(pids)} stale process(es): {', '.join(map(str, pids))}")
    token = _loopback_token()

    for pid in pids:
        ports: list[int] = []
        if psutil is not None:
            try:
                proc = psutil.Process(pid)
                ports = sorted(
                    {
                        conn.laddr.port
                        for conn in proc.connections(kind="inet")
                        if conn.status == "LISTEN"
                    }
                )
            except (psutil.Error, AttributeError):
                ports = []

        if _request_graceful_shutdown(pid, ports, token):
            if _wait_for_exit(pid):
                print(f"Gracefully shut down process {pid}")
                continue
            print(f"Process {pid} did not exit after shutdown request")

        _terminate_with_sigterm(pid)
        if _wait_for_exit(pid):
            print(f"Sent SIGTERM to process {pid}; exited cleanly")
        else:
            print(f"Warning: process {pid} still alive after SIGTERM")

    print("✅ Cleaned up stale processes")
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


def _run_optional_smoke_suite(cmd: list[str], description: str) -> int:
    """Run one optional runtime smoke suite; empty collection is a pass.

    pytest exits 5 when no tests match the requested marker. The LLM/STT/art/
    TTS runtime smoke suites are optional and their tests may not exist in
    every checkout (issue #2055), so an empty collection is reported as a
    skip-style notice instead of failing CI.
    """
    exit_code = run_command(cmd, description, env=_build_pytest_env())
    if exit_code == 5:
        print(
            f"NOTE: {description}: no tests collected for the requested "
            "marker; treating as pass (optional suite)."
        )
        return 0
    return exit_code


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


def _gui_component_targets(base_path: Path, component: str) -> list[Path] | None:
    """Resolve one component into its GUI subtree."""
    gui_path = base_path / component / "gui"
    if gui_path.exists():
        return [gui_path]
    return None


def run_gui_functional_tests(
    component: str = None,
    verbose: bool = False,
) -> int:
    """Run headless GUI functional tests with mocked backends."""
    base_path = Path("src/airunner/components")
    test_targets = [base_path]
    description = "Headless GUI functional tests"

    if component:
        resolved = _gui_component_targets(base_path, component)
        if resolved is None:
            print(f"Error: GUI component '{component}' is not configured")
            return 1
        test_targets = resolved
        description = f"Headless GUI functional tests for {component}"

    cmd = _pytest_command(*[str(path) for path in test_targets])
    cmd.append("-v" if verbose else "--tb=short")
    cmd.extend(["--color=yes", "-ra", "-m", "gui_functional"])
    return run_command(cmd, description, env=_build_pytest_env())


def run_eval_tests(
    verbose: bool = False,
    model: str = None,
    skip_slow: bool = False,
    test_file: str = None,
    judge_service: str = None,
    judge_model: str = None,
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
    test_path = Path("services/tests/eval")

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

    # Pass model path through the environment if specified.
    env = _build_pytest_env()
    if model:
        env["AIRUNNER_TEST_MODEL_PATH"] = model
        print(f"Using model: {model}")
    if judge_service:
        env["AIRUNNER_TEST_JUDGE_SERVICE"] = judge_service
        print(f"Using judge service: {judge_service}")
    if judge_model:
        env["AIRUNNER_TEST_JUDGE_MODEL"] = judge_model
        print(f"Using judge model: {judge_model}")

    description = (
        f"Evaluation framework tests{' - ' + test_file if test_file else ''}"
    )
    return run_command(cmd, description, env=env)


def run_llm_runtime_smoke_tests(verbose: bool = False) -> int:
    """Run the safe llama.cpp runtime smoke suite."""
    test_path = Path("services/tests")
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
    return _run_optional_smoke_suite(cmd, "LLM runtime smoke tests")


def run_stt_runtime_smoke_tests(verbose: bool = False) -> int:
    """Run the safe STT runtime smoke suite."""
    test_path = Path("services/tests")
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
    return _run_optional_smoke_suite(cmd, "STT runtime smoke tests")


def run_art_runtime_smoke_tests(verbose: bool = False) -> int:
    """Run the safe art runtime smoke suite."""
    test_path = Path("services/tests")
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
    return _run_optional_smoke_suite(cmd, "Art runtime smoke tests")


def run_art_service_runtime_tests(verbose: bool = False) -> int:
    """Run the direct art service runtime suite."""
    test_path = Path("services/src/airunner_services/tests/functional")
    cmd = _pytest_command(
        str(test_path),
        "-m",
        "art_service_runtime",
    )

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("--tb=short")

    cmd.extend(["--color=yes", "-ra"])
    return run_command(
        cmd,
        "Direct art service runtime tests",
        env=_build_pytest_env(),
    )


def run_tts_runtime_smoke_tests(verbose: bool = False) -> int:
    """Run the safe TTS runtime smoke suite."""
    test_path = Path("services/tests")
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
    return _run_optional_smoke_suite(cmd, "TTS runtime smoke tests")


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Run AI Runner test suites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --unit                    Run all unit tests
    %(prog)s --eval                    Run eval tests only
        %(prog)s --eval --judge-model qwen3.5-9b
                                                                            Run judged evals with a
                                                                            separate local judge model
        %(prog)s --eval --service groq --llm llama-3.3-70b-versatile
                                                                            Run judged evals through Groq
    %(prog)s --llm-runtime-smoke       Run safe llama.cpp runtime smoke tests
    %(prog)s --stt-runtime-smoke       Run safe STT runtime smoke tests
    %(prog)s --art-runtime-smoke       Run safe art runtime smoke tests
    %(prog)s --art-service-runtime     Run direct art service runtime tests
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
        "--art-service-runtime",
        action="store_true",
        help="Run direct art service runtime tests",
    )

    parser.add_argument(
        "--tts-runtime-smoke",
        action="store_true",
        help="Run safe TTS runtime smoke tests",
    )

    parser.add_argument(
        "--gui-functional",
        action="store_true",
        help="Run headless GUI functional tests with mocked backends",
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
        "--judge-model",
        "--llm",
        dest="judge_model",
        type=str,
        help=(
            "Judge model name for judged evals. Use this to override "
            "the local judge model or select an external judge model."
        ),
    )

    parser.add_argument(
        "--judge-service",
        "--service",
        dest="judge_service",
        choices=["airunner", "local", "groq", "openrouter"],
        help=(
            "Judge provider for judged evals. Defaults to the local "
            "AIRunner daemon."
        ),
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

    if (
        args.judge_service
        and args.judge_service not in {"airunner", "local"}
        and not args.judge_model
    ):
        parser.error(
            "--judge-model/--llm is required for external judge services"
        )

    # Default to running unit tests if no flags specified
    if not (
        args.unit
        or args.eval
        or args.llm_runtime_smoke
        or args.stt_runtime_smoke
        or args.art_runtime_smoke
        or args.art_service_runtime
        or args.tts_runtime_smoke
        or args.gui_functional
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

    if args.art_service_runtime:
        exit_code = run_art_service_runtime_tests(verbose=args.verbose)
        exit_codes.append(exit_code)

    if args.tts_runtime_smoke or args.all:
        exit_code = run_tts_runtime_smoke_tests(verbose=args.verbose)
        exit_codes.append(exit_code)

    if args.gui_functional:
        exit_code = run_gui_functional_tests(
            component=args.component,
            verbose=args.verbose,
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
            judge_service=args.judge_service,
            judge_model=args.judge_model,
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
