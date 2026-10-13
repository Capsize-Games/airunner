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
    venv/bin/python scripts/inspect_linux_bundle.py <bundle-dir> \\
        --require-signed-policy

--require-signed-policy additionally form-checks every frozen
content-safety policy payload (present, strictly versioned,
non-empty, with a well-formed detached signature). Shape only, not
trust: cryptographic trust is established when S06 stages the
release fragment, before the freeze.

Exit code 0 = clean (warnings allowed), 1 = problems found,
2 = usage or spec error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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

_POLICY_FORMAT_ID = "airunner-policy-data/1"
_POLICY_NORMALIZATION = "v1"
_POLICY_SIG_FORMAT_ID = "airunner-policy-signature/1"
_MAX_POLICY_BYTES = 64 * 1024 * 1024
_MAX_POLICY_SIG_BYTES = 4096

_HASH_LINE_RE = re.compile(r"^[0-9a-f]{64}$")
_SIG_VALUE_RE = re.compile(r"^[0-9a-f]{128}$")
_KEY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_META_LINE_RE = re.compile(r"^#\s*([a-z0-9_]+)\s*:\s*(\S+)\s*$")


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


def _policy_meta(text: str) -> dict[str, str] | None:
    """Collect ``# key: value`` metadata; None on duplicate keys."""
    meta: dict[str, str] = {}
    for line in text.splitlines():
        match = _META_LINE_RE.match(line.strip())
        if match is None:
            continue
        if match.group(1) in meta:
            return None
        meta[match.group(1)] = match.group(2)
    return meta


def _policy_digest_lines(text: str) -> list[str] | None:
    """Return lowered digest lines; None on malformed lines."""
    digests: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        candidate = stripped.lower()
        if not _HASH_LINE_RE.match(candidate):
            return None
        digests.append(candidate)
    return digests


def _policy_block_ok(digests: list[str], meta: dict[str, str]) -> bool:
    """True when the digest block matches its integrity metadata."""
    block = "".join(f"{digest}\n" for digest in digests)
    want = meta.get("sha256", "").lower()
    return hashlib.sha256(block.encode("utf-8")).hexdigest() == want


def _check_policy_text(text: str) -> str | None:
    """Validate the versioned release shape; problem or None."""
    meta = _policy_meta(text)
    digests = _policy_digest_lines(text)
    if meta is None or digests is None:
        return "release policy payload is invalid"
    if meta.get("format") != _POLICY_FORMAT_ID:
        return "release policy payload is invalid"
    if meta.get("normalization") != _POLICY_NORMALIZATION:
        return "release policy payload is invalid"
    if not meta.get("count", "").isdigit():
        return "release policy payload is invalid"
    if int(meta["count"]) != len(digests):
        return "release policy payload is invalid"
    if not digests:
        return "release policy payload is empty"
    if sorted(digests) != digests or len(set(digests)) != len(digests):
        return "release policy payload is invalid"
    if not _policy_block_ok(digests, meta):
        return "release policy payload is invalid"
    return None


def _signature_meta(text: str) -> dict[str, str] | None:
    """Collect sidecar metadata; None on content or duplicate lines."""
    meta: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("#"):
            return None
        match = _META_LINE_RE.match(stripped)
        if match is None:
            continue
        if match.group(1) in meta:
            return None
        meta[match.group(1)] = match.group(2)
    return meta


def _check_policy_signature(data: bytes | None) -> str | None:
    """Validate sidecar presence and shape; problem or None."""
    if not data or len(data) > _MAX_POLICY_SIG_BYTES:
        return "release policy payload is unsigned or synthetic-only"
    try:
        meta = _signature_meta(data.decode("utf-8"))
    except UnicodeDecodeError:
        return "release policy signature is invalid"
    if meta is None:
        return "release policy signature is invalid"
    if meta.get("format") != _POLICY_SIG_FORMAT_ID:
        return "release policy signature is invalid"
    if not _KEY_ID_RE.match(meta.get("key_id", "")):
        return "release policy signature is invalid"
    if not _SIG_VALUE_RE.match(meta.get("signature", "").lower()):
        return "release policy signature is invalid"
    return None


def check_policy_bytes(
    data: bytes | None, signature: bytes | None
) -> str | None:
    """Form-check one policy artifact plus sidecar; problem or None.

    Shape only, not trust: present, bounded, strictly versioned,
    non-empty, with a well-formed detached signature. Cryptographic
    trust is established at S06 staging (trust-store verification);
    see scripts/build_policy_terms.py.
    """
    if data is None:
        return "release policy payload is absent"
    if not data or len(data) > _MAX_POLICY_BYTES:
        return "release policy payload is empty or oversized"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "release policy payload is invalid"
    problem = _check_policy_text(text)
    if problem is not None:
        return problem
    return _check_policy_signature(signature)


def check_policy_file(path: Path) -> list[str]:
    """Form-check one .dat file plus its sidecar; content-free."""
    try:
        data = path.read_bytes()
    except OSError:
        return ["release policy payload is absent"]
    sidecar = path.with_name(path.name + ".sig")
    try:
        signature = sidecar.read_bytes() if sidecar.is_file() else None
    except OSError:
        signature = None
    problem = check_policy_bytes(data, signature)
    return [problem] if problem is not None else []


def verify_policy_payload(
    bundle_dir: Path, spec: dict[str, Any]
) -> list[str]:
    """Form-check every frozen policy payload; content-free problems."""
    problems: list[str] = []
    for entry in spec.get("data", []):
        if str(entry.get("stage")) != "collect":
            continue
        if not str(entry.get("source", "")).endswith(".dat"):
            continue
        payload_dir = bundle_dir / "_internal" / str(entry["dest"])
        staged = sorted(payload_dir.glob("*.dat"))
        if not staged:
            problems.append("release policy payload is absent")
            continue
        for path in staged:
            problems.extend(check_policy_file(path))
    return problems


def inspect_bundle(
    bundle_dir: Path,
    spec: dict[str, Any],
    warn_file: Path | None = None,
    toc_paths: list[Path] | None = None,
    require_sidecars: bool = False,
    require_signed_policy: bool = False,
) -> InspectionResult:
    """Run every static check over one built bundle directory."""
    result = InspectionResult()
    if not bundle_dir.is_dir():
        result.problems.append(f"not a directory: {bundle_dir}")
        return result
    _append_manifest(bundle_dir, spec, result)
    _append_warn(result, spec, warn_file)
    _append_toc_sidecars(bundle_dir, spec, result, toc_paths, require_sidecars)
    if require_signed_policy:
        result.problems.extend(verify_policy_payload(bundle_dir, spec))
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
    parser.add_argument("--require-signed-policy", action="store_true")
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
        require_signed_policy=args.require_signed_policy,
    )
    return _report_result(result, args.bundle_dir)


if __name__ == "__main__":
    raise SystemExit(main())
