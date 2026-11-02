"""Validation tests for explicit reviewed source-license supplements."""

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
    import source_notice_supplements
finally:
    sys.path.remove(str(SCRIPTS))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _locked(name: str = "example", version: str = "1.2.3", wheel_sha: str | None = None):
    digest = wheel_sha or _sha(b"selected wheel")
    normalized = name.replace("_", "-").lower()
    return dependency_notices.LockedDistribution(
        name=name,
        normalized_name=normalized,
        version=version,
        hashes=(digest,),
    )


def _fixture(
    tmp_path: Path,
    *,
    package_name: str = "example",
    version: str = "1.2.3",
    file_bytes: bytes = b"Example license text\n",
    file_name: str = "LICENSE",
):
    repo = tmp_path / "repo"
    source_dir = repo / "packaging" / "licenses" / f"{package_name}-{version}-supplement"
    source_dir.mkdir(parents=True)
    source_file = source_dir / file_name
    source_file.write_bytes(file_bytes)
    wheel_sha = _sha(b"selected wheel")
    manifest = {
        "distribution": package_name,
        "version": version,
        "exact_pin": f"{package_name}=={version}",
        "license_source": "hash-verified package source archive; text copied byte-for-byte",
        "source_distribution": {
            "filename": f"{package_name}-{version}.tar.gz",
            "sha256": _sha(b"source distribution"),
        },
        "selected_wheel": {
            "filename": f"{package_name}-{version}-py3-none-any.whl",
            "sha256": wheel_sha,
        },
        "files": [
            {
                "path": source_file.relative_to(repo).as_posix(),
                "source_archive_path": f"{package_name}-{version}/{file_name}",
                "size_bytes": len(file_bytes),
                "sha256": _sha(file_bytes),
            }
        ],
    }
    manifest_path = source_dir / "source-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    spec = {
        "dependency_notices": {
            "source_supplements": [manifest_path.relative_to(repo).as_posix()]
        }
    }
    return repo, manifest_path, source_file, manifest, spec, wheel_sha


def _load(repo: Path, spec: dict, packages, *, bundle_dest: str = "legal/dependencies"):
    return source_notice_supplements.load_source_notice_supplements(
        spec, repo, packages, bundle_dest
    )


def test_loads_locked_source_notice_without_installed_distribution(tmp_path: Path) -> None:
    repo, _manifest_path, _source_file, _manifest, spec, wheel_sha = _fixture(tmp_path)

    result = _load(repo, spec, [_locked(wheel_sha=wheel_sha)])

    assert list(result) == ["example==1.2.3"]
    records, files = result["example==1.2.3"]
    assert files == [
        (
            "legal/dependencies/example-1.2.3/source-supplements/LICENSE",
            b"Example license text\n",
        )
    ]
    assert records[0]["provenance"] == "reviewed-source-supplement"
    assert records[0]["source_archive_path"] == "example-1.2.3/LICENSE"
    assert records[0]["source_archive_sha256"] == _manifest["source_distribution"]["sha256"]
    assert records[0]["manifest_path"] == spec["dependency_notices"]["source_supplements"][0]
    assert records[0]["manifest_sha256"] == _sha(_manifest_path.read_bytes())
    assert "record_hash" not in records[0]


def test_ignores_unlocked_manifest_but_still_validates_config_path(tmp_path: Path) -> None:
    repo, manifest_path, _source_file, _manifest, spec, _wheel_sha = _fixture(tmp_path)

    assert _load(repo, spec, []) == {}
    spec["dependency_notices"]["source_supplements"] = ["../outside.json"]
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="traversal"):
        _load(repo, spec, [])
    spec["dependency_notices"]["source_supplements"] = [manifest_path.relative_to(repo).as_posix()]
    missing = repo / "missing.json"
    spec["dependency_notices"]["source_supplements"] = [missing.relative_to(repo).as_posix()]
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="missing"):
        _load(repo, spec, [])


