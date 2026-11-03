from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from io import BytesIO

import pytest

from scripts import stage_postgresql_runtime as stager


class _Response(BytesIO):
    def __init__(self, body: bytes, final_url: str):
        super().__init__(body)
        self._final_url = final_url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def geturl(self):
        return self._final_url


def _lock_and_payloads() -> tuple[dict, dict[str, bytes]]:
    packages = []
    payloads = {}
    for index in range(24):
        name = "libpq5" if index == 0 else f"fixture-pkg-{index}"
        version = "16.15-0ubuntu0.24.04.1" if name == "libpq5" else "1.0-1"
        body = f"fixture Debian archive contents {index}".encode()
        filename = f"{name}_{version}_amd64.deb"
        payloads[filename] = body
        packages.append({
            "Package": name,
            "Version": version,
            "Architecture": "amd64",
            "Source": f"fixture-source-{index}",
            "Filename": f"pool/main/f/{filename}",
            "Size": str(len(body)),
            "SHA256": hashlib.sha256(body).hexdigest(),
            "Depends": "",
            "Pre-Depends": "",
            "License": "fixture only",
        })
    return {
        "origin_indexes": list(stager.EXPECTED_ORIGIN_INDEXES),
        "root": stager.EXPECTED_ROOT,
        "resolution_policy": "fixture closure",
        "package_count": 24,
        "packages": packages,
        "edges": [],
    }, payloads


def _write_lock(path: Path, lock: dict) -> None:
    path.write_text(json.dumps(lock, sort_keys=True) + "\n", encoding="utf-8")


def _stage_from_cache(tmp_path: Path):
    lock, payloads = _lock_and_payloads()
    lock_path = tmp_path / "lock.json"
    _write_lock(lock_path, lock)
    cache = tmp_path / "private-cache"
    cache.mkdir()
    for filename, body in payloads.items():
        (cache / filename).write_bytes(body)
    output = tmp_path / "staged"
    result = stager.stage(output, cache_dir=cache, lock_path=lock_path)
    return lock, payloads, cache, output, result


