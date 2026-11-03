"""Verify the frozen bundle's exact PostgreSQL OS package prerequisite."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


POSTGRESQL_PAYLOAD = Path("runtime-requirements/postgresql")
LOCK_NAME = "postgresql-libpq-noble-runtime-lock.json"
RECEIPT_NAME = "staging-receipt.json"
POLICY_NAME = "runtime-policy.json"
EXPECTED_ROOT = "libpq5=16.15-0ubuntu0.24.04.1"
EXPECTED_PACKAGE_COUNT = 24
# Integrity pin for the public, checked-in Noble package lock; this is a
# product dependency identity, not an intake/audit receipt hash.
EXPECTED_LOCK_SHA256 = "d63e7580c2e917ee8068a6ae5fc3971db0b7eb7b6a5bf9c34e865735c6711f49"
SUPPLEMENT_LOCK_NAME = "postgresql-libpq-noble-build-supplement-lock.json"
EXPECTED_SUPPLEMENT_LOCK_SHA256 = "85faf9d1efe88be42a7f10905198f42b0275b02f89f9994d11eb5f066ac183b0"
EXPECTED_SUPPLEMENT_ROOT = "libc6-dev=2.39-0ubuntu8.9"
MAX_METADATA_BYTES = 1024 * 1024
PACKAGE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")


class PostgreSQLPrerequisiteError(RuntimeError):
    """The frozen PostgreSQL runtime prerequisite is absent or mismatched."""


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise PostgreSQLPrerequisiteError(
            f"{label} is not a regular file; install a full Linux bundle or use SQLite."
        )
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise PostgreSQLPrerequisiteError(
            f"{label} is missing; install a full Linux bundle or use SQLite."
        ) from exc
    if len(data) > MAX_METADATA_BYTES:
        raise PostgreSQLPrerequisiteError(f"{label} exceeds the accepted size limit.")
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PostgreSQLPrerequisiteError(f"{label} is invalid.") from exc
    if not isinstance(value, dict):
        raise PostgreSQLPrerequisiteError(f"{label} must be an object.")
    return value, data


def parse_os_release(text: str) -> dict[str, str]:
    """Parse the simple key/value fields needed from an os-release file."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"ID", "VERSION_ID"}:
            values[key] = value.strip().strip('"').strip("'")
    return values


def _package_versions(lock: dict[str, Any]) -> dict[str, tuple[str, str]]:
    packages = lock.get("packages")
    if (
        lock.get("root") != EXPECTED_ROOT
        or lock.get("package_count") != EXPECTED_PACKAGE_COUNT
        or not isinstance(packages, list)
        or len(packages) != EXPECTED_PACKAGE_COUNT
    ):
        raise PostgreSQLPrerequisiteError("the bundle's PostgreSQL package lock is not the supported Noble closure.")
    result: dict[str, tuple[str, str]] = {}
    for item in packages:
        if not isinstance(item, dict):
            raise PostgreSQLPrerequisiteError("the bundle's PostgreSQL package lock is malformed.")
        name, version, arch = item.get("Package"), item.get("Version"), item.get("Architecture")
        if (
            not isinstance(name, str)
            or not PACKAGE_NAME_RE.fullmatch(name)
            or not isinstance(version, str)
            or arch != "amd64"
            or name in result
        ):
            raise PostgreSQLPrerequisiteError("the bundle's PostgreSQL package lock is malformed.")
        result[name] = (version, arch)
    if len(result) != EXPECTED_PACKAGE_COUNT or "libpq5" not in result:
        raise PostgreSQLPrerequisiteError("the bundle's PostgreSQL package set is incomplete.")
    return result


def validate_dpkg_query_output(
    expected: dict[str, tuple[str, str]],
    output: str,
    returncode: int = 0,
) -> None:
    """Reject absent or non-exact Debian package identities."""
    actual: dict[str, tuple[str, str, str]] = {}
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 4:
            continue
        name, version, architecture, status = fields
        actual[name] = (version, architecture, status)
    mismatches = []
    for name, (version, architecture) in expected.items():
        observed = actual.get(name)
        if observed != (version, architecture, "installed"):
            if observed is None:
                detail = "not installed"
            elif observed[2] != "installed":
                detail = "not fully installed"
            else:
                detail = f"{observed[0]} {observed[1]}"
            mismatches.append(f"{name} needs {version} amd64 ({detail})")
    if returncode != 0 or mismatches:
        detail = "; ".join(mismatches[:5])
        if len(mismatches) > 5:
            detail += f"; and {len(mismatches) - 5} more package mismatches"
        raise PostgreSQLPrerequisiteError(
            "PostgreSQL requires the reviewed Ubuntu 24.04 amd64 package closure. "
            f"{detail or 'dpkg-query could not verify the installed packages'} "
            "Run runtime-requirements/postgresql/install-postgresql-runtime.sh with sudo, or use SQLite."
        )


