"""Validate the frozen CORE input record before any package activation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


_DEFAULT_MANIFEST = Path("package/core-input-readiness.json")
_VERSION_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)(?:==|\s+@\s+)([^\s\\]+)")
_ROOT_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\[[^]]+\])?(?:==|\s*@\s*|[<>=!~]|\s|$)")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_ORIGIN_POLICY_STATES = {
    "owner-controlled": "The exact input is owner-controlled source.",
    "owner-exception-recorded": "A concrete exact-input flag has a recorded owner exception.",
    "pending-owner-exception": "A concrete exact-input flag awaits its recorded disposition.",
    "pending-review": "The exact input has not completed origin-policy review.",
    "reviewed-no-flag": (
        "The exact input was reviewed and no policy flag was observed; "
        "this does not assert a particular country of origin."
    ),
}


class ReadinessError(ValueError):
    """The CORE inputs do not match their machine-readable record."""


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON fields instead of accepting the last value."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReadinessError("readiness manifest contains duplicate fields")
        result[key] = value
    return result


def _repo_file(root: Path, raw_path: Any) -> Path:
    """Resolve a repository-relative regular file without symlink escapes."""
    if not isinstance(raw_path, str):
        raise ReadinessError("readiness manifest file path is invalid")
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ReadinessError("readiness manifest path escapes the repository")
    path = root.joinpath(*relative.parts)
    if path.is_symlink() or not path.is_file():
        raise ReadinessError(f"readiness input is not a regular file: {raw_path}")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ReadinessError("readiness input resolves outside the repository") from exc
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _locked_versions(text: str) -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in text.splitlines():
        match = _VERSION_RE.match(line)
        if not match:
            continue
        name, version = match.groups()
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key in versions:
            raise ReadinessError(f"lock contains duplicate distribution: {key}")
        versions[key] = version
    return versions


def _normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_roots(text: str) -> set[str]:
    roots: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ROOT_RE.match(stripped)
        if match:
            roots.add(_normalized_name(match.group(1)))
    return roots


def _check_dependency_inventory(
    root: Path,
    raw: dict[str, Any],
    requirement_info: dict[str, Any],
    lock_info: dict[str, Any],
    requirements_text: str,
    locked: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Bind exact package review states to the complete hash-locked graph."""
    try:
        info = raw["dependency_review"]
        inventory_path = _repo_file(root, info["path"])
        inventory_digest = info["sha256"]
        if not isinstance(inventory_digest, str) or not _SHA_RE.fullmatch(
            inventory_digest
        ):
            raise ReadinessError("CORE dependency inventory digest is invalid")
        if _sha256(inventory_path) != inventory_digest:
            raise ReadinessError("CORE dependency inventory digest mismatch")
        inventory = json.loads(
            inventory_path.read_text(encoding="utf-8"), object_pairs_hook=_object
        )
    except (KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        raise ReadinessError("CORE dependency inventory is incomplete") from exc
    if not isinstance(inventory, dict) or inventory.get("schema_version") != 1:
        raise ReadinessError("unsupported CORE dependency inventory")
    if inventory.get("profile") != "linux-services-core":
        raise ReadinessError("dependency inventory names the wrong profile")
    if inventory.get("origin_policy_state_definitions") != _ORIGIN_POLICY_STATES:
        raise ReadinessError("dependency origin-policy state definitions are invalid")
    if inventory.get("requirements_sha256") != requirement_info["sha256"]:
        raise ReadinessError("dependency inventory requirements digest mismatch")
    if inventory.get("lock_sha256") != lock_info["sha256"]:
        raise ReadinessError("dependency inventory lock digest mismatch")

    packages = inventory.get("packages")
    if not isinstance(packages, list):
        raise ReadinessError("CORE dependency inventory package list is invalid")
    indexed: dict[str, dict[str, Any]] = {}
    for package in packages:
        if not isinstance(package, dict):
            raise ReadinessError("CORE dependency inventory entry is invalid")
        name = package.get("name")
        if not isinstance(name, str) or not name:
            raise ReadinessError("CORE dependency inventory package name is invalid")
        key = _normalized_name(name)
        if key in indexed:
            raise ReadinessError(f"duplicate dependency inventory package: {key}")
        if key not in locked:
            raise ReadinessError(f"dependency inventory package is absent from lock: {key}")
        if package.get("lock_reference") != locked[key]:
            raise ReadinessError(f"dependency inventory pin mismatch: {key}")
        version = package.get("version")
        if not isinstance(version, str) or not version:
            raise ReadinessError(f"dependency inventory version is invalid: {key}")
        source_status = package.get("source_review_status")
        if source_status not in {"reviewed", "pending"}:
            raise ReadinessError(f"dependency source review state is invalid: {key}")
        policy_status = package.get("origin_policy_status")
        if policy_status not in {
            "owner-controlled",
            "owner-exception-recorded",
            "reviewed-no-flag",
            "pending-owner-exception",
            "pending-review",
        }:
            raise ReadinessError(f"dependency origin policy state is invalid: {key}")
        role = package.get("role")
        if role not in {
            "runtime-direct",
            "runtime-transitive",
            "builder-direct",
            "builder-transitive",
            "runtime-and-builder-direct",
        }:
            raise ReadinessError(f"dependency role is invalid: {key}")
        if source_status == "reviewed":
            evidence = package.get("review_evidence")
            if not isinstance(evidence, dict):
                raise ReadinessError(f"reviewed dependency lacks evidence: {key}")
            record = evidence.get("record")
            record_path = _repo_file(root, record)
            record_digest = evidence.get("sha256")
            if not isinstance(record_digest, str) or not _SHA_RE.fullmatch(
                record_digest
            ):
                raise ReadinessError(f"dependency evidence digest is invalid: {key}")
            if _sha256(record_path) != record_digest:
                raise ReadinessError(f"dependency evidence digest mismatch: {key}")
            if not isinstance(evidence.get("scope_id"), str) or not evidence[
                "scope_id"
            ]:
                raise ReadinessError(f"dependency review scope is absent: {key}")
        elif not isinstance(package.get("next_action"), str) or not package[
            "next_action"
        ]:
            raise ReadinessError(f"pending dependency lacks next action: {key}")
        indexed[key] = package

    if set(indexed) != set(locked):
        raise ReadinessError("CORE dependency inventory does not cover the full lock")
    direct_names = {
        _normalized_name(match.group(1))
        for line in requirements_text.splitlines()
        if (match := _ROOT_RE.match(line.strip())) and not line.lstrip().startswith("#")
    }
    inventory_direct = {
        name
        for name, package in indexed.items()
        if package["role"]
        in {"runtime-direct", "builder-direct", "runtime-and-builder-direct"}
    }
    if direct_names != inventory_direct:
        raise ReadinessError("dependency inventory direct roots mismatch")

    source_reviewed = sum(
        package["source_review_status"] == "reviewed"
        for package in indexed.values()
    )
    source_pending = len(indexed) - source_reviewed
    origin_ready = sum(
        package["origin_policy_status"]
        in {"owner-controlled", "owner-exception-recorded", "reviewed-no-flag"}
        for package in indexed.values()
    )
    origin_pending_exception = sum(
        package["origin_policy_status"] == "pending-owner-exception"
        for package in indexed.values()
    )
    origin_pending_review = len(indexed) - origin_ready - origin_pending_exception
    expected_counts = {
        "source_reviewed_count": source_reviewed,
        "source_pending_count": source_pending,
        "origin_ready_count": origin_ready,
        "origin_pending_review_count": origin_pending_review,
        "origin_pending_exception_count": origin_pending_exception,
    }
    if any(inventory.get(key) != value for key, value in expected_counts.items()):
        raise ReadinessError("CORE dependency inventory counts disagree with entries")
    if inventory.get("status") != (
        "complete"
        if source_pending == 0
        and origin_pending_review == 0
        and origin_pending_exception == 0
        else "incomplete"
    ):
        raise ReadinessError("CORE dependency inventory completion state is invalid")
    if inventory.get("next_source_intakes") != sorted(
        name
        for name, package in indexed.items()
        if package["source_review_status"] == "pending"
    ):
        raise ReadinessError("CORE dependency source review queue is stale")
    if inventory.get("next_origin_reviews") != sorted(
        name
        for name, package in indexed.items()
        if package["origin_policy_status"] == "pending-review"
    ):
        raise ReadinessError("CORE dependency origin review queue is stale")

    actual_summary = {
        "status": inventory["status"],
        **expected_counts,
    }
    if any(info.get(key) != value for key, value in actual_summary.items()):
        raise ReadinessError("CORE readiness summary disagrees with dependency inventory")
    return indexed, actual_summary


def check_readiness(root: Path, manifest_path: Path) -> dict[str, Any]:
    """Check lock/input integrity and return current activation state."""
    root = root.resolve()
    manifest_file = manifest_path if manifest_path.is_absolute() else root / manifest_path
    try:
        raw = json.loads(
            manifest_file.read_text(encoding="utf-8"), object_pairs_hook=_object
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ReadinessError("cannot read CORE readiness manifest") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ReadinessError("unsupported CORE readiness manifest")
    if raw.get("profile") != "linux-services-core":
        raise ReadinessError("readiness manifest names the wrong profile")

    try:
        requirement_info = raw["requirements"]
        lock_info = raw["lock"]
        requirements = _repo_file(root, requirement_info["path"])
        lock = _repo_file(root, lock_info["path"])
        if _sha256(requirements) != requirement_info["sha256"]:
            raise ReadinessError("CORE requirement input digest mismatch")
        if _sha256(lock) != lock_info["sha256"]:
            raise ReadinessError("CORE lock digest mismatch")
        requirement_text = requirements.read_text(encoding="utf-8")
        forbidden_roots = (
            "torch",
            "torchvision",
            "torchaudio",
            "diffusers",
            "llama-cpp-python",
            "facehuggershield",
            "airunner-tts-vendor",
        )
        if any(
            re.match(rf"\s*{re.escape(name)}(?:\[|\s|=|<|>)", line, re.I)
            for name in forbidden_roots
            for line in requirement_text.splitlines()
        ):
            raise ReadinessError("CORE requirement input includes a non-CORE runtime")
        locked = _locked_versions(lock.read_text(encoding="utf-8"))
    except (KeyError, TypeError, OSError) as exc:
        raise ReadinessError("CORE readiness file records are incomplete") from exc

    if len(locked) != lock_info.get("resolved_distributions"):
        raise ReadinessError("CORE resolved distribution count mismatch")
    dependency_packages, dependency_summary = _check_dependency_inventory(
        root,
        raw,
        requirement_info,
        lock_info,
        requirement_text,
        locked,
    )
    expected_tools = {
        "pyinstaller": "6.12.0",
        "pyinstaller-hooks-contrib": "2026.9",
        "setuptools": "84.2.1",
        "wheel": "0.48.0",
        "packaging": "26.3",
    }
    for name, version in expected_tools.items():
        if locked.get(name) != version:
            raise ReadinessError(f"CORE lock tool pin mismatch: {name}")
    builder_inputs = raw.get("builder_inputs")
    if not isinstance(builder_inputs, list) or len(builder_inputs) != 2:
        raise ReadinessError("CORE builder input set is incomplete")
    for builder in builder_inputs:
        if not isinstance(builder, dict):
            raise ReadinessError("CORE builder input record is invalid")
        name = builder.get("name")
        version = builder.get("version")
        if locked.get(name) != version:
            raise ReadinessError(f"CORE builder source is absent from lock: {name}")
        if not isinstance(builder.get("source_commit"), str) or not _COMMIT_RE.fullmatch(
            builder["source_commit"]
        ):
            raise ReadinessError("CORE builder source commit is invalid")
        if not isinstance(builder.get("source_archive_sha256"), str) or not _SHA_RE.fullmatch(
            builder["source_archive_sha256"]
        ):
            raise ReadinessError("CORE builder archive hash is invalid")
        if not isinstance(builder.get("review_record"), str) or not builder["review_record"]:
            raise ReadinessError("CORE builder review record path is absent")
        if not builder["review_record"].startswith(
            "release-planning/services/input-reviews/"
        ):
            raise ReadinessError("CORE builder review record is not public source material")
        review_file = _repo_file(root, builder["review_record"])
        if not isinstance(builder.get("review_record_sha256"), str) or not _SHA_RE.fullmatch(
            builder["review_record_sha256"]
        ):
            raise ReadinessError("CORE builder review record hash is invalid")
        if _sha256(review_file) != builder["review_record_sha256"]:
            raise ReadinessError("CORE builder review record digest mismatch")
        if builder.get("source_policy_status") not in {
            "pending-owner-exception",
            "owner-exception-recorded",
            "reviewed-no-flag",
        }:
            raise ReadinessError("CORE builder source policy status is invalid")
        dependency = dependency_packages.get(_normalized_name(name))
        if dependency is None or dependency.get("source_review_status") != "reviewed":
            raise ReadinessError(f"CORE builder source review is absent from inventory: {name}")
        if dependency.get("origin_policy_status") != builder["source_policy_status"]:
            raise ReadinessError(f"CORE builder origin state disagrees with inventory: {name}")

    status = raw.get("readiness_status")
    activation_allowed = raw.get("activation_allowed")
    if status not in {"pending-review", "ready"}:
        raise ReadinessError("CORE readiness status is invalid")
    if not isinstance(activation_allowed, bool):
        raise ReadinessError("CORE activation state is invalid")
    if (status == "ready") != activation_allowed:
        raise ReadinessError("CORE readiness status and activation state disagree")
    pending_sources = dependency_summary["source_pending_count"]
    pending_origins = dependency_summary["origin_pending_review_count"]
    pending_builder_exceptions = sum(
        builder.get("source_policy_status") == "pending-owner-exception"
        for builder in builder_inputs
    )
    expected_blockers = []
    if pending_sources:
        expected_blockers.append("dependency-source-review-pending")
    if pending_origins:
        expected_blockers.append("dependency-origin-review-pending")
    if pending_builder_exceptions:
        expected_blockers.append("builder-origin-exception-pending")
    if dependency_summary["origin_pending_exception_count"] > pending_builder_exceptions:
        expected_blockers.append("dependency-origin-exception-pending")
    if raw.get("blockers") != expected_blockers:
        raise ReadinessError("CORE readiness blockers disagree with dependency review state")
    review_summary = raw.get("dependency_review")
    if not isinstance(review_summary, dict) or any(
        review_summary.get(key) != value
        for key, value in dependency_summary.items()
    ):
        raise ReadinessError("CORE readiness dependency review summary is stale")
    should_be_ready = not expected_blockers
    if (status == "ready") != should_be_ready:
        raise ReadinessError(
            "CORE cannot activate until every locked dependency source and origin is reviewed"
        )
    if should_be_ready and not activation_allowed:
        raise ReadinessError("complete CORE dependency review is not activatable")
    return {
        "status": status,
        "activation_allowed": activation_allowed,
        "distribution_count": len(locked),
        "blockers": list(expected_blockers),
        "dependency_review": dependency_summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument(
        "--mode", choices=("verify-record", "activate"), default="verify-record"
    )
    args = parser.parse_args(argv)
    try:
        result = check_readiness(args.root, args.manifest)
    except ReadinessError as exc:
        print(f"CORE INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    if args.mode == "activate" and not result["activation_allowed"]:
        print(
            "CORE INPUT BLOCKED: exact dependency source/origin review is incomplete; "
            "no builder dependencies may be installed and no freeze may run",
            file=sys.stderr,
        )
        return 2
    print(
        f"CORE input record valid: {result['distribution_count']} distributions; "
        f"status={result['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
