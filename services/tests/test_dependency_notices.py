"""Lock-scoped dependency notice collection and bundle verification tests."""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    import dependency_notices
    import assemble_linux_bundle
    import linux_bundle_assemble
    import inspect_linux_bundle
finally:
    sys.path.remove(str(SCRIPTS))


def _hash(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _record_hash(value: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(value).digest())
    return "sha256=" + encoded.decode("ascii").rstrip("=")


def _write_distribution(
    site: Path,
    name: str,
    version: str,
    notices: dict[str, bytes] | None = None,
    *,
    unhashed: set[str] | None = None,
    traversal: bool = False,
    duplicate: bool = False,
    symlink_notice: str | None = None,
    extra_record_rows: list[tuple[str, str, str]] | None = None,
    license_file_headers: list[str] | None = None,
) -> Path:
    """Create a synthetic wheel installation with a realistic RECORD."""
    notices = notices or {"licenses/LICENSE": f"{name} notice\n".encode()}
    unhashed = unhashed or set()
    metadata_dir = site / f"{name}-{version}.dist-info"
    metadata_dir.mkdir(parents=True)
    metadata = (
        f"Metadata-Version: 2.3\nName: {name}\nVersion: {version}\n"
        + "".join(f"License-File: {value}\n" for value in license_file_headers or [])
        + "\n"
    )
    (metadata_dir / "METADATA").write_text(metadata, encoding="utf-8")
    rows: list[tuple[str, str, str]] = []
    metadata_rel = f"{metadata_dir.name}/METADATA"
    metadata_bytes = metadata.encode()
    rows.append((metadata_rel, _record_hash(metadata_bytes), str(len(metadata_bytes))))

    for relative, content in notices.items():
        if traversal:
            relative = "../outside/LICENSE"
        target = site / metadata_dir.name / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if symlink_notice == relative:
            outside = site.parent / "outside-license"
            outside.write_bytes(content)
            target.symlink_to(outside)
        else:
            target.write_bytes(content)
        record_path = f"{metadata_dir.name}/{relative}"
        digest = "" if relative in unhashed else _record_hash(content)
        rows.append((record_path, digest, str(len(content))))
        if duplicate:
            rows.append((record_path, digest, str(len(content))))

    record_rel = f"{metadata_dir.name}/RECORD"
    rows.append((record_rel, "", ""))
    rows.extend(extra_record_rows or [])
    with (metadata_dir / "RECORD").open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream, lineterminator="\n").writerows(rows)
    # A package import would fail. The notice collector must read metadata only.
    package_code = site / name.replace("-", "_")
    package_code.mkdir(exist_ok=True)
    (package_code / "__init__.py").write_text(
        "raise RuntimeError('package code must not be imported')\n", encoding="utf-8"
    )
    return metadata_dir


def _lock(tmp_path: Path, entries: list[tuple[str, str]]) -> Path:
    lines: list[str] = []
    for name, version in entries:
        if version.startswith("https://"):
            lines.extend(
                [
                    f"{name} @ {version} \\",
                    f"    --hash=sha256:{hashlib.sha256((name + version).encode()).hexdigest()}",
                ]
            )
        else:
            lines.extend(
                [
                    f"{name}=={version} \\",
                    f"    --hash=sha256:{hashlib.sha256((name + version).encode()).hexdigest()}",
                ]
            )
    path = tmp_path / "requirements.lock"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    site = tmp_path / "python" / "site-packages"
    site.mkdir(parents=True)
    monkeypatch.setattr(dependency_notices.sys, "prefix", str(tmp_path / "python"))
    entries = [
        ("alpha", "1.0"),
        ("beta", "https://packages.example.invalid/beta-2.0-py3-none-any.whl"),
    ]
    lock = _lock(tmp_path, entries)
    spec = {
        "bundle": {"constraints": lock.name, "name": "fixture", "executable": "daemon", "tool": "pyinstaller", "entry": "fixture:main"},
        "profile": {"services_extra": "fixture"},
        "dependency_notices": {
            "required": True,
            "dest": "legal/dependencies",
            "manifest": "dependency-notices.json",
        },
        "manifest": {"filename": "bundle-manifest.json", "required_fields": ["bundle", "tool", "entry", "base", "files"], "file_fields": ["path", "sha256"]},
        "data": [],
        "runtimes": {"bin_dir": "bin"},
        "console_script": [],
        "code": {"hidden_imports": [], "extension_modules": [], "collect_submodules": [], "collect_binaries": [], "frozen_source_markers": [], "exclude_modules": [], "runtime_hooks": [], "additional_hooks_dirs": []},
        "exclusions": {"patterns": []},
        "qt": {"qt_markers": []},
        "warn_allowlist": {"modules": []},
        "r01_coverage": {},
    }
    spec["bundle"]["constraints"] = lock.name
    _write_distribution(site, "alpha", "1.0", {"licenses/LICENSE": b"Alpha MIT notice\n"})
    _write_distribution(site, "beta", "2.0", {"NOTICE": b"Beta notice\n"})
    # This installed distribution is outside the lock and must be ignored.
    _write_distribution(site, "unlocked", "9.9", {"LICENSE": b"ignore me\n"})
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    return site, lock, spec, bundle


