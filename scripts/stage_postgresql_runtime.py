#!/usr/bin/env python3
"""Stage the exact Ubuntu Noble libpq runtime closure without installing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
from datetime import datetime, timezone
from typing import BinaryIO, Callable
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "packaging/linux/postgresql-libpq-noble-runtime-lock.json"
BUILD_SUPPLEMENT_LOCK_PATH = ROOT / "packaging/linux/postgresql-libpq-noble-build-supplement-lock.json"
ARCHIVE_BASE = "https://archive.ubuntu.com/ubuntu/"
ARCHIVE_HOST = "archive.ubuntu.com"
EXPECTED_ROOT = "libpq5=16.15-0ubuntu0.24.04.1"
EXPECTED_SUPPLEMENT_ROOT = "libc6-dev=2.39-0ubuntu8.9"
EXPECTED_ORIGIN_INDEXES = (
    "noble-main-amd64-Packages.gz",
    "noble-security-main-amd64-Packages.gz",
    "noble-updates-main-amd64-Packages.gz",
)
MAX_LOCK_BYTES = 1024 * 1024
MAX_DEB_BYTES = 128 * 1024 * 1024
MIN_FREE_HEADROOM = 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 30
CHUNK_BYTES = 1024 * 1024


class StageError(RuntimeError):
    """A locked package input failed validation or staging."""


def sha256_file(path: Path) -> str:
    """Hash one archive without loading its contents into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(CHUNK_BYTES):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_filename(value: object) -> PurePosixPath:
    if not isinstance(value, str):
        raise StageError("package lock Filename must be text")
    path = PurePosixPath(value)
    if (
        not value.startswith("pool/main/")
        or path.is_absolute()
        or "\\" in value
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.name in {"", ".", ".."}
    ):
        raise StageError(f"unsafe package archive path: {value!r}")
    return path


def load_lock(path: Path = LOCK_PATH, kind: str = "runtime") -> tuple[dict, bytes, str]:
    """Read and validate the bounded reviewed package lock."""
    try:
        lock_bytes = path.read_bytes()
    except OSError as exc:
        raise StageError(f"cannot read the reviewed libpq lock: {exc}") from exc
    if len(lock_bytes) > MAX_LOCK_BYTES:
        raise StageError("reviewed libpq lock exceeds its size limit")
    try:
        lock = json.loads(lock_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StageError(f"reviewed libpq lock is invalid JSON: {exc}") from exc
    validate_lock(lock, kind)
    return lock, lock_bytes, _sha256_bytes(lock_bytes)


def _validate_runtime_lock_identity(lock: dict) -> int:
    """Check the runtime lock's pinned root and repository indexes."""
    if lock.get("root") != EXPECTED_ROOT:
        raise StageError("reviewed libpq lock has an unexpected root package")
    if tuple(lock.get("origin_indexes", ())) != EXPECTED_ORIGIN_INDEXES:
        raise StageError("reviewed libpq lock has unexpected Noble index identities")
    return 24


def _validate_supplement_origin(lock: dict) -> None:
    """Check the supplementary lock's signed index and source package."""
    expected_index = {
        "name": "noble-security-main-amd64-Packages.gz",
        "sha256": "83390229c3d130ce91963b525085b7c28ff836df44b8ca7a7c7c13442b4e7c8a",
        "size_bytes": 1422415,
        "signer_fingerprint": "F6ECB3762474EDA9D21B7022871920D1991BC93C",
    }
    if lock.get("origin_index") != expected_index:
        raise StageError("reviewed glibc supplement lock has an unexpected signed index identity")
    expected_source = {"name": "glibc", "version": "2.39-0ubuntu8.9"}
    if lock.get("source_package") != expected_source:
        raise StageError("reviewed glibc supplement lock has an unexpected source version")


def _validate_supplement_lock_identity(lock: dict) -> int:
    """Check the build-only supplement kind, pinned root, and origin."""
    if lock.get("kind") != "build-only-compatibility-supplement":
        raise StageError("reviewed glibc supplement lock has an unexpected kind")
    if lock.get("root") != EXPECTED_SUPPLEMENT_ROOT:
        raise StageError("reviewed glibc supplement lock has an unexpected root package")
    _validate_supplement_origin(lock)
    return 2


def _validate_lock_identity(lock: dict, kind: str) -> int:
    """Select the expected identity checks for a supported lock kind."""
    if kind == "runtime":
        return _validate_runtime_lock_identity(lock)
    if kind == "build-supplement":
        return _validate_supplement_lock_identity(lock)
    raise StageError("unsupported PostgreSQL package lock kind")


def _validate_package_count(lock: dict, kind: str, expected_count: int) -> list[dict]:
    """Return the package records after validating the exact locked count."""
    packages = lock.get("packages")
    if (
        not isinstance(packages, list)
        or lock.get("package_count") != expected_count
        or len(packages) != expected_count
    ):
        raise StageError(f"reviewed {kind} lock must contain exactly {expected_count} packages")
    return packages


def _validate_package_name_version(package: object) -> tuple[dict, str]:
    """Validate a package entry's Debian package name and version."""
    if not isinstance(package, dict):
        raise StageError("invalid package entry in reviewed libpq lock")
    name, version = package.get("Package"), package.get("Version")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", name):
        raise StageError("invalid Debian package name in reviewed libpq lock")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9.+:~_-]+", version):
        raise StageError(f"invalid package version in reviewed libpq lock: {name}")
    return package, name


