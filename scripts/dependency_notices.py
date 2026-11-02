"""Collect and verify lock-scoped third-party license files for Linux bundles.

Only stdlib metadata parsing is used. Distribution payloads are read from
RECORD paths in the active build interpreter's site-packages; no package code
or direct_url.json content is loaded.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import re
import sys
import sysconfig
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit

from importlib.metadata import PathDistribution


_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.!+_-]*$")
_HASH_RE = re.compile(r"^sha256:([0-9a-f]{64})$")
_LICENSE_BASENAME_RE = re.compile(
    r"^(?:licen[cs]e|copying|copyright|notice)(?:$|[._-])", re.IGNORECASE
)
_DIST_INFO_SUFFIXES = (".dist-info", ".egg-info")


class DependencyNoticeError(ValueError):
    """The selected lock graph or its installed license files are invalid."""


@dataclass(frozen=True)
class LockedDistribution:
    """One exact distribution selected by a complete hashed requirements lock."""

    name: str
    normalized_name: str
    version: str
    hashes: tuple[str, ...]


def _normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _lock_path(path_text: str, repo_root: Path) -> Path:
    """Resolve one repository-relative regular lock file without symlinks."""
    if not isinstance(path_text, str) or not path_text:
        raise DependencyNoticeError("profile lock path is invalid")
    pure = PurePosixPath(path_text)
    if pure.is_absolute() or ".." in pure.parts or "\\" in path_text:
        raise DependencyNoticeError("profile lock path escapes the source tree")
    root = repo_root.resolve()
    path = repo_root.joinpath(*pure.parts)
    if path.is_symlink() or not path.is_file():
        raise DependencyNoticeError("selected profile lock is missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise DependencyNoticeError("selected profile lock escapes the source tree") from exc
    return path


def _direct_url_version(url: str, expected_name: str) -> str:
    """Read name/version from a pinned wheel filename without retaining its URL."""
    filename = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
    if not filename.endswith(".whl"):
        raise DependencyNoticeError("direct lock reference is not a pinned wheel")
    parts = filename[:-4].split("-")
    if len(parts) < 5 or _normalized_name(parts[0]) != expected_name:
        raise DependencyNoticeError("direct wheel identity differs from lock name")
    version = parts[1]
    if not _VERSION_RE.fullmatch(version):
        raise DependencyNoticeError("direct wheel version is invalid")
    return version


def parse_lock_bytes(lock_bytes: bytes) -> tuple[list[LockedDistribution], str]:
    """Parse a complete pip --require-hashes lock and return identity plus digest."""
    try:
        text = lock_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DependencyNoticeError("profile lock is not UTF-8") from exc

    locked: list[LockedDistribution] = []
    seen: set[str] = set()
    current: tuple[str, str, str] | None = None
    hashes: list[str] = []

    def finish() -> None:
        nonlocal current, hashes
        if current is None:
            return
        name, normalized, version = current
        if not hashes:
            raise DependencyNoticeError(
                f"profile lock package lacks hashes: {normalized}"
            )
        if len(hashes) != len(set(hashes)):
            raise DependencyNoticeError(
                f"profile lock repeats an artifact hash: {normalized}"
            )
        locked.append(
            LockedDistribution(name, normalized, version, tuple(sorted(hashes)))
        )
        current = None
        hashes = []

    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("--hash="):
            if current is None:
                raise DependencyNoticeError(
                    f"profile lock hash has no package on line {line_number}"
                )
            hash_line = line.removesuffix("\\").strip()
            match = re.fullmatch(r"--hash=sha256:([0-9a-f]{64})", hash_line)
            if match is None:
                raise DependencyNoticeError(
                    f"profile lock has an invalid hash on line {line_number}"
                )
            hashes.append(match.group(1))
            continue

        finish()
        requirement = line.removesuffix("\\").strip()
        exact = re.fullmatch(
            r"([A-Za-z0-9][A-Za-z0-9_.-]*)==([^\s\\;]+)", requirement
        )
        direct = re.fullmatch(
            r"([A-Za-z0-9][A-Za-z0-9_.-]*)\s+@\s+(\S+)", requirement
        )
        if exact is not None:
            name, version = exact.groups()
            normalized = _normalized_name(name)
        elif direct is not None:
            name, url = direct.groups()
            normalized = _normalized_name(name)
            version = _direct_url_version(url, normalized)
        else:
            raise DependencyNoticeError(
                f"profile lock has an unsupported requirement on line {line_number}"
            )
        if normalized in seen:
            raise DependencyNoticeError(
                f"profile lock repeats a distribution: {normalized}"
            )
        if not _NAME_RE.fullmatch(name) or not _VERSION_RE.fullmatch(version):
            raise DependencyNoticeError(
                f"profile lock identity is invalid on line {line_number}"
            )
        seen.add(normalized)
        current = (name, normalized, version)

    finish()
    if not locked:
        raise DependencyNoticeError("profile lock contains no pinned distributions")
    return locked, hashlib.sha256(lock_bytes).hexdigest()


def read_lock(
    lock_path_text: str, repo_root: Path
) -> tuple[list[LockedDistribution], str]:
    """Read one selected lock after repository path and symlink checks."""
    path = _lock_path(lock_path_text, repo_root)
    return parse_lock_bytes(path.read_bytes())


def _site_package_roots(explicit: Iterable[Path] | None) -> list[Path]:
    """Return only active interpreter purelib/platlib roots, excluding user sites."""
    if explicit is not None:
        roots = [Path(root) for root in explicit]
    else:
        paths = sysconfig.get_paths()
        roots = [Path(paths[key]) for key in ("purelib", "platlib") if paths.get(key)]
    prefix = Path(sys.prefix).resolve()
    result: list[Path] = []
    for root in roots:
        if root.is_symlink():
            raise DependencyNoticeError("active site-packages root is a symlink")
        try:
            resolved = root.resolve(strict=True)
            resolved.relative_to(prefix)
        except (OSError, ValueError) as exc:
            raise DependencyNoticeError(
                "site-packages root is outside the active Python prefix"
            ) from exc
        if not resolved.is_dir():
            continue
        if resolved not in result:
            result.append(resolved)
    if not result:
        raise DependencyNoticeError("active Python has no usable site-packages root")
    return result


def _metadata_candidates(
    package: LockedDistribution, roots: list[Path]
) -> list[tuple[Path, str, str, list[str]]]:
    """Find exact-name dist-info entries in the scoped active site-packages roots."""
    matches: list[tuple[Path, str, str, list[str]]] = []
    for site_root in roots:
        for item in site_root.iterdir():
            if not item.name.endswith(_DIST_INFO_SUFFIXES):
                continue
            stem = item.name.rsplit(".", 1)[0]
            if not _normalized_name(stem).startswith(package.normalized_name + "-"):
                continue
            if item.is_symlink() or not item.is_dir():
                raise DependencyNoticeError(
                    f"unsafe distribution metadata entry for {package.normalized_name}"
                )
            metadata_file = item / (
                "METADATA" if item.name.endswith(".dist-info") else "PKG-INFO"
            )
            if metadata_file.is_symlink() or not metadata_file.is_file():
                raise DependencyNoticeError(
                    f"distribution metadata is missing for {package.normalized_name}"
                )
            try:
                metadata = PathDistribution(item).metadata
            except (OSError, UnicodeDecodeError) as exc:
                raise DependencyNoticeError(
                    f"distribution metadata is unreadable for {package.normalized_name}"
                ) from exc
            names = metadata.get_all("Name", [])
            versions = metadata.get_all("Version", [])
            if len(names) != 1 or len(versions) != 1:
                raise DependencyNoticeError(
                    f"distribution metadata identity is ambiguous for {package.normalized_name}"
                )
            actual_name = names[0]
            actual_version = versions[0]
            if _normalized_name(actual_name) != package.normalized_name:
                continue
            license_files = metadata.get_all("License-File", []) or []
            matches.append((item, actual_name, actual_version, license_files))
    return matches


def _record_path(site_root: Path, raw_path: str) -> Path:
    """Resolve one RECORD path below site-packages, rejecting traversal/symlinks."""
    if (
        not raw_path
        or "\\" in raw_path
        or "\x00" in raw_path
        or raw_path.startswith("/")
    ):
        raise DependencyNoticeError("distribution RECORD contains an unsafe path")
    relative = PurePosixPath(raw_path)
    if any(part in ("", ".", "..") for part in raw_path.split("/")):
        raise DependencyNoticeError("distribution RECORD contains path traversal")
    candidate = site_root.joinpath(*relative.parts)
    current = site_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise DependencyNoticeError("distribution notice path contains a symlink")
    try:
        candidate.resolve(strict=True).relative_to(site_root)
    except (OSError, ValueError) as exc:
        raise DependencyNoticeError("distribution notice path escapes site-packages") from exc
    if not candidate.is_file():
        raise DependencyNoticeError("distribution notice path is not a regular file")
    return candidate


def _is_notice_path(raw_path: str) -> bool:
    name = PurePosixPath(raw_path).name
    return bool(_LICENSE_BASENAME_RE.match(name))


def _verify_record_hash(raw_hash: str, content: bytes) -> str:
    """Verify a RECORD digest and return its algorithm:hex form."""
    if "=" not in raw_hash:
        raise DependencyNoticeError("distribution notice file is unhashed in RECORD")
    algorithm, encoded = raw_hash.split("=", 1)
    if (
        algorithm not in {"sha256", "sha384", "sha512"}
        or not encoded
        or re.fullmatch(r"[A-Za-z0-9_-]+", encoded) is None
    ):
        raise DependencyNoticeError("distribution notice file has an unsupported RECORD hash")
    try:
        expected = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        digest = hashlib.new(algorithm, content).digest()
    except (ValueError, TypeError) as exc:
        raise DependencyNoticeError("distribution notice RECORD hash is malformed") from exc
    if not hmac.compare_digest(digest, expected):
        raise DependencyNoticeError("distribution notice file differs from its RECORD hash")
    return f"{algorithm}:{digest.hex()}"


def _distribution_notices(
    package: LockedDistribution,
    roots: list[Path],
    bundle_dest: str,
) -> tuple[dict[str, Any], list[tuple[str, bytes]]]:
    """Read verified notice files for one locked package without importing it."""
    candidates = _metadata_candidates(package, roots)
    if not candidates:
        raise DependencyNoticeError(
            f"locked distribution is not installed: {package.normalized_name}"
        )
    if len(candidates) != 1:
        raise DependencyNoticeError(
            f"locked distribution has duplicate installed metadata: {package.normalized_name}"
        )
    metadata_dir, actual_name, actual_version, license_files = candidates[0]
    if actual_version != package.version:
        raise DependencyNoticeError(
            f"installed distribution version differs from lock: {package.normalized_name}"
        )
    site_root = next(root for root in roots if metadata_dir.is_relative_to(root))
    metadata_relative = metadata_dir.relative_to(site_root).as_posix()
    record_path = metadata_dir / "RECORD"
    if record_path.is_symlink() or not record_path.is_file():
        raise DependencyNoticeError(
            f"locked distribution has no usable RECORD: {package.normalized_name}"
        )
    try:
        record_bytes = record_path.read_bytes()
        record_text = record_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DependencyNoticeError(
            f"locked distribution RECORD is unreadable: {package.normalized_name}"
        ) from exc
    record_digest = hashlib.sha256(record_bytes).hexdigest()
    try:
        rows = list(csv.reader(io.StringIO(record_text, newline="")))
    except csv.Error as exc:
        raise DependencyNoticeError(
            f"locked distribution RECORD is malformed: {package.normalized_name}"
        ) from exc
    seen_notice_paths: set[str] = set()
    notices: list[dict[str, Any]] = []
    contents: list[tuple[str, bytes]] = []
    slug = f"{package.normalized_name}-{package.version}"
    if not _NAME_RE.fullmatch(package.normalized_name) or not _VERSION_RE.fullmatch(package.version):
        raise DependencyNoticeError("locked distribution has an unsafe output identity")

    dist_info_relative = metadata_dir.relative_to(site_root).as_posix()
    license_directory = metadata_dir / "licenses"
    license_directory_paths: set[str] = set()
    if license_directory.is_symlink():
        raise DependencyNoticeError(
            f"locked distribution licenses directory is a symlink: {package.normalized_name}"
        )
    if license_directory.exists():
        if not license_directory.is_dir():
            raise DependencyNoticeError(
                f"locked distribution licenses path is not a directory: {package.normalized_name}"
            )
        for path in license_directory.rglob("*"):
            if path.is_symlink():
                raise DependencyNoticeError(
                    f"locked distribution licenses directory contains a symlink: {package.normalized_name}"
                )
            if path.is_dir():
                continue
            if not path.is_file():
                raise DependencyNoticeError(
                    f"locked distribution licenses directory contains a non-file: {package.normalized_name}"
                )
            license_directory_paths.add(path.relative_to(site_root).as_posix())

    declared_paths: dict[str, set[str]] = {}
    for license_file in license_files:
        if license_file in declared_paths:
            raise DependencyNoticeError(
                f"locked distribution repeats a License-File declaration: {package.normalized_name}"
            )
        try:
            relative = _safe_relative(license_file, "License-File metadata path")
        except DependencyNoticeError as exc:
            raise DependencyNoticeError(
                f"locked distribution declares an unsafe License-File path: {package.normalized_name}"
            ) from exc
        candidates = {
            relative.as_posix(),
            f"{dist_info_relative}/{relative.as_posix()}",
        }
        if relative.parts[0] == "licenses":
            candidates.add(f"{dist_info_relative}/{relative.as_posix()}")
        else:
            candidates.add(f"{dist_info_relative}/licenses/{relative.as_posix()}")
        declared_paths[license_file] = candidates

    selected_metadata_paths = set().union(*declared_paths.values()) if declared_paths else set()
    license_directory_prefix = f"{dist_info_relative}/licenses/"
    for row in rows:
        if len(row) != 3:
            raise DependencyNoticeError(
                f"locked distribution RECORD row is malformed: {package.normalized_name}"
            )
        raw_path, raw_hash, raw_size = row
        # Wheels may legitimately record console scripts outside site-packages,
        # such as ../../../bin/tool. Inspect and read only selected notice paths.
        in_license_directory = raw_path.startswith(license_directory_prefix)
        if not (
            _is_notice_path(raw_path)
            or in_license_directory
            or raw_path in selected_metadata_paths
        ):
            continue
        if raw_path in seen_notice_paths:
            raise DependencyNoticeError(
                f"locked distribution RECORD repeats a notice path: {package.normalized_name}"
            )
        seen_notice_paths.add(raw_path)
        source = _record_path(site_root, raw_path)
        try:
            content = source.read_bytes()
        except OSError as exc:
            raise DependencyNoticeError(
                f"locked distribution notice is unreadable: {package.normalized_name}"
            ) from exc
        record_hash = _verify_record_hash(raw_hash, content)
        try:
            recorded_size = int(raw_size)
        except (TypeError, ValueError) as exc:
            raise DependencyNoticeError(
                f"locked distribution notice has no recorded size: {package.normalized_name}"
            ) from exc
        if recorded_size != len(content):
            raise DependencyNoticeError(
                f"locked distribution notice size differs from RECORD: {package.normalized_name}"
            )
        if not content:
            raise DependencyNoticeError(
                f"locked distribution notice is empty: {package.normalized_name}"
            )
        bundle_path = f"{bundle_dest}/{slug}/{raw_path}"
        notices.append(
            {
                "source_path": raw_path,
                "bundle_path": bundle_path,
                "record_hash": record_hash,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }
        )
        contents.append((f"{slug}/{raw_path}", content))

    if not license_directory_paths.issubset(seen_notice_paths):
        raise DependencyNoticeError(
            f"locked distribution licenses directory contains unrecorded files: {package.normalized_name}"
        )
    for license_file, candidates in declared_paths.items():
        matches = candidates & seen_notice_paths
        if len(matches) != 1:
            raise DependencyNoticeError(
                f"locked distribution License-File metadata does not identify one recorded file: {package.normalized_name}"
            )

    if not notices:
        raise DependencyNoticeError(
            f"locked distribution has no hashed license, notice, or copyright file: {package.normalized_name}"
        )
    notices.sort(key=lambda entry: str(entry["source_path"]))
    package_record = {
        "name": actual_name,
        "normalized_name": package.normalized_name,
        "version": actual_version,
        "lock_hashes": list(package.hashes),
        "metadata_path": metadata_relative,
        "record_sha256": record_digest,
        "notices": notices,
    }
    return package_record, contents


def collect_dependency_notices(
    spec: dict[str, Any],
    repo_root: Path,
    bundle_dir: Path,
    *,
    site_packages: Iterable[Path] | None = None,
) -> dict[str, Any]:
    """Copy lock-scoped, RECORD-verified notice files into the bundle."""
    config = spec.get("dependency_notices", {})
    if not config.get("required", False):
        return {}
    lock_text = str(spec.get("bundle", {}).get("constraints", ""))
    packages, lock_digest = read_lock(lock_text, repo_root)
    roots = _site_package_roots(site_packages)

    destination_text = str(config.get("dest", ""))
    manifest_name = str(config.get("manifest", ""))
    destination_rel = _safe_relative(destination_text, "dependency notice directory")
    manifest_rel = _safe_relative(manifest_name, "dependency notice manifest name")
    if len(manifest_rel.parts) != 1:
        raise DependencyNoticeError("dependency notice manifest must be a filename")
    destination = bundle_dir.joinpath(*destination_rel.parts)
    if bundle_dir.is_symlink() or not bundle_dir.is_dir():
        raise DependencyNoticeError("bundle output root is missing or unsafe")
    current = bundle_dir.resolve(strict=True)
    for part in destination_rel.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise DependencyNoticeError("dependency notice output path contains a symlink")
        current.mkdir(exist_ok=True)
        if not current.is_dir():
            raise DependencyNoticeError("dependency notice output parent is not a directory")
    parent = destination.parent
    if destination.exists() or destination.is_symlink():
        raise DependencyNoticeError("dependency notice output already exists")

    distributions: list[dict[str, Any]] = []
    copied: dict[str, bytes] = {}
    for package in packages:
        record, files = _distribution_notices(
            package, roots, destination_rel.as_posix()
        )
        distributions.append(record)
        for relative, content in files:
            path = _safe_relative(relative, "dependency notice output path")
            if relative in copied:
                raise DependencyNoticeError("dependency notice output path collision")
            copied[relative] = content
    if not copied:
        raise DependencyNoticeError("selected lock has no dependency notice files")

    lock_sha_path = _sha256_file(_lock_path(lock_text, repo_root))
    if lock_sha_path != lock_digest:
        raise DependencyNoticeError("selected profile lock changed during collection")
    manifest = {
        "schema_version": 1,
        "profile": str(spec.get("profile", {}).get("services_extra", "unknown")),
        "lock_path": lock_text,
        "lock_sha256": lock_digest,
        "distribution_count": len(distributions),
        "notice_file_count": len(copied),
        "distributions": distributions,
    }

    with tempfile.TemporaryDirectory(prefix="dependency-notices-", dir=parent) as temp:
        staging = Path(temp) / "dependencies"
        staging.mkdir()
        for relative, content in sorted(copied.items()):
            target_rel = _safe_relative(relative, "dependency notice output path")
            target = staging.joinpath(*target_rel.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        manifest_path = staging / manifest_rel.name
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        # Keep the destination parent and staging directory on one filesystem.
        staging.replace(destination)
    return manifest


def _safe_relative(value: str, label: str) -> PurePosixPath:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\x00" in value
        or value.startswith("/")
    ):
        raise DependencyNoticeError(f"{label} is unsafe")
    path = PurePosixPath(value)
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise DependencyNoticeError(f"{label} contains traversal")
    return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _safe_bundle_file(root: Path, relative: str) -> Path:
    path_rel = _safe_relative(relative, "dependency notice manifest path")
    path = root.joinpath(*path_rel.parts)
    current = root
    for part in path_rel.parts:
        current = current / part
        if current.is_symlink():
            raise DependencyNoticeError("dependency notice bundle path contains a symlink")
    try:
        path.resolve(strict=True).relative_to(root.resolve())
    except (OSError, ValueError) as exc:
        raise DependencyNoticeError("dependency notice path escapes the bundle") from exc
    if not path.is_file():
        raise DependencyNoticeError("dependency notice bundle file is missing")
    return path


def verify_dependency_notice_manifest(
    bundle_dir: Path,
    spec: dict[str, Any],
    repo_root: Path,
) -> list[str]:
    """Check lock completeness, package identities, copied file hashes and path safety."""
    config = spec.get("dependency_notices", {})
    if not config.get("required", False):
        return []
    try:
        lock_text = str(spec.get("bundle", {}).get("constraints", ""))
        packages, lock_digest = read_lock(lock_text, repo_root)
        dest = str(config.get("dest", ""))
        dest_rel = _safe_relative(dest, "dependency notice directory")
        manifest_name = str(config.get("manifest", ""))
        manifest_leaf = _safe_relative(manifest_name, "dependency notice manifest name")
        if len(manifest_leaf.parts) != 1:
            raise DependencyNoticeError("dependency notice manifest must be a filename")
        manifest_relative = (dest_rel / manifest_leaf.name).as_posix()
        manifest_path = _safe_bundle_file(bundle_dir, manifest_relative)
        payload = json.loads(
            manifest_path.read_text(encoding="utf-8"), object_pairs_hook=_json_object
        )
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise DependencyNoticeError("dependency notice manifest schema is invalid")
        if payload.get("lock_path") != lock_text or payload.get("lock_sha256") != lock_digest:
            raise DependencyNoticeError("dependency notice manifest lock identity differs")
        expected_profile = str(spec.get("profile", {}).get("services_extra", "unknown"))
        if payload.get("profile") != expected_profile:
            raise DependencyNoticeError("dependency notice profile identity differs")
        expected = {package.normalized_name: package for package in packages}
        distributions = payload.get("distributions")
        if not isinstance(distributions, list):
            raise DependencyNoticeError("dependency notice distribution list is invalid")
        actual: dict[str, dict[str, Any]] = {}
        referenced: set[str] = set()
        for item in distributions:
            if not isinstance(item, dict):
                raise DependencyNoticeError("dependency notice distribution entry is invalid")
            normalized = item.get("normalized_name")
            package = expected.get(normalized) if isinstance(normalized, str) else None
            if package is None or normalized in actual:
                raise DependencyNoticeError("dependency notice distribution identity is unexpected or duplicated")
            if (
                not isinstance(item.get("name"), str)
                or _normalized_name(item["name"]) != normalized
                or item.get("version") != package.version
                or item.get("lock_hashes") != list(package.hashes)
                or not isinstance(item.get("metadata_path"), str)
                or not isinstance(item.get("record_sha256"), str)
                or not _HEX_RE.fullmatch(item["record_sha256"])
            ):
                raise DependencyNoticeError("dependency notice package metadata differs from lock")
            _safe_relative(item["metadata_path"], "dependency notice metadata path")
            notices = item.get("notices")
            if not isinstance(notices, list) or not notices:
                raise DependencyNoticeError("locked distribution has no notice files")
            package_slug = f"{normalized}-{package.version}"
            source_paths: set[str] = set()
            for notice in notices:
                if not isinstance(notice, dict):
                    raise DependencyNoticeError("dependency notice file entry is invalid")
                source_path = notice.get("source_path")
                if not isinstance(source_path, str):
                    raise DependencyNoticeError("dependency notice source path is invalid")
                _safe_relative(source_path, "dependency notice source path")
                if source_path in source_paths:
                    raise DependencyNoticeError("dependency notice source path is duplicated")
                source_paths.add(source_path)
                wanted_path = f"{dest_rel.as_posix()}/{package_slug}/{source_path}"
                if notice.get("bundle_path") != wanted_path or wanted_path in referenced:
                    raise DependencyNoticeError("dependency notice output path is unsafe or duplicated")
                record_hash = notice.get("record_hash")
                hash_match = (
                    re.fullmatch(r"(sha256|sha384|sha512):([0-9a-f]+)", record_hash)
                    if isinstance(record_hash, str)
                    else None
                )
                expected_hash_length = {
                    "sha256": 64,
                    "sha384": 96,
                    "sha512": 128,
                }
                if (
                    hash_match is None
                    or len(hash_match.group(2)) != expected_hash_length[hash_match.group(1)]
                ):
                    raise DependencyNoticeError("dependency notice RECORD hash is invalid")
                digest = notice.get("sha256")
                size = notice.get("size")
                if not isinstance(digest, str) or not _HEX_RE.fullmatch(digest):
                    raise DependencyNoticeError("dependency notice SHA-256 is invalid")
                if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                    raise DependencyNoticeError("dependency notice file size is invalid")
                path = _safe_bundle_file(bundle_dir, wanted_path)
                if path.stat().st_size != size or _sha256_file(path) != digest:
                    raise DependencyNoticeError("dependency notice file hash or size differs")
                referenced.add(wanted_path)
            actual[normalized] = item
        if set(actual) != set(expected):
            raise DependencyNoticeError("dependency notice package set differs from selected lock")
        if payload.get("distribution_count") != len(expected):
            raise DependencyNoticeError("dependency notice distribution count differs")
        if payload.get("notice_file_count") != len(referenced):
            raise DependencyNoticeError("dependency notice file count differs")
        dest_path = bundle_dir.joinpath(*dest_rel.parts)
        if dest_path.is_symlink() or not dest_path.is_dir():
            raise DependencyNoticeError("dependency notice directory is missing or unsafe")
        actual_files: set[str] = set()
        for path in dest_path.rglob("*"):
            if path.is_symlink():
                raise DependencyNoticeError("dependency notice directory contains a symlink")
            if path.is_file():
                actual_files.add(path.relative_to(bundle_dir).as_posix())
        expected_files = referenced | {manifest_relative}
        if actual_files != expected_files:
            raise DependencyNoticeError("dependency notice directory has missing or unrecorded files")
        return []
    except (
        DependencyNoticeError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
        RecursionError,
    ):
        return ["dependency notice manifest is missing, unsafe, or inconsistent with the selected lock"]