def _collect(tmp_path: Path, site: Path, spec: dict, bundle: Path) -> dict:
    return dependency_notices.collect_dependency_notices(
        spec, tmp_path, bundle, site_packages=[site]
    )


def _reviewed_source_fixture(tmp_path, monkeypatch):
    site, lock, spec, bundle = _setup(tmp_path, monkeypatch)
    metadata = site / "alpha-1.0.dist-info"
    (metadata / "licenses/LICENSE").unlink()
    (metadata / "licenses").rmdir()
    record = metadata / "RECORD"
    rows = list(csv.reader(record.read_text().splitlines()))
    with record.open("w", newline="") as stream:
        csv.writer(stream, lineterminator="\n").writerows(
            row for row in rows if not row[0].endswith("licenses/LICENSE")
        )
    source = tmp_path / "reviewed/alpha-LICENSE"
    source.parent.mkdir()
    content = b"Original reviewed source license\n"
    source.write_bytes(content)
    packages, _ = dependency_notices.read_lock(lock.name, tmp_path)
    wheel_hash = next(p.hashes[0] for p in packages if p.normalized_name == "alpha")
    manifest = {
        "distribution": "alpha", "version": "1.0", "exact_pin": "alpha==1.0",
        "license_source": "reviewed source distribution",
        "source_distribution": {"filename": "alpha-1.0.tar.gz", "sha256": "b" * 64},
        "selected_wheel": {"filename": "alpha-1.0-py3-none-any.whl", "sha256": wheel_hash},
        "files": [{
            "path": "reviewed/alpha-LICENSE", "source_archive_path": "alpha-1.0/LICENSE",
            "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content),
        }],
    }
    manifest_path = tmp_path / "reviewed/source-manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return site, spec, bundle


def test_reviewed_source_notice_can_supply_missing_wheel_notice(tmp_path, monkeypatch):
    site, spec, bundle = _reviewed_source_fixture(tmp_path, monkeypatch)
    with pytest.raises(dependency_notices.DependencyNoticeError, match="no hashed license"):
        _collect(tmp_path, site, spec, bundle)
    spec["dependency_notices"]["source_supplements"] = ["reviewed/source-manifest.json"]
    manifest = _collect(tmp_path, site, spec, bundle)
    alpha = next(item for item in manifest["distributions"] if item["normalized_name"] == "alpha")
    assert len(alpha["notices"]) == 1
    assert alpha["notices"][0]["provenance"] == "reviewed-source-supplement"
    assert "record_hash" not in alpha["notices"][0]
    assert dependency_notices.verify_dependency_notice_manifest(bundle, spec, tmp_path) == []


def _add_vendor_fixture(tmp_path, spec):
    packages, _ = dependency_notices.read_lock(spec["bundle"]["constraints"], tmp_path)
    wheel_hash = next(p.hashes[0] for p in packages if p.normalized_name == "alpha")
    folder = tmp_path / "vendor"
    folder.mkdir()
    documents = []
    for name in ("LICENSE.txt", "ThirdPartyNotices.txt"):
        content = f"Original vendor {name}\n".encode()
        (folder / name).write_bytes(content)
        documents.append({
            "publisher": "NVIDIA Corporation", "product": "Fixture",
            "release_scope": "Synthetic integration fixture",
            "official_source_url": f"https://github.com/NVIDIA/nccl/blob/{'a' * 40}/{name}",
            "retrieved_date": "2026-11-02",
            "document_path": f"vendor/{name}",
            "text_path": f"vendor/{name}",
            "document_sha256": hashlib.sha256(content).hexdigest(),
            "text_sha256": hashlib.sha256(content).hexdigest(),
            "document_size_bytes": len(content), "text_size_bytes": len(content),
        })
    manifest = {
        "distribution": "alpha", "version": "1.0", "exact_pin": "alpha==1.0",
        "selected_wheel_sha256": wheel_hash, "vendor_documents": documents,
    }
    (folder / "vendor-license.json").write_text(json.dumps(manifest))
    spec["dependency_notices"]["vendor_supplements"] = ["vendor/vendor-license.json"]


