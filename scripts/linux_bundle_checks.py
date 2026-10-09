"""Bundle content checks for the Linux services bundle (P05).

Single concern: stateless validation of the spec structure and the
bundle tree itself (manifest hashes, required resources, exclusion
scan). No repository imports and no side effects; stdlib only.
"""

import fnmatch
import hashlib
import os
from pathlib import Path
from typing import Any

_REQUIRED_SECTIONS = (
    "bundle",
    "profile",
    "qt",
    "code",
    "runtimes",
    "exclusions",
    "warn_allowlist",
    "manifest",
    "r01_coverage",
)


def _entry_errors(spec: dict[str, Any]) -> list[str]:
    """Return structural problems in data and console entries."""
    errors: list[str] = []
    for index, entry in enumerate(spec.get("data", [])):
        for key in ("source", "dest", "stage"):
            if key not in entry:
                errors.append(f"spec [[data]] #{index} missing {key!r}")
        if entry.get("stage") not in ("collect", "root"):
            errors.append(
                f"spec [[data]] #{index} has unknown stage "
                f"{entry.get('stage')!r}"
            )
    for index, entry in enumerate(spec.get("console_script", [])):
        for key in ("name", "module", "function"):
            if key not in entry:
                errors.append(
                    f"spec [[console_script]] #{index} missing {key!r}"
                )
    return errors


def spec_errors(spec: dict[str, Any]) -> list[str]:
    """Return structural problems with the spec itself."""
    errors = [
        f"spec missing [{section}]"
        for section in _REQUIRED_SECTIONS
        if section not in spec
    ]
    bundle = spec.get("bundle", {})
    for key in ("name", "executable", "tool", "entry"):
        if key not in bundle:
            errors.append(f"spec [bundle] missing {key!r}")
    errors.extend(_entry_errors(spec))
    return errors


def _sha256(path: Path) -> str:
    """Return the hex SHA-256 of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_files(bundle_dir: Path) -> list[Path]:
    """Return every file under the bundle root, relative and sorted."""
    return sorted(
        path.relative_to(bundle_dir)
        for path in bundle_dir.rglob("*")
        if path.is_file()
    )


def check_manifest_shape(
    manifest: dict[str, Any], spec: dict[str, Any]
) -> list[str]:
    """Return shape violations against the P04 manifest contract."""
    problems: list[str] = []
    for field_name in spec["manifest"]["required_fields"]:
        if field_name not in manifest:
            problems.append(f"manifest missing field {field_name!r}")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        problems.append("manifest records no files")
        return problems
    for entry in files:
        for field_name in spec["manifest"]["file_fields"]:
            if field_name not in entry:
                problems.append(
                    f"manifest entry {entry!r} missing {field_name!r}"
                )
    return problems


def _file_problems(
    bundle_dir: Path, recorded: dict[str, str], manifest_name: str
) -> list[str]:
    """Return hash-mismatch and unmanifested-file problems."""
    problems: list[str] = []
    for relpath, expected in sorted(recorded.items()):
        path = bundle_dir / relpath
        if not path.is_file():
            problems.append(f"manifest lists missing file {relpath}")
        elif _sha256(path) != expected:
            problems.append(f"manifest hash mismatch: {relpath}")
    actual = {
        path.as_posix()
        for path in _bundle_files(bundle_dir)
        if path.name != manifest_name
    }
    for relpath in sorted(actual - set(recorded)):
        problems.append(f"bundle file not in manifest: {relpath}")
    return problems


def _identity_problems(
    manifest: dict[str, Any], spec: dict[str, Any]
) -> list[str]:
    """Return manifest identity fields disagreeing with the spec."""
    expected_identity = {
        "bundle": spec["bundle"]["name"],
        "tool": spec["bundle"]["tool"],
        "entry": spec["bundle"]["entry"],
    }
    problems: list[str] = []
    for key, expected in expected_identity.items():
        got = manifest.get(key)
        if got != expected:
            problems.append(f"manifest {key} {got!r} != spec {expected!r}")
    return problems


def verify_manifest(
    bundle_dir: Path, manifest: dict[str, Any], spec: dict[str, Any]
) -> list[str]:
    """Compare recorded manifest entries against the bundle files."""
    problems = check_manifest_shape(manifest, spec)
    if problems:
        return problems
    recorded = {
        str(entry["path"]): str(entry["sha256"]) for entry in manifest["files"]
    }
    problems.extend(
        _file_problems(bundle_dir, recorded, spec["manifest"]["filename"])
    )
    problems.extend(_identity_problems(manifest, spec))
    return problems


def _entry_problem(recorded: set[str], entry: dict[str, Any]) -> list[str]:
    """Return the missing-payload problem for one data entry."""
    dest = str(entry["dest"]).rstrip("/")
    source = str(entry["source"])
    if any(char in source for char in "*?["):
        if any(
            path == dest or path.startswith(dest + "/") for path in recorded
        ):
            return []
        return [f"no bundled file under data dest {dest}/ (from {source})"]
    wanted = f"{dest}/{Path(source).name}"
    if wanted not in recorded:
        return [f"missing required data file {wanted}"]
    return []


def verify_required_resources(
    bundle_dir: Path, manifest: dict[str, Any], spec: dict[str, Any]
) -> list[str]:
    """Return missing entry point, runtime dir, or data payloads."""
    problems: list[str] = []
    recorded = {str(entry["path"]) for entry in manifest.get("files", [])}
    exe = bundle_dir / spec["bundle"]["executable"]
    if not exe.is_file():
        problems.append(f"missing bundle executable {exe.name}")
    elif not os.access(exe, os.X_OK):
        problems.append(f"bundle executable {exe.name} is not executable")
    bin_dir = bundle_dir / spec["runtimes"]["bin_dir"]
    if not bin_dir.is_dir():
        problems.append(f"missing sidecar directory {bin_dir.name}/")
    for entry in spec.get("data", []):
        if not entry.get("required", True):
            continue
        problems.extend(_entry_problem(recorded, entry))
    return problems


def scan_exclusions(bundle_dir: Path, spec: dict[str, Any]) -> list[str]:
    """Return bundle files matching an exclusion pattern or Qt marker."""
    problems: list[str] = []
    patterns = list(spec["exclusions"]["patterns"])
    markers = [m.lower() for m in spec["qt"].get("qt_markers", [])]
    for relpath in _bundle_files(bundle_dir):
        posix = relpath.as_posix()
        lowered = posix.lower()
        for marker in markers:
            if marker in lowered:
                problems.append(f"Qt payload in services bundle: {posix}")
        for pattern in patterns:
            if any(fnmatch.fnmatch(p, pattern) for p in (posix, relpath.name)):
                problems.append(
                    f"excluded payload {posix} (pattern {pattern})"
                )
                break
    return problems
