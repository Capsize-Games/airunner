#!/usr/bin/env python3
"""Exercise the frozen CORE upgrade path around its pre-migration backup.

This stdlib-only controller starts the installed frozen ``airunner-headless``
entry point through the CORE executable. It holds SQLite's write reservation
while production startup snapshots the prior database, then SIGKILLs only the
controller-owned frozen entry-point process before a database write can finish.
The source-level post-DDL probe is separate evidence and is not run here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _db_state(path: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    expected = fixture["synthetic_conversation"]
    with sqlite3.connect(path, timeout=2) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        heads = sorted(
            row[0]
            for row in connection.execute(
                "SELECT version_num FROM alembic_version"
            )
        )
        marker = connection.execute(
            "SELECT payload FROM core_upgrade_fixture WHERE marker = ?",
            ("synthetic-marker",),
        ).fetchone()
        conversation = connection.execute(
            "SELECT id, title, value FROM conversations WHERE id = ?",
            (expected["id"],),
        ).fetchone()
    return {
        "integrity": integrity,
        "heads": heads,
        "fixture_marker_matches": marker == (fixture["fixture_payload"],),
        "conversation_matches": conversation
        == (expected["id"], expected["title"], expected["payload"]),
    }


def _request(url: str, api_key: str | None = None) -> tuple[int, bytes]:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=2) as response:
            return response.status, response.read(1024 * 1024)
    except HTTPError as error:
        return error.code, error.read(1024 * 1024)


def _launch(
    binary: Path,
    env: dict[str, str],
    config: Path,
    log_path: Path,
) -> subprocess.Popen[bytes]:
    # The executable is the frozen /usr/lib/airunner/airunner-core binary;
    # argv[0] selects its packaged airunner-headless production entry point.
    command = [
        "airunner-headless",
        "--host",
        "127.0.0.1",
        "--port",
        env["AIRUNNER_HTTP_PORT"],
        "--no-preload",
        "--daemon-config",
        str(config),
    ]
    log = log_path.open("wb")
    try:
        return subprocess.Popen(
            command,
            executable=str(binary),
            cwd=binary.parent,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
    finally:
        log.close()


def _stop_owned(child: subprocess.Popen[bytes], timeout: float = 40) -> int:
    if child.poll() is None:
        child.send_signal(signal.SIGTERM)
    return child.wait(timeout=timeout)


def _process_identity(pid: int) -> dict[str, int] | None:
    """Return a PID/start-time pair, detecting later PID reuse."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None
    closing = stat.rfind(")")
    if closing < 0:
        raise RuntimeError(f"cannot parse /proc/{pid}/stat")
    fields = stat[closing + 1 :].split()
    if len(fields) < 20:
        raise RuntimeError(f"incomplete /proc/{pid}/stat")
    return {"pid": pid, "starttime": int(fields[19])}


def _same_process(identity: dict[str, int]) -> bool:
    return _process_identity(identity["pid"]) == identity


def _owned_descendants(
    root_pid: int,
    *,
    max_depth: int = 8,
    max_processes: int = 32,
) -> list[dict[str, int]]:
    """Snapshot a bounded child tree rooted at the exact Popen PID."""
    if _process_identity(root_pid) is None:
        raise RuntimeError(f"owned process {root_pid} exited before tree snapshot")
    found: list[dict[str, int]] = []
    queue = [(root_pid, 0)]
    seen = {root_pid}
    while queue:
        parent_pid, depth = queue.pop(0)
        children_path = Path(f"/proc/{parent_pid}/task/{parent_pid}/children")
        try:
            child_pids = [
                int(value)
                for value in children_path.read_text(encoding="ascii").split()
            ]
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if child_pids and depth >= max_depth:
            raise RuntimeError("owned child tree exceeded its depth bound")
        for child_pid in child_pids:
            if child_pid in seen:
                continue
            seen.add(child_pid)
            identity = _process_identity(child_pid)
            if identity is None:
                continue
            found.append(identity)
            if len(found) > max_processes:
                raise RuntimeError("owned child tree exceeded its process bound")
            queue.append((child_pid, depth + 1))
    return found