def test_vendor_can_supply_missing_wheel_notices(tmp_path, monkeypatch):
    site, spec, bundle = _reviewed_source_fixture(tmp_path, monkeypatch)
    _add_vendor_fixture(tmp_path, spec)
    manifest = _collect(tmp_path, site, spec, bundle)
    alpha = manifest["distributions"][0]
    assert len(alpha["notices"]) == 2
    assert all(n["provenance"] == "reviewed-vendor-license-supplement" for n in alpha["notices"])
    assert all("record_hash" not in n for n in alpha["notices"])
    assert dependency_notices.verify_dependency_notice_manifest(bundle, spec, tmp_path) == []


def test_wheel_and_source_and_vendor_notices_are_all_preserved(tmp_path, monkeypatch):
    site, spec, bundle = _reviewed_source_fixture(tmp_path, monkeypatch)
    # Restore the original installed notice while retaining reviewed source evidence.
    shutil.rmtree(site / "alpha-1.0.dist-info")
    shutil.rmtree(site / "alpha")
    _write_distribution(site, "alpha", "1.0")
    spec["dependency_notices"]["source_supplements"] = ["reviewed/source-manifest.json"]
    _add_vendor_fixture(tmp_path, spec)
    manifest = _collect(tmp_path, site, spec, bundle)
    notices = manifest["distributions"][0]["notices"]
    assert len(notices) == 4
    assert sum("record_hash" in notice for notice in notices) == 1
    assert dependency_notices.verify_dependency_notice_manifest(bundle, spec, tmp_path) == []


@pytest.mark.parametrize("tamper", ["omission", "provenance", "payload", "vendor_hash"])
def test_vendor_bundle_rejects_missing_or_forged_evidence(tmp_path, monkeypatch, tamper):
    site, lock, spec, bundle = _setup(tmp_path, monkeypatch)
    _add_vendor_fixture(tmp_path, spec)
    manifest = _collect(tmp_path, site, spec, bundle)
    alpha = manifest["distributions"][0]
    notice = next(n for n in alpha["notices"] if "provenance" in n)
    if tamper == "omission":
        alpha["notices"].remove(notice)
    elif tamper == "provenance":
        notice.pop("provenance")
        notice["record_hash"] = "sha256:" + notice["sha256"]
    elif tamper == "payload":
        (bundle / notice["bundle_path"]).write_bytes(b"altered")
    else:
        notice["vendor_document"]["document_sha256"] = "0" * 64
    (bundle / "legal/dependencies/dependency-notices.json").write_text(json.dumps(manifest))
    assert dependency_notices.verify_dependency_notice_manifest(bundle, spec, tmp_path)


def test_vendor_manifest_failure_is_a_collection_error(tmp_path, monkeypatch):
    site, lock, spec, bundle = _setup(tmp_path, monkeypatch)
    _add_vendor_fixture(tmp_path, spec)
    (tmp_path / "vendor/LICENSE.txt").write_bytes(b"altered")
    with pytest.raises(dependency_notices.DependencyNoticeError, match="differs"):
        _collect(tmp_path, site, spec, bundle)