def test_rejects_tampered_notice_bytes(tmp_path: Path) -> None:
    repo, _manifest_path, source_file, _manifest, spec, wheel_sha = _fixture(tmp_path)
    source_file.write_bytes(b"changed after review\n")

    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="differs"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])


def test_rejects_selected_wheel_hash_not_in_lock(tmp_path: Path) -> None:
    repo, _manifest_path, _source_file, _manifest, spec, _wheel_sha = _fixture(tmp_path)

    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="wheel hash"):
        _load(repo, spec, [_locked(wheel_sha=_sha(b"different wheel"))])


def test_rejects_wrong_locked_version(tmp_path: Path) -> None:
    repo, _manifest_path, _source_file, _manifest, spec, wheel_sha = _fixture(tmp_path)

    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="version differs"):
        _load(repo, spec, [_locked(version="9.9.9", wheel_sha=wheel_sha)])


def test_rejects_symlink_manifest_and_notice_file(tmp_path: Path) -> None:
    repo, manifest_path, source_file, manifest, spec, wheel_sha = _fixture(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_bytes(manifest_path.read_bytes())
    manifest_path.unlink()
    manifest_path.symlink_to(outside)
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="symlink"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])

    manifest_path.unlink()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    source_file.unlink()
    external_notice = tmp_path / "external-LICENSE"
    external_notice.write_bytes(b"Example license text\n")
    source_file.symlink_to(external_notice)
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="symlink"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])


def test_rejects_duplicate_manifest_and_notice_destinations(tmp_path: Path) -> None:
    repo, manifest_path, source_file, manifest, spec, wheel_sha = _fixture(tmp_path)
    spec["dependency_notices"]["source_supplements"] = [
        manifest_path.relative_to(repo).as_posix(),
        manifest_path.relative_to(repo).as_posix(),
    ]
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="duplicated"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])

    spec["dependency_notices"]["source_supplements"] = [manifest_path.relative_to(repo).as_posix()]
    second = source_file.parent / "COPYING"
    second.write_bytes(b"Other notice\n")
    manifest["files"].append(
        {
            "path": second.relative_to(repo).as_posix(),
            "source_archive_path": "example-1.2.3/other/COPYING",
            "size_bytes": len(second.read_bytes()),
            "sha256": _sha(second.read_bytes()),
        }
    )
    # Both files use the same output basename in separate source directories.
    third = source_file.parent / "nested" / "LICENSE"
    third.parent.mkdir()
    third.write_bytes(b"Nested license\n")
    manifest["files"].append(
        {
            "path": third.relative_to(repo).as_posix(),
            "source_archive_path": "example-1.2.3/nested/LICENSE",
            "size_bytes": len(third.read_bytes()),
            "sha256": _sha(third.read_bytes()),
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="basename"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])


def test_rejects_unknown_duplicate_and_traversing_manifest_fields(tmp_path: Path) -> None:
    repo, manifest_path, _source_file, manifest, spec, wheel_sha = _fixture(tmp_path)
    manifest["unexpected"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="unknown JSON keys"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])

    manifest.pop("unexpected")
    manifest["files"][0]["path"] = "../outside/LICENSE"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="traversal"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])

    manifest_path.write_text(
        '{"distribution":"example","version":"1.2.3","version":"1.2.3"}',
        encoding="utf-8",
    )
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="duplicate JSON"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])


def test_rejects_private_url_in_manifest(tmp_path: Path) -> None:
    repo, manifest_path, _source_file, manifest, spec, wheel_sha = _fixture(tmp_path)
    manifest["license_source"] = "private source https://private.example/repo"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="URL"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])


def test_rejects_invalid_source_archive_hash_and_bool_size(tmp_path: Path) -> None:
    repo, manifest_path, _source_file, manifest, spec, wheel_sha = _fixture(tmp_path)
    manifest["source_distribution"]["sha256"] = "not-a-hash"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="source distribution identity"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])

    manifest["source_distribution"]["sha256"] = _sha(b"source distribution")
    manifest["files"][0]["size_bytes"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="size"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])


