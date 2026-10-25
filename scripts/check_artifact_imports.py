"""Fail a release when a built artifact imports what it does not declare.

Why this exists
---------------
`pip install airunner==6.1.3` resolved, installed, and then could not start:
``airunner_services`` imports ``pygments`` at module scope and no distribution
declared it, so the daemon died during import and the launcher reported
"daemon unavailable".

The release workflow builds the wheels and publishes them. Nothing in between
ever installs an artifact and looks at it. The existing ``runtime-smoke`` jobs
run from a *source checkout*, where the developer environment already supplies
``pygments``, ``torch`` and ``transformers`` -- which is why CI stayed green
while the published wheel was dead on arrival.

Earlier fixes for this same class (issues #2037, #2040) worked by hand-listing
the missing imports. That list was incomplete. This is the gate that replaces
the list.

What it checks
--------------
Run it *inside a clean environment that has the built wheels installed*. It
walks every shipped module, collects **module-scope** imports -- the ones that
raise at import time rather than lazily -- and asserts each one is importable.

Anything intentionally optional must be named in ``packaging/optional_imports.toml``
with a reason. That file is the reviewed record of which imports are allowed to
be absent; silence is not a decision.

Usage
-----
    python -m venv /tmp/gate && /tmp/gate/bin/pip install dist/*.whl
    /tmp/gate/bin/python scripts/check_artifact_imports.py

Exit code 0 = every module-scope import is satisfied or explicitly optional.
Exit code 1 = the artifact would fail for a user; do not publish it.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import pathlib
import sys
import sysconfig

import tomllib

# Distributions built from this repository. Imports between them are internal
# and are validated by being importable like any other. Matched exactly:
# a prefix glob such as `airunner*` also catches vendored copies and
# unrelated names (e.g. airunner_common), silently treating them as
# first-party.
OWN_DISTRIBUTIONS = (
    "airunner",
    "airunner_common",
    "airunner_native",
    "airunner_services",
)

DEFAULT_ALLOWLIST = (
    pathlib.Path(__file__).resolve().parent.parent
    / "packaging"
    / "optional_imports.toml"
)


def _site_packages() -> pathlib.Path:
    """The environment's site-packages -- i.e. the artifact as a user gets it."""
    purelib = sysconfig.get_paths().get("purelib")
    if not purelib:
        raise SystemExit("could not locate site-packages for this interpreter")
    return pathlib.Path(purelib)


def _is_type_checking_guard(node: ast.If) -> bool:
    """Return True when an `if` body only runs for type checkers."""
    test = node.test
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    return (
        isinstance(test, ast.Attribute)
        and test.attr == "TYPE_CHECKING"
    )


def _handler_covers_import_error(node: ast.Try) -> bool:
    """Return True when every import in try can fail gracefully.

    A ``try`` whose handlers catch ImportError (or catch-all) is the
    graceful-degradation pattern optional dependencies are supposed to
    follow. Any other try (try/finally, try/except ValueError) still
    raises at import time when the module is missing.
    """
    if not node.handlers:
        return False  # try/finally: nothing is caught
    for handler in node.handlers:
        if handler.type is None:
            return True  # bare `except:` catches everything
        caught = handler.type
        if isinstance(caught, ast.Name) and caught.id in (
            "ImportError",
            "Exception",
            "BaseException",
        ):
            return True
        if isinstance(caught, ast.Tuple):
            for name in caught.elts:
                if isinstance(name, ast.Name) and name.id in (
                    "ImportError",
                    "Exception",
                    "BaseException",
                ):
                    return True
    return False


