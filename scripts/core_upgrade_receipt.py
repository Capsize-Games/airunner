"""Validate the installed-runtime interruption recovery evidence in CORE receipts."""

from __future__ import annotations

import math
import re
from typing import Any


class CoreUpgradeReceiptError(ValueError):
    """The CORE upgrade receipt is missing required successful probe evidence."""


def validate_interrupted_upgrade_receipt(
    upgrade: dict[str, Any], *, source_sha: str, deb_sha256: str
) -> dict[str, Any]:
    """Validate producer status and all material installed-probe evidence fields."""
    if not isinstance(upgrade, dict):
        raise CoreUpgradeReceiptError("upgrade receipt is invalid")
    checks = upgrade.get("checks")
    if not isinstance(checks, dict) or checks.get("interrupted_upgrade_recovery_probe") != "passed":
        raise CoreUpgradeReceiptError("interrupted upgrade probe check did not pass")
    if upgrade.get("debian_sha256") != deb_sha256:
        raise CoreUpgradeReceiptError("upgrade receipt package digest differs")
    probe = upgrade.get("interrupted_upgrade_recovery_probe")
    if not isinstance(probe, dict):
        raise CoreUpgradeReceiptError("interrupted upgrade probe details are missing")
    _validate_probe_identity(probe, upgrade=upgrade, source_sha=source_sha)
    _validate_preserved_state(probe)
    _validate_auth_status(probe)
    _validate_process_cleanup(probe)
    _validate_resumed_migration(probe, upgrade=upgrade)
    _validate_backup_metadata(probe)
    return probe


def _validate_probe_identity(
    probe: dict[str, Any], *, upgrade: dict[str, Any], source_sha: str
) -> None:
    """Bind probe version, installed executable, fixture and interruption scope."""
    fields = {
        "schema_version": 1,
        "probe": "installed_frozen_core_interrupted_after_backup_before_write",
        "evidence_scope": "installed frozen CORE candidate runtime",
        "installed_executable": "/usr/lib/airunner/airunner-core",
        "fixture_kind": "published_prior_debian_schema",
        "fixture_source_sha": source_sha,
        "expected_heads_source_sha": source_sha,
        "interrupted_entry_point": "packaged airunner-headless via airunner-core executable",
        "interrupted_exit_code": -9,
        "interrupted_owned_descendants": [],
        "interruption_boundary": "pre-upgrade backup manifest durable; external BEGIN IMMEDIATE held; before migration writes",
        "recovery": "released controller transaction; normal frozen startup resumed current migration graph",
    }
    for key, expected in fields.items():
        _require_equal(probe, key, expected)
    fixture_sha = upgrade.get("fixture_database_sha256")
    _require_sha(fixture_sha, "upgrade fixture database")
    _require_equal(probe, "fixture_database_sha256", fixture_sha)


def _validate_preserved_state(probe: dict[str, Any]) -> None:
    """Require prior live and backup databases to retain their fixture state."""
    heads_before = _heads(probe.get("backup_heads"), "backup heads")
    for key, label in (
        ("backup_integrity_and_fixture", "backup state"),
        ("live_after_kill", "live database state after interruption"),
    ):
        state = _state(probe.get(key), label)
        if state["heads"] != heads_before:
            raise CoreUpgradeReceiptError("interrupted upgrade did not preserve pre-migration database heads")
    _require_equal(probe, "conversation_fixture_verified", True)


def _validate_auth_status(probe: dict[str, Any]) -> None:
    """Check health availability and authenticated versus unauthenticated API behavior."""
    expected_statuses = {
        "unauthenticated_health_status": 200,
        "unauthenticated_daemon_api_status": 401,
        "authenticated_daemon_api_status": 200,
        "authenticated_conversation_status": 200,
    }
    for key, expected in expected_statuses.items():
        _require_equal(probe, key, expected)