def test_rejects_source_archive_identity_not_bound_to_package(tmp_path: Path) -> None:
    repo, manifest_path, _source_file, manifest, spec, wheel_sha = _fixture(tmp_path)
    manifest["source_distribution"]["filename"] = "different-1.2.3.tar.gz"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="filenames"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])

    manifest["source_distribution"]["filename"] = "example-1.2.3.tar.gz"
    manifest["files"][0]["source_archive_path"] = "different-1.2.3/LICENSE"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match="does not map"):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])


def test_loads_upstream_license_without_claiming_it_is_in_package_sdist(
    tmp_path: Path,
) -> None:
    repo, manifest_path, source_file, manifest, spec, wheel_sha = _fixture(
        tmp_path, file_name="LICENSE-ptflops.txt", file_bytes=b"MIT License\n"
    )
    package_source_hash = _sha(b"DeepCache flops.py attribution source")
    upstream_hash = _sha(b"MIT License\n")
    manifest["package_source_evidence"] = {
        "path": "example-1.2.3/DeepCache/flops.py",
        "sha256": package_source_hash,
    }
    manifest["files"][0].pop("source_archive_path")
    manifest["files"][0]["upstream_source"] = {
        "repository": "sovrasov/flops-counter.pytorch",
        "revision": "a" * 40,
        "path": "LICENSE",
        "sha256": upstream_hash,
        "size_bytes": len(b"MIT License\n"),
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = _load(repo, spec, [_locked(wheel_sha=wheel_sha)])

    records, files = result["example==1.2.3"]
    assert files == [
        (
            "legal/dependencies/example-1.2.3/source-supplements/LICENSE-ptflops.txt",
            b"MIT License\n",
        )
    ]
    assert records[0]["provenance"] == "reviewed-upstream-source-supplement"
    assert records[0]["source_archive_filename"] == "example-1.2.3.tar.gz"
    assert records[0]["source_archive_sha256"] == manifest["source_distribution"]["sha256"]
    assert records[0]["package_source_evidence"] == manifest["package_source_evidence"]
    assert records[0]["upstream_source"] == manifest["files"][0]["upstream_source"]
    assert "source_archive_path" not in records[0]


@pytest.mark.parametrize(
    "change,match",
    [
        ("bad-revision", "repository or revision"),
        ("bad-upstream-hash", "bytes differ"),
        ("bad-package-path", "does not map"),
        ("missing-package-evidence", "requires package source attribution"),
    ],
)
def test_rejects_invalid_upstream_notice_provenance(
    tmp_path: Path, change: str, match: str
) -> None:
    repo, manifest_path, _source_file, manifest, spec, wheel_sha = _fixture(
        tmp_path, file_name="LICENSE-ptflops.txt", file_bytes=b"MIT License\n"
    )
    manifest["package_source_evidence"] = {
        "path": "example-1.2.3/src.py",
        "sha256": _sha(b"package source path"),
    }
    file = manifest["files"][0]
    file.pop("source_archive_path")
    file["upstream_source"] = {
        "repository": "sovrasov/flops-counter.pytorch",
        "revision": "a" * 40,
        "path": "LICENSE",
        "sha256": _sha(b"MIT License\n"),
        "size_bytes": len(b"MIT License\n"),
    }
    if change == "bad-revision":
        file["upstream_source"]["revision"] = "not-a-commit"
    elif change == "bad-upstream-hash":
        file["upstream_source"]["sha256"] = _sha(b"different bytes")
    elif change == "bad-package-path":
        manifest["package_source_evidence"]["path"] = "other-1.2.3/src.py"
    elif change == "missing-package-evidence":
        manifest.pop("package_source_evidence")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(source_notice_supplements.SourceNoticeSupplementError, match=match):
        _load(repo, spec, [_locked(wheel_sha=wheel_sha)])
