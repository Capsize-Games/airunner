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
# import. "This project" packages are the keys of this dict plus
# "airunner_services.vendor" and "airunner_services.eval", which are
# checked as separate, narrower owners below.
OWNED_ROOTS: dict[str, tuple[str, frozenset[str]]] = {
    "src/airunner": (
        "airunner",
        frozenset(
            {"airunner_services", "airunner_common", "airunner_native"}
        ),
    ),
    "services/src/airunner_services": (
        "airunner_services",
        frozenset({"airunner_common"}),
    ),
    "native/src/airunner_native": (
        "airunner_native",
        # See check_import_boundaries.py's module docstring:
        # launcher.py structurally needs to import what it launches.
        frozenset({"airunner", "airunner_services", "airunner_common"}),
    ),
    "shared/airunner_common": (
        "airunner_common",
        frozenset(),
    ),
}

# Project package names recognized anywhere (used to detect a
# disallowed import even when it isn't the file's own owning root).
PROJECT_PACKAGES = frozenset(
    {"airunner", "airunner_common", "airunner_services", "airunner_native"}
)

VENDOR_REL_ROOT = "services/src/airunner_services/vendor"
EVAL_REL_ROOT = "services/src/airunner_services/eval"


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
        in_vendor = rel.startswith(VENDOR_REL_ROOT)
        in_eval = rel.startswith(EVAL_REL_ROOT)

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

            if in_vendor:
                # Rule: vendor must not import anything from this
                # project *outside its own subtree*. A vendor file
                # importing a sibling vendor module (melo importing
                # melo.commons, say) is fine; that is the vendored
                # library's own internal structure, not a project
                # dependency.
                if module == "airunner_services.vendor" or (
                    module.startswith("airunner_services.vendor.")
                ):
                    continue
                violations.append(
                    Violation(
                        Path(rel),
                        lineno,
                        module,
                        "airunner_services.vendor must import nothing "
                        "from this project outside its own subtree",
                    )
                )
                continue

            if not in_eval and (
                module == "airunner_services.eval"
                or module.startswith("airunner_services.eval.")
            ):
                violations.append(
                    Violation(
                        Path(rel),
                        lineno,
                        module,
                        "nothing outside airunner_services.eval may "
                        "import airunner_services.eval",
                    )
                )
                continue

            if top == owner_name:
                continue  # importing within your own package is fine

            if in_eval and top in {"airunner_services", "airunner_common"}:
                continue

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