def test_cached_debs_are_stream_checked_and_receipted(tmp_path):
    lock, payloads, cache, output, receipt = _stage_from_cache(tmp_path)

    assert receipt["status"].startswith("hash-verified")
    assert receipt["installation_performed"] is False
    assert receipt["maintainer_scripts_executed"] is False
    assert receipt["database_driver_imported"] is False
    assert receipt["package_count"] == 24
    assert receipt["total_bytes"] == sum(map(len, payloads.values()))
    assert len(receipt["lock_sha256"]) == 64
    assert str(cache) not in json.dumps(receipt)
    assert {path.name for path in (output / "debs").iterdir()} == set(payloads)
    assert output.stat().st_mode & 0o777 == 0o755
    assert (output / "debs").stat().st_mode & 0o777 == 0o755
    for filename, body in payloads.items():
        assert (output / "debs" / filename).read_bytes() == body
        assert (output / "debs" / filename).stat().st_mode & 0o777 == 0o644

    assert not (output / "Packages").exists()
    assert not (output / "Packages.gz").exists()
    expected_install = "".join(f"{package['Package']}={package['Version']}\n" for package in lock["packages"])
    assert (output / "install-packages.txt").read_text(encoding="ascii") == expected_install

    for line in (output / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        digest, relative = line.split("  ", 1)
        assert re.fullmatch(r"[0-9a-f]{64}", digest)
        assert hashlib.sha256((output / relative).read_bytes()).hexdigest() == digest


def test_glibc_build_supplement_lock_preserves_authenticated_package_metadata():
    lock_path = stager.BUILD_SUPPLEMENT_LOCK_PATH
    lock, _lock_bytes, _lock_hash = stager.load_lock(lock_path, "build-supplement")

    assert lock["root"] == "libc6-dev=2.39-0ubuntu8.9"
    assert lock["source_package"] == {"name": "glibc", "version": "2.39-0ubuntu8.9"}
    packages = {item["Package"]: item for item in lock["packages"]}
    assert set(packages) == {"libc-dev-bin", "libc6-dev"}
    assert packages["libc-dev-bin"]["SHA256"] == "77db23aba4582d034d9a95e4818a16e7e51a2d4fb17a9204439688e288d67f4c"
    assert packages["libc6-dev"]["SHA256"] == "e13d5fcc1b2a86f75bca8e0026a8e39f24fe97ca86e92be79991f8697eb1306f"
    assert "libc6 (= 2.39-0ubuntu8.9)" in packages["libc6-dev"]["Depends"]
    assert "libc-dev-bin (= 2.39-0ubuntu8.9)" in packages["libc6-dev"]["Depends"]
    record = packages["libc6-dev"]["signed_index_record"]
    assert "Provides: libc-dev (= 2.39-0ubuntu8.9)" in record
    assert "Conflicts: libc0.3-dev, libc6.1-dev" in record
    assert "Breaks: binutils (<< 2.38)" in record
    assert "Replaces: libc6 (<< 2.38-1ubuntu1)" in record
    assert "Multi-Arch: same" in record


@pytest.mark.parametrize(
    ("field", "value"),
    (("Package", "libpq5-other"), ("Version", "16.15-0ubuntu0.24.04.2")),
)
def test_runtime_root_spec_matches_actual_package_row(tmp_path, field, value):
    lock, _payloads = _lock_and_payloads()
    lock["packages"][0][field] = value
    lock_path = tmp_path / "lock.json"
    _write_lock(lock_path, lock)

    with pytest.raises(stager.StageError, match="root package"):
        stager.load_lock(lock_path)


@pytest.mark.parametrize(
    ("field", "value"),
    (("Package", "libc6-dev-other"), ("Version", "2.39-0ubuntu8.10")),
)
def test_supplement_root_spec_matches_actual_package_row(field, value):
    lock, _lock_bytes, _lock_hash = stager.load_lock(
        stager.BUILD_SUPPLEMENT_LOCK_PATH, "build-supplement"
    )
    package = next(item for item in lock["packages"] if item["Package"] == "libc6-dev")
    package[field] = value

    with pytest.raises(stager.StageError, match="root package"):
        stager.validate_lock(lock, "build-supplement")


def test_signed_index_metadata_rejects_duplicate_and_changed_fields():
    lock, _lock_bytes, _lock_hash = stager.load_lock(
        stager.BUILD_SUPPLEMENT_LOCK_PATH, "build-supplement"
    )
    package = next(item for item in lock["packages"] if item["Package"] == "libc6-dev")
    package["signed_index_record"] = package["signed_index_record"].replace(
        "Version: 2.39-0ubuntu8.9\n",
        "Version: 2.39-0ubuntu8.8\nversion: 2.39-0ubuntu8.9\n",
        1,
    )
    with pytest.raises(stager.StageError, match="duplicate signed package metadata field"):
        stager.validate_lock(lock, "build-supplement")

    package["signed_index_record"] = package["signed_index_record"].replace(
        "Version: 2.39-0ubuntu8.8\nversion: 2.39-0ubuntu8.9\n",
        "Version: 2.39-0ubuntu8.9\n",
        1,
    )
    package["signed_index_record"] = "\ud800"
    with pytest.raises(stager.StageError, match="malformed signed package metadata record"):
        stager.validate_lock(lock, "build-supplement")

    lock, _lock_bytes, _lock_hash = stager.load_lock(
        stager.BUILD_SUPPLEMENT_LOCK_PATH, "build-supplement"
    )
    package = next(item for item in lock["packages"] if item["Package"] == "libc6-dev")
    package["Breaks"] = "binutils (<< 2.39)"
    with pytest.raises(stager.StageError, match="signed package metadata differs.*Breaks"):
        stager.validate_lock(lock, "build-supplement")


def test_build_supplement_rejects_a_mixed_package_set():
    lock, _lock_bytes, _lock_hash = stager.load_lock(
        stager.BUILD_SUPPLEMENT_LOCK_PATH, "build-supplement"
    )
    package = next(item for item in lock["packages"] if item["Package"] == "libc-dev-bin")
    package["Package"] = "libc-dev-bin-extra"
    package["signed_index_record"] = package["signed_index_record"].replace(
        "Package: libc-dev-bin\n", "Package: libc-dev-bin-extra\n", 1
    )

    with pytest.raises(stager.StageError, match="must be libc-dev-bin and libc6-dev only"):
        stager.validate_lock(lock, "build-supplement")


def test_corrupt_cache_rejects_without_network_fallback(tmp_path):
    lock, payloads = _lock_and_payloads()
    lock_path = tmp_path / "lock.json"
    _write_lock(lock_path, lock)
    cache = tmp_path / "cache"
    cache.mkdir()
    for filename, body in payloads.items():
        (cache / filename).write_bytes(body)
    first = next(iter(payloads))
    (cache / first).write_bytes(b"corrupt")
    output = tmp_path / "stage"

    def unexpected_fetch(*_args, **_kwargs):
        pytest.fail("corrupt cached bytes must reject, not fall through to network")

    with pytest.raises(stager.StageError, match="size or SHA-256"):
        stager.stage(output, cache_dir=cache, opener=unexpected_fetch, lock_path=lock_path)
    assert not output.exists()
    assert list(tmp_path.glob(".stage.*")) == []


def test_symlinked_cache_member_is_rejected(tmp_path):
    lock, payloads = _lock_and_payloads()
    lock_path = tmp_path / "lock.json"
    _write_lock(lock_path, lock)
    cache = tmp_path / "cache"
    cache.mkdir()
    for filename, body in payloads.items():
        (cache / filename).write_bytes(body)
    outside = tmp_path / "outside.deb"
    outside.write_bytes(next(iter(payloads.values())))
    first = next(iter(payloads))
    (cache / first).unlink()
    (cache / first).symlink_to(outside)

    with pytest.raises(stager.StageError, match="symlink"):
        stager.stage(tmp_path / "stage", cache_dir=cache, lock_path=lock_path)


def test_canonical_download_is_hash_checked_and_only_records_source_url(tmp_path):
    lock, payloads = _lock_and_payloads()
    lock_path = tmp_path / "lock.json"
    _write_lock(lock_path, lock)
    expected = iter(payloads.items())
    requests = []

    def fake_open(request, timeout):
        filename, body = next(expected)
        requests.append((request.full_url, timeout))
        return _Response(body, request.full_url)

    output = tmp_path / "stage"
    receipt = stager.stage(output, opener=fake_open, lock_path=lock_path)
    assert len(requests) == 24
    assert all(url.startswith(stager.ARCHIVE_BASE) for url, _timeout in requests)
    assert all(timeout == stager.REQUEST_TIMEOUT_SECONDS for _url, timeout in requests)
    assert all(item["source"] == "canonical_archive_download" for item in receipt["packages"])
    assert all(item["source_url"].startswith(stager.ARCHIVE_BASE) for item in receipt["packages"])


def test_download_redirect_outside_canonical_host_fails_before_output_commit(tmp_path):
    lock, payloads = _lock_and_payloads()
    lock_path = tmp_path / "lock.json"
    _write_lock(lock_path, lock)
    body = next(iter(payloads.values()))

    def fake_open(request, timeout):
        return _Response(body, "https://example.invalid/redirected.deb")

    output = tmp_path / "stage"
    with pytest.raises(stager.StageError, match="redirected outside"):
        stager.stage(output, opener=fake_open, lock_path=lock_path)
    assert not output.exists()


def test_wrong_hash_download_and_unsafe_lock_paths_fail_closed(tmp_path):
    lock, payloads = _lock_and_payloads()
    lock_path = tmp_path / "lock.json"
    first = next(iter(lock["packages"]))
    first["SHA256"] = "0" * 64
    _write_lock(lock_path, lock)

    def fake_open(request, timeout):
        return _Response(next(iter(payloads.values())), request.full_url)

    with pytest.raises(stager.StageError, match="size or SHA-256"):
        stager.stage(tmp_path / "bad-hash-stage", opener=fake_open, lock_path=lock_path)

    lock["packages"][0]["Filename"] = "pool/main/../../outside.deb"
    _write_lock(lock_path, lock)
    with pytest.raises(stager.StageError, match="unsafe package archive path"):
        stager.stage(tmp_path / "bad-path-stage", opener=fake_open, lock_path=lock_path)


def test_populated_output_and_incomplete_lock_are_rejected_before_fetch(tmp_path):
    lock, _payloads = _lock_and_payloads()
    lock_path = tmp_path / "lock.json"
    output = tmp_path / "stage"
    output.mkdir()
    (output / "keep").write_text("private", encoding="utf-8")
    _write_lock(lock_path, lock)

    def unexpected_fetch(*_args, **_kwargs):
        pytest.fail("input validation should fail before fetching")

    with pytest.raises(stager.StageError, match="must not exist or must be empty"):
        stager.stage(output, opener=unexpected_fetch, lock_path=lock_path)

    (output / "keep").unlink()
    output.rmdir()
    lock["packages"].pop()
    _write_lock(lock_path, lock)
    with pytest.raises(stager.StageError, match="exactly 24 packages"):
        stager.stage(output, opener=unexpected_fetch, lock_path=lock_path)


def test_docker_release_uses_hash_checked_local_closure_without_glibc_overlay():
    root = stager.ROOT
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/docker-release.yml").read_text(encoding="utf-8")
    candidate_workflow = (root / ".github/workflows/pypi-dispatch.yml").read_text(encoding="utf-8")

    assert "runs-on: ubuntu-24.04" in workflow
    assert "stage_postgresql_runtime.py" in workflow
    assert "--cache-dir /var/cache/apt/archives" in workflow
    assert "--kind runtime" in workflow
    assert "--kind build-supplement" in workflow
    assert "source=postgresql,target=/tmp/release-inputs/postgresql,ro" in dockerfile
    assert "source=postgresql-build-supplement,target=/tmp/release-inputs/postgresql-build-supplement,ro" in dockerfile
    assert dockerfile.index("sha256sum -c SHA256SUMS") < dockerfile.index("apt-get install -y $packages")
    assert dockerfile.index("sha256sum -c SHA256SUMS", dockerfile.index("apt-get install -y $packages")) < dockerfile.index("xargs -r apt-get")
    assert "--network=none" in dockerfile
    assert 'cp "$repo"/debs/*.deb /var/cache/apt/archives/' in dockerfile
    assert 'metadata="$(dpkg-deb -f "$deb")"' in dockerfile
    assert "--no-download --no-remove --no-install-recommends -y install" in dockerfile
    assert "Dir::Etc::sourceparts=-" in dockerfile
    assert "file:/tmp/airunner-postgresql-local ./" in dockerfile
    assert "libpq5=16.15-0ubuntu0.24.04.1" not in dockerfile
    assert "/usr/share/doc/airunner/release-inputs/postgresql/" in dockerfile
    assert "COPY --from=reviewed-inputs /postgresql" not in dockerfile
    assert "--allow-downgrades" not in dockerfile
    assert "reviewed PostgreSQL runtime drift" in dockerfile
    assert 'postgresql-build-supplement/staging-receipt.json"), "build-supplement", 2' in dockerfile
    assert 'stage_postgresql_runtime.py \\\n            --output-dir "$audit/postgresql-runtime"' in candidate_workflow
    assert "linux-candidate-input-audit/postgresql-runtime/**" in candidate_workflow

    lock = json.loads((root / "packaging/linux/postgresql-libpq-noble-runtime-lock.json").read_text())
    packages = {package["Package"] for package in lock["packages"]}
    assert {"libpq5", "libssl3t64", "libldap2", "libsasl2-2"} <= packages
