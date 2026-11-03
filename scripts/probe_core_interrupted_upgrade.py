#!/usr/bin/env python3
"""Exercise recovery after killing one owned CORE migration subprocess.

The probe copies a synthetic published-baseline database, invokes the
installed candidate's production ``setup_database`` in a child, and has the
controller SIGKILL that exact child after its first application-schema DDL.
It then checks the production backup/recovery decision and completes setup
on the isolated copy. The receipt records whether the first application DDL
occurred during Alembic or the post-migration schema repair.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from typing import Any

from alembic.config import Config


_DDL = re.compile(r"^\s*(?:CREATE|ALTER|DROP|REINDEX)\b", re.IGNORECASE)
_TABLE = re.compile(
    r"^\s*(?:CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?|ALTER\s+TABLE|DROP\s+TABLE(?:\s+IF\s+EXISTS)?)\s+[`\"\[]?([\w.]+)",
    re.IGNORECASE,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _integrity(path: Path) -> str:
    with sqlite3.connect(path, timeout=10) as connection:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "missing-result"


def _fixture_values(database: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    expected = fixture["synthetic_conversation"]
    with sqlite3.connect(database, timeout=10) as connection:
        conversation = connection.execute(
            "SELECT id, title, value FROM conversations WHERE id = ?",
            (expected["id"],),
        ).fetchone()
        marker = connection.execute(
            "SELECT payload FROM core_upgrade_fixture WHERE marker = ?",
            ("synthetic-marker",),
        ).fetchone()
    return {
        "conversation_matches": conversation
        == (expected["id"], expected["title"], expected["payload"]),
        "fixture_marker_matches": marker == (fixture["fixture_payload"],),
    }


def _candidate_migration_heads(setup_module: Any) -> tuple[str, ...]:
    """Resolve heads using setup_database's configured migration locations."""
    base = Path(os.path.dirname(os.path.realpath(setup_module.__file__)))
    alembic_file = base / "alembic.ini"
    alembic_dir = base / "alembic"
    config = Config(alembic_file)
    config.set_main_option("script_location", str(alembic_dir))
    version_locations = setup_module._version_locations(base, alembic_dir)
    config.set_main_option(
        "version_locations",
        os.pathsep.join(str(path) for path in version_locations),
    )
    return setup_module._expected_migration_heads(config)


def _child(db_url: str, base_path: str, backup_dir: str, barrier: Path) -> int:
    """Run production setup with a one-shot barrier after actual schema DDL."""
    os.environ["AIRUNNER_BASE_PATH"] = base_path
    os.environ["AIRUNNER_USER_DATA_PATH"] = base_path
    os.environ["AIRUNNER_DATA_DIR"] = str(Path(base_path) / "data")
    os.environ["AIRUNNER_DATABASE_URL"] = db_url
    os.environ["DATABASE_URL"] = db_url
    os.environ["AIRUNNER_UPGRADE_BACKUP_DIR"] = backup_dir
    os.environ["AIRUNNER_DISABLE_DB_SETUP_CACHE"] = "1"

    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    setup_module = importlib.import_module(
        "airunner_services.database.setup_database"
    )
    original_upgrade = setup_module.command.upgrade
    migration_active = False
    setup_active = False

    def tracked_upgrade(*args, **kwargs):
        nonlocal migration_active
        migration_active = True
        try:
            return original_upgrade(*args, **kwargs)
        finally:
            migration_active = False

    setup_module.command.upgrade = tracked_upgrade

    seen = False

    def after_execute(_conn, _cursor, statement, _parameters, _context, _many):
        nonlocal seen
        if not setup_active or seen or not _DDL.search(statement or ""):
            return
        normalized = " ".join((statement or "").split())
        if "alembic_version" in normalized.lower():
            return
        table_match = _TABLE.search(normalized)
        seen = True
        payload = {
            "event": "schema_ddl_after_cursor_execute",
            "phase": (
                "alembic_command_upgrade"
                if migration_active
                else "setup_database_repair"
            ),
            "statement_sha256": hashlib.sha256(
                normalized.encode("utf-8", "replace")
            ).hexdigest(),
            "statement_kind": normalized.split(None, 1)[0].upper(),
            "table": table_match.group(1) if table_match else None,
            "pid": os.getpid(),
            "setup_database_module": str(Path(setup_module.__file__).resolve()),
            "backup_manifests_present": sorted(
                path.name for path in Path(backup_dir).glob("*.db.json")
            ),
        }
        temporary = barrier.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, sort_keys=True) + "\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, barrier)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            time.sleep(0.05)
        raise RuntimeError("interrupted-upgrade controller did not terminate child")

    event.listen(Engine, "after_cursor_execute", after_execute)
    setup_active = True
    try:
        setup_module.setup_database(db_url=db_url)
    finally:
        setup_active = False
    return 0


