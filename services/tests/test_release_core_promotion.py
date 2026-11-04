from __future__ import annotations

import hashlib
import json
import shutil
import signal
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_release_identity as guard  # noqa: E402
from prepare_core_release_assets import prepare  # noqa: E402
import probe_core_installed_interrupted_upgrade as installed_probe  # noqa: E402
from prepare_core_release_assets import validate_candidate_acceptance  # noqa: E402
from verify_core_candidate_run import (  # noqa: E402
    CandidateRunError,
    verify_candidate_run,
)


def _fixture(root: Path, *, clean_status: str = "passed") -> tuple[Path, str]:
    (root / "services").mkdir()
    (root / "services/setup.py").write_text('_RELEASE_VERSION = "1.2.3"\n')
    artifact = root / "candidate"
    artifact.mkdir()
    deb = artifact / "airunner_1.2.3-1_amd64.deb"
    deb.write_bytes(b"exact fake Debian bytes")
    sha = hashlib.sha256(deb.read_bytes()).hexdigest()
    (artifact / "candidate.json").write_text(json.dumps({
        "profile": "linux-services-core", "source_sha": "a" * 40,
        "build_status": "passed", "debian_filename": deb.name,
        "debian_version": "1.2.3-1", "debian_sha256": sha,
        "requirements_sha256": "1" * 64, "lock_sha256": "2" * 64,
    }))
    (artifact / "candidate-validation.json").write_text(json.dumps({
        "source_sha": "a" * 40, "debian_sha256": sha,
        "clean_install_smoke": clean_status,
    }))
    upgrade = {
        "source_sha": "a" * 40, "debian_sha256": sha,
        "upgrade_smoke": "passed",
        "checks": {"interrupted_upgrade_recovery_probe": "passed"},
        "fixture_database_sha256": "b" * 64,
        "expected_alembic_heads_after": ["f3a2c9e4b710"],
        "interrupted_upgrade_recovery_probe": _valid_interruption_probe("a" * 40),
    }
    (artifact / "candidate-upgrade-validation.json").write_text(json.dumps(upgrade))
    (root / "package").mkdir()
    (root / "package/requirements-linux-core.in").write_text("core requirements")
    (root / "package/constraints-linux-core.txt").write_text("core lock")
    candidate_record = json.loads((artifact / "candidate.json").read_text())
    candidate_record["requirements_sha256"] = hashlib.sha256(
        (root / "package/requirements-linux-core.in").read_bytes()
    ).hexdigest()
    candidate_record["lock_sha256"] = hashlib.sha256(
        (root / "package/constraints-linux-core.txt").read_bytes()
    ).hexdigest()
    (artifact / "candidate.json").write_text(json.dumps(candidate_record))
    artifact_names = [
        "core-debian-candidate-51-2",
        "core-debian-validation-51-2",
        "core-debian-upgrade-validation-51-2",
    ]
    (root / "candidate-run.json").write_text(json.dumps({
        "workflow": ".github/workflows/core-debian-candidate.yml", "run_id": 51,
        "run_attempt": 2, "tag": "v1.2.3", "source_sha": "a" * 40,
        "run_conclusion": "success",
        "successful_jobs": ["build-core-debian-candidate", "clean-install-smoke", "published-upgrade-data-smoke", "verify-candidate-receipts"],
        "artifacts": {
            name: {"name": name, "id": index, "size_in_bytes": 100}
            for index, name in enumerate(artifact_names, 1)
        },
    }))
    notices = root / "notices"
    notices.mkdir()
    (notices / "LICENSE").write_text("reviewed notice")
    return artifact, sha


