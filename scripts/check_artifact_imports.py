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
walks every shipped module and collects **module-scope** imports -- the ones
that raise at import time rather than lazily. It fails for missing base
requirements and missing requirements belonging to explicitly active extras.
Imports whose distributions are declared only by inactive extras are reported
as outside this profile's import check; the behavioral artifact gate separately
proves the supported base entrypoints and capability-unavailable response.

An undeclared missing import still fails. ``packaging/optional_imports.toml``
continues to cover only narrowly reviewed imports with no distribution
requirement in the built artifact metadata.

Usage
-----
    python -m venv /tmp/gate && /tmp/gate/bin/pip install dist/*.whl
    /tmp/gate/bin/python scripts/check_artifact_imports.py

Exit code 0 = base imports and the requested active extras are satisfied;
inactive extra imports are listed as untested by this profile.
Exit code 1 = a base/active-extra import is undeclared or missing.
"""

from __future__ import annotations

import argparse
import ast
import importlib.metadata as import_metadata
import importlib.util
import pathlib
import re
import sys
import sysconfig

import tomllib

from packaging.requirements import Requirement

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

# Import names do not always match their distribution names. Keep this mapping
# limited to established aliases needed by the shipped modules; it is not an
# optional-dependency allowlist.
IMPORT_DISTRIBUTION_ALIASES = {
    "bs4": "beautifulsoup4",
    "lingua": "lingua-language-detector",
}


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


def _canonical_distribution_name(name: str) -> str:
    """Normalize an import/distribution alias for PEP 503 name comparison."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _owner_distribution_metadata() -> list[import_metadata.Distribution]:
    """Return installed metadata for first-party distributions in this scan."""
    distributions = []
    for name in OWN_DISTRIBUTIONS:
        try:
            distributions.append(import_metadata.distribution(name))
        except import_metadata.PackageNotFoundError:
            continue
    return distributions


def _inactive_requirement_sources(
    import_name: str,
    distributions: list[import_metadata.Distribution],
    active_extras: set[str],
) -> list[str] | None:
    """Return declared but inactive requirement owners for one import.

    ``None`` means the import is required in this profile or has no matching
    declaration, so a missing module remains a gate failure. Extra-scoped and
    platform/version-scoped requirements are evaluated against the current
    interpreter and the explicitly selected extras.
    """
    target = _canonical_distribution_name(
        IMPORT_DISTRIBUTION_ALIASES.get(import_name, import_name)
    )
    inactive: set[str] = set()
    matched_requirement = False
    active_requirement = False

    for distribution in distributions:
        distribution_name = distribution.metadata.get("Name", "")
        if not distribution_name:
            continue
        provides_extra = set(
            distribution.metadata.get_all("Provides-Extra") or ()
        )
        for raw_requirement in distribution.requires or ():
            requirement = Requirement(raw_requirement)
            if _canonical_distribution_name(requirement.name) != target:
                continue
            matched_requirement = True
            marker = requirement.marker
            if marker is None or marker.evaluate({"extra": ""}):
                active_requirement = True
                continue

            for extra in provides_extra:
                if not marker.evaluate({"extra": extra}):
                    continue
                if extra in active_extras:
                    active_requirement = True
                else:
                    inactive.add(f"{distribution_name}[{extra}]")

            # A non-extra marker can be false for this interpreter/platform.
            if not inactive and not any(
                marker.evaluate({"extra": extra}) for extra in provides_extra
            ):
                inactive.add(
                    f"{distribution_name} (inactive environment marker)"
                )

    if active_requirement or not matched_requirement or not inactive:
        return None
    return sorted(inactive)


def classify_missing_imports(
    missing: dict[str, list[str]],
    allowlist: dict[str, str],
    distributions: list[import_metadata.Distribution],
    active_extras: set[str],
) -> tuple[
    dict[str, list[str]],
    dict[str, str],
    dict[str, tuple[list[str], list[str]]],
]:
    """Separate blockers from absent imports declared only by inactive extras."""
    undeclared: dict[str, list[str]] = {}
    optional_absent: dict[str, str] = {}
    inactive_extras: dict[str, tuple[list[str], list[str]]] = {}
    for name, files in missing.items():
        if name in allowlist:
            optional_absent[name] = allowlist[name]
            continue
        sources = _inactive_requirement_sources(
            name, distributions, active_extras
        )
        if sources is None:
            undeclared[name] = files
        else:
            inactive_extras[name] = (files, sources)
    return undeclared, optional_absent, inactive_extras


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allowlist",
        type=pathlib.Path,
        default=DEFAULT_ALLOWLIST,
        help="TOML file naming imports that may legitimately be absent.",
    )
    parser.add_argument(
        "--active-extra",
        action="append",
        default=[],
        help=(
            "Extra explicitly installed in this clean environment; repeat for "
            "each extra. Missing dependencies from these extras remain errors."
        ),
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
    distributions = _owner_distribution_metadata()
    known_extras = {
        extra
        for distribution in distributions
        for extra in (distribution.metadata.get_all("Provides-Extra") or ())
    }
    unknown_extras = sorted(set(args.active_extra) - known_extras)
    if unknown_extras:
        parser.error(
            "active extra(s) not declared by installed artifacts: "
            + ", ".join(unknown_extras)
        )
    missing = {
        name: files
        for name, files in imports.items()
        if importlib.util.find_spec(name) is None
    }
    undeclared, optional_absent, inactive_extras = classify_missing_imports(
        missing,
        allowed,
        distributions,
        set(args.active_extra),
    )

    print(f"scanned {site_packages}")
    print(
        "  active extras:                     "
        + (", ".join(sorted(set(args.active_extra))) or "(none; base profile)")
    )
    print(f"  module-scope third-party imports: {len(imports)}")
    print(f"  satisfied:                        {len(imports) - len(missing)}")
    print(f"  absent but declared optional:     {len(optional_absent)}")
    print(f"  declared only by inactive extras: {len(inactive_extras)}")
    print(f"  UNDECLARED:                       {len(undeclared)}")

    if optional_absent:
        print("\nreviewed optional imports absent by design:")
        for name, reason in sorted(optional_absent.items()):
            print(f"  {name:<26} {reason}")

    if inactive_extras:
        print("\nnot installed in this profile; declared by inactive extras:")
        for name, (files, sources) in sorted(inactive_extras.items()):
            print(f"  {name:<26} {', '.join(sources)}")
            for path in files[:3]:
                print(f"      {path}")
            if len(files) > 3:
                print(f"      ... and {len(files) - 3} more")

    if undeclared:
        print(
            "\nUNDECLARED module-scope imports -- this artifact will fail for users:"
        )
        for name, files in sorted(undeclared.items()):
            print(
                f"  {name:<26} imported at module scope by {len(files)} file(s)"
            )
            for path in files[:3]:
                print(f"      {path}")
            if len(files) > 3:
                print(f"      ... and {len(files) - 3} more")
        print(
            "\nDeclare missing base/active-extra imports in the owning artifact."
        )
        return 1

    print(
        "\nOK: base and active-extra imports are satisfied or reviewed; "
        "inactive extra imports were not tested in this profile."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