def run_probe(
    fixture_db: Path,
    fixture_record: Path,
    output: Path,
    *,
    child_timeout: int = 90,
) -> dict[str, Any]:
    fixture_db = fixture_db.resolve(strict=True)
    fixture = json.loads(fixture_record.read_text(encoding="utf-8"))
    if fixture.get("fixture_kind") != "published_prior_debian_schema":
        raise ValueError("expected the published-baseline synthetic fixture")
    if fixture.get("database_sha256") != _sha256(fixture_db):
        raise ValueError("fixture database digest does not match its record")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing existing output path: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    work = Path(tempfile.mkdtemp(prefix="core-interrupted-upgrade-"))
    work.chmod(0o700)
    print(f"isolated probe workdir retained: {work}", file=sys.stderr, flush=True)
    database = work / "airunner.db"
    backup_dir = work / "backups"
    base_path = work / "application-data"
    base_path.mkdir(mode=0o700)
    os.environ["AIRUNNER_BASE_PATH"] = str(base_path)
    os.environ["AIRUNNER_USER_DATA_PATH"] = str(base_path)
    os.environ["AIRUNNER_DATA_DIR"] = str(base_path / "data")
    os.environ["AIRUNNER_UPGRADE_BACKUP_DIR"] = str(backup_dir)
    os.environ["AIRUNNER_DISABLE_DB_SETUP_CACHE"] = "1"
    from airunner_services.database.upgrade_backup import (
        current_heads,
        plan_recovery,
        read_manifest,
        restore_backup,
    )
    setup_module = importlib.import_module(
        "airunner_services.database.setup_database"
    )
    setup_database = setup_module.setup_database
    expected_candidate_heads = _candidate_migration_heads(setup_module)
    if not expected_candidate_heads:
        raise RuntimeError("candidate migration graph has no heads")

    shutil.copyfile(fixture_db, database)
    database.chmod(0o600)
    db_url = f"sqlite:///{database.as_posix()}"
    marker = work / "ddl-barrier.json"
    stdout_path = work / "child.stdout"
    stderr_path = work / "child.stderr"
    child_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(work),
        "TMPDIR": str(work),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
        "AIRUNNER_BASE_PATH": str(base_path),
        "AIRUNNER_USER_DATA_PATH": str(base_path),
        "AIRUNNER_DATA_DIR": str(base_path / "data"),
        "AIRUNNER_DATABASE_URL": db_url,
        "DATABASE_URL": db_url,
        "AIRUNNER_UPGRADE_BACKUP_DIR": str(backup_dir),
        "AIRUNNER_DISABLE_DB_SETUP_CACHE": "1",
        "HF_HUB_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "CUDA_VISIBLE_DEVICES": "",
    }
    if os.environ.get("PYTHONPATH"):
        child_env["PYTHONPATH"] = os.environ["PYTHONPATH"]

    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        child = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--child",
                "--database-url",
                db_url,
                "--base-path",
                str(base_path),
                "--backup-dir",
                str(backup_dir),
                "--barrier",
                str(marker),
            ],
            env=child_env,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            close_fds=True,
        )
        try:
            deadline = started + child_timeout
            while time.monotonic() < deadline and child.poll() is None:
                if marker.is_file():
                    break
                time.sleep(0.05)
            if not marker.is_file():
                stderr.flush()
                detail = stderr_path.read_text(errors="replace")[-4000:]
                raise RuntimeError(
                    "migration child did not reach DDL barrier; "
                    f"status={child.returncode}; {detail}"
                )
            barrier = json.loads(marker.read_text(encoding="utf-8"))
            manifests = sorted(backup_dir.glob("*.db.json"))
            if len(manifests) != 1 or not barrier["backup_manifests_present"]:
                raise RuntimeError(
                    f"expected one pre-upgrade backup manifest, got {len(manifests)}"
                )
            records = [read_manifest(path) for path in manifests]
            expected_heads = tuple(
                sorted(
                    fixture["migration_source_inventory"][
                        "heads_before_candidate_upgrade"
                    ]
                )
            )
            if records[0].heads != expected_heads:
                raise RuntimeError(
                    "pre-upgrade backup heads differ from fixture baseline"
                )
            child.kill()  # SIGKILL is scoped to this exact Popen child.
            return_code = child.wait(timeout=10)
            if return_code != -signal.SIGKILL:
                raise RuntimeError(f"expected SIGKILL exit, got {return_code}")
        except BaseException:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
            raise

    live_integrity = _integrity(database)
    backup_paths = [Path(record.path) for record in records]
    if any(
        path.is_symlink()
        or path.resolve().parent != backup_dir.resolve()
        or not path.is_file()
        or path.stat().st_size != record.size_bytes
        or _sha256(path) != record.sha256
        for path, record in zip(backup_paths, records, strict=True)
    ):
        raise RuntimeError("pre-upgrade backup file failed manifest verification")
    backup_integrity = [_integrity(path) for path in backup_paths]
    if live_integrity != "ok" or any(value != "ok" for value in backup_integrity):
        raise RuntimeError("SQLite integrity check failed after interruption")
    fixture_checks_in_backup = [
        _fixture_values(path, fixture) for path in backup_paths
    ]
    if any(not all(checks.values()) for checks in fixture_checks_in_backup):
        raise RuntimeError("synthetic fixture values missing from pre-upgrade backup")
    fixture_checks_after_kill = _fixture_values(database, fixture)
    if not all(fixture_checks_after_kill.values()):
        raise RuntimeError("synthetic fixture values changed before recovery")

    recovery = plan_recovery(db_url, records[0])
    restored = False
    if recovery.allow_database_restore:
        restore_backup(records[0], db_url)
        restored = True
    final_heads_before_resume = current_heads(db_url)
    os.environ["AIRUNNER_BASE_PATH"] = str(base_path)
    os.environ["AIRUNNER_USER_DATA_PATH"] = str(base_path)
    os.environ["AIRUNNER_DATA_DIR"] = str(base_path / "data")
    os.environ["AIRUNNER_UPGRADE_BACKUP_DIR"] = str(backup_dir)
    os.environ["AIRUNNER_DISABLE_DB_SETUP_CACHE"] = "1"
    setup_database(db_url=db_url)
    final_heads = current_heads(db_url)
    if final_heads != expected_candidate_heads:
        raise RuntimeError(
            "resumed database heads differ from candidate migration graph: "
            f"{final_heads!r} != {expected_candidate_heads!r}"
        )
    final_integrity = _integrity(database)
    final_fixture_checks = _fixture_values(database, fixture)
    if final_integrity != "ok" or not all(final_fixture_checks.values()):
        raise RuntimeError("resumed upgrade failed integrity or fixture preservation")

    receipt: dict[str, Any] = {
        "schema_version": 1,
        "probe": "production_setup_database_interrupted_after_first_schema_ddl",
        "fixture_kind": fixture["fixture_kind"],
        "fixture_database_sha256": fixture["database_sha256"],
        "child_python": sys.executable,
        "child_pid": barrier["pid"],
        "child_exit_code": return_code,
        "interruption_boundary": barrier,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "backup_count": len(records),
        "backup_heads": list(records[0].heads),
        "backup_sha256": records[0].sha256,
        "fixture_values_in_backup": fixture_checks_in_backup[0],
        "backup_integrity": backup_integrity,
        "live_integrity_after_kill": live_integrity,
        "fixture_values_after_kill": fixture_checks_after_kill,
        "recovery_plan": {
            "allow_database_restore": recovery.allow_database_restore,
            "reason": recovery.reason,
            "backup_heads": list(recovery.backup_heads),
            "current_heads": list(recovery.current_heads),
        },
        "backup_restored": restored,
        "heads_before_resume": list(final_heads_before_resume),
        "expected_candidate_heads": list(expected_candidate_heads),
        "heads_after_resume": list(final_heads),
        "integrity_after_resume": final_integrity,
        "fixture_values_after_resume": final_fixture_checks,
        "limitations": [
            "Synthetic SQLite database only; no owner or production database was opened.",
            "SIGKILL occurred after one observed schema DDL returned and before the child continued.",
            "This does not simulate arbitrary power loss, filesystem corruption, or interruption during dpkg unpack/configuration.",
            "No host dpkg, systemd service, GPU, model, or network action was performed by this probe.",
        ],
    }
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.chmod(0o600)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-db", type=Path)
    parser.add_argument("--fixture-record", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--database-url")
    parser.add_argument("--base-path")
    parser.add_argument("--backup-dir")
    parser.add_argument("--barrier", type=Path)
    args = parser.parse_args()
    if args.child:
        if not all((args.database_url, args.base_path, args.backup_dir, args.barrier)):
            parser.error("child mode needs database URL, base path, backup dir, and barrier")
        return _child(args.database_url, args.base_path, args.backup_dir, args.barrier)
    if not all((args.fixture_db, args.fixture_record, args.output)):
        parser.error("fixture DB, fixture record, and output are required")
    receipt = run_probe(args.fixture_db, args.fixture_record, args.output)
    print(json.dumps({"status": "passed", "receipt": str(args.output), "child_pid": receipt["child_pid"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
