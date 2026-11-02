from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

import pytest

from scripts.build_triton_external_toolchain_subset import WheelError, build_candidate


MANIFEST_PATH = Path(__file__).resolve().parents[2] / "package" / "triton-external-toolchain-subset.json"


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_source_wheel(path: Path, files: dict[str, bytes]) -> None:
    dist_info = "triton-3.7.1+capsize.1.dist-info"
    record_name = f"{dist_info}/RECORD"
    rows = []
    for name, content in sorted(files.items()):
        encoded = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip("=")
        rows.append((name, f"sha256={encoded}", str(len(content))))
    rows.append((record_name, "", ""))
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    files[record_name] = buffer.getvalue().encode()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)


def _fixture(tmp_path: Path) -> tuple[dict, Path, bytes]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    ptxas = b"unredistributable source-member fixture"
    libdevice = b"explicitly permitted libdevice fixture"
    files = {
        "triton-3.7.1+capsize.1.dist-info/METADATA": b"Metadata-Version: 2.4\nName: triton\nVersion: 3.7.1+capsize.1\n",
        "triton-3.7.1+capsize.1.dist-info/WHEEL": b"Wheel-Version: 1.0\nTag: py3-none-any\n",
        "triton/backends/nvidia/bin/ptxas": ptxas,
        "triton/backends/nvidia/lib/libdevice.10.bc": libdevice,
        "triton/core.py": b"compile-time feature remains\n",
    }
    source = tmp_path / "input.whl"
    _write_source_wheel(source, files)
    manifest["source"]["hardening_candidate"]["filename"] = source.name
    manifest["source"]["hardening_candidate"]["sha256"] = _hash(source.read_bytes())
    manifest["subset"]["exclude_members"] = [
        {"path": "triton/backends/nvidia/bin/ptxas", "sha256": _hash(ptxas), "size_bytes": len(ptxas)}
    ]
    manifest["subset"]["retain_members"] = [
        {
            "path": "triton/backends/nvidia/lib/libdevice.10.bc",
            "sha256": _hash(libdevice),
            "size_bytes": len(libdevice),
        }
    ]
    return manifest, source, libdevice


def _output_path(tmp_path: Path, manifest: dict, folder: str = "out") -> Path:
    output_dir = tmp_path / folder
    output_dir.mkdir()
    return output_dir / manifest["subset"]["output_filename"]


def test_subset_preserves_jit_payload_metadata_and_valid_record(tmp_path: Path) -> None:
    manifest, source, expected_libdevice = _fixture(tmp_path)
    output = _output_path(tmp_path, manifest)

    receipt = build_candidate(source, output, manifest)

    assert receipt["record_verified"] is True
    assert receipt["zip_crc_verified"] is True
    assert receipt["excluded_members"] == 1
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "triton/backends/nvidia/bin/ptxas" not in names
        assert archive.read("triton/backends/nvidia/lib/libdevice.10.bc") == expected_libdevice
        assert archive.read("triton/core.py") == b"compile-time feature remains\n"
        metadata = archive.read("triton-3.7.1+capsize.2.dist-info/METADATA")
        assert b"Version: 3.7.1+capsize.2\n" in metadata
        assert "triton-3.7.1+capsize.2.dist-info/RECORD" in names


def test_subset_output_is_deterministic_from_the_same_input(tmp_path: Path) -> None:
    manifest, source, _ = _fixture(tmp_path)
    first = _output_path(tmp_path, manifest, "out-a")
    second = _output_path(tmp_path, manifest, "out-b")

    build_candidate(source, first, manifest)
    build_candidate(source, second, manifest)

    assert _hash(first.read_bytes()) == _hash(second.read_bytes())


def test_changed_excluded_member_fails_before_output(tmp_path: Path) -> None:
    manifest, source, _ = _fixture(tmp_path)
    files = {}
    with zipfile.ZipFile(source) as archive:
        files = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/RECORD")}
    files["triton/backends/nvidia/bin/ptxas"] = b"different tool bytes"
    changed = tmp_path / "changed.whl"
    _write_source_wheel(changed, files)
    manifest["source"]["hardening_candidate"]["filename"] = changed.name
    manifest["source"]["hardening_candidate"]["sha256"] = _hash(changed.read_bytes())
    output = _output_path(tmp_path, manifest)

    with pytest.raises(WheelError, match="pinned excluded member bytes changed"):
        build_candidate(changed, output, manifest)
    assert not output.exists()


def test_invalid_source_record_fails_closed(tmp_path: Path) -> None:
    manifest, source, _ = _fixture(tmp_path)
    with zipfile.ZipFile(source) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    files["triton-3.7.1+capsize.1.dist-info/METADATA"] = b"changed without updating RECORD\n"
    broken = tmp_path / "broken.whl"
    with zipfile.ZipFile(broken, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    manifest["source"]["hardening_candidate"]["filename"] = broken.name
    manifest["source"]["hardening_candidate"]["sha256"] = _hash(broken.read_bytes())
    output = _output_path(tmp_path, manifest)

    with pytest.raises(WheelError, match="wheel RECORD does not match"):
        build_candidate(broken, output, manifest)


def test_pinned_output_digest_is_enforced(tmp_path: Path) -> None:
    manifest, source, _ = _fixture(tmp_path)
    output = _output_path(tmp_path, manifest)

    with pytest.raises(WheelError, match="differs from the pinned output"):
        build_candidate(source, output, manifest, expected_output_sha256="0" * 64)
    assert not output.exists()


@pytest.mark.parametrize("bad_name", ["triton//alias.py", "triton/./alias.py"])
def test_noncanonical_paths_are_rejected_before_output(tmp_path: Path, bad_name: str) -> None:
    manifest, source, _ = _fixture(tmp_path)
    with zipfile.ZipFile(source) as archive:
        files = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/RECORD")}
    files[bad_name] = b"noncanonical member"
    changed = tmp_path / "noncanonical.whl"
    _write_source_wheel(changed, files)
    manifest["source"]["hardening_candidate"].update(
        filename=changed.name, sha256=_hash(changed.read_bytes())
    )
    output = _output_path(tmp_path, manifest)
    with pytest.raises(WheelError, match="unsafe member path"):
        build_candidate(changed, output, manifest)
    assert not output.exists()


def test_concurrently_created_output_is_not_overwritten_or_deleted(tmp_path: Path, monkeypatch) -> None:
    manifest, source, _ = _fixture(tmp_path)
    output = _output_path(tmp_path, manifest)
    original_link = os.link

    def race_link(source_path, destination_path):
        Path(destination_path).write_bytes(b"concurrent owner artifact")
        original_link(source_path, destination_path)

    monkeypatch.setattr(os, "link", race_link)
    with pytest.raises(FileExistsError):
        build_candidate(source, output, manifest)
    assert output.read_bytes() == b"concurrent owner artifact"
    assert not list(output.parent.glob("*.tmp"))
