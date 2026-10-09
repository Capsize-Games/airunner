"""Freeze-gate checks for the Linux services bundle (release P05).

Single concern: quality gates over the PyInstaller freeze inputs and
the release-provisioned sidecars (warn-file gate, frozen-module
presence, sidecar presence). Stateless predicates; stdlib only.
"""

import re
from pathlib import Path
from typing import Any

_WARN_RE = re.compile(r"missing module named\s+['\"]?([A-Za-z_][\w.]*)")
_TOC_RE = re.compile(r"\('([A-Za-z_][\w.]*)',\s*'[^']*',\s*'PYMODULE'\)")


def parse_warn_file(text: str) -> dict[str, list[str]]:
    """Map each missing module to the importers named for it.

    PyInstaller 6.12 warn files list one ``missing module named X -
    imported by ...`` line per absent module (verified by micro-build);
    "excluded module" lines are deliberate --exclude choices, not
    missing modules, and are ignored.
    """
    missing: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = _WARN_RE.search(line)
        if not match:
            continue
        importers: list[str] = []
        if "imported by" in line:
            importers.append(line.rsplit("imported by", 1)[1].strip())
        missing.setdefault(match.group(1), []).extend(importers)
    return missing


def _gate_missing(
    missing: dict[str, list[str]],
    allowlist: list[str],
    excluded: list[str],
) -> tuple[list[str], list[str]]:
    """Split missing modules into problems and tolerated names."""
    allowed = {name.split(".")[0] for name in allowlist}
    banned = {name.split(".")[0] for name in excluded}
    problems: list[str] = []
    tolerated: list[str] = []
    for name in sorted(missing):
        if name.split(".")[0] in allowed | banned:
            tolerated.append(name)
        else:
            problems.append(f"unreviewed missing module: {name}")
    return problems, tolerated


def gate_warn_file(
    warn_path: Path,
    allowlist: list[str],
    excluded: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Gate the freeze on unreviewed missing modules.

    Returns (problems, tolerated). Comparison is by top-level name, so
    an allowlist entry of "collections.abc" also tolerates "collections".
    Excluded tops are tolerated here because the toc-exclusion gate
    separately enforces their absence from the freeze.
    """
    try:
        text = warn_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"cannot read warn file {warn_path}: {exc}"], []
    return _gate_missing(parse_warn_file(text), allowlist, excluded or [])


def parse_toc_modules(text: str) -> set[str]:
    """Return the PYMODULE names listed in a PYZ-00.toc file."""
    return set(_TOC_RE.findall(text))


def _read_toc_modules(toc_paths: list[Path]) -> tuple[set[str], list[str]]:
    """Return (modules, read problems) for the given .toc files."""
    modules: set[str] = set()
    problems: list[str] = []
    for toc_path in toc_paths:
        try:
            modules |= parse_toc_modules(
                toc_path.read_text(encoding="utf-8", errors="replace")
            )
        except OSError as exc:
            problems.append(f"cannot read toc {toc_path}: {exc}")
    return modules, problems


def _toc_presence(modules: set[str], spec: dict[str, Any]) -> list[str]:
    """Return spec modules absent from the frozen module set."""
    problems: list[str] = []
    exact = [entry["module"] for entry in spec.get("console_script", [])]
    exact.extend(spec["code"].get("hidden_imports", []))
    for name in exact:
        if name not in modules:
            problems.append(f"frozen bundle lacks module {name}")
    for parent in spec["code"].get("collect_submodules", []):
        prefix = parent + "."
        if parent not in modules and not any(
            name.startswith(prefix) for name in modules
        ):
            problems.append(f"frozen bundle lacks {parent}.* modules")
    return problems


def _toc_exclusions(modules: set[str], spec: dict[str, Any]) -> list[str]:
    """Return frozen modules under excluded top-level names."""
    excluded = set(spec["code"].get("exclude_modules", []))
    return [
        f"frozen bundle ships excluded module {name}"
        for name in sorted(modules)
        if name.split(".")[0] in excluded
    ]


def check_toc_modules(
    toc_paths: list[Path], spec: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Check frozen-module presence for entry points and loaders.

    Returns (problems, warnings). Console-script modules and hidden
    imports must appear exactly; each collect-submodules parent must
    contribute at least one module; no excluded top level may appear.
    """
    problems: list[str] = []
    warnings: list[str] = []
    if not toc_paths:
        return problems, ["no .toc supplied; frozen modules unchecked"]
    modules, read_problems = _read_toc_modules(toc_paths)
    problems.extend(read_problems)
    if problems:
        return problems, warnings
    problems.extend(_toc_presence(modules, spec))
    problems.extend(_toc_exclusions(modules, spec))
    return problems, warnings


def _extension_glob(name: str) -> str:
    """Return the _internal/ glob for a (possibly dotted) extension."""
    return "/".join(name.split(".")) + "*.so"


def check_extension_modules(
    bundle_dir: Path, spec: dict[str, Any]
) -> list[str]:
    """Return extension modules missing their collected native lib."""
    problems: list[str] = []
    internal = bundle_dir / "_internal"
    for name in spec["code"].get("extension_modules", []):
        if not list(internal.glob(_extension_glob(str(name)))):
            problems.append(f"frozen bundle lacks native extension {name}")
    return problems


def check_collected_binaries(
    bundle_dir: Path, spec: dict[str, Any]
) -> list[str]:
    """Return collect-binaries packages missing any .so in-tree."""
    problems: list[str] = []
    internal = bundle_dir / "_internal"
    for package in spec["code"].get("collect_binaries", []):
        if not list((internal / str(package)).rglob("*.so")):
            problems.append(
                f"frozen bundle lacks collected binaries for {package}"
            )
    return problems


def check_frozen_sources(
    bundle_dir: Path, spec: dict[str, Any]
) -> list[str]:
    """Return frozen import-scan sources missing from the tree."""
    problems: list[str] = []
    for marker in spec["code"].get("frozen_source_markers", []):
        if not (bundle_dir / str(marker)).is_file():
            problems.append(
                f"frozen bundle lacks import-scan source {marker}"
            )
    return problems


def check_sidecars(
    bundle_dir: Path, spec: dict[str, Any], require: bool
) -> tuple[list[str], list[str]]:
    """Report release-provided sidecars absent from bin/."""
    problems: list[str] = []
    warnings: list[str] = []
    bin_dir = bundle_dir / spec["runtimes"]["bin_dir"]
    for runtime in spec.get("runtime", []):
        if (bin_dir / runtime["name"]).exists():
            continue
        message = (
            f"sidecar {runtime['name']} absent from {bin_dir.name}/ "
            f"(release-provided for {runtime['feature']})"
        )
        (problems if require else warnings).append(message)
    return problems, warnings
