"""Coverage report helper for the services-only test suite."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def _pytest_args(component: str | None) -> list[str]:
    """Build one pytest target list for coverage runs."""
    base_path = Path("services") / "tests"
    if component:
        component_path = base_path / component
        if not component_path.exists():
            raise SystemExit(
                f"Component '{component}' is not configured for coverage"
            )
        return [str(component_path)]
    return [str(base_path)]


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
    """Run coverage for the services test suite."""
    parser = argparse.ArgumentParser(description="Run AI Runner coverage")
    parser.add_argument(
        "--component",
        type=str,
        help="Optional services test subdirectory for coverage",
    )
    args = parser.parse_args()

    pytest_args = _pytest_args(args.component)
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