def test_reviewed_upstream_notice_keeps_separate_source_provenance(tmp_path, monkeypatch):
    site, spec, bundle = _reviewed_source_fixture(tmp_path, monkeypatch)
    source_path = tmp_path / "reviewed/source-manifest.json"
    source = json.loads(source_path.read_text())
    source["package_source_evidence"] = {
        "path": "alpha-1.0/attribution.py", "sha256": "e" * 64,
    }
    notice = source["files"][0]
    notice.pop("source_archive_path")
    notice["upstream_source"] = {
        "repository": "example/attributed-project", "revision": "d" * 40,
        "path": "LICENSE", "size_bytes": notice["size_bytes"], "sha256": notice["sha256"],
    }
    source_path.write_text(json.dumps(source))
    spec["dependency_notices"]["source_supplements"] = ["reviewed/source-manifest.json"]
    manifest = _collect(tmp_path, site, spec, bundle)
    alpha = next(item for item in manifest["distributions"] if item["normalized_name"] == "alpha")
    assert alpha["notices"][0]["provenance"] == "reviewed-upstream-source-supplement"
    assert "source_archive_path" not in alpha["notices"][0]
    assert "record_hash" not in alpha["notices"][0]
    assert dependency_notices.verify_dependency_notice_manifest(bundle, spec, tmp_path) == []


@pytest.mark.parametrize("tamper", ["manifest", "provenance", "omission", "payload"])
def test_source_notice_bundle_rejects_forged_or_missing_provenance(
    tmp_path, monkeypatch, tamper
):
    site, spec, bundle = _reviewed_source_fixture(tmp_path, monkeypatch)
    spec["dependency_notices"]["source_supplements"] = ["reviewed/source-manifest.json"]
    manifest = _collect(tmp_path, site, spec, bundle)
    alpha = next(item for item in manifest["distributions"] if item["normalized_name"] == "alpha")
    notice = alpha["notices"][0]
    if tamper == "manifest":
        notice["manifest_sha256"] = "c" * 64
    elif tamper == "provenance":
        notice.pop("provenance")
        notice["record_hash"] = "sha256:" + notice["sha256"]
    elif tamper == "omission":
        alpha["notices"].clear()
    else:
        (bundle / notice["bundle_path"]).write_bytes(b"changed license")
    (bundle / "legal/dependencies/dependency-notices.json").write_text(json.dumps(manifest))
    assert dependency_notices.verify_dependency_notice_manifest(bundle, spec, tmp_path)


def test_collects_only_locked_notice_files_and_inspector_accepts_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, lock, spec, bundle = _setup(tmp_path, monkeypatch)
    result = _collect(tmp_path, site, spec, bundle)
    manifest_path = bundle / "legal/dependencies/dependency-notices.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result["lock_sha256"] == hashlib.sha256(lock.read_bytes()).hexdigest()
    assert {item["normalized_name"] for item in manifest["distributions"]} == {
        "alpha",
        "beta",
    }
    manifest_text = manifest_path.read_text(encoding="utf-8")
    assert str(tmp_path) not in manifest_text
    assert "packages.example.invalid" not in manifest_text
    assert not any(path.name == "unlocked" for path in (bundle / "legal/dependencies").rglob("*"))
    assert (
        bundle
        / "legal/dependencies/alpha-1.0/alpha-1.0.dist-info/licenses/LICENSE"
    ).read_bytes() == b"Alpha MIT notice\n"

    executable = bundle / "daemon"
    executable.write_bytes(b"fixture executable\n")
    executable.chmod(0o755)
    (bundle / "bin").mkdir()
    linux_bundle_assemble.write_manifest(bundle, spec, "fixture-revision")
    inspection = inspect_linux_bundle.inspect_bundle(
        bundle, spec, repo_root=tmp_path
    )
    assert inspection.problems == []


def test_assembly_finishes_pruning_before_collecting_dependency_notices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, _lock, spec, bundle = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(assemble_linux_bundle, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        dependency_notices.sysconfig,
        "get_paths",
        lambda: {"purelib": str(site), "platlib": str(site)},
    )
    calls: list[str] = []

    def stage(_spec: dict, _repo: Path, _bundle: Path) -> None:
        calls.append("stage")

    def prune(_bundle: Path, _spec: dict) -> list[str]:
        calls.append("prune")
        return ["removed-hook-data"]

    monkeypatch.setattr(assemble_linux_bundle, "stage_root_files", stage)
    monkeypatch.setattr(assemble_linux_bundle, "prune_bundle", prune)
    assemble_linux_bundle._finish_tree(spec, bundle)

    assert calls == ["stage", "prune"]
    notice_manifest = bundle / "legal/dependencies/dependency-notices.json"
    assert notice_manifest.is_file()
    assert dependency_notices.verify_dependency_notice_manifest(
        bundle, spec, tmp_path
    ) == []


