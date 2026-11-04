"""Frozen PostgreSQL package preflight tests; no DBAPI or native load."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from airunner_services.runtimes import postgresql_prerequisites as prereq
from airunner_services.runtimes.postgresql_runtime import configure_postgresql_runtime


def _bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, dict[str, tuple[str, str]]]:
    root = tmp_path / "bundle"
    directory = root / prereq.POSTGRESQL_PAYLOAD
    directory.mkdir(parents=True)
    packages = []
    expected = {}
    for index in range(prereq.EXPECTED_PACKAGE_COUNT):
        if index == 0:
            name, version = "libpq5", "16.15-0ubuntu0.24.04.1"
        else:
            name, version = f"fixture-pkg-{index:02}", "1.0-1"
        packages.append({
            "Package": name,
            "Version": version,
            "Architecture": "amd64",
            "Filename": f"pool/main/{name[0]}/{name}/{name}_{version}_amd64.deb",
            "Size": "1",
            "SHA256": "0" * 64,
        })
        expected[name] = (version, "amd64")
    lock = {
        "root": prereq.EXPECTED_ROOT,
        "package_count": prereq.EXPECTED_PACKAGE_COUNT,
        "packages": packages,
    }
    lock_bytes = (json.dumps(lock, sort_keys=True) + "\n").encode()
    monkeypatch.setattr(
        prereq, "EXPECTED_LOCK_SHA256", hashlib.sha256(lock_bytes).hexdigest()
    )
    (directory / prereq.LOCK_NAME).write_bytes(lock_bytes)
    receipt = {
        "kind": "runtime",
        "package_count": prereq.EXPECTED_PACKAGE_COUNT,
        "lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
    }
    (directory / prereq.RECEIPT_NAME).write_text(json.dumps(receipt), encoding="utf-8")
    (directory / prereq.POLICY_NAME).write_text(json.dumps({
        "schema_version": 1,
        "mode": "locked-ubuntu-debs",
        "target": {"os_id": "ubuntu", "version_id": "24.04", "architecture": "amd64"},
        "root_package": prereq.EXPECTED_ROOT,
        "package_count": prereq.EXPECTED_PACKAGE_COUNT,
        "lock_file": prereq.LOCK_NAME,
        "receipt_file": prereq.RECEIPT_NAME,
        "build_supplement": {
            "lock_file": f"build-supplement/{prereq.SUPPLEMENT_LOCK_NAME}",
            "receipt_file": "build-supplement/staging-receipt.json",
            "package_count": 2,
            "install_condition": "only when libc6-dev is already installed",
        },
    }), encoding="utf-8")
    return root, expected


def _query_output(expected: dict[str, tuple[str, str]]) -> str:
    return "".join(
        f"{name}\t{version}\t{arch}\tinstalled\n"
        for name, (version, arch) in sorted(expected.items())
    )


def _supplement(root: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, tuple[str, str]]:
    payload = root / prereq.POSTGRESQL_PAYLOAD / "build-supplement"
    payload.mkdir(parents=True)
    packages = [
        {"Package": name, "Version": "2.39-0ubuntu8.9", "Architecture": "amd64"}
        for name in ("libc-dev-bin", "libc6-dev")
    ]
    lock = {
        "kind": "build-only-compatibility-supplement",
        "root": prereq.EXPECTED_SUPPLEMENT_ROOT,
        "package_count": 2,
        "packages": packages,
    }
    data = (json.dumps(lock, sort_keys=True) + "\n").encode()
    monkeypatch.setattr(prereq, "EXPECTED_SUPPLEMENT_LOCK_SHA256", hashlib.sha256(data).hexdigest())
    (payload / prereq.SUPPLEMENT_LOCK_NAME).write_bytes(data)
    receipt = {
        "kind": "build-supplement", "package_count": 2,
        "lock_sha256": hashlib.sha256(data).hexdigest(),
    }
    (payload / "staging-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    return {item["Package"]: (item["Version"], item["Architecture"]) for item in packages}


def test_exact_os_and_package_versions_pass_with_bounded_metadata_queries(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    root, expected = _bundle(tmp_path, monkeypatch)
    release = tmp_path / "os-release"
    release.write_text('ID=ubuntu\nVERSION_ID="24.04"\n', encoding="utf-8")
    calls = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        if args[0] == "dpkg":
            return SimpleNamespace(returncode=0, stdout="amd64\n", stderr="")
        return SimpleNamespace(
            returncode=0,
            stdout=_query_output(expected),
            stderr="",
        )

    prereq.verify_postgresql_os_runtime(root, os_release_path=release, runner=runner)

    assert [call[0][0] for call in calls] == ["dpkg", "dpkg-query", "dpkg-query"]
    assert calls[0][1]["timeout"] <= 5
    assert calls[1][1]["timeout"] <= 15


def test_dev_host_requires_exact_optional_build_supplement(tmp_path, monkeypatch):
    root, expected = _bundle(tmp_path, monkeypatch)
    expected.update(_supplement(root, monkeypatch))
    release = tmp_path / "os-release"
    release.write_text("ID=ubuntu\nVERSION_ID=24.04\n", encoding="utf-8")
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        if args[0] == "dpkg":
            return SimpleNamespace(returncode=0, stdout="amd64\n", stderr="")
        if len(args) == 4 and args[1] == "--show" and "libc6-dev" in args:
            return SimpleNamespace(returncode=0, stdout="installed\n", stderr="")
        return SimpleNamespace(returncode=0, stdout=_query_output(expected), stderr="")

    prereq.verify_postgresql_os_runtime(root, os_release_path=release, runner=runner)
    assert {"libc-dev-bin", "libc6-dev"}.issubset(set(calls[-1]))


def test_dev_host_rejects_missing_supplement_receipt(tmp_path, monkeypatch):
    root, _expected = _bundle(tmp_path, monkeypatch)
    _supplement(root, monkeypatch)
    (root / prereq.POSTGRESQL_PAYLOAD / "build-supplement" / "staging-receipt.json").unlink()
    release = tmp_path / "os-release"
    release.write_text("ID=ubuntu\nVERSION_ID=24.04\n", encoding="utf-8")

    def runner(args, **_kwargs):
        if args[0] == "dpkg":
            return SimpleNamespace(returncode=0, stdout="amd64\n", stderr="")
        if len(args) == 4 and args[1] == "--show" and "libc6-dev" in args:
            return SimpleNamespace(returncode=0, stdout="installed\n", stderr="")
        pytest.fail("package version query must not run after supplement receipt failure")

    with pytest.raises(prereq.PostgreSQLPrerequisiteError, match="receipt"):
        prereq.verify_postgresql_os_runtime(root, os_release_path=release, runner=runner)


def test_wrong_os_and_architecture_fail_before_dpkg_query(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    root, _expected = _bundle(tmp_path, monkeypatch)
    release = tmp_path / "os-release"
    release.write_text("ID=debian\nVERSION_ID=13\n", encoding="utf-8")

    def forbidden_runner(*_args, **_kwargs):
        pytest.fail("wrong platform must reject before package queries")

    with pytest.raises(prereq.PostgreSQLPrerequisiteError, match="Ubuntu 24.04 amd64 only"):
        prereq.verify_postgresql_os_runtime(root, os_release_path=release, runner=forbidden_runner)

    release.write_text("ID=ubuntu\nVERSION_ID=24.04\n", encoding="utf-8")
    with pytest.raises(prereq.PostgreSQLPrerequisiteError, match="amd64 only"):
        prereq.verify_postgresql_os_runtime(
            root,
            os_release_path=release,
            architecture="arm64",
            runner=forbidden_runner,
        )


def test_missing_or_drifted_package_is_actionable(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    root, expected = _bundle(tmp_path, monkeypatch)
    release = tmp_path / "os-release"
    release.write_text("ID=ubuntu\nVERSION_ID=24.04\n", encoding="utf-8")
    expected["libpq5"] = ("16.15-0ubuntu0.24.04.1", "amd64")
    output = _query_output(expected).replace("libpq5\t16.15-0ubuntu0.24.04.1", "libpq5\t16.14-0ubuntu0.24.04.1")
    runner = lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=output, stderr="")

    with pytest.raises(prereq.PostgreSQLPrerequisiteError, match="libpq5 needs"):
        prereq.verify_postgresql_os_runtime(root, os_release_path=release, architecture="amd64", runner=runner)


def test_modified_lock_is_rejected_before_platform_package_query(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    root, _expected = _bundle(tmp_path, monkeypatch)
    lock_path = root / prereq.POSTGRESQL_PAYLOAD / prereq.LOCK_NAME
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["packages"][0]["Version"] = "16.14-0ubuntu0.24.04.1"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")

    def forbidden_runner(*_args, **_kwargs):
        pytest.fail("tampered lock must reject before package queries")

    with pytest.raises(prereq.PostgreSQLPrerequisiteError, match="differs from the reviewed Noble"):
        prereq.verify_postgresql_os_runtime(root, runner=forbidden_runner)


def test_missing_bundle_prerequisite_rejects_postgresql_before_runtime_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path / "missing-bundle"))
    monkeypatch.setenv("SASL_PATH", "/host/sasl")
    monkeypatch.setenv("PSYCOPG_IMPL", "binary")
    runtime_root = tmp_path / "runtime"

    with pytest.raises(prereq.PostgreSQLPrerequisiteError, match="runtime policy is not a regular file"):
        configure_postgresql_runtime(
            "postgresql://db.example/service", runtime_root=runtime_root
        )

    assert os.environ["SASL_PATH"] == "/host/sasl"
    assert os.environ["PSYCOPG_IMPL"] == "binary"
    assert not runtime_root.exists()


def test_sqlite_does_not_require_frozen_postgresql_prerequisites(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path / "no-metadata"))

    assert configure_postgresql_runtime("sqlite:///state.db") is None


def test_core_bundle_policy_rejects_postgresql(tmp_path: Path):
    root = tmp_path / "bundle"
    directory = root / prereq.POSTGRESQL_PAYLOAD
    directory.mkdir(parents=True)
    (directory / prereq.POLICY_NAME).write_text(
        json.dumps({"schema_version": 1, "mode": "disabled"}), encoding="utf-8"
    )

    with pytest.raises(prereq.PostgreSQLPrerequisiteError, match="SQLite-only bundle"):
        prereq.verify_postgresql_os_runtime(root)