def _valid_interruption_probe(source_sha: str) -> dict:
    prior_heads = ["a7c93f2e1b4d", "d951d2fd378d"]
    current_heads = ["f3a2c9e4b710"]
    state_before = {
        "integrity": "ok", "heads": prior_heads,
        "fixture_marker_matches": True, "conversation_matches": True,
    }
    state_after = {
        "integrity": "ok", "heads": current_heads,
        "fixture_marker_matches": True, "conversation_matches": True,
    }
    return {
        "schema_version": 1,
        "probe": "installed_frozen_core_interrupted_after_backup_before_write",
        "evidence_scope": "installed frozen CORE candidate runtime",
        "installed_executable": "/usr/lib/airunner/airunner-core",
        "fixture_kind": "published_prior_debian_schema",
        "fixture_source_sha": source_sha,
        "fixture_database_sha256": "b" * 64,
        "expected_heads_source_sha": source_sha,
        "expected_current_heads": current_heads,
        "interrupted_entry_point": "packaged airunner-headless via airunner-core executable",
        "interrupted_pid": 4604, "interrupted_exit_code": -9,
        "interrupted_owned_descendants": [],
        "interruption_boundary": "pre-upgrade backup manifest durable; external BEGIN IMMEDIATE held; before migration writes",
        "backup_manifest": "airunner-20261104T011016959058-4604Z.db.json",
        "backup_sha256": "c" * 64, "backup_heads": prior_heads,
        "backup_integrity_and_fixture": state_before,
        "live_after_kill": state_before,
        "recovery": "released controller transaction; normal frozen startup resumed current migration graph",
        "unauthenticated_health_status": 200,
        "unauthenticated_daemon_api_status": 401,
        "authenticated_daemon_api_status": 200,
        "authenticated_conversation_status": 200,
        "conversation_fixture_verified": True,
        "daemon_health_pid": 4613,
        "daemon_process_identity": {"pid": 4613, "starttime": 19165},
        "resumed_owned_descendants_before_stop": [{"pid": 4613, "starttime": 19165}],
        "resumed_owned_descendants_gone_after_stop": True,
        "resumed_entry_point_exit_code": 0,
        "daemon_stopped_after_entry_point_exit": True,
        "database_after_resume": state_after,
        "elapsed_seconds": 9.357, "limitations": ["synthetic fixture only"],
    }