def _validate_package_identity(
    package: object,
    names: set[str],
    filenames: set[str],
) -> str:
    """Validate architecture and unique filename after package identity."""
    package, name = _validate_package_name_version(package)
    if name in names:
        raise StageError(f"duplicate package in reviewed libpq lock: {name}")
    names.add(name)
    if package.get("Architecture") != "amd64":
        raise StageError(f"unsupported package architecture in reviewed lock: {name}")
    rel = _safe_filename(package.get("Filename"))
    if rel.name in filenames:
        raise StageError(f"duplicate .deb filename in reviewed libpq lock: {rel.name}")
    filenames.add(rel.name)
    return name


def _validate_package_size(package: dict, name: str) -> int:
    """Validate and return a package's bounded archive size."""
    size_text = package.get("Size")
    if not isinstance(size_text, str) or not size_text.isdecimal():
        raise StageError(f"invalid package size in reviewed libpq lock: {name}")
    size = int(size_text)
    if size <= 0 or size > MAX_DEB_BYTES:
        raise StageError(f"package size is outside the accepted bound: {name}")
    return size


def _validate_package_digest(package: dict, name: str) -> None:
    """Require the locked archive digest to be a lowercase SHA-256 value."""
    digest = package.get("SHA256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise StageError(f"invalid package SHA-256 in reviewed libpq lock: {name}")


def _validate_package_dependencies(package: dict, name: str) -> None:
    """Reject malformed dependency fields that could alter install parsing."""
    for field in ("Depends", "Pre-Depends"):
        value = package.get(field, "")
        if not isinstance(value, str) or "\n" in value or "\r" in value:
            raise StageError(f"invalid {field} value in reviewed libpq lock: {name}")


def _validate_package_bounds(package: dict, name: str) -> int:
    """Validate a package's size, digest, and dependency text bounds."""
    size = _validate_package_size(package, name)
    _validate_package_digest(package, name)
    _validate_package_dependencies(package, name)
    return size


def _bounded_signed_record(record: object, name: str) -> str:
    """Return valid UTF-8 signed metadata within the record size limit."""
    if not isinstance(record, str):
        raise StageError(f"missing or oversized signed package metadata record: {name}")
    try:
        encoded_size = len(record.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise StageError(f"malformed signed package metadata record for {name}") from exc
    if encoded_size > 64 * 1024:
        raise StageError(f"missing or oversized signed package metadata record: {name}")
    return record


def _parse_signed_record(record: object, name: str) -> dict[str, str]:
    """Parse one bounded Debian control stanza and reject malformed duplicates."""
    record = _bounded_signed_record(record, name)
    fields: dict[str, str] = {}
    seen_names: set[str] = set()
    for line in record.splitlines():
        if not line or line[0].isspace():
            continue
        if ": " not in line:
            raise StageError(f"malformed signed package metadata record for {name}")
        field_name, value = line.split(": ", 1)
        normalized_name = field_name.casefold()
        if not field_name or normalized_name in seen_names:
            raise StageError(f"duplicate signed package metadata field for {name}: {field_name}")
        seen_names.add(normalized_name)
        fields[field_name] = value
    return fields


def _validate_signed_record(package: dict, name: str) -> None:
    """Require signed index identity and relationship fields to match the lock."""
    fields = _parse_signed_record(package.get("signed_index_record"), name)
    for field in ("Package", "Version", "Architecture", "Filename", "Size", "SHA256"):
        if fields.get(field) != package.get(field):
            raise StageError(f"signed package metadata differs from lock for {name}: {field}")
    for field in ("Depends", "Pre-Depends", "Provides", "Conflicts", "Breaks", "Replaces", "Multi-Arch"):
        if fields.get(field, "") != package.get(field, ""):
            raise StageError(f"signed package metadata differs from lock for {name}: {field}")


def _validate_root_package(lock: dict, kind: str, packages_by_name: dict[str, dict]) -> None:
    """Require the actual package row to agree with the lock's root spec."""
    root = lock.get("root")
    if not isinstance(root, str) or "=" not in root:
        raise StageError(f"reviewed {kind} lock has an invalid root package identity")
    name, version = root.split("=", 1)
    package = packages_by_name.get(name)
    if package is None:
        message = "reviewed libpq closure omits its root package" if kind == "runtime" else "reviewed glibc build supplement omits its root package"
        raise StageError(message)
    if package.get("Version") != version:
        raise StageError(f"reviewed {kind} root package row differs from its root identity")


def _validate_package_closure(lock: dict, kind: str, names: set[str], total_size: int) -> None:
    """Validate the final package set, aggregate bound, and runtime edge evidence."""
    if kind == "build-supplement" and names != {"libc-dev-bin", "libc6-dev"}:
        raise StageError("reviewed glibc build supplement must be libc-dev-bin and libc6-dev only")
    if total_size > 256 * 1024 * 1024:
        raise StageError("reviewed libpq closure exceeds the staging size limit")
    if kind == "runtime" and not isinstance(lock.get("edges"), list):
        raise StageError("reviewed libpq lock has no dependency-edge evidence")


def validate_lock(lock: object, kind: str = "runtime") -> list[dict]:
    """Validate lock identity, package records, signed metadata, and closure."""
    if not isinstance(lock, dict):
        raise StageError("reviewed libpq lock must be a JSON object")
    expected_count = _validate_lock_identity(lock, kind)
    packages = _validate_package_count(lock, kind, expected_count)
    names: set[str] = set()
    filenames: set[str] = set()
    packages_by_name = {}
    total_size = 0
    for package in packages:
        name = _validate_package_identity(package, names, filenames)
        total_size += _validate_package_bounds(package, name)
        packages_by_name[name] = package
    _validate_root_package(lock, kind, packages_by_name)
    if kind == "build-supplement":
        for name, package in packages_by_name.items():
            _validate_signed_record(package, name)
    _validate_package_closure(lock, kind, names, total_size)
    return packages


def _open_regular_file(path: Path) -> BinaryIO:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise StageError(f"cannot open cached package safely: {path.name}: {exc}") from exc
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode):
        os.close(descriptor)
        raise StageError(f"cached package is not a regular file: {path.name}")
    return os.fdopen(descriptor, "rb")


def _stream_checked(source: BinaryIO, destination: Path, expected_size: int, expected_hash: str) -> None:
    digest = hashlib.sha256()
    size = 0
    try:
        with destination.open("xb") as output:
            while block := source.read(CHUNK_BYTES):
                size += len(block)
                if size > expected_size:
                    raise StageError("package download exceeded locked size")
                digest.update(block)
                output.write(block)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    if size != expected_size or digest.hexdigest() != expected_hash:
        destination.unlink(missing_ok=True)
        raise StageError("package size or SHA-256 differs from the reviewed lock")


def _stage_one(package: dict, deb_dir: Path, cache_dir: Path | None,
               opener: Callable = urlopen) -> dict:
    filename = _safe_filename(package["Filename"]).name
    size = int(package["Size"])
    expected_hash = package["SHA256"]
    destination = deb_dir / filename
    cached = cache_dir / filename if cache_dir is not None else None
    if cached is not None and (cached.exists() or cached.is_symlink()):
        if cached.is_symlink():
            raise StageError(f"refusing symlink in .deb cache: {filename}")
        with _open_regular_file(cached) as source:
            temp = deb_dir / f".{filename}.partial"
            try:
                _stream_checked(source, temp, size, expected_hash)
                os.replace(temp, destination)
            finally:
                temp.unlink(missing_ok=True)
        source_kind = "verified_private_cache"
        source_url = None
    else:
        url = ARCHIVE_BASE + package["Filename"]
        request = Request(url, headers={"User-Agent": "airunner-libpq-input-stager/1"})
        temp = deb_dir / f".{filename}.partial"
        try:
            with opener(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                final_url = urlparse(response.geturl())
                if final_url.scheme != "https" or final_url.hostname != ARCHIVE_HOST:
                    raise StageError("Ubuntu package download redirected outside the pinned archive host")
                _stream_checked(response, temp, size, expected_hash)
                os.replace(temp, destination)
        except (OSError, URLError, TimeoutError) as exc:
            raise StageError(f"failed to fetch reviewed package {package['Package']}: {exc}") from exc
        finally:
            temp.unlink(missing_ok=True)
        source_kind = "canonical_archive_download"
        source_url = url
    return {
        "package": package["Package"],
        "version": package["Version"],
        "architecture": package["Architecture"],
        "filename": filename,
        "size_bytes": size,
        "sha256": expected_hash,
        "source": source_kind,
        "source_url": source_url,
    }


def _build_install_list(packages: list[dict]) -> bytes:
    install_lines: list[str] = []
    for package in packages:
        name = package["Package"]
        version = package["Version"]
        install_lines.append(f"{name}={version}")
    return ("\n".join(install_lines) + "\n").encode("ascii")


def _write_bytes(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _write_stage_files(temp: Path, lock: dict, lock_bytes: bytes,
                       lock_hash: str, staged: list[dict], kind: str) -> None:
    _write_bytes(temp / "install-packages.txt", _build_install_list(lock["packages"]))
    lock_name = (
        "postgresql-libpq-noble-runtime-lock.json"
        if kind == "runtime"
        else "postgresql-libpq-noble-build-supplement-lock.json"
    )
    _write_bytes(temp / lock_name, lock_bytes)

    source_indexes = (
        {"origin_indexes": lock["origin_indexes"]}
        if kind == "runtime"
        else {"origin_index": lock["origin_index"]}
    )
    receipt = {
        "schema_version": 1,
        "kind": kind,
        "status": f"hash-verified Ubuntu Noble {kind} package inputs staged; not installed",
        "installation_performed": False,
        "maintainer_scripts_executed": False,
        "database_driver_imported": False,
        "database_connection_attempted": False,
        "root_package": lock["root"],
        "lock_sha256": lock_hash,
        "package_count": len(staged),
        "total_bytes": sum(item["size_bytes"] for item in staged),
        "packages": staged,
        **source_indexes,
    }
    _write_bytes(
        temp / "staging-receipt.json",
        (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    sums = []
    for path in sorted(item for item in temp.rglob("*") if item.is_file() and item.name != "SHA256SUMS"):
        sums.append(f"{sha256_file(path)}  {path.relative_to(temp).as_posix()}")
    _write_bytes(temp / "SHA256SUMS", ("\n".join(sums) + "\n").encode("ascii"))


def _validate_paths(output: Path, cache: Path | None) -> tuple[Path, Path | None]:
    if not output.is_absolute():
        raise StageError("--output-dir must be absolute")
    if output.is_symlink():
        raise StageError("--output-dir must not be a symlink")
    parent = output.parent.resolve(strict=True)
    target = parent / output.name
    if target == ROOT or ROOT in target.parents or target == LOCK_PATH:
        raise StageError("output directory must be outside the repository and lock file")
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise StageError("--output-dir must not exist or must be empty")
    cache_real = None
    if cache is not None:
        if cache.is_symlink() or not cache.is_dir():
            raise StageError("--cache-dir must be an existing real directory")
        cache_real = cache.resolve(strict=True)
        if target == cache_real or target in cache_real.parents or cache_real in target.parents:
            raise StageError("output and package cache paths must be disjoint")
    return target, cache_real


def stage(output: Path, cache_dir: Path | None = None,
          opener: Callable = urlopen, lock_path: Path = LOCK_PATH,
          kind: str = "runtime") -> dict:
    """Stage only verified locked inputs and retain a non-installation receipt."""
    lock, lock_bytes, lock_hash = load_lock(lock_path, kind)
    packages = lock["packages"]
    output, cache_dir = _validate_paths(output, cache_dir)
    expected_total = sum(int(package["Size"]) for package in packages)
    if shutil.disk_usage(output.parent).free < expected_total + MIN_FREE_HEADROOM:
        raise StageError("insufficient free disk for the locked .debs and staging headroom")
    temp = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    deb_dir = temp / "debs"
    deb_dir.mkdir()
    completed: list[dict] = []
    try:
        for package in packages:
            completed.append(_stage_one(package, deb_dir, cache_dir, opener))
        _write_stage_files(temp, lock, lock_bytes, lock_hash, completed, kind)
        # Keep the lock-indexed closure exact; do not pass through extra cache files.
        expected_debs = {item["filename"] for item in completed}
        if {path.name for path in deb_dir.iterdir()} != expected_debs:
            raise StageError("staging directory contains files outside the locked package set")
        # The isolated apt acquisition user must traverse the local file
        # repository; inputs are public Ubuntu packages and lock metadata.
        for path in temp.rglob("*"):
            path.chmod(0o755 if path.is_dir() else 0o644)
        temp.chmod(0o755)
        if output.exists():
            output.rmdir()
        os.replace(temp, output)
        return json.loads((output / "staging-receipt.json").read_text(encoding="utf-8"))
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise


def main() -> int:
    """Run the package staging CLI without importing a database driver."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--kind", choices=("runtime", "build-supplement"), default="runtime")
    parser.add_argument("--cache-dir", type=Path, help="reuse exact cached .debs before fetching archive.ubuntu.com")
    args = parser.parse_args()
    try:
        lock_path = LOCK_PATH if args.kind == "runtime" else BUILD_SUPPLEMENT_LOCK_PATH
        receipt = stage(args.output_dir, args.cache_dir, lock_path=lock_path, kind=args.kind)
    except (OSError, StageError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps({key: receipt[key] for key in ("status", "root_package", "package_count", "total_bytes", "lock_sha256")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
