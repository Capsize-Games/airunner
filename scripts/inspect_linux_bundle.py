"""Inspect a built Linux services bundle without repository imports.

Release issue P05: artifact inspection instead of relying on editable
imports. Every check here is static -- manifest hashes, required
resources, exclusion scans, the PyInstaller missing-module gate, and
frozen-module presence -- so it runs with no repository on PYTHONPATH
and no application import. stdlib only.

Usage::

    venv/bin/python scripts/inspect_linux_bundle.py <bundle-dir>
    venv/bin/python scripts/inspect_linux_bundle.py <bundle-dir> \\
        --warn-file work/airunner-daemon/warn-airunner-daemon.txt \\
        --toc work/airunner-daemon/PYZ-00.toc --require-sidecars

Exit code 0 = clean (warnings allowed), 1 = problems found,
2 = usage or spec error.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Re-exported so this CLI keeps the single-file module API intact.
from linux_bundle_checks import (
    check_manifest_shape,
    scan_exclusions,
    spec_errors,
    verify_manifest,
    verify_required_resources,
)
from linux_bundle_gates import (
    check_collected_binaries,
    check_extension_modules,
    check_frozen_sources,
    check_sidecars,
    check_toc_modules,
    gate_warn_file,
    parse_toc_modules,
    parse_warn_file,
)

DEFAULT_SPEC = (
    Path(__file__).resolve().parent.parent
    / "packaging"
    / "linux"
    / "services-bundle-spec.toml"
)


@dataclass
class InspectionResult:
    """Outcome of one bundle inspection."""

    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        """True when the bundle must not ship."""
        return bool(self.problems)


def load_spec(path: Path | None = None) -> dict[str, Any]:
    """Return the parsed bundle spec."""
    spec_path = path or DEFAULT_SPEC
    try:
        text = spec_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"cannot read bundle spec: {exc}") from exc
    try:
        return dict(tomllib.loads(text))
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"invalid bundle spec {spec_path}: {exc}") from exc


def _read_manifest(
    bundle_dir: Path, spec: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    """Return the parsed manifest, or None plus problems."""
    manifest_path = bundle_dir / spec["manifest"]["filename"]
    if not manifest_path.is_file():
        return None, [f"missing {manifest_path.name}"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"cannot parse {manifest_path.name}: {exc}"]
    if not isinstance(manifest, dict):
        return None, [f"{manifest_path.name} is not an object"]
    return manifest, []


def _append_manifest(
    bundle_dir: Path, spec: dict[str, Any], result: InspectionResult
) -> None:
    """Append manifest, resource, and exclusion findings to result."""
    manifest, manifest_problems = _read_manifest(bundle_dir, spec)
    result.problems.extend(manifest_problems)
    if manifest is not None:
        result.problems.extend(verify_manifest(bundle_dir, manifest, spec))
        result.problems.extend(
            verify_required_resources(bundle_dir, manifest, spec)
        )
    result.problems.extend(scan_exclusions(bundle_dir, spec))
    result.problems.extend(check_extension_modules(bundle_dir, spec))
    result.problems.extend(check_collected_binaries(bundle_dir, spec))
    result.problems.extend(check_frozen_sources(bundle_dir, spec))


def _append_warn(
    result: InspectionResult, spec: dict[str, Any], warn_file: Path | None
) -> None:
    """Append warn-file gate findings to the result."""
    if warn_file is None:
        result.warnings.append("no warn file supplied; freeze gate skipped")
        return
    gate_problems, _ = gate_warn_file(
        warn_file,
        list(spec["warn_allowlist"]["modules"]),
        list(spec["code"].get("exclude_modules", [])),
    )
    result.problems.extend(gate_problems)


def _append_toc_sidecars(
    bundle_dir: Path,
    spec: dict[str, Any],
    result: InspectionResult,
    toc_paths: list[Path] | None,
    require_sidecars: bool,
) -> None:
    """Append frozen-module and sidecar findings to the result."""
    toc_problems, toc_warnings = check_toc_modules(toc_paths or [], spec)
    result.problems.extend(toc_problems)
    result.warnings.extend(toc_warnings)
    sidecar_problems, sidecar_warnings = check_sidecars(
        bundle_dir, spec, require_sidecars
    )
    result.problems.extend(sidecar_problems)
    result.warnings.extend(sidecar_warnings)


def inspect_bundle(
    bundle_dir: Path,
    spec: dict[str, Any],
    warn_file: Path | None = None,
    toc_paths: list[Path] | None = None,
    require_sidecars: bool = False,
) -> InspectionResult:
    """Run every static check over one built bundle directory."""
    result = InspectionResult()
    if not bundle_dir.is_dir():
        result.problems.append(f"not a directory: {bundle_dir}")
        return result
    _append_manifest(bundle_dir, spec, result)
    _append_warn(result, spec, warn_file)
    _append_toc_sidecars(bundle_dir, spec, result, toc_paths, require_sidecars)
    return result


def _toc_paths(value: str | None) -> list[Path]:
    """Expand --toc (one file or directory) into .toc files."""
    if value is None:
        return []
    path = Path(value)
    if path.is_dir():
        return sorted(path.glob("*.toc"))
    return [path]


def _inspect_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the inspect CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("--spec", type=Path, default=None)
    parser.add_argument("--warn-file", type=Path, default=None)
    parser.add_argument("--toc", default=None)
    parser.add_argument("--require-sidecars", action="store_true")
    return parser.parse_args(argv)


def _report_result(result: InspectionResult, bundle_dir: Path) -> int:
    """Print warnings and problems; return the exit code."""
    for warning in result.warnings:
        print(f"WARN: {warning}")
    for problem in result.problems:
        print(f"FAIL: {problem}")
    if result.failed:
        return 1
    print(f"OK: {bundle_dir} passes bundle inspection")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Inspect a bundle directory and report problems."""
    args = _inspect_args(argv)
    spec = load_spec(args.spec)
    errors = spec_errors(spec)
    if errors:
        for error in errors:
            print(f"SPEC: {error}", file=sys.stderr)
        return 2
    result = inspect_bundle(
        args.bundle_dir,
        spec,
        warn_file=args.warn_file,
        toc_paths=_toc_paths(args.toc),
        require_sidecars=args.require_sidecars,
    )
    return _report_result(result, args.bundle_dir)


if __name__ == "__main__":
    raise SystemExit(main())