def test_core_release_assets_are_deterministic_and_source_bound(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    artifact, _ = _fixture(tmp_path)
    validate_candidate_acceptance(artifact, "a" * 40)
    outputs = []
    for name in ("out-a", "out-b"):
        output = tmp_path / name
        prepare(
            artifact_dir=artifact, notices_dir=tmp_path / "notices", output_dir=output,
            source_sha="a" * 40, tag="v1.2.3", workflow_run_id=42,
            workflow=".github/workflows/core-debian-candidate.yml",
            candidate_run_id=51, candidate_attempt=2,
            candidate_run_receipt=tmp_path / "candidate-run.json",
        )
        outputs.append(output)
    for filename in sorted(path.name for path in outputs[0].iterdir()):
        assert (outputs[0] / filename).read_bytes() == (outputs[1] / filename).read_bytes()
    guard._require_promotion_groups(
        list(outputs[0].iterdir()), tag="v1.2.3", source_sha="a" * 40,
        root=tmp_path, profile="core", expected_run_id=42,
    )
    manifest_path = outputs[0] / "airunner-core-release.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["debian_version"] = "1.2.30-1"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(guard.ReleaseIdentityError, match="package version differs"):
        guard._require_promotion_groups(
            list(outputs[0].iterdir()), tag="v1.2.3", source_sha="a" * 40,
            root=tmp_path, profile="core", expected_run_id=42,
        )
    manifest["debian_version"] = "1.2.3-1"
    manifest["promotion_workflow_run_id"] = 41
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(guard.ReleaseIdentityError, match="promotion_workflow_run_id"):
        guard._require_promotion_groups(
            list(outputs[0].iterdir()), tag="v1.2.3", source_sha="a" * 40,
            root=tmp_path, profile="core", expected_run_id=42,
        )
    manifest["promotion_workflow_run_id"] = 42
    manifest_path.write_text(json.dumps(manifest))
    (outputs[0] / "SHA256SUMS").write_text("0" * 64 + "  airunner-core-release.json\n")
    with pytest.raises(guard.ReleaseIdentityError, match="checksum"):
        guard._verify_checksum_manifest(list(outputs[0].iterdir()))


def test_core_release_refuses_failed_or_mismatched_install_evidence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    artifact, _ = _fixture(tmp_path, clean_status="failed")
    with pytest.raises(ValueError, match="evidence is incomplete"):
        prepare(
            artifact_dir=artifact, notices_dir=tmp_path / "notices",
            output_dir=tmp_path / "out", source_sha="a" * 40, tag="v1.2.3",
            workflow_run_id=42, workflow=".github/workflows/core-debian-candidate.yml",
            candidate_run_id=51, candidate_attempt=2,
            candidate_run_receipt=tmp_path / "candidate-run.json",
        )


def test_installed_probe_receipt_can_be_promoted(tmp_path, monkeypatch):
    """Exercise receipt production through promotion with runtime/HTTP doubles."""
    monkeypatch.chdir(tmp_path)
    artifact, _ = _fixture(tmp_path)
    database = tmp_path / "fixture.db"
    conversation = {"id": 1, "title": "fixture", "payload": "value", "summary": "summary"}
    with sqlite3.connect(database) as connection:
        connection.executescript(
            "CREATE TABLE alembic_version (version_num TEXT);"
            "INSERT INTO alembic_version VALUES ('a7c93f2e1b4d');"
            "CREATE TABLE core_upgrade_fixture (marker TEXT, payload TEXT);"
            "INSERT INTO core_upgrade_fixture VALUES ('synthetic-marker', 'marker');"
            "CREATE TABLE conversations (id INTEGER, title TEXT, value TEXT);"
            "INSERT INTO conversations VALUES (1, 'fixture', 'value');"
        )
    fixture_record = tmp_path / "fixture.json"
    fixture_record.write_text(json.dumps({
        "fixture_kind": "published_prior_debian_schema", "source_sha": "a" * 40,
        "database_sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
        "migration_source_inventory": {"heads_before_candidate_upgrade": ["a7c93f2e1b4d"]},
        "synthetic_conversation": conversation, "fixture_payload": "marker",
    }))
    expected = tmp_path / "expected.json"
    expected.write_text(json.dumps({
        "source_sha": "a" * 40, "expected_alembic_heads_after_upgrade": ["f3a2c9e4b710"],
    }))
    binary = tmp_path / "runtime-double"
    binary.touch(mode=0o700)

    class Child:
        pid = 100
        returncode = None

        def poll(self):
            return self.returncode

        def kill(self):
            self.returncode = -signal.SIGKILL

        def wait(self, timeout):
            return self.returncode

    stopped = False
    resumed = False

    def launch(_binary, env, _config, log):
        nonlocal resumed
        live = Path(env["AIRUNNER_DATA_DIR"]) / "airunner.db"
        if log.name == "interrupted.log":
            backup = Path(env["AIRUNNER_UPGRADE_BACKUP_DIR"]) / "backup.db"
            shutil.copyfile(live, backup)
            backup.with_suffix(".db.json").write_text(json.dumps({
                "heads": ["a7c93f2e1b4d"], "path": str(backup),
                "size_bytes": backup.stat().st_size,
                "sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
            }))
        else:
            resumed = True
            with sqlite3.connect(live) as connection:
                connection.execute("UPDATE alembic_version SET version_num = 'f3a2c9e4b710'")
        return Child()

    def request(url, api_key=None):
        if stopped:
            raise OSError("owned runtime stopped")
        if url.endswith("/health"):
            return 200, b'{"pid": 101}'
        if url.endswith("/health/daemon"):
            return (200 if api_key else 401), b"{}"
        return 200, json.dumps({
            "conversation": conversation,
            "messages": [{"content": "published-upgrade-marker-v1"}, {}],
        }).encode()

    def stop(child):
        nonlocal stopped
        stopped = True
        child.returncode = 0
        return 0

    monkeypatch.setattr(installed_probe, "_launch", launch)
    monkeypatch.setattr(installed_probe, "_request", request)
    monkeypatch.setattr(installed_probe, "_stop_owned", stop)
    monkeypatch.setattr(installed_probe, "_owned_descendants", lambda _pid: [{"pid": 101, "starttime": 1}] if resumed else [])
    monkeypatch.setattr(installed_probe, "_wait_identities_gone", lambda *_args, **_kwargs: True)
    receipt_path = tmp_path / "installed-receipt.json"
    receipt = installed_probe.run_probe(binary, database, fixture_record, expected, receipt_path)
    assert json.loads(receipt_path.read_text()) == receipt
    assert receipt["status"] == "passed"
    assert receipt["database_after_resume"]["heads"] == ["f3a2c9e4b710"]
    upgrade_path = artifact / "candidate-upgrade-validation.json"
    upgrade = json.loads(upgrade_path.read_text())
    # The process double uses a temporary executable in place of the installed path.
    receipt["installed_executable"] = "/usr/lib/airunner/airunner-core"
    upgrade["fixture_database_sha256"] = receipt["fixture_database_sha256"]
    upgrade["interrupted_upgrade_recovery_probe"] = receipt
    upgrade_path.write_text(json.dumps(upgrade))
    prepare(
        artifact_dir=artifact, notices_dir=tmp_path / "notices", output_dir=tmp_path / "out",
        source_sha="a" * 40, tag="v1.2.3", workflow_run_id=42,
        workflow=".github/workflows/core-debian-candidate.yml",
        candidate_run_id=51, candidate_attempt=2,
        candidate_run_receipt=tmp_path / "candidate-run.json",
    )


@pytest.mark.parametrize("probe", [None, {}, {"status": "failed"}, {"status": "incomplete"}])
def test_core_release_rejects_incomplete_interruption_receipt(tmp_path, monkeypatch, probe):
    monkeypatch.chdir(tmp_path)
    artifact, _ = _fixture(tmp_path)
    path = artifact / "candidate-upgrade-validation.json"
    upgrade = json.loads(path.read_text())
    upgrade["interrupted_upgrade_recovery_probe"] = probe
    path.write_text(json.dumps(upgrade))
    with pytest.raises(ValueError, match="recovery evidence is incomplete"):
        prepare(
            artifact_dir=artifact, notices_dir=tmp_path / "notices", output_dir=tmp_path / "out",
            source_sha="a" * 40, tag="v1.2.3", workflow_run_id=42,
            workflow=".github/workflows/core-debian-candidate.yml",
            candidate_run_id=51, candidate_attempt=2,
            candidate_run_receipt=tmp_path / "candidate-run.json",
        )
@pytest.mark.parametrize(
    "mutate",
    [
        lambda record: record["checks"].update(interrupted_upgrade_recovery_probe="failed"),
        lambda record: record["interrupted_upgrade_recovery_probe"].update(fixture_source_sha="f" * 40),
        lambda record: record["interrupted_upgrade_recovery_probe"].update(resumed_entry_point_exit_code=1),
        lambda record: record["interrupted_upgrade_recovery_probe"].update(resumed_entry_point_exit_code=False),
        lambda record: record["interrupted_upgrade_recovery_probe"].update(resumed_owned_descendants_gone_after_stop=False),
        lambda record: record["interrupted_upgrade_recovery_probe"].update(unauthenticated_daemon_api_status=200),
        lambda record: record["interrupted_upgrade_recovery_probe"]["database_after_resume"].update(heads=["a7c93f2e1b4d"]),
        lambda record: record["interrupted_upgrade_recovery_probe"].update(interrupted_owned_descendants=[{"pid": 99}]),
    ],
    ids=("status", "fixture-source", "resume-exit", "boolean-exit", "cleanup", "auth", "heads", "killed-descendants"),
)
def test_candidate_acceptance_rejects_incomplete_interruption_probe(tmp_path, monkeypatch, mutate):
    monkeypatch.chdir(tmp_path)
    artifact, _ = _fixture(tmp_path)
    receipt = artifact / "candidate-upgrade-validation.json"
    record = json.loads(receipt.read_text())
    mutate(record)
    receipt.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="interrupted-upgrade recovery evidence"):
        validate_candidate_acceptance(artifact, "a" * 40)