def _wait_identities_gone(
    identities: list[dict[str, int]], timeout: float
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(_same_process(identity) for identity in identities):
            return True
        time.sleep(0.05)
    return not any(_same_process(identity) for identity in identities)


def _stop_verified_descendants(
    identities: list[dict[str, int]], *, timeout: float = 5
) -> None:
    """Stop only identities previously observed under an owned Popen."""
    for identity in reversed(identities):
        if _same_process(identity):
            os.kill(identity["pid"], signal.SIGTERM)
    if _wait_identities_gone(identities, timeout):
        return
    for identity in reversed(identities):
        if _same_process(identity):
            os.kill(identity["pid"], signal.SIGKILL)
    if not _wait_identities_gone(identities, timeout):
        raise RuntimeError("verified owned descendant identities did not exit")


def run_probe(
    binary: Path,
    fixture_db: Path,
    fixture_record: Path,
    expected_heads_record: Path,
    output: Path,
    *,
    timeout_seconds: int = 45,
) -> dict[str, Any]:
    binary = binary.resolve(strict=True)
    fixture_db = fixture_db.resolve(strict=True)
    fixture = json.loads(fixture_record.read_text(encoding="utf-8"))
    expected_record = json.loads(
        expected_heads_record.read_text(encoding="utf-8")
    )
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError("CORE executable must be a regular executable file")
    if fixture.get("fixture_kind") != "published_prior_debian_schema":
        raise ValueError("expected the published-prior synthetic fixture")
    if fixture.get("database_sha256") != _sha256(fixture_db):
        raise ValueError("fixture DB digest differs from fixture record")
    if fixture.get("source_sha") != expected_record.get("source_sha"):
        raise ValueError("expected-heads fixture has a different source SHA")
    expected_heads = sorted(
        expected_record["expected_alembic_heads_after_upgrade"]
    )
    if not expected_heads:
        raise ValueError("expected-heads fixture has no current migration heads")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing existing receipt path: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    work = Path(tempfile.mkdtemp(prefix="core-installed-interruption-"))
    work.chmod(0o700)
    print(
        f"isolated installed-runtime workdir retained on failure: {work}",
        file=sys.stderr,
        flush=True,
    )
    base = work / "application-data"
    database = base / "data" / "airunner.db"
    backup_dir = work / "backups"
    runtime = base / "runtime"
    for directory in (
        database.parent,
        backup_dir,
        runtime / "configs",
        runtime / "logs",
        runtime / "sockets",
        base / "cache",
        base / "models",
        work / "config",
        work / "data",
        work / "state",
        work / "xdg-runtime",
    ):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    shutil.copyfile(fixture_db, database)
    database.chmod(0o600)

    port = 18080
    api_key = secrets.token_urlsafe(32)
    config = runtime / "configs" / "daemon.yaml"
    config.write_text(
        "server:\n  host: 127.0.0.1\n  port: 18818\n"
        "  enable_cors: false\n  allowed_origins: []\n",
        encoding="utf-8",
    )
    config.chmod(0o600)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "TMPDIR": str(work),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "XDG_CONFIG_HOME": str(work / "config"),
        "XDG_DATA_HOME": str(work / "data"),
        "XDG_CACHE_HOME": str(base / "cache"),
        "XDG_STATE_HOME": str(work / "state"),
        "XDG_RUNTIME_DIR": str(work / "xdg-runtime"),
        "AIRUNNER_BASE_PATH": str(base),
        "AIRUNNER_USER_DATA_PATH": str(base),
        "AIRUNNER_DATA_DIR": str(database.parent),
        "AIRUNNER_DATABASE_URL": f"sqlite:///{database.as_posix()}",
        "DATABASE_URL": f"sqlite:///{database.as_posix()}",
        "AIRUNNER_UPGRADE_BACKUP_DIR": str(backup_dir),
        "AIRUNNER_RUNTIME_ROOT": str(runtime),
        "AIRUNNER_RUNTIME_CONFIG_DIR": str(runtime / "configs"),
        "AIRUNNER_RUNTIME_LOG_DIR": str(runtime / "logs"),
        "AIRUNNER_RUNTIME_SOCKET_DIR": str(runtime / "sockets"),
        "AIRUNNER_CACHE_DIR": str(base / "cache"),
        "AIRUNNER_MODEL_DIR": str(base / "models"),
        "AIRUNNER_API_KEY": api_key,
        "AIRUNNER_HTTP_HOST": "127.0.0.1",
        "AIRUNNER_HTTP_PORT": str(port),
        "AIRUNNER_HEADLESS_SERVER_HOST": "127.0.0.1",
        "AIRUNNER_HEADLESS_SERVER_PORT": str(port),
        "AIRUNNER_HEADLESS": "1",
        "AIRUNNER_LLM_ON": "0",
        "AIRUNNER_SD_ON": "0",
        "AIRUNNER_TTS_ON": "0",
        "AIRUNNER_STT_ON": "0",
        "AIRUNNER_NO_PRELOAD": "1",
        "AIRUNNER_PRELOAD": "0",
        "HF_HUB_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "CUDA_VISIBLE_DEVICES": "",
        "QT_QPA_PLATFORM": "offscreen",
        "PYTHONNOUSERSITE": "1",
    }
    controller: sqlite3.Connection | None = None
    interrupted: subprocess.Popen[bytes] | None = None
    resumed: subprocess.Popen[bytes] | None = None
    interrupted_return: int | None = None
    resumed_return: int | None = None
    interrupted_descendants: list[dict[str, int]] = []
    resumed_descendants: list[dict[str, int]] = []
    daemon_identity: dict[str, int] | None = None
    success = False
    started = time.monotonic()
    try:
        # BEGIN IMMEDIATE reserves the sole SQLite writer slot before the
        # frozen production startup begins. VACUUM INTO can still snapshot
        # this committed fixture; Alembic's first write must wait or fail.
        controller = sqlite3.connect(database, timeout=1, isolation_level=None)
        controller.execute("BEGIN IMMEDIATE")
        interrupted = _launch(binary, env, config, work / "interrupted.log")
        deadline = time.monotonic() + timeout_seconds
        manifests: list[Path] = []
        while time.monotonic() < deadline:
            if interrupted.poll() is not None:
                raise RuntimeError(
                    "frozen startup exited before producing its pre-upgrade backup; "
                    f"exit={interrupted.returncode}; log={work / 'interrupted.log'}"
                )
            manifests = sorted(backup_dir.glob("*.db.json"))
            if manifests:
                break
            time.sleep(0.02)
        if len(manifests) != 1:
            raise TimeoutError(
                "frozen startup did not produce exactly one pre-upgrade backup "
                f"manifest within {timeout_seconds}s; log={work / 'interrupted.log'}"
            )
        manifest_path = manifests[0]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if sorted(manifest.get("heads", [])) != sorted(
            fixture["migration_source_inventory"]["heads_before_candidate_upgrade"]
        ):
            raise RuntimeError("backup manifest does not describe fixture prior heads")
        if interrupted.poll() is not None:
            raise RuntimeError(
                "frozen startup exited before interruption after backup manifest; "
                f"exit={interrupted.returncode}"
            )
        interrupted_descendants = _owned_descendants(interrupted.pid)
        interrupted.kill()  # SIGKILL targets exactly the owned frozen Popen.
        interrupted_return = interrupted.wait(timeout=10)
        if interrupted_return != -signal.SIGKILL:
            raise RuntimeError(f"expected SIGKILL exit, got {interrupted_return}")
        controller.execute("ROLLBACK")
        controller.close()
        controller = None
        if not _wait_identities_gone(interrupted_descendants, timeout=5):
            _stop_verified_descendants(interrupted_descendants)
            raise RuntimeError(
                "interrupted frozen entry point left an observed child process"
            )

        backup_path = Path(manifest["path"])
        if backup_path.resolve().parent != backup_dir.resolve():
            raise RuntimeError("backup manifest points outside the isolated directory")
        if (
            not backup_path.is_file()
            or backup_path.stat().st_size != int(manifest["size_bytes"])
            or _sha256(backup_path) != manifest["sha256"]
        ):
            raise RuntimeError("pre-upgrade backup failed size or digest verification")
        live_after_kill = _db_state(database, fixture)
        backup_after_kill = _db_state(backup_path, fixture)
        prior_heads = sorted(
            fixture["migration_source_inventory"]["heads_before_candidate_upgrade"]
        )
        if (
            live_after_kill["integrity"] != "ok"
            or live_after_kill["heads"] != prior_heads
            or not live_after_kill["fixture_marker_matches"]
            or not live_after_kill["conversation_matches"]
        ):
            raise RuntimeError(
                f"live DB changed or failed integrity after kill: {live_after_kill}"
            )
        if (
            backup_after_kill["integrity"] != "ok"
            or backup_after_kill["heads"] != prior_heads
            or not backup_after_kill["fixture_marker_matches"]
            or not backup_after_kill["conversation_matches"]
        ):
            raise RuntimeError(
                "pre-upgrade backup failed fixture checks: "
                f"{backup_after_kill}"
            )

        resumed = _launch(binary, env, config, work / "resumed.log")
        base_url = f"http://127.0.0.1:{port}"
        unauthenticated_health: int | None = None
        health_deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < health_deadline:
            if resumed.poll() is not None:
                raise RuntimeError(
                    "resumed frozen entry point exited before health was ready; "
                    f"exit={resumed.returncode}; log={work / 'resumed.log'}"
                )
            try:
                unauthenticated_health, health_body = _request(
                    base_url + "/health"
                )
                if unauthenticated_health == 200:
                    break
            except (OSError, URLError):
                pass
            time.sleep(0.2)
        if unauthenticated_health != 200:
            raise TimeoutError("frozen runtime did not serve unauthenticated /health")
        health_payload = json.loads(health_body)
        daemon_pid = int(health_payload["pid"])
        resumed_descendants = _owned_descendants(resumed.pid)
        matching_daemons = [
            identity
            for identity in resumed_descendants
            if identity["pid"] == daemon_pid
        ]
        if len(matching_daemons) != 1:
            raise RuntimeError(
                "health PID did not identify exactly one owned daemon child: "
                f"pid={daemon_pid}, descendants={resumed_descendants}"
            )
        daemon_identity = matching_daemons[0]
        unauthenticated_api_status, _ = _request(
            base_url + "/api/v1/health/daemon"
        )
        if unauthenticated_api_status != 401:
            raise RuntimeError(
                "daemon API did not reject missing authentication: "
                f"{unauthenticated_api_status}"
            )
        authenticated_api_status, _ = _request(
            base_url + "/api/v1/health/daemon", api_key
        )
        if authenticated_api_status != 200:
            raise RuntimeError(
                "authenticated daemon health failed: "
                f"{authenticated_api_status}"
            )
        conversation = fixture["synthetic_conversation"]
        query = urlencode(
            {"conversation_id": conversation["id"], "max_messages": 10}
        )
        conversation_status, conversation_body = _request(
            f"{base_url}/api/v1/llm/conversations/session?{query}", api_key
        )
        if conversation_status != 200:
            raise RuntimeError(f"conversation endpoint returned {conversation_status}")
        response = json.loads(conversation_body)
        actual = response.get("conversation")
        messages = response.get("messages")
        if (
            not isinstance(actual, dict)
            or actual.get("id") != conversation["id"]
            or actual.get("title") != conversation["title"]
            or actual.get("summary") != conversation["summary"]
            or not isinstance(messages, list)
            or len(messages) != 2
            or not any(
                item.get("content") == "published-upgrade-marker-v1"
                for item in messages
                if isinstance(item, dict)
            )
        ):
            raise RuntimeError(
                "authenticated conversation response lost fixture values"
            )
        resumed_return = _stop_owned(resumed)
        if resumed_return != 0:
            raise RuntimeError(
                f"resumed frozen entry point stopped with {resumed_return}"
            )
        resumed = None
        if not _wait_identities_gone(resumed_descendants, timeout=10):
            _stop_verified_descendants(resumed_descendants)
            raise RuntimeError(
                "clean entry-point exit left an observed daemon descendant"
            )
        stop_deadline = time.monotonic() + 10
        daemon_stopped = False
        while time.monotonic() < stop_deadline:
            try:
                _request(base_url + "/health")
            except (OSError, URLError):
                daemon_stopped = True
                break
            time.sleep(0.1)
        if not daemon_stopped:
            raise RuntimeError(
                "owned daemon still served health after clean entry-point exit"
            )

        final = _db_state(database, fixture)
        if final["integrity"] != "ok" or final["heads"] != expected_heads:
            raise RuntimeError(
                "resumed DB heads/integrity differ from candidate current fixture: "
                f"{final}; expected_heads={expected_heads}"
            )
        if not final["fixture_marker_matches"] or not final["conversation_matches"]:
            raise RuntimeError("resumed database did not retain fixture values")

        receipt: dict[str, Any] = {
            "schema_version": 1,
            "probe": "installed_frozen_core_interrupted_after_backup_before_write",
            "evidence_scope": "installed frozen CORE candidate runtime",
            "installed_executable": str(binary),
            "fixture_kind": fixture["fixture_kind"],
            "fixture_source_sha": fixture["source_sha"],
            "fixture_database_sha256": fixture["database_sha256"],
            "expected_heads_source_sha": expected_record["source_sha"],
            "expected_current_heads": expected_heads,
            "interrupted_entry_point": (
                "packaged airunner-headless via airunner-core executable"
            ),
            "interrupted_pid": interrupted.pid,
            "interrupted_exit_code": interrupted_return,
            "interrupted_owned_descendants": interrupted_descendants,
            "interruption_boundary": (
                "pre-upgrade backup manifest durable; external BEGIN IMMEDIATE "
                "held; before migration writes"
            ),
            "backup_manifest": manifest_path.name,
            "backup_sha256": manifest["sha256"],
            "backup_heads": sorted(manifest["heads"]),
            "backup_integrity_and_fixture": backup_after_kill,
            "live_after_kill": live_after_kill,
            "recovery": (
                "released controller transaction; normal frozen startup "
                "resumed current migration graph"
            ),
            "unauthenticated_health_status": unauthenticated_health,
            "unauthenticated_daemon_api_status": unauthenticated_api_status,
            "authenticated_daemon_api_status": authenticated_api_status,
            "authenticated_conversation_status": conversation_status,
            "conversation_fixture_verified": True,
            "daemon_health_pid": daemon_pid,
            "daemon_process_identity": daemon_identity,
            "resumed_owned_descendants_before_stop": resumed_descendants,
            "resumed_owned_descendants_gone_after_stop": True,
            "resumed_entry_point_exit_code": resumed_return,
            "daemon_stopped_after_entry_point_exit": daemon_stopped,
            "database_after_resume": final,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "limitations": [
                "Synthetic published-prior SQLite fixture only; no owner or "
                "production database was opened.",
                "The frozen headless entry point was killed after production "
                "emitted the pre-upgrade backup manifest while an isolated "
                "SQLite writer reservation remained held; this establishes "
                "an after-backup/before-write boundary.",
                "This is distinct from the source-level probe that kills "
                "after one observed DDL returns.",
                "No arbitrary power loss, filesystem corruption, or "
                "interrupted dpkg unpack/configuration is simulated.",
                "No system package install/remove, systemd service, GPU, "
                "model, or model download was used by this probe.",
            ],
        }
        output.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        output.chmod(0o600)
        success = True
        return receipt
    finally:
        if controller is not None:
            try:
                controller.execute("ROLLBACK")
            finally:
                controller.close()
        if interrupted is not None and interrupted.poll() is None:
            if not interrupted_descendants:
                interrupted_descendants = _owned_descendants(interrupted.pid)
            interrupted.kill()
            interrupted.wait(timeout=10)
        if interrupted_descendants and not _wait_identities_gone(
            interrupted_descendants, timeout=2
        ):
            _stop_verified_descendants(interrupted_descendants, timeout=2)
        if resumed is not None and resumed.poll() is None:
            try:
                if not resumed_descendants:
                    resumed_descendants = _owned_descendants(resumed.pid)
                _stop_owned(resumed)
            except subprocess.TimeoutExpired:
                print(
                    "resumed entry point did not stop cleanly; inspect "
                    f"{work / 'resumed.log'}",
                    file=sys.stderr,
                    flush=True,
                )
        if resumed_descendants and not _wait_identities_gone(
            resumed_descendants, timeout=2
        ):
            _stop_verified_descendants(resumed_descendants, timeout=2)
        if success:
            shutil.rmtree(work)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--fixture-db", type=Path, required=True)
    parser.add_argument("--fixture-record", type=Path, required=True)
    parser.add_argument("--expected-heads-record", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()
    receipt = run_probe(
        args.binary,
        args.fixture_db,
        args.fixture_record,
        args.expected_heads_record,
        args.output,
        timeout_seconds=args.timeout,
    )
    print(
        json.dumps(
            {
                "status": "passed",
                "interrupted_pid": receipt["interrupted_pid"],
                "resumed_exit": receipt["resumed_entry_point_exit_code"],
                "receipt": str(args.output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
