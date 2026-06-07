#!/usr/bin/env python3
"""Pre-commit hook that enforces code size and complexity constraints.

Rules (configurable via constants below):
- Files must be at most ``MAX_FILE_LINES`` lines.
- Functions/methods must be at most ``MAX_FUNCTION_LINES`` body lines
  (decorators, the def signature, and the docstring are excluded).
- Functions/methods must have a McCabe cyclomatic complexity at or
  below ``MAX_COMPLEXITY``.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

MAX_FILE_LINES = 250
MAX_FUNCTION_LINES = 40
MAX_COMPLEXITY = 12


def _file_too_long(path: Path, source_lines: list[str]) -> str | None:
    """Return an error message when *path* exceeds ``MAX_FILE_LINES``."""
    total = len(source_lines)
    if total > MAX_FILE_LINES:
        return f"{path}: {total} lines (max {MAX_FILE_LINES})"
    return None


def _get_function_body_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count the body lines of one function, excluding docstrings."""
    if not node.body:
        return 0

    first_body = node.body[0]
    # Skip the docstring if present
    if (
        isinstance(first_body, ast.Expr)
        and isinstance(first_body.value, ast.Constant)
        and isinstance(first_body.value.value, str)
    ):
        body = node.body[1:]
    else:
        body = node.body

    if not body:
        return 0

    first_line = body[0].lineno
    last_line = body[-1].end_lineno or body[-1].lineno
    return last_line - first_line + 1


def _compute_mccabe(node: ast.AST) -> int:
    """Compute McCabe cyclomatic complexity for a single AST node."""
    # Count the function/method itself as 1
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                              ast.ExceptHandler, ast.With, ast.AsyncWith,
                              ast.Assert)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            # Each 'and' / 'or' adds 1
            complexity += len(child.values) - 1
        elif isinstance(child, (ast.Match,)):
            complexity += 1
        elif isinstance(child, ast.comprehension):
            complexity += 1
    return complexity


def _check_functions(tree: ast.AST, path: Path,
                     source_code: str) -> list[str]:
    """Return error messages for functions that exceed limits."""
    errors: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        body_lines = _get_function_body_lines(node)
        if body_lines > MAX_FUNCTION_LINES:
            errors.append(
                f"{path}:{node.lineno} "
                f"function {node.name} has {body_lines} body lines "
                f"(max {MAX_FUNCTION_LINES})"
            )

        complexity = _compute_mccabe(node)
        if complexity > MAX_COMPLEXITY:
            errors.append(
                f"{path}:{node.lineno} "
                f"function {node.name} has McCabe complexity "
                f"{complexity} (max {MAX_COMPLEXITY})"
            )

    return errors


def _check_one(path: Path) -> int:
    """Run all checks on a single Python file. Returns 1 on failure."""
    if not path.suffix == ".py" or not path.is_file():
        return 0

    raw = path.read_text(encoding="utf-8")
    source_lines = raw.splitlines()

    err = _file_too_long(path, source_lines)
    if err is not None:
        print(err)

    try:
        tree = ast.parse(raw, filename=str(path))
    except SyntaxError:
        return 1 if err is not None else 0

    func_errors = _check_functions(tree, path, raw)
    for e in func_errors:
        print(e)

    return 1 if (err is not None or func_errors) else 0


def main() -> int:
    """Run checks on all Python files passed as arguments."""
    paths = [Path(p) for p in sys.argv[1:]]
    return max(_check_one(p) for p in paths) if paths else 0


if __name__ == "__main__":
    sys.exit(main())
