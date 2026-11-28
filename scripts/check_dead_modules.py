"""Fail-closed dead-module gate for the services tree (issue #2480).

A module is dead when nothing references it: no static import, no
dotted-path string reference (registries, lazy ``__getattr__`` surface,
console-script tables), no ``__main__`` execution, and no living
submodule beneath it. Anything dead that is not a documented framework
exclusion (tests, alembic migrations, generated files) must be named in
``scripts/dead_module_allowlist.py`` with a justification, or this
script exits non-zero -- so newly abandoned modules fail CI instead of
accumulating silently.

Only the standard library is used so the gate runs in any CI job with
plain CPython, including the minimal tools wheelhouse. Run from the
repository root::

    python scripts/check_dead_modules.py

Exit codes: 0 when every module is referenced or allowlisted,
1 when unlisted dead modules exist, 2 on configuration errors.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

_REPO_ROOT = Path(__file__).resolve().parent.parent

PACKAGE_ROOT = _REPO_ROOT / "services" / "src" / "airunner_services"
TESTS_ROOT = _REPO_ROOT / "services" / "tests"

# Subtrees that are framework-managed, generated, or collected rather
# than imported. They are never flagged, but files inside them still
# count as importers when they reference real modules.
EXCLUDED_PARTS = frozenset({"tests", "alembic", "vendor", "__pycache__"})

# ``name=module:attr`` console-script strings (services/setup.py,
# frozen-bundle tables) reference the module between ``=`` and ``:``.
_CONSOLE_SCRIPT_RE = re.compile(r"=([A-Za-z_][\w.]*):[A-Za-z_]")


def _module_name(package_root: Path, path: Path) -> str:
    """Return the dotted module name for a file under the package root."""
    rel = path.relative_to(package_root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return "airunner_services" + ("." + ".".join(parts) if parts else "")


def _is_flaggable(package_root: Path, path: Path) -> bool:
    """Return whether a module can ever be reported as dead."""
    if path.name == "__main__.py":
        return False
    if "__pycache__" in path.parts:
        return False
    rel_parts = path.relative_to(package_root).parts
    if any(part in EXCLUDED_PARTS for part in rel_parts):
        return False
    if path.stem.endswith(("_ui", "_rc")):
        return False
    return True


def _docstring_ids(tree: ast.Module) -> set[int]:
    """Return ``id()``s of docstring constants (module/class/function)."""
    found: set[int] = set()

    def _visit(node: ast.AST) -> None:
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                found.add(id(first.value))
        for child in ast.iter_child_nodes(node):
            _visit(child)

    _visit(tree)
    return found


def _containing_package(module: str, filename: str) -> str:
    """Return the package used for relative-import resolution."""
    if filename == "__init__.py":
        return module
    return module.rpartition(".")[0]


def _resolve_relative(
    module: str, filename: str, level: int, name: str | None
) -> str | None:
    """Resolve a relative ``from`` import to a dotted module path."""
    package = _containing_package(module, filename)
    base = package.split(".") if package else []
    if level - 1 > len(base):
        return None
    prefix = base[: len(base) - (level - 1)] if level > 1 else base
    if name:
        return ".".join(prefix + [name])
    return ".".join(prefix) if prefix else None


def collect_references(
    package_root: Path, importer_files: list[Path], known: set[str]
) -> set[str]:
    """Return every known module referenced by the importer files.

    Counts static imports (including function-level and relative ones),
    ``from X import Y`` submodule references, non-docstring string
    literals that exactly name a module, ``name=module:attr``
    console-script strings, and ``__all__`` short names in package
    ``__init__`` files (the lazy ``__getattr__`` surface used by
    ``api.routes``). Docstring prose (``:mod:`` mentions, design notes)
    never counts: documenting a module is not loading it.
    """
    referenced: set[str] = set()
    for path in importer_files:
        if path.suffix != ".py" or "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(
                path.read_text(encoding="utf-8"), filename=str(path)
            )
        except (OSError, SyntaxError, ValueError):
            continue
        try:
            module = _module_name(package_root, path)
            in_package = True
        except ValueError:
            # Importer outside the package (services/tests, scripts):
            # only real import statements count. String literals out
            # here are policy data, documentation, or test assertions --
            # including this gate's own allowlist, whose keys name every
            # exempted module and must never self-license them.
            module = ""
            in_package = False
            docstrings: set[int] = set()
        else:
            docstrings = _docstring_ids(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    referenced.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    target = _resolve_relative(
                        module, path.name, node.level, node.module
                    )
                    if target:
                        if node.module:
                            referenced.add(target)
                        else:
                            for alias in node.names:
                                if alias.name != "*":
                                    referenced.add(target + "." + alias.name)
                    continue
                if node.module:
                    referenced.add(node.module)
                    for alias in node.names:
                        if alias.name != "*":
                            referenced.add(node.module + "." + alias.name)
            elif not in_package:
                continue
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
            ):
                literal = node.value.strip()
                referenced.add(literal)
                match = _CONSOLE_SCRIPT_RE.search(literal)
                if match:
                    referenced.add(match.group(1))
            elif (
                isinstance(node, ast.Assign)
                and path.name == "__init__.py"
                and module
                and any(
                    isinstance(target, ast.Name) and target.id == "__all__"
                    for target in node.targets
                )
                and isinstance(node.value, (ast.List, ast.Tuple))
            ):
                for element in node.value.elts:
                    if isinstance(element, ast.Constant) and isinstance(
                        element.value, str
                    ):
                        referenced.add(module + "." + element.value)
    # Keep references that name a module or a parent of one; drop every
    # other string literal so prose can never mark a module live.
    return {
        ref
        for ref in referenced
        if ref in known
        or any(m == ref or m.startswith(ref + ".") for m in known)
    }


def collect_text_references(
    roots: list[Path], known: set[str]
) -> set[str]:
    """Return known modules named in packaging/service/shell text files.

    Frozen-bundle specs (``packaging/linux/*.toml``), systemd units, and
    dev scripts name entry modules outside Python import statements
    (``module = "airunner_services.bin.airunner_service"``). A bare
    substring scan would over-match, so only full dotted paths that
    resolve to a real module count.
    """
    pattern = re.compile(r"airunner_services\.[A-Za-z_][A-Za-z0-9_.]*")
    found: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix in {
                ".py",
                ".pyc",
            } or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="strict")
            except (OSError, ValueError):
                continue
            found.update(
                candidate
                for candidate in pattern.findall(text)
                if candidate in known
            )
    return found


def find_package_modules(package_root: Path) -> dict[str, Path]:
    """Map every dotted module in the package tree to its file."""
    modules: dict[str, Path] = {}
    for path in sorted(package_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        modules[_module_name(package_root, path)] = path
    return modules


def _is_live(module: str, referenced: set[str]) -> bool:
    """Return whether a module is imported or parents a reference."""
    if module in referenced:
        return True
    return any(ref.startswith(module + ".") for ref in referenced)


def raw_orphans(
    package_root: Path | None = None,
    extra_importer_roots: list[Path] | None = None,
    text_roots: list[Path] | None = None,
) -> tuple[dict[str, Path], set[str]]:
    """Return ``(modules, orphans)`` before the allowlist is applied."""
    package_root = (package_root or PACKAGE_ROOT).resolve()
    if not package_root.is_dir():
        raise FileNotFoundError(f"package root missing: {package_root}")
    modules = find_package_modules(package_root)
    known = set(modules)

    importer_files = list(modules.values())
    if extra_importer_roots is None:
        extra_importer_roots = [TESTS_ROOT, Path(_SCRIPTS_DIR)]
    for extra in extra_importer_roots:
        extra = Path(extra)
        if extra.is_dir():
            importer_files.extend(sorted(extra.rglob("*.py")))
        elif extra.is_file() and extra.suffix == ".py":
            importer_files.append(extra)

    referenced = collect_references(package_root, importer_files, known)
    if text_roots is None:
        text_roots = [
            _REPO_ROOT / "packaging" / "linux",
            _REPO_ROOT / "deployment",
            _REPO_ROOT / "scripts" / "dev",
        ]
    referenced |= collect_text_references(text_roots, known)
    live = {module for module in known if _is_live(module, referenced)}
    # A package __init__ executes on any living submodule import.
    for module, path in modules.items():
        if (
            path.name == "__init__.py"
            and module not in live
            and any(
                other != module
                and other.startswith(module + ".")
                and other in live
                for other in known
            )
        ):
            live.add(module)
    orphans = {
        module
        for module in known
        if module not in live and _is_flaggable(package_root, modules[module])
    }
    return modules, orphans


def run_check(repo_root: Path | None = None) -> list[str]:
    """Return one human-readable problem per unlisted dead module."""
    from dead_module_allowlist import ALLOWLIST

    root = (repo_root or _REPO_ROOT).resolve()
    modules, orphans = raw_orphans(
        root / "services" / "src" / "airunner_services",
        [root / "services" / "tests", root / "scripts"],
    )
    problems = []
    for module in sorted(orphans):
        if module in ALLOWLIST:
            continue
        path = modules[module].relative_to(root).as_posix()
        problems.append(f"dead module {module} ({path})")
    return problems


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python scripts/check_dead_modules.py``."""
    parser = argparse.ArgumentParser(
        description="Fail when the services tree has unlisted dead modules."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_REPO_ROOT,
        help="Repository root (default: inferred from this file).",
    )
    args = parser.parse_args(argv)
    try:
        problems = run_check(repo_root=args.root)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if problems:
        print(f"Found {len(problems)} dead module(s):\n")
        for problem in problems:
            print(f"  - {problem}")
        print(
            "\nReference the module (import it, register it by dotted path, "
            "or add a justified entry to scripts/dead_module_allowlist.py)."
        )
        return 1
    print("No unlisted dead modules found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