def test_unrelated_console_script_record_is_not_resolved_or_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, _lock, spec, bundle = _setup(tmp_path, monkeypatch)
    # This is a normal wheel RECORD convention. The referenced executable is
    # outside site-packages and intentionally does not exist in the fixture.
    shutil.rmtree(site / "alpha-1.0.dist-info")
    _write_distribution(
        site,
        "alpha",
        "1.0",
        {"licenses/LICENSE": b"Alpha MIT notice\n"},
        extra_record_rows=[("../../../bin/alpha", "", "")],
    )
    _collect(tmp_path, site, spec, bundle)
    assert (bundle / "legal/dependencies/dependency-notices.json").is_file()


def test_traversing_notice_record_is_rejected_without_reading_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, _lock, spec, bundle = _setup(tmp_path, monkeypatch)
    shutil.rmtree(site / "alpha-1.0.dist-info")
    _write_distribution(
        site,
        "alpha",
        "1.0",
        {"licenses/LICENSE": b"unused"},
        extra_record_rows=[("../../../outside/LICENSE", "", "")],
    )
    with pytest.raises(dependency_notices.DependencyNoticeError, match="path traversal"):
        _collect(tmp_path, site, spec, bundle)


def test_collects_metadata_license_directory_and_declared_legacy_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, _lock, spec, bundle = _setup(tmp_path, monkeypatch)
    shutil.rmtree(site / "alpha-1.0.dist-info")
    _write_distribution(
        site,
        "alpha",
        "1.0",
        {
            "licenses/vendor-third-party.txt": b"Vendor notice\n",
            "legacy-notice.dat": b"Legacy notice\n",
        },
        license_file_headers=["legacy-notice.dat"],
    )
    _collect(tmp_path, site, spec, bundle)
    manifest = json.loads(
        (bundle / "legal/dependencies/dependency-notices.json").read_text(
            encoding="utf-8"
        )
    )
    alpha = next(item for item in manifest["distributions"] if item["normalized_name"] == "alpha")
    assert {item["source_path"] for item in alpha["notices"]} == {
        "alpha-1.0.dist-info/licenses/vendor-third-party.txt",
        "alpha-1.0.dist-info/legacy-notice.dat",
    }


def test_rejects_traversing_metadata_license_file_declaration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, _lock, spec, bundle = _setup(tmp_path, monkeypatch)
    shutil.rmtree(site / "alpha-1.0.dist-info")
    _write_distribution(
        site,
        "alpha",
        "1.0",
        {"licenses/LICENSE": b"Alpha notice\n"},
        license_file_headers=["../../../../outside/LICENSE"],
    )
    with pytest.raises(
        dependency_notices.DependencyNoticeError, match="unsafe License-File"
    ):
        _collect(tmp_path, site, spec, bundle)


def test_collector_rejects_missing_package_wrong_version_and_no_notice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, _lockfile, spec, bundle = _setup(tmp_path, monkeypatch)
    beta_metadata = site / "beta-2.0.dist-info"
    for path in beta_metadata.rglob("*"):
        if path.is_file() or path.is_symlink():
            path.unlink()
    for path in sorted(beta_metadata.rglob("*"), reverse=True):
        if path.is_dir():
            path.rmdir()
    beta_metadata.rmdir()
    with pytest.raises(dependency_notices.DependencyNoticeError, match="not installed"):
        _collect(tmp_path, site, spec, bundle)

    _write_distribution(site, "beta", "2.1", {"NOTICE": b"wrong version\n"})
    with pytest.raises(dependency_notices.DependencyNoticeError, match="version differs"):
        _collect(tmp_path, site, spec, bundle)

    site2 = tmp_path / "python2" / "site-packages"
    site2.mkdir(parents=True)
    monkeypatch.setattr(dependency_notices.sys, "prefix", str(tmp_path / "python2"))
    _write_distribution(site2, "alpha", "1.0", {"metadata.txt": b"not a notice"})
    _write_distribution(site2, "beta", "2.0", {"NOTICE": b"beta notice"})
    bundle2 = tmp_path / "bundle2"
    bundle2.mkdir()
    with pytest.raises(dependency_notices.DependencyNoticeError, match="no hashed license"):
        dependency_notices.collect_dependency_notices(
            spec, tmp_path, bundle2, site_packages=[site2]
        )