def test_core_profile_rejects_extra_assets_and_wrong_workflow_run(tmp_path):
    files = []
    clean_receipt = json.dumps({
        "source_sha": "a" * 40,
        "debian_sha256": hashlib.sha256(b"deb").hexdigest(),
        "clean_install_smoke": "passed",
    }).encode()
    upgrade_receipt = json.dumps({
        "source_sha": "a" * 40,
        "debian_sha256": hashlib.sha256(b"deb").hexdigest(),
        "upgrade_smoke": "passed",
        "interrupted_upgrade_recovery_probe": {"status": "passed"},
    }).encode()
    for name, data in {
        "airunner_1.2.3-1_amd64.deb": b"deb",
        "airunner-core-notices.tar.gz": b"notices",
        "airunner-core-candidate-run.json": json.dumps({
            "workflow": ".github/workflows/core-debian-candidate.yml", "run_id": 51,
            "run_attempt": 2, "tag": "v1.2.3", "source_sha": "a" * 40,
            "run_conclusion": "success",
            "successful_jobs": ["build-core-debian-candidate", "clean-install-smoke", "published-upgrade-data-smoke", "verify-candidate-receipts"],
            "artifacts": {
                name: {"name": name, "id": index, "size_in_bytes": 100}
                for index, name in enumerate((
                    "core-debian-candidate-51-2", "core-debian-validation-51-2",
                    "core-debian-upgrade-validation-51-2",
                ), 1)
            },
        }).encode(),
        "airunner-core-clean-install-validation.json": clean_receipt,
        "airunner-core-upgrade-validation.json": upgrade_receipt,
        "airunner-core-release.json": json.dumps({
            "schema_version": 1, "profile": "linux-services-core", "tag": "v1.2.3",
            "source_sha": "a" * 40,
            "workflow": ".github/workflows/core-debian-candidate.yml",
            "promotion_workflow_run_id": 99, "debian_filename": "airunner_1.2.3-1_amd64.deb",
            "debian_sha256": hashlib.sha256(b"deb").hexdigest(),
            "debian_version": "1.2.3-1", "requirements_sha256": "1" * 64,
            "lock_sha256": "2" * 64,
            "build_status": "passed", "clean_install_smoke": "passed",
            "upgrade_smoke": "passed", "notices_path": "/usr/lib/airunner/legal",
            "notices_sha256": hashlib.sha256(b"notices").hexdigest(),
            "promotion_workflow_run_id": 42, "candidate_workflow_run_id": 51,
            "candidate_run_attempt": 2,
            "candidate_run_receipt_sha256": "5" * 64,
            "clean_install_validation_sha256": hashlib.sha256(clean_receipt).hexdigest(),
            "upgrade_validation_sha256": hashlib.sha256(upgrade_receipt).hexdigest(),
        }).encode(),
        "SHA256SUMS": b"",
        "extra.txt": b"unexpected",
    }.items():
        path = tmp_path / name
        path.write_bytes(data)
        files.append(path)
    with pytest.raises(guard.ReleaseIdentityError, match="exactly the package"):
        guard._require_promotion_groups(
            files, tag="v1.2.3", source_sha="a" * 40, root=tmp_path,
            profile="core", expected_run_id=42,
        )


