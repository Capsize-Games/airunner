"""Tests for explicit vendor-document license supplements."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    import dependency_notices
    import vendor_notice_supplements
finally:
    sys.path.remove(str(SCRIPTS))


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _locked(
    name: str = "cuda-toolkit",
    version: str = "12.9.1",
    wheel_hash: str | None = None,
):
    digest = wheel_hash or _sha(b"selected wheel")
    return dependency_notices.LockedDistribution(
        name=name,
        normalized_name=name.replace("_", "-").lower(),
        version=version,
        hashes=(digest,),
    )


def _document(
    repo: Path,
    *,
    folder: str = "cuda-toolkit-12.9.1-supplement",
    publisher: str = "NVIDIA Corporation",
    product: str = "CUDA Toolkit meta-package",
    release_scope: str = "CUDA Toolkit EULA, Release 12.9 applies to 12.9.1.",
    url: str = "https://docs.nvidia.com/cuda/archive/12.9.1/pdf/EULA.pdf",
    document_name: str = "EULA.pdf",
    document: bytes = b"%PDF-1.7 original vendor document\n",
    text_name: str = "EULA.txt",
    text: bytes = b"Extracted vendor license text\n",
):
    source_dir = repo / "packaging" / "licenses" / folder
    source_dir.mkdir(parents=True, exist_ok=True)
    document_path = source_dir / document_name
    text_path = source_dir / text_name
    document_path.write_bytes(document)
    text_path.write_bytes(text)
    wheel_hash = _sha(b"selected wheel")
    manifest = {
        "distribution": "cuda-toolkit",
        "version": "12.9.1",
        "exact_pin": "cuda-toolkit==12.9.1",
        "selected_wheel_sha256": wheel_hash,
        "vendor_document": {
            "publisher": publisher,
            "product": product,
            "release_scope": release_scope,
            "official_source_url": url,
            "retrieved_date": "2026-11-02",
            "document_path": document_path.relative_to(repo).as_posix(),
            "document_sha256": _sha(document),
            "document_size_bytes": len(document),
            "text_path": text_path.relative_to(repo).as_posix(),
            "text_sha256": _sha(text),
            "text_size_bytes": len(text),
        },
    }
    manifest_path = source_dir / "vendor-license.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    spec = {
        "dependency_notices": {
            "vendor_supplements": [manifest_path.relative_to(repo).as_posix()]
        }
    }
    return repo, manifest_path, document_path, text_path, manifest, spec, wheel_hash


def _load(repo: Path, spec: dict, packages, *, dest: str = "legal/dependencies"):
    return vendor_notice_supplements.load_vendor_notice_supplements(
        spec, repo, packages, dest
    )


def test_loads_exact_archived_nccl_binary_sla(tmp_path: Path) -> None:
    url = (
        "https://docs.nvidia.com/deeplearning/nccl/archives/"
        "nccl_2297/pdf/NCCL-SLA.pdf"
    )
    repo, _manifest, _document_path, _text_path, _data, spec, wheel_hash = (
        _document(tmp_path, url=url)
    )
    result = _load(repo, spec, [_locked(wheel_hash=wheel_hash)])
    records, files = result["cuda-toolkit==12.9.1"]
    assert len(files) == 2
    assert all(record["vendor_document"]["official_source_url"] == url for record in records)


@pytest.mark.parametrize("path", [
    "/deeplearning/nccl/latest/pdf/NCCL-SLA.pdf",
    "/deeplearning/nccl/archives/nccl_2297/pdf/other.pdf",
    "/unreviewed/NCCL-SLA.pdf",
])
def test_rejects_other_nvidia_document_paths(path: str) -> None:
    with pytest.raises(vendor_notice_supplements.VendorNoticeSupplementError):
        vendor_notice_supplements._official_url("https://docs.nvidia.com" + path)


def test_loads_both_vendor_document_and_extracted_text_with_provenance(
    tmp_path: Path,
) -> None:
    repo, manifest_path, document_path, text_path, manifest, spec, wheel_hash = (
        _document(tmp_path)
    )

    result = _load(repo, spec, [_locked(wheel_hash=wheel_hash)])

    assert list(result) == ["cuda-toolkit==12.9.1"]
    records, files = result["cuda-toolkit==12.9.1"]
    assert files == [
        (
            "legal/dependencies/cuda-toolkit-12.9.1/vendor-supplements/EULA.pdf",
            document_path.read_bytes(),
        ),
        (
            "legal/dependencies/cuda-toolkit-12.9.1/vendor-supplements/EULA.txt",
            text_path.read_bytes(),
        ),
    ]
    assert [record["provenance"] for record in records] == [
        "reviewed-vendor-license-supplement",
        "reviewed-vendor-license-supplement",
    ]
    assert records[0]["vendor_document"]["official_source_url"] == manifest[
        "vendor_document"
    ]["official_source_url"]
    assert records[0]["vendor_document"]["document_sha256"] == manifest[
        "vendor_document"
    ]["document_sha256"]
    assert records[1]["vendor_document"]["text_sha256"] == manifest[
        "vendor_document"
    ]["text_sha256"]
    assert records[0]["manifest_sha256"] == _sha(manifest_path.read_bytes())
    assert all("record_hash" not in record for record in records)


def test_same_original_plain_text_file_is_emitted_once_with_both_roles(
    tmp_path: Path,
) -> None:
    license_bytes = b"Original NVSHMEM License.txt\n"
    repo, _manifest_path, _document_path, _text_path, manifest, spec, wheel_hash = (
        _document(
            tmp_path,
            folder="nvshmem",
            product="NVIDIA NVSHMEM SDK",
            release_scope="NVSHMEM source release v3.4.5-0.",
            url=(
                "https://github.com/NVIDIA/nvshmem/blob/"
                "131da55f643ac87c810ba0bc51d359258bf433a1/License.txt"
            ),
            document_name="License.txt",
            document=license_bytes,
            text_name="License.txt",
            text=license_bytes,
        )
    )
    doc = manifest["vendor_document"]
    doc["text_path"] = doc["document_path"]
    doc["text_sha256"] = doc["document_sha256"]
    doc["text_size_bytes"] = doc["document_size_bytes"]
    (_manifest_path).write_text(json.dumps(manifest), encoding="utf-8")

    result = _load(repo, spec, [_locked(wheel_hash=wheel_hash)])

    records, files = result["cuda-toolkit==12.9.1"]
    assert len(files) == 1
    assert files[0][1] == license_bytes
    assert records[0]["content_role"] == [
        "original_vendor_document",
        "extracted_text",
    ]


def test_supports_multiple_distinct_vendor_documents(tmp_path: Path) -> None:
    repo, manifest_path, _document_path, _text_path, manifest, spec, wheel_hash = (
        _document(tmp_path)
    )
    second_dir = manifest_path.parent
    second_doc = second_dir / "LICENSE.txt"
    second_text = second_dir / "LICENSE-extracted.txt"
    second_doc.write_bytes(b"Apache source license\n")
    second_text.write_bytes(b"Apache source license\n")
    original = manifest.pop("vendor_document")
    original["official_source_url"] = (
        "https://github.com/NVIDIA/nccl/blob/"
        "0123456789abcdef0123456789abcdef01234567/LICENSE.txt"
    )
    second = {
        **original,
        "product": "NVIDIA NCCL source release",
        "release_scope": "NCCL source release v2.29.7-1 Apache license.",
        "official_source_url": (
            "https://github.com/NVIDIA/nccl/blob/"
            "0123456789abcdef0123456789abcdef01234567/ThirdPartyNotices.txt"
        ),
        "document_path": second_doc.relative_to(repo).as_posix(),
        "document_sha256": _sha(second_doc.read_bytes()),
        "document_size_bytes": second_doc.stat().st_size,
        "text_path": second_text.relative_to(repo).as_posix(),
        "text_sha256": _sha(second_text.read_bytes()),
        "text_size_bytes": second_text.stat().st_size,
    }
    manifest["vendor_documents"] = [original, second]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = _load(repo, spec, [_locked(wheel_hash=wheel_hash)])

    records, files = result["cuda-toolkit==12.9.1"]
    assert [path.rsplit("/", 1)[1] for path, _ in files] == [
        "01-EULA.pdf",
        "01-EULA.txt",
        "02-LICENSE.txt",
        "02-LICENSE-extracted.txt",
    ]
    source_urls = {
        record["vendor_document"]["official_source_url"] for record in records
    }
    assert len(source_urls) == 2


def test_ignores_unlocked_manifest_but_validates_config_path(tmp_path: Path) -> None:
    repo, manifest_path, *_rest = _document(tmp_path)
    spec = {
        "dependency_notices": {
            "vendor_supplements": [manifest_path.relative_to(repo).as_posix()]
        }
    }

    assert _load(repo, spec, []) == {}
    spec["dependency_notices"]["vendor_supplements"] = ["../outside.json"]
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="traversal"
    ):
        _load(repo, spec, [])


def test_rejects_tampered_original_or_extracted_text(tmp_path: Path) -> None:
    repo, _manifest_path, document_path, _text_path, _manifest, spec, wheel_hash = (
        _document(tmp_path)
    )
    document_path.write_bytes(b"tampered original\n")
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="document differs"
    ):
        _load(repo, spec, [_locked(wheel_hash=wheel_hash)])

    repo, _manifest_path, _document_path, text_path, _manifest, spec, wheel_hash = (
        _document(tmp_path / "second")
    )
    text_path.write_bytes(b"tampered text\n")
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="text differs"
    ):
        _load(repo, spec, [_locked(wheel_hash=wheel_hash)])


def test_rejects_unselected_wheel_hash_and_wrong_version(tmp_path: Path) -> None:
    repo, _manifest_path, *_rest, wheel_hash = _document(tmp_path)
    spec = {
        "dependency_notices": {
            "vendor_supplements": [
                "packaging/licenses/cuda-toolkit-12.9.1-supplement/vendor-license.json"
            ]
        }
    }
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="wheel hash"
    ):
        _load(repo, spec, [_locked(wheel_hash=_sha(b"other"))])
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="version differs"
    ):
        _load(repo, spec, [_locked(version="12.8.0", wheel_hash=wheel_hash)])


@pytest.mark.parametrize(
    "url",
    [
        "http://docs.nvidia.com/cuda/archive/12.9/EULA.pdf",
        "https://docs.nvidia.com/cuda/archive/12.9/EULA.pdf?download=1",
        "https://docs.nvidia.com/cuda/archive/12.9/EULA.pdf?",
        "https://docs.nvidia.com/cuda/archive/12.9/EULA.pdf#page=1",
        "https://docs.nvidia.com/cuda/archive/12.9/EULA.pdf#",
        "https://user@docs.nvidia.com/cuda/archive/12.9/EULA.pdf",
        "https://evil.example/cuda/archive/12.9/EULA.pdf",
        "https://docs.nvidia.com/other/EULA.pdf",
        "https://github.com/other/nvshmem/blob/"
        "131da55f643ac87c810ba0bc51d359258bf433a1/License.txt",
        "https://github.com/NVIDIA/nvshmem/blob/main/License.txt",
        "https://github.com/NVIDIA/nvshmem/blob/"
        "131da55f643ac87c810ba0bc51d359258bf433a1/README.md",
    ],
)
def test_rejects_noncanonical_or_disallowed_urls(tmp_path: Path, url: str) -> None:
    repo, manifest_path, *_rest = _document(tmp_path, url=url)
    spec = {
        "dependency_notices": {
            "vendor_supplements": [manifest_path.relative_to(repo).as_posix()]
        }
    }
    with pytest.raises(vendor_notice_supplements.VendorNoticeSupplementError):
        _load(repo, spec, [])


def test_rejects_symlink_paths_unknown_fields_duplicate_keys_and_bool_size(
    tmp_path: Path,
) -> None:
    repo, manifest_path, document_path, *_rest, wheel_hash = _document(tmp_path)
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(document_path.read_bytes())
    document_path.unlink()
    document_path.symlink_to(outside)
    spec = {
        "dependency_notices": {
            "vendor_supplements": [manifest_path.relative_to(repo).as_posix()]
        }
    }
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="symlink"
    ):
        _load(repo, spec, [_locked(wheel_hash=wheel_hash)])

    document_path.unlink()
    document_path.write_bytes(outside.read_bytes())
    manifest = json.loads(manifest_path.read_text())
    manifest["source_distribution"] = {
        "filename": "invented.tar.gz",
        "sha256": "a" * 64,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="unknown JSON keys"
    ):
        _load(repo, spec, [_locked(wheel_hash=wheel_hash)])

    manifest_path.write_text(
        '{"distribution":"cuda-toolkit","distribution":"cuda-toolkit"}',
        encoding="utf-8",
    )
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="duplicate JSON"
    ):
        _load(repo, spec, [])

    repo, manifest_path, *_rest, wheel_hash = _document(tmp_path / "bool")
    manifest = json.loads(manifest_path.read_text())
    manifest["vendor_document"]["document_size_bytes"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    spec = {
        "dependency_notices": {
            "vendor_supplements": [manifest_path.relative_to(repo).as_posix()]
        }
    }
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="size is invalid"
    ):
        _load(repo, spec, [_locked(wheel_hash=wheel_hash)])


def test_rejects_symlink_manifest_and_traversing_document_path(
    tmp_path: Path,
) -> None:
    repo, manifest_path, _document_path, *_rest, wheel_hash = _document(tmp_path)
    outside = tmp_path / "vendor-manifest.json"
    outside.write_bytes(manifest_path.read_bytes())
    manifest_path.unlink()
    manifest_path.symlink_to(outside)
    spec = {
        "dependency_notices": {
            "vendor_supplements": [manifest_path.relative_to(repo).as_posix()]
        }
    }
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="symlink"
    ):
        _load(repo, spec, [_locked(wheel_hash=wheel_hash)])

    manifest_path.unlink()
    manifest_path.write_bytes(outside.read_bytes())
    manifest = json.loads(manifest_path.read_text())
    manifest["vendor_document"]["document_path"] = "../outside.pdf"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="traversal"
    ):
        _load(repo, spec, [_locked(wheel_hash=wheel_hash)])


def test_rejects_duplicate_vendor_documents_and_oversized_file_claim(
    tmp_path: Path,
) -> None:
    repo, manifest_path, _document_path, *_rest, wheel_hash = _document(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    document = manifest.pop("vendor_document")
    manifest["vendor_documents"] = [document, document]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    spec = {
        "dependency_notices": {
            "vendor_supplements": [manifest_path.relative_to(repo).as_posix()]
        }
    }
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError,
        match="repeats an official source URL",
    ):
        _load(repo, spec, [_locked(wheel_hash=wheel_hash)])

    manifest["vendor_documents"] = [document]
    document["document_size_bytes"] = 33 * 1024 * 1024
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(
        vendor_notice_supplements.VendorNoticeSupplementError, match="size is invalid"
    ):
        _load(repo, spec, [_locked(wheel_hash=wheel_hash)])


@pytest.mark.parametrize(
    "manifest_path",
    [
        "packaging/licenses/cuda-toolkit-12.9.1-supplement/vendor-license.json",
        "packaging/licenses/nvidia-nvshmem-cu12-3.4.5-supplement/vendor-license.json",
        "packaging/licenses/nvidia-nccl-cu12-2.29.7-supplement/vendor-license.json",
    ],
)
def test_loads_staged_nvidia_source_pairs(
    manifest_path: str,
) -> None:
    path = ROOT / manifest_path
    if not path.exists():
        pytest.skip("NVIDIA vendor source files are not present in this checkout")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    package = _locked(
        name=manifest["distribution"],
        version=manifest["version"],
        wheel_hash=manifest["selected_wheel_sha256"],
    )

    result = _load(
        ROOT,
        {"dependency_notices": {"vendor_supplements": [manifest_path]}},
        [package],
    )

    records, files = result[f"{package.normalized_name}=={package.version}"]
    assert records
    assert files
    assert all(
        record["provenance"] == "reviewed-vendor-license-supplement"
        for record in records
    )
    assert all("record_hash" not in record for record in records)