def _module_scope_imports(tree: ast.Module) -> set[str]:
    """Top-level import names only.

    An import nested in a function fails lazily, at worst when that
    code path runs. A module-scope import fails for everyone, on
    import, which is the failure this gate exists to catch. Module-level
    ``try``/``if`` bodies count too -- they still execute at import
    time -- except the two graceful patterns: a ``try`` guarded by an
    ImportError (or broader) handler, and ``if TYPE_CHECKING:`` bodies,
    which never run outside a type checker.
    """
    names: set[str] = set()

    def record(node: ast.Import | ast.ImportFrom) -> None:
        if isinstance(node, ast.Import):
            names.update(
                alias.name.split(".")[0] for alias in node.names
            )
        elif not node.level and node.module:
            # Relative imports resolve within the package itself.
            names.add(node.module.split(".")[0])

    def visit(statements: list[ast.stmt]) -> None:
        for node in statements:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                record(node)
            elif isinstance(node, ast.Try):
                # `else`/`finally` run at import time outside the
                # handlers' protection, so they always count; only
                # the `try` body itself is excused by graceful
                # handling. Handler bodies are failure-path-only.
                if not _handler_covers_import_error(node):
                    visit(node.body)
                visit(node.orelse)
                visit(node.finalbody)
            elif isinstance(node, ast.If):
                if _is_type_checking_guard(node):
                    continue
                visit(node.body)
                visit(node.orelse)

    visit(tree.body)
    return names


def collect(site_packages: pathlib.Path) -> dict[str, list[str]]:
    """Map each third-party module-scope import to the files that import it."""
    stdlib = set(sys.stdlib_module_names)
    found: dict[str, list[str]] = {}
    for distribution in OWN_DISTRIBUTIONS:
        root = site_packages / distribution
        if not root.is_dir():
            continue
        for py in sorted(root.rglob("*.py")):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
            except SyntaxError:
                # A file that will not parse cannot be imported either, but
                # that is a build problem, not a declaration problem.
                continue
            for name in _module_scope_imports(tree):
                if name in stdlib or name == "__future__":
                    continue
                if name in OWN_DISTRIBUTIONS:
                    continue
                found.setdefault(name, []).append(
                    str(py.relative_to(site_packages))
                )
    return found


def load_allowlist(path: pathlib.Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {
        name: str(entry.get("reason", ""))
        for name, entry in data.get("optional", {}).items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allowlist",
        type=pathlib.Path,
        default=DEFAULT_ALLOWLIST,
        help="TOML file naming imports that may legitimately be absent.",
    )
    args = parser.parse_args()

    site_packages = _site_packages()
    imports = collect(site_packages)
    if not imports:
        print(
            f"error: no airunner packages found in {site_packages}.\n"
            "Install the built wheels into this environment first.",
            file=sys.stderr,
        )
        return 1

    allowed = load_allowlist(args.allowlist)
    missing = {
        name: files
        for name, files in imports.items()
        if importlib.util.find_spec(name) is None
    }
    undeclared = {n: f for n, f in missing.items() if n not in allowed}
    optional_absent = sorted(n for n in missing if n in allowed)

    print(f"scanned {site_packages}")
    print(f"  module-scope third-party imports: {len(imports)}")
    print(f"  satisfied:                        {len(imports) - len(missing)}")
    print(f"  absent but declared optional:     {len(optional_absent)}")
    print(f"  UNDECLARED:                       {len(undeclared)}")

    if optional_absent:
        print("\noptional, absent by design:")
        for name in optional_absent:
            print(f"  {name:<26} {allowed[name]}")

    if undeclared:
        print("\nUNDECLARED module-scope imports -- this artifact will fail for users:")
        for name, files in sorted(undeclared.items()):
            print(f"  {name:<26} imported at module scope by {len(files)} file(s)")
            for path in files[:3]:
                print(f"      {path}")
            if len(files) > 3:
                print(f"      ... and {len(files) - 3} more")
        print(
            "\nEither declare each one as a dependency, or add it to\n"
            f"{args.allowlist} with a reason if it is genuinely optional\n"
            "(and make the importing module degrade gracefully when it is absent)."
        )
        return 1

    print("\nOK: every module-scope import is satisfied or explicitly optional.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