def test_candidate_run_verifier_binds_workflow_sha_jobs_and_attempt_artifacts(tmp_path):
    run_id = 87
    attempt = 3
    tag = "v1.2.3"
    source = "a" * 40
    names = {
        f"core-debian-candidate-{run_id}-{attempt}",
        f"core-debian-validation-{run_id}-{attempt}",
        f"core-debian-upgrade-validation-{run_id}-{attempt}",
    }
    payloads = {
        f"https://api.github.com/repos/Capsize-Games/airunner/actions/runs/{run_id}": {
            "id": run_id,
            "path": ".github/workflows/core-debian-candidate.yml@refs/tags/v1.2.3",
            "repository": {"full_name": "Capsize-Games/airunner"},
            "head_repository": {"full_name": "Capsize-Games/airunner"},
            "event": "workflow_dispatch", "head_branch": tag, "head_sha": source,
            "status": "completed", "conclusion": "success", "run_attempt": attempt,
        },
        f"https://api.github.com/repos/Capsize-Games/airunner/actions/runs/{run_id}/jobs?filter=latest&per_page=100": {
            "jobs": [{"name": name, "status": "completed", "conclusion": "success"} for name in (
                "build-core-debian-candidate", "clean-install-smoke", "published-upgrade-data-smoke", "verify-candidate-receipts"
            )]
        },
        f"https://api.github.com/repos/Capsize-Games/airunner/actions/runs/{run_id}/artifacts?per_page=100": {
            "artifacts": [
                {"id": index, "name": name, "expired": False, "size_in_bytes": 100}
                for index, name in enumerate(sorted(names), 1)
            ]
        },
    }

    class Response:
        def __init__(self, value):
            self.value = value
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def read(self):
            return json.dumps(self.value).encode()

    def opener(request, timeout):
        assert timeout == 15
        return Response(payloads[request.full_url])

    receipt = tmp_path / "candidate-run.json"
    proof = verify_candidate_run(
        repository="Capsize-Games/airunner", run_id=run_id, tag=tag,
        source_sha=source, token="test-token", output_json=receipt, opener=opener,
    )
    assert proof["run_attempt"] == attempt
    assert set(proof["artifacts"]) == names

    jobs_url = next(url for url in payloads if "/jobs?filter=latest" in url)
    payloads[jobs_url]["jobs"][0]["conclusion"] = "failure"
    with pytest.raises(CandidateRunError, match="lacks a successful"):
        verify_candidate_run(
            repository="Capsize-Games/airunner", run_id=run_id, tag=tag,
            source_sha=source, token="test-token", output_json=tmp_path / "bad.json", opener=opener,
        )
