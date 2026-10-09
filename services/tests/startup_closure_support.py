"""Transitive module-scope import walker for startup checks.

Follows the modules imported at module scope from entry points,
through absolute and relative imports, and reports the third-party
top-level packages reached. Typing-only branches are skipped; live
conditional branches are followed conservatively. Supports the
"imported base-startup requirements are declared" acceptance of
release issue P02.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path


def _module_level_imports(path: Path) -> list[ast.Import | ast.ImportFrom]:
    """Module-scope imports, following live branches only."""
    found: list[ast.Import | ast.ImportFrom] = []
    body = ast.parse(path.read_text(encoding="utf-8")).body
    pending: list[list[ast.stmt]] = [body]
    while pending:
        for node in pending.pop():
            if isinstance(node, ast.If):
                if "TYPE_CHECKING" not in ast.dump(node.test):
                    pending.extend((node.body, node.orelse))
            elif isinstance(node, ast.Try):
                pending.extend(_try_bodies(node))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                found.append(node)
    return found


def _tolerates_import_failure(handler: ast.ExceptHandler) -> bool:
    """Whether an except handler swallows a failed try-body import."""
    if handler.type is None:
        caught = ""
    else:
        caught = ast.dump(handler.type)
    relevant = (
        not caught
        or "ImportError" in caught
        or "ModuleNotFound" in caught
        or "Exception" in caught
    )
    if not relevant:
        return False
    return not any(isinstance(node, ast.Raise) for node in handler.body)


def _try_bodies(node: ast.Try) -> list[list[ast.stmt]]:
    """Bodies of a try statement whose imports may execute."""
    bodies = [handler.body for handler in node.handlers]
    bodies.extend((node.orelse, node.finalbody))
    if not any(_tolerates_import_failure(h) for h in node.handlers):
        bodies.append(node.body)
    return bodies


def _resolve_module(root: Path, dotted: str) -> Path | None:
    """Resolve a dotted name to a module file under root, if any."""
    relative = dotted.replace(".", "/")
    for found in (root / f"{relative}.py", root / relative / "__init__.py"):
        if found.is_file():
            return found
    return None


def _anchor_package(
    roots: dict[str, Path], package: str, path: Path
) -> str:
    """Containing package dotted name for relative-import resolution."""
    relative = path.relative_to(roots[package]).with_suffix("")
    parts = list(relative.parts)[:-1]
    if not parts:
        return package
    return f"{package}.{'.'.join(parts)}"


class _ClosureWalker:
    """Follows module-scope imports transitively from entry modules."""

    def __init__(self, roots: dict[str, Path]) -> None:
        self._roots = roots
        self._seen: set[Path] = set()
        self._third_party: set[str] = set()
        self._stack: list[tuple[str, Path]] = []

    def closure(self, entries: list[tuple[str, Path]]) -> set[str]:
        """Third-party top-level imports reachable from entries."""
        self._stack = list(entries)
        while self._stack:
            package, path = self._stack.pop()
            if path in self._seen:
                continue
            self._seen.add(path)
            self._follow_module(package, path)
        return self._third_party

    def _follow_module(self, package: str, path: Path) -> None:
        """Follow one module's imports into the stack or aside."""
        anchor = _anchor_package(self._roots, package, path)
        for node in _module_level_imports(path):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._push_absolute(alias.name)
                continue
            if node.level:
                self._push_relative(anchor, node)
                continue
            assert node.module, f"bad from-import {path}"
            for alias in node.names:
                self._push_absolute(f"{node.module}.{alias.name}")

    def _push_relative(self, anchor: str, node: ast.ImportFrom) -> None:
        """Follow a relative from-import via its absolute name."""
        base = importlib.util.resolve_name(
            "." * node.level + (node.module or ""), anchor
        )
        for alias in node.names:
            self._push_absolute(f"{base}.{alias.name}")

    def _push_absolute(self, dotted: str) -> None:
        """Follow one absolute dotted import into the stack or aside."""
        top, *bits = dotted.split(".")
        if top in sys.stdlib_module_names:
            return
        if top not in self._roots:
            self._third_party.add(top)
            return
        for end in range(len(bits), 0, -1):
            found = _resolve_module(self._roots[top], ".".join(bits[:end]))
            if found is not None:
                self._stack.append((top, found))
                return
        self._stack.append((top, self._roots[top] / "__init__.py"))


def startup_closure(
    roots: dict[str, Path], entries: list[tuple[str, Path]]
) -> set[str]:
    """Third-party top-level imports reachable from entry modules."""
    return _ClosureWalker(roots).closure(entries)
