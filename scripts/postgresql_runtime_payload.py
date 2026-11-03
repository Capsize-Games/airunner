"""Validate and stage the reviewed Ubuntu libpq prerequisite in bundles."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
from typing import Any


LOCK_RELATIVE = Path("packaging/linux/postgresql-libpq-noble-runtime-lock.json")
LOCK_NAME = "postgresql-libpq-noble-runtime-lock.json"
SUPPLEMENT_LOCK_RELATIVE = Path("packaging/linux/postgresql-libpq-noble-build-supplement-lock.json")
SUPPLEMENT_LOCK_NAME = "postgresql-libpq-noble-build-supplement-lock.json"
DESTINATION = Path("runtime-requirements/postgresql")
EXPECTED_ROOT = "libpq5=16.15-0ubuntu0.24.04.1"
EXPECTED_COUNT = 24
EXPECTED_SUPPLEMENT_ROOT = "libc6-dev=2.39-0ubuntu8.9"
EXPECTED_SUPPLEMENT_COUNT = 2
EXPECTED_SUPPLEMENT_PACKAGES = {"libc-dev-bin", "libc6-dev"}
MAX_METADATA_BYTES = 1024 * 1024
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class PostgreSQLPayloadError(ValueError):
    """The staged PostgreSQL OS prerequisite is incomplete or unsafe."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _regular(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _real_directory(path: Path, label: str) -> Path:
    """Resolve a directory only after rejecting symlink components."""
    absolute = Path(os.path.abspath(path))
    for component in (*reversed(absolute.parents), absolute):
        if component.is_symlink():
            raise PostgreSQLPayloadError(f"{label} path contains a symlink")
    if not absolute.is_dir():
        raise PostgreSQLPayloadError(f"{label} path is absent or not a directory")
    return absolute.resolve(strict=True)


def _load_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    if not _regular(path):
        raise PostgreSQLPayloadError(f"{label} is missing or not a regular file")
    data = path.read_bytes()
    if len(data) > MAX_METADATA_BYTES:
        raise PostgreSQLPayloadError(f"{label} exceeds the size limit")
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PostgreSQLPayloadError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise PostgreSQLPayloadError(f"{label} must be a JSON object")
    return value, data


def _valid_package_record(item: Any, label: str) -> tuple[str, str]:
    if not isinstance(item, dict):
        raise PostgreSQLPayloadError(f"{label} package record is invalid")
    name, version, arch = item.get("Package"), item.get("Version"), item.get("Architecture")
    rel = PurePosixPath(str(item.get("Filename", "")))
    digest, size = item.get("SHA256"), item.get("Size")
    safe_path = (
        not rel.is_absolute()
        and len(rel.parts) >= 3
        and rel.parts[0] == "pool"
        and all(part not in {"", ".", ".."} for part in rel.parts)
        and "\\" not in str(item.get("Filename", ""))
    )
    valid_identity = (
        isinstance(name, str)
        and re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", name)
        and isinstance(version, str)
        and arch == "amd64"
    )
    valid_digest = isinstance(digest, str) and SHA_RE.fullmatch(digest)
    valid_size = isinstance(size, str) and size.isdecimal() and int(size) > 0
    if not (safe_path and valid_identity and valid_digest and valid_size):
        raise PostgreSQLPayloadError(f"{label} package record is malformed")
    return name, rel.name