def _runtime_policy(payload: Path) -> dict[str, Any]:
    policy, _ = _read_json(payload / POLICY_NAME, "PostgreSQL runtime policy")
    mode = policy.get("mode")
    if mode == "disabled":
        raise PostgreSQLPrerequisiteError("PostgreSQL is unavailable in this SQLite-only bundle; use SQLite.")
    expected_supplement = {
        "lock_file": f"build-supplement/{SUPPLEMENT_LOCK_NAME}",
        "receipt_file": "build-supplement/staging-receipt.json",
        "package_count": 2,
        "install_condition": "only when libc6-dev is already installed",
    }
    if (
        mode != "locked-ubuntu-debs"
        or policy.get("target") != {"os_id": "ubuntu", "version_id": "24.04", "architecture": "amd64"}
        or policy.get("root_package") != EXPECTED_ROOT
        or policy.get("package_count") != EXPECTED_PACKAGE_COUNT
        or policy.get("lock_file") != LOCK_NAME
        or policy.get("receipt_file") != RECEIPT_NAME
        or policy.get("build_supplement") != expected_supplement
    ):
        raise PostgreSQLPrerequisiteError("the bundle's PostgreSQL platform policy is unsupported.")
    return policy


def _runtime_versions(payload: Path) -> dict[str, tuple[str, str]]:
    lock, lock_bytes = _read_json(payload / LOCK_NAME, "PostgreSQL package lock")
    if hashlib.sha256(lock_bytes).hexdigest() != EXPECTED_LOCK_SHA256:
        raise PostgreSQLPrerequisiteError(
            "the bundle's PostgreSQL package lock differs from the reviewed Noble runtime lock."
        )
    versions = _package_versions(lock)
    receipt, _ = _read_json(payload / RECEIPT_NAME, "PostgreSQL staging receipt")
    if (
        receipt.get("kind") != "runtime"
        or receipt.get("package_count") != EXPECTED_PACKAGE_COUNT
        or receipt.get("lock_sha256") != hashlib.sha256(lock_bytes).hexdigest()
    ):
        raise PostgreSQLPrerequisiteError("the bundle's PostgreSQL staging receipt does not match its package lock.")
    return versions


