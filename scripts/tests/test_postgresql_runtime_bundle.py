"""CPU-only tests for the frozen PostgreSQL OS prerequisite payload."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    import linux_bundle_assemble
    import postgresql_runtime_payload as payload
finally:
    sys.path.remove(str(SCRIPTS))


def _fixture_supplement(repo_root: Path, tmp_path: Path) -> Path:
    stage = tmp_path / "supplement-stage"
    (stage / "debs").mkdir(parents=True)
    lock_path = repo_root / payload.SUPPLEMENT_LOCK_RELATIVE
    packages = []
    receipt_packages = []
    for name in sorted(payload.EXPECTED_SUPPLEMENT_PACKAGES):
        version = "2.39-0ubuntu8.9"
        filename = f"{name}_{version}_amd64.deb"
        data = f"synthetic supplement {name}".encode()
        digest = hashlib.sha256(data).hexdigest()
        packages.append({
            "Package": name, "Version": version, "Architecture": "amd64",
            "Filename": f"pool/main/g/glibc/{filename}", "Size": str(len(data)), "SHA256": digest,
        })
        (stage / "debs" / filename).write_bytes(data)
        receipt_packages.append({
            "package": name, "version": version, "architecture": "amd64", "filename": filename,
            "size_bytes": len(data), "sha256": digest,
        })
    lock = {
        "kind": "build-only-compatibility-supplement",
        "root": payload.EXPECTED_SUPPLEMENT_ROOT,
        "package_count": payload.EXPECTED_SUPPLEMENT_COUNT,
        "packages": packages,
    }
    lock_bytes = (json.dumps(lock, sort_keys=True) + "\n").encode()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_bytes(lock_bytes)
    (stage / payload.SUPPLEMENT_LOCK_NAME).write_bytes(lock_bytes)
    (stage / "install-packages.txt").write_text(
        "".join(f"{item['Package']}={item['Version']}\n" for item in packages), encoding="ascii"
    )
    receipt = {
        "kind": "build-supplement", "installation_performed": False,
        "package_count": len(packages), "lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        "packages": receipt_packages,
    }
    (stage / "staging-receipt.json").write_text(json.dumps(receipt, sort_keys=True) + "\n")
    checksummed = sorted(item for item in stage.rglob("*") if item.is_file())
    (stage / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(item.read_bytes()).hexdigest()}  {item.relative_to(stage).as_posix()}\n"
        for item in checksummed
    ), encoding="ascii")
    return stage


def _fixture_stage(tmp_path: Path) -> tuple[Path, Path, Path, dict]:
    repo_root = tmp_path / "repo"
    stage_dir = tmp_path / "stage"
    deb_dir = stage_dir / "debs"
    lock_path = repo_root / payload.LOCK_RELATIVE
    lock_path.parent.mkdir(parents=True)
    deb_dir.mkdir(parents=True)
    packages = []
    receipt_packages = []
    for index in range(payload.EXPECTED_COUNT):
        if index == 0:
            name = "libpq5"
            version = "16.15-0ubuntu0.24.04.1"
            filename = f"{name}_{version}_amd64.deb"
        else:
            name = f"fixture-pkg-{index:02}"
            version = "1.0-1"
            filename = f"{name}_{version}_amd64.deb"
        content = f"synthetic deb payload {index}".encode()
        digest = hashlib.sha256(content).hexdigest()
        packages.append({
            "Package": name,
            "Version": version,
            "Architecture": "amd64",
            "Filename": f"pool/main/{name[0]}/{name}/{filename}",
            "Size": str(len(content)),
            "SHA256": digest,
        })
        (deb_dir / filename).write_bytes(content)
        receipt_packages.append({
            "package": name,
            "version": version,
            "architecture": "amd64",
            "filename": filename,
            "size_bytes": len(content),
            "sha256": digest,
            "source": "canonical_archive_download",
            "source_url": f"https://archive.ubuntu.com/ubuntu/pool/main/{filename}",
        })
    lock = {
        "origin_indexes": ["noble-main-amd64-Packages.gz"],
        "root": payload.EXPECTED_ROOT,
        "package_count": payload.EXPECTED_COUNT,
        "packages": packages,
        "edges": [],
    }
    lock_bytes = (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode()
    lock_path.write_bytes(lock_bytes)
    (stage_dir / payload.LOCK_NAME).write_bytes(lock_bytes)
    install_text = "".join(f"{p['Package']}={p['Version']}\n" for p in packages)
    (stage_dir / "install-packages.txt").write_text(install_text, encoding="ascii")
    receipt = {
        "schema_version": 1,
        "kind": "runtime",
        "installation_performed": False,
        "database_driver_imported": False,
        "database_connection_attempted": False,
        "root_package": payload.EXPECTED_ROOT,
        "lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        "package_count": payload.EXPECTED_COUNT,
        "total_bytes": sum(p["size_bytes"] for p in receipt_packages),
        "origin_indexes": lock["origin_indexes"],
        "packages": receipt_packages,
    }
    (stage_dir / "staging-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    checksummed = sorted(path for path in stage_dir.rglob("*") if path.is_file())
    (stage_dir / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(stage_dir).as_posix()}\n"
            for path in checksummed
        ),
        encoding="ascii",
    )
    installer = repo_root / "packaging/linux/install-postgresql-runtime.sh"
    installer.parent.mkdir(parents=True, exist_ok=True)
    installer.write_bytes((ROOT / "packaging/linux/install-postgresql-runtime.sh").read_bytes())
    verifier = repo_root / "services/src/airunner_services/runtimes/postgresql_prerequisites.py"
    verifier.parent.mkdir(parents=True)
    verifier.write_bytes((ROOT / "services/src/airunner_services/runtimes/postgresql_prerequisites.py").read_bytes())
    return repo_root, stage_dir, _fixture_supplement(repo_root, tmp_path), lock


def test_full_payload_contains_hashed_lock_receipt_and_offline_debs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        payload,
        "_builder_provenance",
        lambda _bundle_dir=None: {
            "schema_version": 1,
            "build_host": {
                "os_release": {"ID": "ubuntu", "VERSION_ID": "24.04"},
                "architecture": "x86_64",
                "libpq5_package": {"availability": "unavailable", "reason": "synthetic"},
            },
            "freeze_analysis": {
                "native_library_load_observation": "not_measured",
                "runtime_loader": "synthetic runtime lookup metadata",
                "candidate_bundle_libpq_paths": [],
                "libpq_collection_expected": False,
            },
        },
    )
    repo_root, stage_dir, supplement_dir, lock = _fixture_stage(tmp_path)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    spec = {"postgresql_runtime": {"mode": "locked-ubuntu-debs"}}

    payload.stage_runtime_payload(stage_dir, bundle, spec, repo_root, supplement_dir)
    issues = payload.verify_runtime_payload(bundle, spec, repo_root)

    assert issues == []
    destination = bundle / payload.DESTINATION
    assert json.loads((destination / "runtime-policy.json").read_text())["package_count"] == payload.EXPECTED_COUNT
    assert (destination / "staging-receipt.json").is_file()
    assert (destination / payload.LOCK_NAME).read_bytes() == (repo_root / payload.LOCK_RELATIVE).read_bytes()
    assert len(list((destination / "debs").glob("*.deb"))) == payload.EXPECTED_COUNT
    assert hashlib.sha256((destination / "debs" / "libpq5_16.15-0ubuntu0.24.04.1_amd64.deb").read_bytes()).hexdigest() == lock["packages"][0]["SHA256"]
    provenance = json.loads((destination / "freeze-build-provenance.json").read_text())
    assert provenance["freeze_analysis"]["native_library_load_observation"] == "not_measured"
    assert provenance["freeze_analysis"]["candidate_bundle_libpq_paths"] == []
    manifest = linux_bundle_assemble.write_manifest(
        bundle,
        {
            "bundle": {"name": "fixture", "tool": "pyinstaller", "entry": "fixture:main"},
            "manifest": {"filename": "bundle-manifest.json"},
        },
        "fixture-source",
    )
    manifested = {item["path"] for item in manifest["files"]}
    assert (payload.DESTINATION / payload.LOCK_NAME).as_posix() in manifested
    assert (payload.DESTINATION / "staging-receipt.json").as_posix() in manifested
    assert (payload.DESTINATION / "debs" / "libpq5_16.15-0ubuntu0.24.04.1_amd64.deb").as_posix() in manifested
    assert (payload.DESTINATION / "build-supplement" / payload.SUPPLEMENT_LOCK_NAME).as_posix() in manifested


def test_runtime_bundle_inspector_rejects_missing_and_drifted_deb(tmp_path: Path):
    repo_root, stage_dir, supplement_dir, _lock = _fixture_stage(tmp_path)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    spec = {"postgresql_runtime": {"mode": "locked-ubuntu-debs"}}
    payload.stage_runtime_payload(stage_dir, bundle, spec, repo_root, supplement_dir)
    destination = bundle / payload.DESTINATION

    first = next((destination / "debs").glob("*.deb"))
    first.unlink()
    problems = payload.verify_runtime_payload(bundle, spec, repo_root)
    assert any(
        any(term in problem for term in ("checksum mismatch", "missing", ".deb differs"))
        for problem in problems
    )


def test_stage_rejects_receipt_or_package_hash_drift_before_copy(tmp_path: Path):
    repo_root, stage_dir, supplement_dir, _lock = _fixture_stage(tmp_path)
    first = next((stage_dir / "debs").glob("*.deb"))
    first.write_bytes(b"changed")
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    with pytest.raises(payload.PostgreSQLPayloadError, match=r"\.deb differs"):
        payload.stage_runtime_payload(
            stage_dir,
            bundle,
            {"postgresql_runtime": {"mode": "locked-ubuntu-debs"}},
            repo_root,
            supplement_dir,
        )
    assert not (bundle / payload.DESTINATION).exists()


def test_stage_rejects_symlink_destination_before_writing_outside_bundle(tmp_path: Path):
    repo_root, stage_dir, supplement_dir, _lock = _fixture_stage(tmp_path)
    bundle = tmp_path / "bundle"
    outside = tmp_path / "outside"
    bundle.mkdir()
    outside.mkdir()
    (bundle / "runtime-requirements").symlink_to(outside, target_is_directory=True)

    with pytest.raises(payload.PostgreSQLPayloadError, match="symlink"):
        payload.stage_runtime_payload(
            stage_dir, bundle, {"postgresql_runtime": {"mode": "locked-ubuntu-debs"}},
            repo_root, supplement_dir,
        )
    assert list(outside.iterdir()) == []


def test_staged_input_rejects_symlink_and_special_file(tmp_path: Path):
    repo_root, stage_dir, _supplement_dir, _lock = _fixture_stage(tmp_path)
    linked = tmp_path / "linked-target"
    linked.write_text("unrelated", encoding="utf-8")
    (stage_dir / "debs" / "unexpected-link").symlink_to(linked)
    with pytest.raises(payload.PostgreSQLPayloadError, match="symlink"):
        payload.validate_staged_runtime(stage_dir, repo_root)

    (stage_dir / "debs" / "unexpected-link").unlink()
    fifo = stage_dir / "unexpected-fifo"
    os.mkfifo(fifo)
    with pytest.raises(payload.PostgreSQLPayloadError, match="special file"):
        payload.validate_staged_runtime(stage_dir, repo_root)


def test_sqlite_only_policy_has_no_os_package_payload(tmp_path: Path):
    repo_root = tmp_path / "repo"
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    spec = {"postgresql_runtime": {"mode": "disabled"}}

    payload.stage_runtime_payload(None, bundle, spec, repo_root)

    destination = bundle / payload.DESTINATION
    assert payload.verify_runtime_payload(bundle, spec, repo_root) == []
    assert json.loads((destination / "runtime-policy.json").read_text())["mode"] == "disabled"
    assert not any(path.is_file() for path in destination.rglob("*")) or list(destination.iterdir()) == [destination / "runtime-policy.json"]


def test_inspector_rejects_omitted_postgresql_policy(tmp_path: Path):
    repo_root = tmp_path / "repo"
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    spec = {"postgresql_runtime": {"mode": "locked-ubuntu-debs"}}

    problems = payload.verify_runtime_payload(bundle, spec, repo_root)

    assert problems == ["missing PostgreSQL runtime policy metadata"]


def test_full_build_rejects_unreviewed_builder_platform(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        payload,
        "_builder_provenance",
        lambda: {
            "build_host": {
                "os_release": {"ID": "debian", "VERSION_ID": "13"},
                "architecture": "x86_64",
                "libpq5_package": {"availability": "unavailable"},
            }
        },
    )

    with pytest.raises(payload.PostgreSQLPayloadError, match="Ubuntu 24.04 amd64"):
        payload.validate_build_host()
