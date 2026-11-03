#!/usr/bin/env python3
"""Validate and stage a reviewed eSpeak NG native payload into a bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "packaging/espeak/source-lock.json"
RECEIPT_NAME = "build-receipt.json"
MANIFEST_RELATIVE = Path("share/airunner/espeak-ng-native/component-manifest.json")
PROVENANCE_RELATIVE = Path("share/airunner/espeak-ng-native")
MAX_RECEIPT_BYTES = 1024 * 1024
MAX_RECEIPT_FILES = 10_000


class StagingError(ValueError):
    """The payload or bundle destination is not safe to stage."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_blob_id(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def _json_no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StagingError("receipt contains duplicate JSON keys")
        result[key] = value
    return result


def _read_json(path: Path, *, max_bytes: int) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            raw = stream.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise StagingError("JSON file exceeds the configured size limit")
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_json_no_duplicate_keys
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise StagingError("JSON file is missing or malformed") from exc
    if not isinstance(value, dict):
        raise StagingError("JSON root must be an object")
    return value


def _safe_relative_file(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise StagingError("receipt has an invalid file path")
    if "\\" in value or "\x00" in value:
        raise StagingError("receipt has an invalid file path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise StagingError("receipt path escapes the payload")
    if relative.as_posix() != value:
        raise StagingError("receipt path is not canonical")
    return value


def _walk_payload(payload: Path) -> tuple[set[str], set[str]]:
    """Return regular-file and directory paths, rejecting every symlink."""
    files: set[str] = set()
    directories: set[str] = set()
    for current, names, filenames in os.walk(payload, followlinks=False):
        current_path = Path(current)
        for name in names:
            path = current_path / name
            if path.is_symlink():
                raise StagingError("payload contains a symlink directory")
            if not path.is_dir():
                raise StagingError("payload contains a non-directory entry")
            directories.add(path.relative_to(payload).as_posix())
        for name in filenames:
            path = current_path / name
            if path.is_symlink():
                raise StagingError("payload contains a symlink file")
            try:
                mode = path.lstat().st_mode
            except OSError as exc:
                raise StagingError("payload file cannot be inspected") from exc
            if not stat.S_ISREG(mode):
                raise StagingError("payload contains a non-regular file")
            if mode & (stat.S_ISUID | stat.S_ISGID):
                raise StagingError("payload contains a setuid or setgid file")
            files.add(path.relative_to(payload).as_posix())
    return files, directories


def _expected_provenance(repo_root: Path) -> dict[str, Path]:
    package_dir = repo_root / "packaging/espeak"
    return {
        "source/BUILD.md": package_dir / "BUILD.md",
        "source/build_espeak_native_payload.py": repo_root / "scripts/build_espeak_native_payload.py",
        "source/intake_espeak_source.py": repo_root / "scripts/intake_espeak_source.py",
        "source/source-lock.json": package_dir / "source-lock.json",
        "source/0001-offline-no-playback.patch": package_dir / "0001-offline-no-playback.patch",
    }


def _validate_identity(
    payload: Path,
    receipt: dict[str, Any],
    files: dict[str, str],
    lock: dict[str, Any],
    repo_root: Path,
) -> None:
    upstream = lock.get("upstream")
    archive_info = lock.get("source_archive")
    patches = lock.get("patches")
    if not isinstance(upstream, dict) or not isinstance(archive_info, dict):
        raise StagingError("committed eSpeak source lock is malformed")
    if not isinstance(patches, list) or len(patches) != 1 or not isinstance(patches[0], dict):
        raise StagingError("committed eSpeak patch lock is malformed")

    expected_fields = {
        "source_commit": upstream.get("commit"),
        "source_tree": upstream.get("tree"),
        "source_archive_sha256": archive_info.get("sha256"),
        "patch_sha256": patches[0].get("sha256"),
        "target": lock.get("target"),
    }
    for field, expected in expected_fields.items():
        if expected is None or receipt.get(field) != expected:
            raise StagingError(f"build receipt {field} does not match the committed lock")

    archive_name = archive_info.get("filename")
    patch_name = patches[0].get("filename")
    if (
        not isinstance(archive_name, str)
        or Path(archive_name).name != archive_name
        or "/" in archive_name
        or "\\" in archive_name
        or not isinstance(patch_name, str)
        or Path(patch_name).name != patch_name
        or "/" in patch_name
        or "\\" in patch_name
    ):
        raise StagingError("committed eSpeak source lock has invalid filenames")
    required = {
        "bin/espeak-ng",
        "share/espeak-ng-data/phondata",
        "share/espeak-ng-data/phondata-manifest",
        "share/espeak-ng-data/phonindex",
        "share/espeak-ng-data/phontab",
        "share/espeak-ng-data/intonations",
        f"source/{archive_name}",
        f"source/{patch_name}",
        *(_expected_provenance(repo_root).keys()),
    }
    licenses = lock.get("license_git_blob_ids")
    if not isinstance(licenses, dict) or not licenses:
        raise StagingError("committed eSpeak license lock is malformed")
    required.update(f"licenses/espeak-ng/{name}" for name in licenses)
    if not required.issubset(files):
        missing = sorted(required.difference(files))
        raise StagingError("payload is missing required files: " + ", ".join(missing[:8]))
    expected_sources = set(_expected_provenance(repo_root))
    expected_licenses = {f"licenses/espeak-ng/{name}" for name in licenses}
    supported = (
        {"bin/espeak-ng"}
        | expected_sources
        | expected_licenses
        | {
            relative
            for relative in files
            if relative.startswith("share/espeak-ng-data/")
        }
        | {f"source/{archive_name}", f"source/{patch_name}"}
    )
    if set(files) != supported:
        raise StagingError("payload contains unsupported component files")

    if _sha256(payload / f"source/{archive_name}") != archive_info.get("sha256"):
        raise StagingError("source archive does not match the committed lock")
    if (payload / f"source/{archive_name}").stat().st_size != archive_info.get("size_bytes"):
        raise StagingError("source archive size does not match the committed lock")
    if _sha256(payload / f"source/{patch_name}") != patches[0].get("sha256"):
        raise StagingError("source patch does not match the committed lock")

    for relative, committed_path in _expected_provenance(repo_root).items():
        if (
            committed_path.is_symlink()
            or not committed_path.is_file()
            or not (payload / relative).is_file()
        ):
            raise StagingError(f"required provenance file is missing: {relative}")
        if _sha256(committed_path) != _sha256(payload / relative):
            raise StagingError(f"provenance does not match the committed file: {relative}")

    if not (payload / "bin/espeak-ng").stat().st_mode & 0o111:
        raise StagingError("eSpeak NG executable is not marked executable")
    for relative in (
        "share/espeak-ng-data/phondata",
        "share/espeak-ng-data/phondata-manifest",
        "share/espeak-ng-data/phonindex",
        "share/espeak-ng-data/phontab",
        "share/espeak-ng-data/intonations",
    ):
        if (payload / relative).stat().st_size <= 0:
            raise StagingError(f"required eSpeak data file is empty: {relative}")

    for name, blob_id in licenses.items():
        if (
            not isinstance(name, str)
            or not name
            or Path(name).name != name
            or "/" in name
            or "\\" in name
        ):
            raise StagingError("committed eSpeak license lock has an unsafe filename")
        if (
            not isinstance(blob_id, str)
            or len(blob_id) != 40
            or any(char not in "0123456789abcdef" for char in blob_id)
        ):
            raise StagingError("committed eSpeak license lock has an invalid blob id")
        notice = payload / "licenses/espeak-ng" / name
        if _git_blob_id(notice) != blob_id:
            raise StagingError(f"license notice does not match the locked source: {name}")


def _validate_payload(
    payload: Path, lock_path: Path, repo_root: Path
) -> tuple[dict[str, str], dict[str, Any]]:
    if payload.is_symlink() or not payload.is_dir():
        raise StagingError("payload must be an existing real directory")
    payload = payload.resolve(strict=True)
    receipt_path = payload / RECEIPT_NAME
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise StagingError("payload build receipt is missing or unsafe")
    receipt = _read_json(receipt_path, max_bytes=MAX_RECEIPT_BYTES)
    listed = receipt.get("files_sha256")
    if not isinstance(listed, dict) or not listed or len(listed) > MAX_RECEIPT_FILES:
        raise StagingError("build receipt file list is missing or oversized")

    expected_hashes: dict[str, str] = {}
    for raw_path, digest in listed.items():
        relative = _safe_relative_file(raw_path)
        if not isinstance(digest, str) or len(digest) != 64:
            raise StagingError("build receipt contains an invalid SHA-256 value")
        if any(char not in "0123456789abcdef" for char in digest):
            raise StagingError("build receipt contains an invalid SHA-256 value")
        expected_hashes[relative] = digest

    actual_files, actual_directories = _walk_payload(payload)
    if actual_files != set(expected_hashes) | {RECEIPT_NAME}:
        raise StagingError("payload has missing or unlisted files")
    implied_directories = {
        parent.as_posix()
        for relative in actual_files
        for parent in PurePosixPath(relative).parents
        if parent.as_posix() != "."
    }
    if actual_directories != implied_directories:
        raise StagingError("payload has unlisted or missing directories")

    for relative, expected in expected_hashes.items():
        if _sha256(payload / relative) != expected:
            raise StagingError(f"payload file hash mismatch: {relative}")

    committed_lock = repo_root / "packaging/espeak/source-lock.json"
    if (
        lock_path.is_symlink()
        or committed_lock.is_symlink()
        or lock_path.resolve(strict=True) != committed_lock.resolve(strict=True)
    ):
        raise StagingError("lock path must be the committed eSpeak source lock")
    lock = _read_json(lock_path, max_bytes=MAX_RECEIPT_BYTES)
    _validate_identity(payload, receipt, expected_hashes, lock, repo_root)
    return expected_hashes, receipt


def _destination_file_map(
    payload: Path,
    hashes: dict[str, str],
) -> dict[str, tuple[Path, str]]:
    files: dict[str, tuple[Path, str]] = {
        "bin/espeak-ng": (payload / "bin/espeak-ng", hashes["bin/espeak-ng"])
    }
    for relative, digest in hashes.items():
        if relative.startswith("share/espeak-ng-data/") or relative.startswith(
            "licenses/espeak-ng/"
        ):
            files[relative] = (payload / relative, digest)
        elif relative.startswith("source/"):
            destination = (PROVENANCE_RELATIVE / relative).as_posix()
            files[destination] = (payload / relative, digest)
    receipt_relative = (PROVENANCE_RELATIVE / RECEIPT_NAME).as_posix()
    files[receipt_relative] = (
        payload / RECEIPT_NAME,
        _sha256(payload / RECEIPT_NAME),
    )
    return files


def _check_destination_path(root: Path, relative: str) -> Path:
    destination = root
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        destination = destination / part
        if destination.is_symlink():
            raise StagingError(f"destination contains a symlink: {relative}")
        if destination.exists():
            final_component = index == len(parts) - 1
            if final_component and not destination.is_file():
                raise StagingError(f"destination is not a regular file: {relative}")
            if final_component:
                mode = destination.stat().st_mode
                if mode & (stat.S_ISUID | stat.S_ISGID):
                    raise StagingError(f"destination has setuid or setgid mode: {relative}")
                if relative == "bin/espeak-ng" and not mode & 0o111:
                    raise StagingError("destination eSpeak NG is not executable")
            if not final_component and not destination.is_dir():
                raise StagingError(f"destination parent is not a directory: {relative}")
    try:
        destination.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise StagingError(f"destination escapes bundle: {relative}") from exc
    return destination


def verify_staged_espeak(bundle: Path, *, required: bool = True) -> list[str]:
    """Check the staged component independently of its build directory."""
    manifest_path = bundle / MANIFEST_RELATIVE
    if not manifest_path.exists() and not manifest_path.is_symlink():
        return ["missing eSpeak NG native component manifest"] if required else []
    try:
        root = bundle.resolve(strict=True)
        _check_destination_path(root, MANIFEST_RELATIVE.as_posix())
        manifest = _read_json(manifest_path, max_bytes=MAX_RECEIPT_BYTES)
        if manifest.get("schema_version") != 1 or manifest.get("component") != "espeak-ng-native":
            raise StagingError("invalid eSpeak NG component manifest identity")
        entries = manifest.get("files")
        if not isinstance(entries, list) or not entries or len(entries) > MAX_RECEIPT_FILES:
            raise StagingError("invalid eSpeak NG component inventory")
        seen: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise StagingError("invalid eSpeak NG component entry")
            relative = _safe_relative_file(entry.get("path"))
            if relative in seen:
                raise StagingError("duplicate eSpeak NG component entry")
            seen.add(relative)
            digest = entry.get("sha256")
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise StagingError("invalid eSpeak NG component digest")
            path = _check_destination_path(root, relative)
            if not path.is_file() or _sha256(path) != digest:
                raise StagingError(f"missing or changed eSpeak NG component file: {relative}")
        required_files = {
            "bin/espeak-ng",
            *(f"share/espeak-ng-data/{name}" for name in (
                "phondata", "phondata-manifest", "phonindex", "phontab", "intonations"
            )),
            *(f"licenses/espeak-ng/{name}" for name in (
                "COPYING", "COPYING.APACHE", "COPYING.BSD2", "COPYING.UCD"
            )),
            (PROVENANCE_RELATIVE / RECEIPT_NAME).as_posix(),
            (PROVENANCE_RELATIVE / "source/source-lock.json").as_posix(),
        }
        if not required_files.issubset(seen):
            raise StagingError("eSpeak NG component inventory omits required resources")
        if any((root / relative).stat().st_size == 0 for relative in required_files):
            raise StagingError("eSpeak NG component contains an empty required resource")
    except (OSError, ValueError) as exc:
        return [f"eSpeak NG native component: {exc}"]
    return []


def stage_espeak_payload(
    payload: Path,
    bundle: Path,
    *,
    lock_path: Path = DEFAULT_LOCK,
    repo_root: Path = ROOT,
) -> Path:
    """Validate all input and destination state before staging any file."""
    payload = payload.expanduser()
    bundle = bundle.expanduser()
    hashes, _receipt = _validate_payload(payload, lock_path, repo_root)
    payload = payload.resolve(strict=True)
    files = _destination_file_map(payload, hashes)
    manifest = {
        "schema_version": 1,
        "component": "espeak-ng-native",
        "files": [
            {"path": relative, "sha256": digest}
            for relative, (_source, digest) in sorted(files.items())
        ],
    }
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    manifest_relative = MANIFEST_RELATIVE.as_posix()

    if bundle.is_symlink() or not bundle.is_dir():
        raise StagingError("bundle destination must be an existing real directory")
    root = bundle.resolve(strict=True)
    all_files = dict(files)
    all_files[manifest_relative] = (Path(), hashlib.sha256(manifest_bytes).hexdigest())
    destinations: dict[str, Path] = {}
    for relative, (source, expected_hash) in all_files.items():
        destination = _check_destination_path(root, relative)
        destinations[relative] = destination
        if destination.exists():
            actual = (
                hashlib.sha256(destination.read_bytes()).hexdigest()
                if relative == manifest_relative
                else _sha256(destination)
            )
            if actual != expected_hash:
                raise StagingError(f"conflicting file already exists: {relative}")

    with tempfile.TemporaryDirectory(prefix=".stage-espeak-native-", dir=root) as temporary:
        staging = Path(temporary)
        staged_files: dict[str, Path] = {}
        for relative, (source, _digest) in files.items():
            staged = staging / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, staged)
            if _sha256(staged) != files[relative][1]:
                raise StagingError(f"payload changed while staging: {relative}")
            if relative == "bin/espeak-ng":
                os.chmod(staged, stat.S_IMODE(source.stat().st_mode))
            staged_files[relative] = staged
        staged_manifest = staging / "component-manifest.json"
        staged_manifest.write_bytes(manifest_bytes)

        # Hard links publish complete files atomically and refuse overwrites.
        for relative, staged in staged_files.items():
            destination = destinations[relative]
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                continue
            try:
                os.link(staged, destination, follow_symlinks=False)
            except FileExistsError:
                _check_destination_path(root, relative)
                if _sha256(destination) != files[relative][1]:
                    raise StagingError(f"destination changed during stage: {relative}")

        manifest_path = destinations[manifest_relative]
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        if not manifest_path.exists():
            try:
                os.link(staged_manifest, manifest_path, follow_symlinks=False)
            except FileExistsError:
                if manifest_path.is_symlink() or not manifest_path.is_file():
                    raise StagingError("component manifest changed during stage")
                if hashlib.sha256(manifest_path.read_bytes()).digest() != hashlib.sha256(manifest_bytes).digest():
                    raise StagingError("component manifest changed during stage")
    return destinations[manifest_relative]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = stage_espeak_payload(
            args.payload,
            args.bundle,
            repo_root=ROOT,
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"stage-espeak-native: error: {exc}\n")
    print(f"stage-espeak-native: staged component manifest {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
