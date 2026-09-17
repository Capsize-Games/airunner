"""Rule definitions and AST checks for check_import_boundaries.py.

Split out of that module (issue #2193) because the checking logic and
the allowed-dependency-graph data together pushed
check_import_boundaries.py well past this account's 250-line file
guideline. See that module's docstring for the actual policy this
enforces and why.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

# Each entry maps a source root (relative to the repo root) to the
# fully-qualified package name that root's files belong to, and the
# set of top-level project package names that package is allowed to
# import.
OWNED_ROOTS: dict[str, tuple[str, frozenset[str]]] = {
    "src/airunner": (
        "airunner",
        frozenset({"airunner_services", "airunner_native"}),
    ),
    "services/src/airunner_services": (
        "airunner_services",
        frozenset(),
    ),
    "native/src/airunner_native": (
        "airunner_native",
        # See check_import_boundaries.py's module docstring:
        # launcher.py structurally needs to import what it launches.
        frozenset({"airunner", "airunner_services"}),
    ),
}

# Project package names recognized anywhere (used to detect a
# disallowed import even when it isn't the file's own owning root).
# airunner_common is deliberately not here: it moved to its own
# repository (issue #2197, https://github.com/Capsize-Games/airunner-common)
# and is now an ordinary installed dependency like any other third-party
# package, not a project-internal boundary this checker enforces --
# there's no cycle risk left once it doesn't live in this repo's tree.
PROJECT_PACKAGES = frozenset(
    {"airunner", "airunner_services", "airunner_native"}
)


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    imported: str
    rule: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.imported} ({self.rule})"


def iter_python_files(directory: Path):
    for path in sorted(directory.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def imported_top_level_names(tree: ast.AST) -> list[tuple[int, str]]:
    """Return (lineno, dotted_module_path) for every import in a file.

    Walks the whole tree, not just module-level statements, so a
    function-body ``import`` counts exactly like a top-of-file one.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.module is None:
                continue  # relative "from . import x": not cross-package
            if node.module:
                found.append((node.lineno, node.module))
    return found


def check_owned_root(
    repo_root: Path,
    root_rel: str,
    owner_name: str,
    allowed: frozenset[str],
) -> list[Violation]:
    root = repo_root / root_rel
    if not root.is_dir():
        return []

    violations: list[Violation] = []
    for path in iter_python_files(root):
        rel = path.relative_to(repo_root).as_posix()

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            violations.append(
                Violation(
                    Path(rel), exc.lineno or 0, str(exc), "syntax-error"
                )
            )
            continue

        for lineno, module in imported_top_level_names(tree):
            top = module.split(".", 1)[0]
            if top not in PROJECT_PACKAGES:
                continue  # third-party or stdlib: not this checker's job

            if top == owner_name:
                continue  # importing within your own package is fine

            if top in allowed:
                continue

            violations.append(
                Violation(
                    Path(rel),
                    lineno,
                    module,
                    f"{owner_name} may not import {top}",
                )
            )
    return violations


def check_pyside6_not_at_module_scope(repo_root: Path) -> list[Violation]:
    """airunner_services must not import PySide6 at module scope.

    A function-level import is fine (several services modules already
    do this deliberately, guarded by try/except, so the service can
    run headless without PySide6 installed).
    """
    root = repo_root / "services/src/airunner_services"
    violations: list[Violation] = []
    if not root.is_dir():
        return violations

    for path in iter_python_files(root):
        rel = path.relative_to(repo_root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in tree.body:  # module-level statements only
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".", 1)[0] == "PySide6":
                    violations.append(
                        Violation(
                            Path(rel),
                            node.lineno,
                            name,
                            "airunner_services must not import PySide6 "
                            "at module scope",
                        )
                    )
    return violations
