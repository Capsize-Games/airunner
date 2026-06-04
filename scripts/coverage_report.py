"""Coverage report helper for AI Runner test suites."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _pytest_args(gui_functional: bool, component: str | None) -> list[str]:
    """Build one pytest target list for coverage runs."""
    if not gui_functional:
        return []

    base_path = Path("services/tests")
    if component:
        test_path = base_path / component
        if not test_path.exists():
            raise SystemExit(
                f"Service component '{component}' is not configured for coverage"
            )
        return [str(test_path), "-m", "gui_functional"]

    return [str(base_path), "-m", "gui_functional"]


def _run_command(cmd: list[str], report_file) -> None:
    """Run one coverage command and stop on failure."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        stdout=report_file if "report" in cmd else None,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    """Run coverage for the default or GUI functional test suite."""
    parser = argparse.ArgumentParser(description="Run AI Runner coverage")
    parser.add_argument(
        "--gui-functional",
        action="store_true",
        help="Run coverage for headless GUI functional tests only",
    )
    parser.add_argument(
        "--component",
        type=str,
        help="Optional component name for GUI functional coverage",
    )
    args = parser.parse_args()

    pytest_args = _pytest_args(args.gui_functional, args.component)
    commands = [
        ["coverage", "erase"],
        ["coverage", "run", "-m", "pytest", *pytest_args],
        ["coverage", "report"],
    ]

    with open("coverage_report.txt", "w", encoding="utf-8") as report_file:
        for cmd in commands:
            _run_command(cmd, report_file)


if __name__ == "__main__":
    main()
