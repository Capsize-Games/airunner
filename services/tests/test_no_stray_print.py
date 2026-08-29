"""Guard test: no stray print() instrumentation outside CLI surfaces (issue #2050).

Walks ``src/airunner`` and ``services/src`` and asserts every real builtin
``print(...)`` call is either:
- under a whitelisted CLI path (``bin/``, ``scripts/``), or
- carries the ``# intentional CLI output`` marker on the same line or the
  line above.

The scan is AST-based so it only matches actual ``print`` call nodes — custom
functions named like ``debug_print(...)`` and ``print`` examples inside
docstrings are not flagged. Test files and vendored code are excluded: tests
may print, and ``services/src/airunner_services/vendor`` is third-party.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_GUI_ROOT = _PROJECT_ROOT / "src" / "airunner"
_SERVICES_ROOT = _PROJECT_ROOT / "services" / "src" / "airunner_services"

_MARKER = "# intentional CLI output"
# Path fragments (relative to the scanned root) whose prints are always CLI.
_WHITELISTED_DIRS = ("bin", "scripts")
_EXCLUDED_DIRS = ("tests", "vendor", "__pycache__")


class _PrintCallFinder(ast.NodeVisitor):
    """Collect line numbers of real builtin ``print(...)`` calls."""

    def __init__(self) -> None:
        self.lines: list[int] = []

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.lines.append(node.lineno)
        self.generic_visit(node)


def _iter_python_files(root: Path):
    for path in sorted(root.rglob("*.py")):
        if any(part in _EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def _assert_no_stray_prints(root: Path) -> list[str]:
    """Return a list of offending 'file:line: content' strings."""
    offending: list[str] = []
    for path in _iter_python_files(root):
        rel = path.relative_to(root)
        if any(part in _WHITELISTED_DIRS for part in rel.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        finder = _PrintCallFinder()
        finder.visit(tree)
        if not finder.lines:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno in finder.lines:
            idx = lineno - 1
            line = lines[idx] if idx < len(lines) else ""
            previous = lines[idx - 1] if idx > 0 else ""
            if _MARKER in line or _MARKER in previous:
                continue
            offending.append(f"{rel}:{lineno}: {line.strip()}")
    return offending


def test_no_stray_print_in_gui() -> None:
    """Every print under src/airunner is CLI output or explicitly marked."""
    offending = _assert_no_stray_prints(_GUI_ROOT)
    assert not offending, (
        "print() without '# intentional CLI output' marker found under "
        f"src/airunner:\n" + "\n".join(offending)
    )


def test_no_stray_print_in_services() -> None:
    """Every print under services/src is CLI output or explicitly marked."""
    offending = _assert_no_stray_prints(_SERVICES_ROOT)
    assert not offending, (
        "print() without '# intentional CLI output' marker found under "
        f"services/src:\n" + "\n".join(offending)
    )


def _verdict(source: str, rel_parts: tuple[str, ...]) -> bool:
    """Return True when a print call is allowed for one synthetic file."""
    if any(part in _WHITELISTED_DIRS for part in rel_parts):
        return True
    if any(part in _EXCLUDED_DIRS for part in rel_parts):
        return True
    tree = ast.parse(source)
    finder = _PrintCallFinder()
    finder.visit(tree)
    lines = source.splitlines()
    for lineno in finder.lines:
        idx = lineno - 1
        line = lines[idx]
        previous = lines[idx - 1] if idx > 0 else ""
        if _MARKER in line or _MARKER in previous:
            continue
        return False
    return True


@pytest.mark.parametrize(
    "source,rel_parts,expected",
    [
        ("x = 1\nprint('debug')\n", ("foo.py",), False),
        ("x = 1\nprint('cli')  # intentional CLI output\n", ("foo.py",), True),
        ("x = 1\nprint('cli')\n", ("bin", "foo.py"), True),
        ("x = 1\nprint('cli')\n", ("scripts", "foo.py"), True),
        (
            "# intentional CLI output\nprint('multi')\n",
            ("foo.py",),
            True,
        ),
        ("print('test')\n", ("tests", "test_x.py"), True),
        ("print('v')\n", ("vendor", "x.py"), True),
        # custom-named function is not a builtin print call
        ("def debug_print(m):\n    print(m)\n", ("foo.py",), False),
        # docstring examples are not print calls
        ('"""\n>>> print("x")\n"""\n', ("foo.py",), True),
    ],
)
def test_marker_logic(source, rel_parts, expected) -> None:
    """Sanity check the whitelist/marker decision logic."""
    assert _verdict(source, rel_parts) is expected, (source, rel_parts)