def _validate_process_cleanup(probe: dict[str, Any]) -> None:
    """Require process identity tracking and successful cleanup of owned children."""
    daemon_pid = _positive_int(probe.get("daemon_health_pid"), "daemon health PID")
    identity = probe.get("daemon_process_identity")
    if not isinstance(identity, dict):
        raise CoreUpgradeReceiptError("daemon process identity is missing")
    _require_equal(identity, "pid", daemon_pid)
    _positive_int(identity.get("starttime"), "daemon process start time")
    descendants = probe.get("resumed_owned_descendants_before_stop")
    if not isinstance(descendants, list) or not descendants:
        raise CoreUpgradeReceiptError("resumed owned process identities are missing")
    for descendant in descendants:
        if not isinstance(descendant, dict):
            raise CoreUpgradeReceiptError("resumed owned process identity is invalid")
        _positive_int(descendant.get("pid"), "resumed descendant PID")
        _positive_int(descendant.get("starttime"), "resumed descendant start time")
    _require_equal(probe, "resumed_owned_descendants_gone_after_stop", True)
    _require_equal(probe, "resumed_entry_point_exit_code", 0)
    _require_equal(probe, "daemon_stopped_after_entry_point_exit", True)


def _validate_resumed_migration(
    probe: dict[str, Any], *, upgrade: dict[str, Any]
) -> None:
    """Require successful migration heads, SQLite integrity and data retention."""
    expected_heads = _heads(probe.get("expected_current_heads"), "expected current heads")
    if _heads(upgrade.get("expected_alembic_heads_after"), "upgrade expected heads") != expected_heads:
        raise CoreUpgradeReceiptError("probe current migration heads differ from upgrade record")
    final_state = _state(probe.get("database_after_resume"), "database state after resume")
    if final_state["heads"] != expected_heads:
        raise CoreUpgradeReceiptError("resumed database does not have the expected migration heads")


def _validate_backup_metadata(probe: dict[str, Any]) -> None:
    """Check that the pre-upgrade backup and bounded probe timing are recorded."""
    _require_sha(probe.get("backup_sha256"), "pre-upgrade backup")
    manifest_name = probe.get("backup_manifest")
    if not isinstance(manifest_name, str) or not manifest_name or "/" in manifest_name or "\\" in manifest_name:
        raise CoreUpgradeReceiptError("pre-upgrade backup manifest identity is invalid")
    _positive_number(probe.get("elapsed_seconds"), "probe elapsed time")
    limitations = probe.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        raise CoreUpgradeReceiptError("probe limitations are missing")


def _require_equal(record: dict[str, Any], key: str, expected: Any) -> None:
    actual = record.get(key)
    if isinstance(expected, bool):
        matches = type(actual) is bool and actual is expected
    elif isinstance(expected, int):
        matches = type(actual) is int and actual == expected
    else:
        matches = actual == expected
    if not matches:
        raise CoreUpgradeReceiptError(f"interrupted upgrade probe field differs: {key}")


def _positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise CoreUpgradeReceiptError(f"{label} is invalid")
    return value


def _positive_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise CoreUpgradeReceiptError(f"{label} is invalid")
    if not math.isfinite(value) or value <= 0:
        raise CoreUpgradeReceiptError(f"{label} is invalid")
    return float(value)


def _heads(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise CoreUpgradeReceiptError(f"{label} are missing")
    if any(not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{12}", head) for head in value):
        raise CoreUpgradeReceiptError(f"{label} are invalid")
    if value != sorted(set(value)):
        raise CoreUpgradeReceiptError(f"{label} are not normalized")
    return value


def _state(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CoreUpgradeReceiptError(f"{label} is missing")
    integrity = value.get("integrity")
    if integrity != "ok":
        raise CoreUpgradeReceiptError(f"{label} integrity check failed")
    _require_equal(value, "fixture_marker_matches", True)
    _require_equal(value, "conversation_matches", True)
    return {**value, "heads": _heads(value.get("heads"), f"{label} heads")}


def _require_sha(value: Any, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise CoreUpgradeReceiptError(f"{label} SHA-256 is invalid")