@pytest.mark.parametrize("bad_case", ["unhashed", "mutated", "symlink", "traversal", "duplicate"])
def test_collector_rejects_unsafe_or_unverifiable_record_notices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_case: str
) -> None:
    site, _lockfile, spec, bundle = _setup(tmp_path, monkeypatch)
    metadata_dir = site / "alpha-1.0.dist-info"
    notice = metadata_dir / "licenses/LICENSE"
    if bad_case == "unhashed":
        shutil.rmtree(site / "alpha-1.0.dist-info")
        _write_distribution(
            site, "alpha", "1.0", {"licenses/LICENSE": b"unhashed"}, unhashed={"licenses/LICENSE"}
        )
    elif bad_case == "mutated":
        notice.write_bytes(b"modified after RECORD\n")
    elif bad_case == "symlink":
        notice.unlink()
        external = tmp_path / "outside"
        external.write_bytes(b"outside\n")
        notice.symlink_to(external)
    elif bad_case == "traversal":
        shutil.rmtree(site / "alpha-1.0.dist-info")
        _write_distribution(site, "alpha", "1.0", {"licenses/LICENSE": b"traversal"}, traversal=True)
    else:
        shutil.rmtree(site / "alpha-1.0.dist-info")
        _write_distribution(site, "alpha", "1.0", {"licenses/LICENSE": b"duplicate"}, duplicate=True)
    with pytest.raises(dependency_notices.DependencyNoticeError):
        _collect(tmp_path, site, spec, bundle)


def test_lock_parser_rejects_duplicate_normalized_names_and_unhashed_entries(
    tmp_path: Path,
) -> None:
    repeated_hash = hashlib.sha256(b"pin").hexdigest()
    duplicate = (
        f"Foo_Bar==1.0 \\\n    --hash=sha256:{repeated_hash}\n"
        f"foo-bar==1.0 \\\n    --hash=sha256:{repeated_hash}\n"
    ).encode()
    with pytest.raises(dependency_notices.DependencyNoticeError, match="repeats a distribution"):
        dependency_notices.parse_lock_bytes(duplicate)
    unhashed = b"foo==1.0\nbar==2.0 \\\n    --hash=sha256:" + repeated_hash.encode() + b"\n"
    with pytest.raises(dependency_notices.DependencyNoticeError, match="lacks hashes"):
        dependency_notices.parse_lock_bytes(unhashed)


def test_inspector_rejects_lock_change_tampered_notice_and_incomplete_package_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, lock, spec, bundle = _setup(tmp_path, monkeypatch)
    _collect(tmp_path, site, spec, bundle)
    assert dependency_notices.verify_dependency_notice_manifest(bundle, spec, tmp_path) == []

    notice = (
        bundle
        / "legal/dependencies/alpha-1.0/alpha-1.0.dist-info/licenses/LICENSE"
    )
    notice.write_bytes(b"tampered\n")
    assert dependency_notices.verify_dependency_notice_manifest(bundle, spec, tmp_path)
    notice.write_bytes(b"Alpha MIT notice\n")

    manifest_path = bundle / "legal/dependencies/dependency-notices.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["distributions"].pop()
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    assert dependency_notices.verify_dependency_notice_manifest(bundle, spec, tmp_path)

    shutil.rmtree(bundle / "legal/dependencies")
    _collect(tmp_path, site, spec, bundle)
    lock.write_text(lock.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    assert dependency_notices.verify_dependency_notice_manifest(bundle, spec, tmp_path)


def test_collects_nested_source_relative_license_paths(tmp_path, monkeypatch):
    """The tzdata layout retains licenses/ inside the wheel license directory."""
    site, _lock, spec, bundle = _setup(tmp_path, monkeypatch)
    shutil.rmtree(site / "alpha-1.0.dist-info")
    _write_distribution(
        site, "alpha", "1.0",
        {"licenses/LICENSE": b"Package notice", "licenses/licenses/LICENSE_APACHE": b"Apache notice"},
        license_file_headers=["LICENSE", "licenses/LICENSE_APACHE"],
    )
    manifest = _collect(tmp_path, site, spec, bundle)
    alpha = next(item for item in manifest["distributions"] if item["normalized_name"] == "alpha")
    assert len(alpha["notices"]) == 2
    assert (bundle / "legal/dependencies/alpha-1.0/alpha-1.0.dist-info/licenses/licenses/LICENSE_APACHE").read_bytes() == b"Apache notice"
    assert dependency_notices.verify_dependency_notice_manifest(bundle, spec, tmp_path) == []