def _host_architecture(os_release_path: Path, architecture: str | None, runner) -> str:
    try:
        release = parse_os_release(os_release_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PostgreSQLPrerequisiteError("cannot identify the operating system for PostgreSQL support.") from exc
    if release.get("ID") != "ubuntu" or release.get("VERSION_ID") != "24.04":
        raise PostgreSQLPrerequisiteError(
            "the frozen PostgreSQL runtime supports Ubuntu 24.04 amd64 only; use SQLite on this system."
        )
    if architecture is None:
        architecture = _query_architecture(runner)
    if architecture != "amd64":
        raise PostgreSQLPrerequisiteError(
            "the frozen PostgreSQL runtime supports Ubuntu 24.04 amd64 only; use SQLite on this system."
        )
    return architecture


def _query_architecture(runner) -> str:
    try:
        result = runner(
            ["dpkg", "--print-architecture"],
            check=False, capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PostgreSQLPrerequisiteError("cannot verify the dpkg target architecture.") from exc
    if result.returncode != 0:
        raise PostgreSQLPrerequisiteError("cannot verify the dpkg target architecture.")
    return result.stdout.strip()


def _supplement_versions(payload: Path, runner) -> dict[str, tuple[str, str]]:
    try:
        status = runner(
            ["dpkg-query", "--show", "--showformat=${db:Status-Status}", "libc6-dev"],
            check=False, capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PostgreSQLPrerequisiteError(
            "cannot verify whether the optional glibc development compatibility package is installed."
        ) from exc
    if status.returncode != 0 or status.stdout.strip() != "installed":
        return {}
    return _read_supplement_versions(payload)


def _read_supplement_versions(payload: Path) -> dict[str, tuple[str, str]]:
    directory = payload / "build-supplement"
    lock, lock_bytes = _read_json(directory / SUPPLEMENT_LOCK_NAME, "glibc build compatibility lock")
    packages = lock.get("packages")
    valid_lock = (
        hashlib.sha256(lock_bytes).hexdigest() == EXPECTED_SUPPLEMENT_LOCK_SHA256
        and lock.get("kind") == "build-only-compatibility-supplement"
        and lock.get("root") == EXPECTED_SUPPLEMENT_ROOT
        and lock.get("package_count") == 2
        and isinstance(packages, list)
        and len(packages) == 2
    )
    if not valid_lock or not _supplement_names_valid(packages):
        raise PostgreSQLPrerequisiteError("the optional glibc compatibility lock is unsupported or mismatched.")
    receipt, _ = _read_json(directory / "staging-receipt.json", "glibc build compatibility receipt")
    if (
        receipt.get("kind") != "build-supplement"
        or receipt.get("package_count") != 2
        or receipt.get("lock_sha256") != hashlib.sha256(lock_bytes).hexdigest()
    ):
        raise PostgreSQLPrerequisiteError("the optional glibc compatibility receipt does not match its lock.")
    return _supplement_package_map(packages)


def _supplement_names_valid(packages: Any) -> bool:
    if not isinstance(packages, list):
        return False
    names = {item.get("Package") for item in packages if isinstance(item, dict)}
    return names == {"libc-dev-bin", "libc6-dev"}


def _supplement_package_map(packages: list[Any]) -> dict[str, tuple[str, str]]:
    versions = {}
    for item in packages:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("Package"), str)
            or not isinstance(item.get("Version"), str)
            or item.get("Architecture") != "amd64"
        ):
            raise PostgreSQLPrerequisiteError("the optional glibc compatibility package lock is malformed.")
        versions[item["Package"]] = (item["Version"], "amd64")
    return versions


def _verify_installed_packages(versions: dict[str, tuple[str, str]], runner) -> None:
    query = [
        "dpkg-query", "--show",
        "--showformat=${Package}\\t${Version}\\t${Architecture}\\t${db:Status-Status}\\n",
        *sorted(versions),
    ]
    try:
        result = runner(query, check=False, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PostgreSQLPrerequisiteError(
            "cannot verify installed PostgreSQL OS packages with dpkg-query."
        ) from exc
    validate_dpkg_query_output(versions, result.stdout, result.returncode)


def verify_postgresql_os_runtime(
    bundle_root: Path,
    *,
    os_release_path: Path = Path("/etc/os-release"),
    architecture: str | None = None,
    runner=subprocess.run,
) -> None:
    """Check policy, Ubuntu identity, and all exact package versions.

    The bounded subprocess calls query package metadata only; they do not
    import Psycopg or load libpq.
    """
    payload = bundle_root / POSTGRESQL_PAYLOAD
    _runtime_policy(payload)
    versions = _runtime_versions(payload)
    _host_architecture(os_release_path, architecture, runner)
    versions.update(_supplement_versions(payload, runner))
    _verify_installed_packages(versions, runner)


def _frozen_bundle_root() -> Path:
    configured = os.environ.get("AIRUNNER_BUNDLE_ROOT", "").strip()
    if configured:
        return Path(os.path.expanduser(configured)).resolve()
    internal = getattr(sys, "_MEIPASS", "")
    if internal:
        return Path(internal).resolve().parent
    raise PostgreSQLPrerequisiteError(
        "cannot locate the frozen bundle's PostgreSQL prerequisites; use SQLite."
    )


def require_frozen_postgresql_runtime() -> None:
    """Apply package preflight only to frozen applications."""
    if getattr(sys, "frozen", False):
        verify_postgresql_os_runtime(_frozen_bundle_root())


def main(argv: list[str] | None = None) -> int:
    """Verify the installed target OS PostgreSQL prerequisite packages."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        verify_postgresql_os_runtime(args.bundle_root.resolve())
    except PostgreSQLPrerequisiteError as exc:
        parser.exit(1, f"PostgreSQL prerequisite check failed: {exc}\n")
    print("Verified Ubuntu 24.04 amd64 PostgreSQL OS package prerequisites.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
