"""Focused safety tests for the eSpeak native build preparer."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
from types import SimpleNamespace

import pytest

from scripts import prepare_espeak_native_payload as prepare


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _cmake_tar(path: Path, binary: bytes = b"cmake synthetic binary\n") -> str:
    member_name = f"{prepare.CMAKE_ROOT}/bin/cmake"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo(member_name)
        info.mode = 0o755
        info.size = len(binary)
        import io

        archive.addfile(info, io.BytesIO(binary))
    return _sha(binary)


def test_cmake_archive_hash_rejected_before_tar_inspection_or_extraction(tmp_path, monkeypatch):
    archive = tmp_path / "cmake-3.31.6-linux-x86_64.tar.gz"
    archive.write_bytes(b"tampered input")
    destination = tmp_path / "unpacked"
    tar_open = tarfile.open
    monkeypatch.setattr(tarfile, "open", lambda *args, **kwargs: pytest.fail("archive inspected before hash check"))

    with pytest.raises(prepare.PreparationError, match="archive SHA-256"):
        prepare.verify_and_extract_cmake(
            archive, destination, expected_archive_sha256="0" * 64
        )

    assert not destination.exists()
    monkeypatch.setattr(tarfile, "open", tar_open)


def test_cmake_binary_hash_rejected_before_any_extraction(tmp_path, monkeypatch):
    archive_path = tmp_path / "cmake.tar.gz"
    binary_hash = _cmake_tar(archive_path)
    destination = tmp_path / "unpacked"
    monkeypatch.setattr(
        tarfile.TarFile,
        "extractall",
        lambda *args, **kwargs: pytest.fail("archive extracted before binary hash check"),
    )

    with pytest.raises(prepare.PreparationError, match="executable SHA-256"):
        prepare.verify_and_extract_cmake(
            archive_path,
            destination,
            expected_archive_sha256=_sha(archive_path.read_bytes()),
            expected_binary_sha256="f" * 64,
        )

    assert not destination.exists()
    assert binary_hash != "f" * 64


def test_cmake_archive_and_binary_hashes_pass_before_safe_extraction(tmp_path):
    archive_path = tmp_path / "cmake.tar.gz"
    binary = b"synthetic cmake tool"
    binary_hash = _cmake_tar(archive_path, binary)
    destination = tmp_path / "unpacked"

    root = prepare.verify_and_extract_cmake(
        archive_path,
        destination,
        expected_archive_sha256=_sha(archive_path.read_bytes()),
        expected_binary_sha256=binary_hash,
    )

    assert (root / "bin/cmake").read_bytes() == binary


def test_work_directory_must_be_new_and_existing_data_is_preserved(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "keep.txt"
    marker.write_text("keep")

    with pytest.raises(prepare.PreparationError, match="must not already exist"):
        prepare._new_private_work_dir(existing)

    assert marker.read_text() == "keep"


def test_docker_command_is_pinned_isolated_and_only_output_is_writable(tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshot"
    (snapshot / "scripts").mkdir(parents=True)
    (snapshot / "packaging/espeak").mkdir(parents=True)
    cmake = tmp_path / "cmake"
    (cmake / "bin").mkdir(parents=True)
    python = tmp_path / "python"
    (python / "bin").mkdir(parents=True)
    executable = python / "bin/python3.13"
    executable.write_bytes(b"python")
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"archive")
    output = tmp_path / "out"
    output.mkdir()
    cidfile = tmp_path / "container.cid"
    monkeypatch.setattr(prepare.platform, "machine", lambda: "x86_64")

    command = prepare.docker_command(
        image=prepare.BUILD_IMAGE,
        source_snapshot=snapshot,
        cmake_prefix=cmake,
        python_prefix=python,
        source_archive=archive,
        output_dir=output,
        cidfile=cidfile,
    )

    for flag in ("--runtime=runc", "--network=none", "--read-only", "--cpus=2", "--memory=4g"):
        assert flag in command
    assert prepare.BUILD_IMAGE in command
    assert "--gpus" not in command
    mounts = [command[index + 1] for index, item in enumerate(command[:-1]) if item == "--mount"]
    assert any("dst=/out" in mount and not mount.endswith(",readonly") for mount in mounts)
    assert all(
        mount.endswith(",readonly")
        for mount in mounts
        if "dst=/out" not in mount
    )
    assert "CUDA_VISIBLE_DEVICES=" in command


def test_container_cleanup_stops_only_recorded_container_and_confirms_absence(tmp_path, monkeypatch):
    cid = "a" * 64
    cidfile = tmp_path / "container.cid"
    cidfile.write_text(cid)
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[1:3] == ["inspect", "--format"]:
            return SimpleNamespace(returncode=0, stdout="true\n", stderr="")
        if command[1:3] == ["rm", "--force"]:
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"Error: No such object: " + cid.encode())

    monkeypatch.setattr(prepare.subprocess, "run", fake_run)

    actual_cid, absent = prepare._container_cleanup(cidfile)

    assert actual_cid == cid
    assert absent is True
    assert calls == [
        ["docker", "inspect", "--format", "{{.State.Running}}", cid],
        ["docker", "rm", "--force", cid],
        ["docker", "inspect", cid],
    ]


def test_invalid_container_id_does_not_run_docker(tmp_path, monkeypatch):
    cidfile = tmp_path / "container.cid"
    cidfile.write_text("not-a-container-id")
    monkeypatch.setattr(prepare.subprocess, "run", lambda *args, **kwargs: pytest.fail("unexpected Docker call"))

    with pytest.raises(prepare.PreparationError, match="invalid container ID"):
        prepare._container_cleanup(cidfile)


def test_stopped_container_is_also_removed_by_exact_id(tmp_path, monkeypatch):
    cid = "b" * 64
    cidfile = tmp_path / "container.cid"
    cidfile.write_text(cid)
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[1:3] == ["inspect", "--format"]:
            return SimpleNamespace(returncode=0, stdout="false\n", stderr="")
        if command[1:3] == ["rm", "--force"]:
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"Error: No such object")

    monkeypatch.setattr(prepare.subprocess, "run", fake_run)

    actual_cid, absent = prepare._container_cleanup(cidfile)

    assert actual_cid == cid
    assert absent is True
    assert calls[1] == ["docker", "rm", "--force", cid]


def test_build_timeout_kills_owned_process_group(tmp_path, monkeypatch):
    process = SimpleNamespace(pid=4242, wait=lambda **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("docker", 3)))
    monkeypatch.setattr(prepare.subprocess, "Popen", lambda *args, **kwargs: process)
    killed: list[int] = []
    monkeypatch.setattr(prepare, "_kill_group", lambda owned: killed.append(owned.pid))

    with pytest.raises(prepare.PreparationError, match="timeout"):
        prepare._run_build(["docker", "run"], tmp_path / "build.log", 3)

    assert killed == [4242]


def test_cmake_verification_failure_in_prepare_prevents_build_launch(tmp_path, monkeypatch):
    work_parent = tmp_path / "work"
    archive = tmp_path / "cmake-3.31.6-linux-x86_64.tar.gz"
    archive.write_bytes(b"tampered cmake archive")
    python_prefix = tmp_path / "python"
    (python_prefix / "bin").mkdir(parents=True)
    executable = python_prefix / "bin/python3.13"
    executable.write_bytes(b"python")
    executable.chmod(0o755)
    locked_source = b"synthetic eSpeak archive"

    def fake_snapshot(work):
        snapshot = work / "source-snapshot"
        (snapshot / "packaging/espeak").mkdir(parents=True)
        lock = {
            "upstream": {
                "commit": "a" * 40,
                "tree": "b" * 40,
                "canonical_project": "https://github.com/espeak-ng/espeak-ng",
            },
            "source_archive": {
                "filename": "espeak-ng-1.52.0-4870adf.tar.gz",
                "sha256": _sha(locked_source),
                "size_bytes": len(locked_source),
            },
        }
        (snapshot / "packaging/espeak/source-lock.json").write_text(json.dumps(lock))
        return snapshot, "c" * 40, {"input": "d" * 64}

    def fake_intake(snapshot, git_dir, archive_dir, archive_filename):
        archive_dir.mkdir(parents=True)
        source_archive = archive_dir / archive_filename
        source_archive.write_bytes(locked_source)
        return source_archive

    monkeypatch.setattr(prepare, "_snapshot_committed_inputs", fake_snapshot)
    monkeypatch.setattr(prepare, "_private_git_dir", lambda path: Path("/private/mirror.git"))
    monkeypatch.setattr(prepare, "_git_output", lambda _mirror, *args: "commit" if args[0] == "cat-file" else "b" * 40)
    monkeypatch.setattr(prepare, "_run_intake", fake_intake)

    def reject_cmake(path, destination):
        raise prepare.PreparationError("CMake archive SHA-256 does not match the reviewed pin")

    monkeypatch.setattr(prepare, "verify_and_extract_cmake", reject_cmake)
    monkeypatch.setattr(prepare, "_run_build", lambda *args, **kwargs: pytest.fail("Docker build was launched"))
    args = SimpleNamespace(
        work_dir=work_parent,
        fetch_canonical=False,
        git_dir=tmp_path / "mirror.git",
        download_cmake=False,
        cmake_archive=archive,
        python_base_prefix=python_prefix,
        timeout_seconds=30,
    )

    with pytest.raises(prepare.PreparationError, match="archive SHA-256"):
        prepare.prepare(args)

    assert work_parent.is_dir()
    assert not (work_parent / "container.cid").exists()
