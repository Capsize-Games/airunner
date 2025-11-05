#!/usr/bin/env python
"""
Unused imports remover for AI Runner codebase.

Uses autoflake to automatically remove unused imports from Python files.
Excludes auto-generated files, tests, and specific directories.

Usage:
    airunner-remove-unused-imports [--path PATH] [--check] [--verbose]

Examples:
    # Remove unused imports from entire codebase
    airunner-remove-unused-imports

    # Check for unused imports without modifying files
    airunner-remove-unused-imports --check

    # Remove from specific file or directory
    airunner-remove-unused-imports --path src/airunner/components/llm

    # Verbose output
    airunner-remove-unused-imports --verbose
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


# Permanent exclusions - always skip these
PERMANENT_EXCLUSIONS = [
    "_ui.py",  # Auto-generated Qt UI files (don't modify generated code)
    "alembic",  # Database migrations
    "/data/",  # Data models (may have imports for SQLAlchemy)
    "__pycache__",
    ".venv",
    "__init__.py",
    "venv",
    "build",
    "dist",
]


def find_python_files(
    root_path: Path, exclude_patterns: List[str]
) -> List[Path]:
    """
    Find all Python files in the project.

    Args:
        root_path: Root directory or file to search
        exclude_patterns: Patterns to exclude

    Returns:
        List of Python file paths
    """
    # If root_path is a file, return it directly (after checking exclusions)
    if root_path.is_file() and root_path.suffix == ".py":
        for pattern in exclude_patterns:
            if pattern in str(root_path):
                print(f"Skipping excluded file: {root_path}")
                return []
        return [root_path]

    # Otherwise search directory
    python_files = []

    for py_file in root_path.rglob("*.py"):
        # Check exclusions
        skip = False
        for pattern in exclude_patterns:
            if pattern in str(py_file):
                skip = True
                break

        if not skip:
            python_files.append(py_file)

    return python_files


def run_autoflake(
    files: List[Path],
    check_only: bool = False,
    verbose: bool = False,
) -> int:
    """
    Run autoflake on the given files.

    Args:
        files: List of Python files to process
        check_only: If True, only check for unused imports without modifying
        verbose: Print detailed output

    Returns:
        Exit code (0 = success, 1 = issues found or error)
    """
    if not files:
        print("No files to process")
        return 0

    # Build autoflake command
    cmd = [
        "autoflake",
        "--remove-all-unused-imports",
        "--remove-unused-variables",
        "--remove-duplicate-keys",
        "--ignore-init-module-imports",  # Keep __init__.py imports
    ]

    if not check_only:
        cmd.append("--in-place")

    if check_only:
        cmd.append("--check")

    # Add files
    cmd.extend(str(f) for f in files)

    if verbose:
        print(f"Running: {' '.join(cmd)}")
        print(f"Processing {len(files)} files...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if verbose or result.stdout:
            print(result.stdout)

        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if check_only and result.returncode != 0:
            print(
                "\n⚠️  Unused imports found. Run without --check to remove them."
            )
            return 1
        elif not check_only and result.returncode == 0:
            print(f"✅ Successfully processed {len(files)} files")
            return 0
        elif result.returncode != 0:
            print(f"❌ autoflake exited with code {result.returncode}")
            return 1

        return result.returncode

    except FileNotFoundError:
        print(
            "ERROR: autoflake not found. Install with: pip install autoflake",
            file=sys.stderr,
        )
        return 1
    except Exception as e:
        print(f"ERROR: Failed to run autoflake: {e}", file=sys.stderr)
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Remove unused imports from AI Runner codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Remove from entire codebase
  %(prog)s --check                  # Check without modifying
  %(prog)s --path src/airunner/llm  # Process specific directory
  %(prog)s --verbose                # Show detailed output

Permanent exclusions (always skipped):
  - *_ui.py files (auto-generated Qt UI - don't modify generated code)
  - alembic/ (database migrations)
  - data/ directories (SQLAlchemy models)
  - vendor/ (third-party code)
        """,
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Path to analyze (default: src/airunner)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for unused imports without modifying files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        help="Additional patterns to exclude (beyond permanent exclusions)",
    )

    args = parser.parse_args()

    # Merge user exclusions with permanent ones
    all_exclusions = list(set(PERMANENT_EXCLUSIONS + args.exclude))

    # Determine root path
    if args.path:
        root_path = args.path
    else:
        # Find project root (look for setup.py)
        current = Path.cwd()
        while current != current.parent:
            if (current / "setup.py").exists():
                root_path = current / "src" / "airunner"
                break
            current = current.parent
        else:
            print(
                "ERROR: Could not find project root (setup.py)",
                file=sys.stderr,
            )
            sys.exit(1)

    if not root_path.exists():
        print(f"ERROR: Path does not exist: {root_path}", file=sys.stderr)
        sys.exit(1)

    # Find Python files
    python_files = find_python_files(root_path, all_exclusions)

    if not python_files:
        print(
            f"WARNING: No Python files found in {root_path}",
            file=sys.stderr,
        )
        sys.exit(0)

    if args.verbose:
        print(f"Found {len(python_files)} Python files to process")
        print(f"Exclusions: {', '.join(all_exclusions)}")
        print()

    # Run autoflake
    exit_code = run_autoflake(
        python_files,
        check_only=args.check,
        verbose=args.verbose,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