def _package_map(
    packages: Any,
    expected_count: int,
    label: str,
    expected_names: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(packages, list) or len(packages) != expected_count:
        raise PostgreSQLPayloadError(f"{label} lock package count is invalid")
    result: dict[str, dict[str, Any]] = {}
    names: set[str] = set()
    for item in packages:
        name, filename = _valid_package_record(item, label)
        if filename in result or name in names:
            raise PostgreSQLPayloadError(f"{label} lock has duplicate package identities")
        result[filename] = item
        names.add(name)
    if expected_names is not None and names != expected_names:
        raise PostgreSQLPayloadError(f"{label} lock package set is incomplete or unexpected")
    return result


def _package_files(lock: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if lock.get("root") != EXPECTED_ROOT or lock.get("package_count") != EXPECTED_COUNT:
        raise PostgreSQLPayloadError("reviewed Noble PostgreSQL lock has an unexpected shape")
    result = _package_map(lock.get("packages"), EXPECTED_COUNT, "PostgreSQL")
    if "libpq5_16.15-0ubuntu0.24.04.1_amd64.deb" not in result:
        raise PostgreSQLPayloadError("reviewed PostgreSQL lock does not contain the exact libpq root")
    return result


def _verify_checksums(stage_dir: Path) -> set[str]:
    sums_path = stage_dir / "SHA256SUMS"
    if not _regular(sums_path):
        raise PostgreSQLPayloadError("staged PostgreSQL SHA256SUMS is missing")
    listed: set[str] = set()
    for raw_line in sums_path.read_text(encoding="ascii").splitlines():
        if len(raw_line) < 67 or raw_line[64:66] != "  ":
            raise PostgreSQLPayloadError("staged PostgreSQL checksum record is malformed")
        digest, relative = raw_line[:64], raw_line[66:]
        path = PurePosixPath(relative)
        if (
            not SHA_RE.fullmatch(digest)
            or path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or relative in listed
        ):
            raise PostgreSQLPayloadError("staged PostgreSQL checksum path is unsafe or duplicated")
        target = stage_dir.joinpath(*path.parts)
        if not _regular(target) or _sha256(target) != digest:
            raise PostgreSQLPayloadError(f"staged PostgreSQL checksum mismatch: {relative}")
        listed.add(relative)
    return listed


def _validate_input_tree(stage_dir: Path, expected_files: set[str], label: str) -> None:
    """Reject symlinks, special files, and unlisted files or directories."""
    files: set[str] = set()
    directories: set[str] = set()
    for path in stage_dir.rglob("*"):
        mode = path.lstat().st_mode
        relative = path.relative_to(stage_dir).as_posix()
        if stat.S_ISLNK(mode):
            raise PostgreSQLPayloadError(f"{label} contains a symlink: {relative}")
        if stat.S_ISDIR(mode):
            directories.add(relative)
        elif stat.S_ISREG(mode):
            files.add(relative)
        else:
            raise PostgreSQLPayloadError(f"{label} contains a special file: {relative}")
    expected_directories = {
        PurePosixPath(name).parent.as_posix()
        for name in expected_files
        if PurePosixPath(name).parent.as_posix() != "."
    }
    if files != expected_files or directories != expected_directories:
        raise PostgreSQLPayloadError(f"{label} contains missing or unexpected files or directories")


def _prepare_bundle_destination(bundle_dir: Path) -> Path:
    """Create a new PostgreSQL destination below real bundle directories only."""
    bundle_dir = _real_directory(bundle_dir, "bundle output")
    runtime_root = bundle_dir / "runtime-requirements"
    if runtime_root.exists() or runtime_root.is_symlink():
        if runtime_root.is_symlink() or not runtime_root.is_dir():
            raise PostgreSQLPayloadError("bundle runtime-requirements path is a symlink or not a real directory")
    else:
        runtime_root.mkdir()
    destination = runtime_root / "postgresql"
    if destination.exists() or destination.is_symlink():
        raise PostgreSQLPayloadError("bundle PostgreSQL payload destination already exists")
    destination.mkdir()
    return destination


def _prepare_disabled_destination(bundle_dir: Path, policy: dict[str, Any]) -> Path:
    """Allow only an identical prior SQLite-only policy during repeated assembly."""
    bundle_dir = _real_directory(bundle_dir, "bundle output")
    runtime_root = bundle_dir / "runtime-requirements"
    if runtime_root.is_symlink() or (runtime_root.exists() and not runtime_root.is_dir()):
        raise PostgreSQLPayloadError("bundle runtime-requirements path is unsafe")
    runtime_root.mkdir(exist_ok=True)
    destination = runtime_root / "postgresql"
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise PostgreSQLPayloadError("bundle PostgreSQL payload destination is unsafe")
    if destination.exists():
        entries = list(destination.iterdir())
        policy_path = destination / "runtime-policy.json"
        if len(entries) != 1 or entries[0] != policy_path or not _regular(policy_path):
            raise PostgreSQLPayloadError("bundle PostgreSQL payload destination already contains data")
        existing, _ = _load_json(policy_path, "SQLite-only runtime policy")
        if existing != policy:
            raise PostgreSQLPayloadError("bundle contains a different PostgreSQL runtime policy")
        return destination
    destination.mkdir()
    return destination


def _receipt_packages(receipt: dict[str, Any], expected_count: int, label: str) -> dict[str, dict[str, Any]]:
    records = receipt.get("packages")
    if not isinstance(records, list) or len(records) != expected_count:
        raise PostgreSQLPayloadError(f"{label} receipt has an unexpected package count")
    result = {}
    for item in records:
        if not isinstance(item, dict) or not isinstance(item.get("filename"), str):
            raise PostgreSQLPayloadError(f"{label} receipt package record is invalid")
        filename = item["filename"]
        if filename in result:
            raise PostgreSQLPayloadError(f"{label} receipt has duplicate package files")
        result[filename] = item
    return result


def _validate_receipt(
    stage_dir: Path,
    receipt: dict[str, Any],
    lock: dict[str, Any],
    lock_bytes: bytes,
    package_files: dict[str, dict[str, Any]],
    label: str,
    kind: str,
) -> None:
    expected_count = len(package_files)
    valid = (
        receipt.get("kind") == kind
        and receipt.get("installation_performed") is False
        and receipt.get("package_count") == expected_count
        and receipt.get("lock_sha256") == hashlib.sha256(lock_bytes).hexdigest()
    )
    if kind == "runtime":
        valid = valid and receipt.get("database_driver_imported") is False
        valid = valid and receipt.get("database_connection_attempted") is False
        valid = valid and tuple(receipt.get("origin_indexes", ())) == tuple(lock.get("origin_indexes", ()))
    if not valid:
        raise PostgreSQLPayloadError(f"{label} receipt does not match its reviewed lock")
    by_filename = _receipt_packages(receipt, expected_count, label)
    if set(by_filename) != set(package_files):
        raise PostgreSQLPayloadError(f"{label} receipt package set differs from the lock")
    for filename, package in package_files.items():
        _validate_receipt_package(by_filename[filename], package, stage_dir, filename, label)


def _validate_receipt_package(
    receipt_item: dict[str, Any], package: dict[str, Any],
    stage_dir: Path, filename: str, label: str,
) -> None:
    receipt_matches = (
        receipt_item.get("package") == package["Package"]
        and receipt_item.get("version") == package["Version"]
        and receipt_item.get("architecture") == package["Architecture"]
        and receipt_item.get("sha256") == package["SHA256"]
        and receipt_item.get("size_bytes") == int(package["Size"])
    )
    if not receipt_matches:
        raise PostgreSQLPayloadError(f"{label} receipt differs from lock for {package['Package']}")
    deb_path = stage_dir / "debs" / filename
    if (
        not _regular(deb_path)
        or deb_path.stat().st_size != int(package["Size"])
        or _sha256(deb_path) != package["SHA256"]
    ):
        raise PostgreSQLPayloadError(f"staged .deb differs from lock: {package['Package']}")


def _validate_stage_indexes(
    stage_dir: Path,
    package_files: dict[str, dict[str, Any]],
    lock_name: str,
    label: str,
    allowed_additional_files: set[str] | None = None,
) -> None:
    packages = list(package_files.values())
    expected_list = "".join(f"{item['Package']}={item['Version']}\n" for item in packages)
    install_list = stage_dir / "install-packages.txt"
    if not _regular(install_list) or install_list.read_text(encoding="ascii") != expected_list:
        raise PostgreSQLPayloadError(f"{label} install list differs from its reviewed lock")
    expected_files = {
        "SHA256SUMS", "install-packages.txt", lock_name, "staging-receipt.json",
        *(f"debs/{name}" for name in package_files),
    }
    additions = allowed_additional_files or set()
    if _verify_checksums(stage_dir) != expected_files - {"SHA256SUMS"}:
        raise PostgreSQLPayloadError(f"{label} has missing or extra checksum records")
    _validate_input_tree(stage_dir, expected_files | additions, label)


def validate_staged_runtime(
    stage_dir: Path,
    repo_root: Path,
    allowed_additional_files: set[str] | None = None,
) -> dict[str, Any]:
    """Verify staged package bytes against the source lock and receipt."""
    stage_dir = _real_directory(stage_dir, "staged PostgreSQL input")
    lock_path = stage_dir / LOCK_NAME
    lock, lock_bytes = _load_json(lock_path, "staged PostgreSQL lock")
    expected_lock = repo_root / LOCK_RELATIVE
    if not _regular(expected_lock) or lock_bytes != expected_lock.read_bytes():
        raise PostgreSQLPayloadError("staged PostgreSQL lock differs from the reviewed repository lock")
    package_files = _package_files(lock)
    receipt, _ = _load_json(stage_dir / "staging-receipt.json", "staging receipt")
    _validate_receipt(stage_dir, receipt, lock, lock_bytes, package_files, "PostgreSQL", "runtime")
    _validate_stage_indexes(
        stage_dir, package_files, LOCK_NAME, "staged PostgreSQL input directory",
        allowed_additional_files,
    )
    return {"lock": lock, "receipt": receipt, "package_files": package_files}


def validate_staged_supplement(stage_dir: Path, repo_root: Path) -> dict[str, Any]:
    """Verify the optional glibc compatibility supplement, without installing it."""
    stage_dir = _real_directory(stage_dir, "staged glibc compatibility input")
    lock, lock_bytes = _load_json(stage_dir / SUPPLEMENT_LOCK_NAME, "staged glibc supplement lock")
    expected_lock = repo_root / SUPPLEMENT_LOCK_RELATIVE
    if not _regular(expected_lock) or lock_bytes != expected_lock.read_bytes():
        raise PostgreSQLPayloadError("staged glibc supplement lock differs from the reviewed repository lock")
    if (
        lock.get("kind") != "build-only-compatibility-supplement"
        or lock.get("root") != EXPECTED_SUPPLEMENT_ROOT
        or lock.get("package_count") != EXPECTED_SUPPLEMENT_COUNT
    ):
        raise PostgreSQLPayloadError("reviewed glibc supplement lock has an unexpected shape")
    package_files = _package_map(
        lock.get("packages"), EXPECTED_SUPPLEMENT_COUNT, "glibc supplement",
        EXPECTED_SUPPLEMENT_PACKAGES,
    )
    receipt, _ = _load_json(stage_dir / "staging-receipt.json", "glibc supplement receipt")
    _validate_receipt(stage_dir, receipt, lock, lock_bytes, package_files, "glibc supplement", "build-supplement")
    _validate_stage_indexes(stage_dir, package_files, SUPPLEMENT_LOCK_NAME, "staged glibc supplement")
    return {"lock": lock, "receipt": receipt, "package_files": package_files}


def _query_builder_package() -> dict[str, str]:
    """Read builder libpq package metadata without loading a shared library."""
    try:
        result = subprocess.run(
            [
                "dpkg-query",
                "--show",
                "--showformat=${Package}\\t${Version}\\t${Architecture}\\t${db:Status-Status}\\n",
                "libpq5",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"availability": "unavailable", "reason": "dpkg-query could not be read"}
    fields = result.stdout.strip().split("\t")
    if result.returncode != 0 or len(fields) != 4 or fields[0] != "libpq5" or fields[3] != "installed":
        return {"availability": "unavailable", "reason": "libpq5 is not installed on the freeze builder"}
    return {
        "availability": "installed",
        "package": fields[0],
        "version": fields[1],
        "architecture": fields[2],
        "status": fields[3],
    }


def _builder_provenance(bundle_dir: Path | None = None) -> dict[str, Any]:
    """Record builder metadata and observed bundle paths, without loading libpq."""
    os_release: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                if key in {"ID", "VERSION_ID", "PRETTY_NAME"}:
                    os_release[key] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    libpq_paths = (
        sorted(
            path.relative_to(bundle_dir).as_posix()
            for path in bundle_dir.rglob("*")
            if re.fullmatch(r"libpq\.so(?:\..+)?", path.name)
            and (path.is_file() or path.is_symlink())
        )
        if bundle_dir is not None
        else []
    )
    return {
        "schema_version": 1,
        "build_host": {
            "os_release": os_release,
            "architecture": platform.machine(),
            "libpq5_package": _query_builder_package(),
        },
        "freeze_analysis": {
            "native_library_load_observation": "not_measured",
            "runtime_loader": "Psycopg's selected ctypes implementation resolves system libpq at application runtime.",
            "candidate_bundle_libpq_paths": libpq_paths,
            "libpq_collection_expected": False,
        },
    }


def validate_build_host() -> dict[str, Any]:
    """Require the reviewed Ubuntu Noble amd64 host before full freezing."""
    provenance = _builder_provenance()
    host = provenance["build_host"]
    release = host.get("os_release", {})
    if (
        not isinstance(release, dict)
        or release.get("ID") != "ubuntu"
        or release.get("VERSION_ID") != "24.04"
        or host.get("architecture") not in {"x86_64", "amd64"}
    ):
        raise PostgreSQLPayloadError(
            "full PostgreSQL candidate freezing requires Ubuntu 24.04 amd64"
        )
    return provenance


def stage_runtime_payload(
    stage_dir: Path,
    bundle_dir: Path,
    spec: dict[str, Any],
    repo_root: Path,
    supplement_stage_dir: Path | None = None,
) -> None:
    """Copy exact offline OS prerequisites and policy into the bundle."""
    config = spec.get("postgresql_runtime", {})
    mode = config.get("mode") if isinstance(config, dict) else None
    if mode == "disabled":
        if stage_dir is not None or supplement_stage_dir is not None:
            raise PostgreSQLPayloadError("SQLite-only bundle must not receive PostgreSQL package inputs")
        _stage_disabled_policy(bundle_dir)
        return
    if mode != "locked-ubuntu-debs":
        raise PostgreSQLPayloadError("bundle spec must explicitly select a PostgreSQL runtime policy")
    if stage_dir is None:
        raise PostgreSQLPayloadError("full bundle requires staged PostgreSQL OS package inputs")
    if supplement_stage_dir is None:
        raise PostgreSQLPayloadError("full bundle requires staged glibc build compatibility inputs")
    staged = validate_staged_runtime(stage_dir, repo_root)
    supplement = validate_staged_supplement(supplement_stage_dir, repo_root)
    destination = _prepare_bundle_destination(bundle_dir)
    _copy_runtime_files(stage_dir, destination, staged["package_files"], repo_root)
    _copy_supplement_files(supplement_stage_dir, destination, supplement["package_files"])
    _write_runtime_policy(destination, bundle_dir)


def _stage_disabled_policy(bundle_dir: Path) -> None:
    policy = {
        "schema_version": 1,
        "mode": "disabled",
        "reason": "This bundle profile is SQLite-only and does not include PostgreSQL support.",
    }
    destination = _prepare_disabled_destination(bundle_dir, policy)
    (destination / "runtime-policy.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _copy_runtime_files(
    stage_dir: Path, destination: Path, package_files: dict[str, Any], repo_root: Path
) -> None:
    for name in ("SHA256SUMS", "install-packages.txt", LOCK_NAME, "staging-receipt.json"):
        shutil.copyfile(stage_dir / name, destination / name)
    shutil.copyfile(
        repo_root / "packaging/linux/install-postgresql-runtime.sh",
        destination / "install-postgresql-runtime.sh",
    )
    (destination / "install-postgresql-runtime.sh").chmod(0o755)
    shutil.copyfile(
        repo_root / "services/src/airunner_services/runtimes/postgresql_prerequisites.py",
        destination / "verify-postgresql-runtime.py",
    )
    debs = destination / "debs"
    debs.mkdir()
    for filename in package_files:
        shutil.copyfile(stage_dir / "debs" / filename, debs / filename)


def _copy_supplement_files(
    stage_dir: Path, destination: Path, package_files: dict[str, Any]
) -> None:
    supplement_destination = destination / "build-supplement"
    supplement_destination.mkdir()
    for name in ("SHA256SUMS", "install-packages.txt", SUPPLEMENT_LOCK_NAME, "staging-receipt.json"):
        shutil.copyfile(stage_dir / name, supplement_destination / name)
    supplement_debs = supplement_destination / "debs"
    supplement_debs.mkdir()
    for filename in package_files:
        shutil.copyfile(stage_dir / "debs" / filename, supplement_debs / filename)


def _write_runtime_policy(destination: Path, bundle_dir: Path) -> None:
    policy = {
        "schema_version": 1,
        "mode": "locked-ubuntu-debs",
        "target": {"os_id": "ubuntu", "version_id": "24.04", "architecture": "amd64"},
        "root_package": EXPECTED_ROOT,
        "package_count": EXPECTED_COUNT,
        "package_directory": "debs",
        "lock_file": LOCK_NAME,
        "receipt_file": "staging-receipt.json",
        "installer": "install-postgresql-runtime.sh",
        "freeze_analysis_native_library_load_observation": "not_measured",
        "freeze_native_libpq_collected": False,
        "build_supplement": {
            "lock_file": f"build-supplement/{SUPPLEMENT_LOCK_NAME}",
            "receipt_file": "build-supplement/staging-receipt.json",
            "package_count": EXPECTED_SUPPLEMENT_COUNT,
            "install_condition": "only when libc6-dev is already installed",
        },
    }
    (destination / "runtime-policy.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    provenance = _builder_provenance(bundle_dir)
    (destination / "freeze-build-provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if provenance["freeze_analysis"]["candidate_bundle_libpq_paths"]:
        raise PostgreSQLPayloadError("candidate unexpectedly contains a builder-provided libpq shared library")


def _expected_policy() -> dict[str, Any]:
    return {
        "mode": "locked-ubuntu-debs",
        "target": {"os_id": "ubuntu", "version_id": "24.04", "architecture": "amd64"},
        "root_package": EXPECTED_ROOT,
        "package_count": EXPECTED_COUNT,
        "package_directory": "debs",
        "lock_file": LOCK_NAME,
        "receipt_file": "staging-receipt.json",
        "installer": "install-postgresql-runtime.sh",
        "freeze_native_libpq_collected": False,
        "freeze_analysis_native_library_load_observation": "not_measured",
        "build_supplement": {
            "lock_file": f"build-supplement/{SUPPLEMENT_LOCK_NAME}",
            "receipt_file": "build-supplement/staging-receipt.json",
            "package_count": EXPECTED_SUPPLEMENT_COUNT,
            "install_condition": "only when libc6-dev is already installed",
        },
    }


def _verify_provenance(bundle_dir: Path, destination: Path, repo_root: Path) -> list[str]:
    problems: list[str] = []
    provenance_path = destination / "freeze-build-provenance.json"
    installer_path = destination / "install-postgresql-runtime.sh"
    verifier_path = destination / "verify-postgresql-runtime.py"
    if not _regular(provenance_path) or not _regular(installer_path):
        return ["PostgreSQL runtime provenance or installer is missing"]
    try:
        provenance, _ = _load_json(provenance_path, "freeze build provenance")
    except PostgreSQLPayloadError as exc:
        return [str(exc)]
    analysis = provenance.get("freeze_analysis")
    if not isinstance(analysis, dict):
        problems.append("freeze build provenance lacks libpq resolution data")
        analysis = {}
    candidate_paths = analysis.get("candidate_bundle_libpq_paths")
    if (
        analysis.get("native_library_load_observation") != "not_measured"
        or analysis.get("libpq_collection_expected") is not False
        or not isinstance(candidate_paths, list)
    ):
        problems.append("freeze build provenance overstates libpq load or collection evidence")
        candidate_paths = []
    elif candidate_paths:
        problems.append("candidate contains a builder-provided libpq shared library")
    actual_paths = _bundle_libpq_paths(bundle_dir)
    if sorted(candidate_paths) != sorted(actual_paths):
        problems.append("freeze build provenance does not match candidate libpq shared-library paths")
    problems.extend(_verify_builder_identity(provenance))
    problems.extend(_verify_source_copy(installer_path, repo_root / "packaging/linux/install-postgresql-runtime.sh", "installer"))
    problems.extend(_verify_source_copy(verifier_path, repo_root / "services/src/airunner_services/runtimes/postgresql_prerequisites.py", "verifier"))
    return problems


def _bundle_libpq_paths(bundle_dir: Path) -> list[str]:
    return [
        path.relative_to(bundle_dir).as_posix()
        for path in bundle_dir.rglob("*")
        if re.fullmatch(r"libpq\.so(?:\..+)?", path.name)
        and (path.is_file() or path.is_symlink())
    ]


def _verify_builder_identity(provenance: dict[str, Any]) -> list[str]:
    host = provenance.get("build_host")
    release = host.get("os_release", {}) if isinstance(host, dict) else {}
    if (
        not isinstance(host, dict)
        or not isinstance(release, dict)
        or release.get("ID") != "ubuntu"
        or release.get("VERSION_ID") != "24.04"
        or host.get("architecture") not in {"x86_64", "amd64"}
    ):
        return ["PostgreSQL frozen candidate was not built on Ubuntu 24.04 amd64"]
    if not isinstance(host.get("libpq5_package"), dict):
        return ["freeze build provenance lacks builder libpq package identity or unavailable status"]
    return []


def _verify_source_copy(path: Path, source: Path, label: str) -> list[str]:
    if not _regular(source) or not _regular(path) or _sha256(path) != _sha256(source):
        return [f"bundled PostgreSQL {label} differs from its reviewed source"]
    return []


def _check_policy(policy: dict[str, Any], mode: Any, destination: Path) -> list[str]:
    problems = []
    if policy.get("schema_version") != 1:
        problems.append("PostgreSQL runtime policy schema is unsupported")
    if mode == "disabled":
        if policy.get("mode") != "disabled":
            problems.append("SQLite-only bundle does not declare PostgreSQL disabled")
        if any(
            (path.is_file() or path.is_symlink()) and path != destination / "runtime-policy.json"
            for path in destination.rglob("*")
        ):
            problems.append("SQLite-only bundle unexpectedly contains PostgreSQL runtime files")
        return problems
    if mode != "locked-ubuntu-debs":
        return ["bundle spec has no supported PostgreSQL runtime mode"]
    for key, value in _expected_policy().items():
        if policy.get(key) != value:
            problems.append(f"PostgreSQL runtime policy has unexpected {key}")
    return problems


def verify_runtime_payload(
    bundle_dir: Path,
    spec: dict[str, Any],
    repo_root: Path,
) -> list[str]:
    """Return bundle-inspection findings for PostgreSQL OS prerequisites."""
    config = spec.get("postgresql_runtime", {})
    mode = config.get("mode") if isinstance(config, dict) else None
    destination = bundle_dir / DESTINATION
    policy_path = destination / "runtime-policy.json"
    if not _regular(policy_path):
        return ["missing PostgreSQL runtime policy metadata"]
    try:
        policy, _ = _load_json(policy_path, "PostgreSQL runtime policy")
    except (OSError, PostgreSQLPayloadError) as exc:
        return [str(exc)]
    problems = _check_policy(policy, mode, destination)
    if mode == "disabled":
        return problems
    try:
        supplement = validate_staged_supplement(destination / "build-supplement", repo_root)
    except (OSError, PostgreSQLPayloadError) as exc:
        problems.append(f"invalid glibc build compatibility payload: {exc}")
        return problems
    try:
        staged = validate_staged_runtime(
            destination,
            repo_root,
            allowed_additional_files={
                "runtime-policy.json",
                "freeze-build-provenance.json",
                "install-postgresql-runtime.sh",
                "verify-postgresql-runtime.py",
                "build-supplement/SHA256SUMS",
                "build-supplement/install-packages.txt",
                f"build-supplement/{SUPPLEMENT_LOCK_NAME}",
                "build-supplement/staging-receipt.json",
                *(f"build-supplement/debs/{name}" for name in supplement["package_files"]),
            },
        )
    except (OSError, PostgreSQLPayloadError) as exc:
        problems.append(f"invalid PostgreSQL runtime payload: {exc}")
        return problems
    problems.extend(_verify_provenance(bundle_dir, destination, repo_root))
    return problems
