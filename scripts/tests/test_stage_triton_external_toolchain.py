"""Safety and provenance tests for private Triton toolchain staging."""

from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from scripts import stage_triton_external_toolchain as stage


def _tar(path: Path, members: list[tuple[str, bytes, str]]) -> None:
    with tarfile.open(path, "w:xz") as archive:
        for name, content, kind in members:
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "target"
                archive.addfile(info)


def _pin(data: bytes) -> dict[str, object]:
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def test_archive_members_are_checked_and_staged_as_regular_files(tmp_path: Path):
    payload = b"reviewed input bytes"
    source = tmp_path / "fixture.tar.xz"
    _tar(source, [("root/bin/ptxas", payload, "file")])
    output = tmp_path / "private/bin/ptxas"

    receipt = stage._copy_tar_member(
        source, "root/bin/ptxas", output, _pin(payload), executable=True
    )

    assert output.read_bytes() == payload
    assert output.stat().st_mode & 0o111
    assert receipt["sha256"] == hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize(
    "name",
    ["/absolute", "root/../escape", "root/./escape", "root//empty", "root\\escape"],
)
def test_noncanonical_archive_paths_are_rejected(name: str):
    assert not stage._safe_member_name(name)


def test_symlink_and_duplicate_archive_members_are_rejected(tmp_path: Path):
    source = tmp_path / "unsafe.tar.xz"
    _tar(source, [("root/bin/tool", b"", "symlink")])
    with pytest.raises(stage.StageError, match="safe regular file"):
        stage._copy_tar_member(source, "root/bin/tool", tmp_path / "out", _pin(b""))

    duplicate = tmp_path / "duplicate.tar.xz"
    _tar(duplicate, [
        ("root/bin/tool", b"first", "file"),
        ("root/bin/tool", b"other", "file"),
    ])
    with pytest.raises(stage.StageError, match="missing or duplicated"):
        stage._copy_tar_member(duplicate, "root/bin/tool", tmp_path / "out", _pin(b"first"))


def test_member_digest_mismatch_removes_partial_staged_file(tmp_path: Path):
    source = tmp_path / "fixture.tar.xz"
    _tar(source, [("root/include/cuda.h", b"changed header", "file")])
    output = tmp_path / "private/include/cuda.h"

    with pytest.raises(stage.StageError, match="hash differs"):
        stage._copy_tar_member(
            source,
            "root/include/cuda.h",
            output,
            {"sha256": "0" * 64, "size_bytes": len(b"changed header")},
        )
    assert not output.exists()


def test_archive_license_is_preserved_with_derived_hash_and_size(tmp_path: Path):
    license_text = b"NVIDIA archive license fixture\n"
    source = tmp_path / "official.tar.xz"
    _tar(source, [("component-1.0/LICENSE", license_text, "file")])
    output = tmp_path / "private/share/licenses/LICENSE.txt"

    receipt = stage._copy_archive_license(
        source, "component-1.0/LICENSE", output
    )

    assert output.read_bytes() == license_text
    assert receipt["sha256"] == hashlib.sha256(license_text).hexdigest()
    assert receipt["size_bytes"] == len(license_text)


def test_reviewed_notice_requires_hash_and_records_official_source_url(
    tmp_path: Path,
):
    notice = tmp_path / "EULA.txt"
    notice.write_bytes(b"reviewed NVIDIA EULA fixture\n")
    output = tmp_path / "private/EULA.txt"
    expected_hash = hashlib.sha256(notice.read_bytes()).hexdigest()

    receipt = stage._copy_notice(
        notice,
        output,
        expected_hash,
        "https://docs.nvidia.com/cuda/archive/13.1.1/pdf/EULA.pdf",
    )

    assert receipt["official_source_url"].endswith("EULA.pdf")
    assert receipt["sha256"] == expected_hash
    with pytest.raises(stage.StageError, match="document changed"):
        stage._copy_notice(
            notice,
            tmp_path / "private/bad-EULA.txt",
            "0" * 64,
            "https://docs.nvidia.com/cuda/archive/13.1.1/pdf/EULA.pdf",
        )


def test_existing_destination_is_never_overwritten(tmp_path: Path):
    existing = tmp_path / "already-there"
    existing.mkdir()
    with pytest.raises(stage.StageError, match="private AIRunner cache or /tmp"):
        stage._allowed_private_path(Path("/etc"))
    with pytest.raises(stage.StageError, match="refusing to overwrite"):
        stage.stage_external_toolchain(existing)
    assert existing.is_dir()


def test_user_scoped_airunner_cache_is_an_allowed_destination():
    target = Path.home() / ".cache" / "airunner" / "triton" / "external"
    assert stage._allowed_private_path(target) == target.resolve()


def test_reviewed_nvidia_publisher_archive_pins_are_exact():
    assert stage.REDISTRIBUTIONS["12.8.1"]["sha256"] == (
        "249e28a83008d711d5f72880541c8be6253f6d61608461de4fcb715554a6cf17"
    )
    assert stage.ARCHIVES[("13.1.0", "cuda_nvcc")]["sha256"] == (
        "5ed3b7cfe7f12557199773e7769445357ee048958ff51e623e15f36d3393ca8b"
    )
