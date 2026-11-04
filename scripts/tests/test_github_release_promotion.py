"""Mocked tests for draft-first immutable GitHub Release promotion."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts"))

import check_release_identity as guard  # noqa: E402
import linux_release_wheel_assets as runtime_wheel_assets  # noqa: E402


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _fixture(tmp_path: Path) -> tuple[Path, str, list[Path], list[Path]]:
    root = tmp_path / "repo"
    (root / "services").mkdir(parents=True)
    (root / "services" / "setup.py").write_text(
        '_RELEASE_VERSION = "1.2.3"\n', encoding="utf-8"
    )
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Release Test")
    _git(root, "config", "user.email", "release-test@example.invalid")
    package = root / "package"
    package.mkdir()
    distributions = (
        "llama-cpp-python", "nvidia-nvshmem-cu12", "torchaudio",
        "torchvision", "triton",
    )
    source_rows = []
    lock_lines = []
    wheel_payloads = {}
    for index, name in enumerate(distributions, 1):
        version = "1.0.0"
        filename = f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
        payload = f"fixture wheel:{name}".encode()
        digest = hashlib.sha256(payload).hexdigest()
        source = {
            "kind": "actions_artifact",
            "repo": "Capsize-Games/airunner",
            "artifact_id": 100 + index,
            "run_id": 200 + index,
            "artifact_name": f"runtime-wheels-{index}",
            "source_revision": "a" * 40,
            "archive_sha256": "b" * 64,
            "max_archive_bytes": 4096,
            "durable_release_url": (
                f"https://github.com/Capsize-Games/airunner/releases/download/"
                f"v1.2.3/{filename}"
            ),
        }
        source_rows.append({
            "name": name,
            "version": version,
            "filename": filename,
            "sha256": digest,
            "size_bytes": len(payload),
            "source": source,
        })
        lock_lines.append(
            f"{name}=={version} \\\n    --hash=sha256:{digest}"
        )
        wheel_payloads[filename] = payload
    lock_text = "\n".join(lock_lines) + "\n"
    selected_lock = package / "constraints-linux-nvidia-cu129-linux-release.txt"
    selected_lock.write_text(lock_text, encoding="utf-8")
    source_manifest = package / "linux-release-v4-artifact-sources.json"
    source_manifest.write_text(
        json.dumps({
            "schema_version": 1,
            "status": "candidate-only; not activated",
            "durable_release_tag": "v1.2.3",
            "selected_count": len(source_rows),
            "selected_lock_sha256": hashlib.sha256(lock_text.encode()).hexdigest(),
            "artifact_sources": source_rows,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    _git(root, "add", "services/setup.py", "package")
    _git(root, "commit", "-qm", "fixture")
    sha = _git(root, "rev-parse", "HEAD")
    _git(root, "tag", "-a", "v1.2.3", "-m", "v1.2.3")

    asset_dirs = [
        tmp_path / name
        for name in ("python-dist", "sidecars", "linux-candidate", "debian", "runtime-wheels")
    ]
    for directory in asset_dirs[:-1]:
        directory.mkdir()
    paths: list[Path] = []
    grouped_names = (
        ("python-dist", "airunner_services-1.2.3-py3-none-any.whl"),
        ("python-dist", "airunner_services-1.2.3.tar.gz"),
        ("python-dist", "airunner_native-1.2.3-py3-none-any.whl"),
        ("python-dist", "airunner_native-1.2.3.tar.gz"),
        ("sidecars", "runtime-sidecars-linux.tar.gz"),
        ("sidecars", "runtime-sidecars-windows.tar.gz"),
        ("linux-candidate", f"airunner-services-linux-1.2.3-{sha[:12]}.tar.gz"),
        ("debian", "airunner_1.2.3-1_amd64.deb"),
        ("debian", "airunner-apt-release.json"),
    )
    for group, name in grouped_names:
        path = tmp_path / group / name
        path.write_bytes(("fixture:" + name).encode())
        paths.append(path)
    staged_wheelhouse = tmp_path / "staged-runtime"
    staged_wheelhouse.mkdir()
    for filename, payload in wheel_payloads.items():
        (staged_wheelhouse / filename).write_bytes(payload)
    source_manifest_sha = hashlib.sha256(source_manifest.read_bytes()).hexdigest()
    lock_sha = hashlib.sha256(selected_lock.read_bytes()).hexdigest()
    staging_receipt = {
        "schema_version": 1,
        "status": "verified wheel inputs; not installed or imported",
        "selected_count": len(source_rows),
        "manifest_sha256": source_manifest_sha,
        "selected_lock_sha256": lock_sha,
        "requirements_sha256": lock_sha,
        "source_routes": [
            {
                "filename": row["filename"],
                "selected_route": "actions_artifact",
                "durable_release_url": row["source"]["durable_release_url"],
                "original_actions_source": {
                    key: row["source"][key]
                    for key in (
                        "repo", "artifact_id", "run_id", "artifact_name",
                        "source_revision", "archive_sha256", "max_archive_bytes",
                    )
                },
            }
            for row in source_rows
        ],
        "wheels": [
            {
                "filename": row["filename"],
                "sha256": row["sha256"],
                "size_bytes": row["size_bytes"],
                "source_kind": "actions_artifact",
                "artifact_id": row["source"]["artifact_id"],
            }
            for row in source_rows
        ],
    }
    (staged_wheelhouse / "staging-receipt.json").write_text(
        json.dumps(staging_receipt, indent=2) + "\n", encoding="utf-8"
    )
    runtime_wheel_assets.create_assets(
        staged_wheelhouse,
        asset_dirs[-1],
        source_manifest=source_manifest,
        selected_lock=selected_lock,
        application_version="1.2.3",
        source_sha=sha,
    )
    paths.extend(asset_dirs[-1].iterdir())
    deb = next(path for path in paths if path.suffix == ".deb")
    manifest = next(path for path in paths if path.name == "airunner-apt-release.json")
    manifest.write_text(
        json.dumps(
            {
                "schema": 2,
                "repository": "Capsize-Games/airunner",
                "tag": "v1.2.3",
                "source_commit": sha,
                "workflow": ".github/workflows/pypi-dispatch.yml",
                "workflow_event": "workflow_dispatch",
                "promotion_job": "publish-release-assets",
                "workflow_run_id": 123,
                "package": "airunner",
                "version": "1.2.3-1",
                "architecture": "amd64",
                "filename": deb.name,
                "size": deb.stat().st_size,
                "sha256": hashlib.sha256(deb.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    checksum_data = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in paths
    )
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(checksum_data, encoding="ascii")
    return root, sha, asset_dirs, [sums]


class _Response:
    def __init__(self, value: Any) -> None:
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.value).encode("utf-8")


class _GitHub:
    def __init__(self, root: Path) -> None:
        self.tag_object = _git(root, "rev-parse", "refs/tags/v1.2.3")
        self.publish_immutable = True
        self.immutable_releases_enabled = True
        self.release: dict[str, Any] | None = None
        self.assets: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, str]] = []
        self.fail_upload_name: str | None = None

    def __call__(self, request, timeout: int):
        assert timeout == 60 or timeout == 15
        method = request.get_method()
        parsed = urlparse(request.full_url)
        path = parsed.path
        self.calls.append((method, request.full_url))
        assert request.get_header("Authorization") == "Bearer fixture-token"

        if path.endswith("/immutable-releases") and method == "GET":
            return _Response({"enabled": self.immutable_releases_enabled})
        if path.endswith("/git/ref/tags/v1.2.3"):
            return _Response({
                "ref": "refs/tags/v1.2.3",
                "object": {"sha": self.tag_object, "type": "tag"},
            })
        if path.endswith("/releases/tags/v1.2.3") and method == "GET":
            if self.release is None or self.release.get("draft"):
                raise HTTPError(request.full_url, 404, "missing", Message(), None)
            return _Response(self.release)
        if path.endswith("/releases") and method == "GET":
            return _Response([self.release] if self.release is not None else [])
        if path.endswith("/releases") and method == "POST":
            payload = json.loads(request.data)
            assert payload["tag_name"] == "v1.2.3"
            assert payload["target_commitish"] == "a" * 40 or payload["target_commitish"] == self.release_source
            self.release = {
                "id": 71,
                "tag_name": payload["tag_name"],
                "draft": True,
                "prerelease": False,
                "immutable": False,
            }
            return _Response(self.release)
        if path.endswith("/releases/71/assets") and method == "GET":
            return _Response(list(self.assets.values()))
        if parsed.hostname == "uploads.github.com" and method == "POST":
            name = parse_qs(parsed.query)["name"][0]
            if self.fail_upload_name == name:
                self.fail_upload_name = None
                raise HTTPError(request.full_url, 503, "fixture failure", Message(), None)
            data = request.data
            asset = {
                "id": len(self.assets) + 1,
                "name": name,
                "state": "uploaded",
                "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
            self.assets[name] = asset
            return _Response(asset)
        if path.endswith("/releases/71") and method == "PATCH":
            assert json.loads(request.data) == {"draft": False}
            assert self.release is not None
            self.release["draft"] = False
            self.release["immutable"] = self.publish_immutable
            return _Response(self.release)
        raise AssertionError(f"unexpected request: {method} {request.full_url}")

    @property
    def release_source(self) -> str:
        return self._release_source

    @release_source.setter
    def release_source(self, value: str) -> None:
        self._release_source = value


def _promote(root: Path, sha: str, dirs: list[Path], files: list[Path], api: _GitHub):
    api.release_source = sha
    return guard.promote_release_assets(
        repository="Capsize-Games/airunner",
        tag="v1.2.3",
        source_sha=sha,
        token="fixture-token",
        root=root,
        asset_dirs=dirs,
        asset_files=files,
        expected_run_id=123,
        opener=api,
    )


def test_promotion_creates_draft_uploads_exact_set_then_publishes_immutable(
    tmp_path: Path,
) -> None:
    root, sha, dirs, files = _fixture(tmp_path)
    api = _GitHub(root)

    release = _promote(root, sha, dirs, files, api)

    assert release["draft"] is False
    assert release["immutable"] is True
    methods = [method for method, _ in api.calls]
    assert methods.index("POST") < methods.index("PATCH")
    assert len(api.assets) == 17
    assert api.calls.count(("POST", "https://api.github.com/repos/Capsize-Games/airunner/releases")) == 1


def test_promotion_detects_when_github_did_not_immutably_publish(
    tmp_path: Path,
) -> None:
    root, sha, dirs, files = _fixture(tmp_path)
    api = _GitHub(root)
    api.publish_immutable = False
    with pytest.raises(guard.ReleaseIdentityError, match="expected immutable release"):
        _promote(root, sha, dirs, files, api)
    # GitHub has already published the release at this point. The workflow
    # therefore requires the repository-level setting to be enabled first.
    assert api.release is not None and api.release["draft"] is False
    assert api.release["immutable"] is False


def test_promotion_rejects_tampered_runtime_wheel_before_remote_mutation(
    tmp_path: Path,
) -> None:
    root, sha, dirs, files = _fixture(tmp_path)
    runtime_dir = next(directory for directory in dirs if directory.name == "runtime-wheels")
    wheel = next(runtime_dir.glob("llama_cpp_python-*.whl"))
    wheel.write_bytes(b"tampered wheel bytes")
    all_assets = [
        path for directory in dirs for path in directory.iterdir()
        if path.name != "SHA256SUMS"
    ]
    sums = files[0]
    sums.write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in sorted(all_assets)
        ),
        encoding="ascii",
    )
    api = _GitHub(root)

    with pytest.raises(guard.ReleaseIdentityError, match="runtime wheel release assets"):
        _promote(root, sha, dirs, files, api)
    assert not any(method in {"POST", "PATCH"} for method, _ in api.calls)


def test_promotion_rejects_asset_basename_collision_before_remote_mutation(
    tmp_path: Path,
) -> None:
    root, sha, dirs, files = _fixture(tmp_path)
    runtime_dir = next(directory for directory in dirs if directory.name == "runtime-wheels")
    duplicate = dirs[0] / "llama_cpp_python-1.0.0-py3-none-any.whl"
    duplicate.write_bytes((runtime_dir / duplicate.name).read_bytes())
    all_assets = [
        path for directory in dirs for path in directory.iterdir()
        if path.name != "SHA256SUMS"
    ]
    files[0].write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in sorted(all_assets)
        ),
        encoding="ascii",
    )
    api = _GitHub(root)

    with pytest.raises(guard.ReleaseIdentityError, match="checksum manifest is malformed"):
        _promote(root, sha, dirs, files, api)
    assert not any(method in {"POST", "PATCH"} for method, _ in api.calls)


def test_promotion_rejects_wrong_source_before_github_mutation(tmp_path: Path) -> None:
    root, _sha, dirs, files = _fixture(tmp_path)
    api = _GitHub(root)
    with pytest.raises(guard.ReleaseIdentityError, match="event SHA"):
        _promote(root, "b" * 40, dirs, files, api)
    assert not any(method in {"POST", "PATCH"} for method, _ in api.calls)


def test_promotion_resumes_matching_partial_draft_without_replacing_assets(
    tmp_path: Path,
) -> None:
    root, sha, dirs, files = _fixture(tmp_path)
    api = _GitHub(root)
    api.fail_upload_name = "runtime-sidecars-linux.tar.gz"
    with pytest.raises(guard.ReleaseIdentityError, match="request failed"):
        _promote(root, sha, dirs, files, api)
    assert api.release is not None and api.release["draft"] is True
    first_assets = set(api.assets)

    release = _promote(root, sha, dirs, files, api)
    assert release["immutable"] is True
    assert first_assets <= set(api.assets)
    assert api.calls.count(("POST", "https://api.github.com/repos/Capsize-Games/airunner/releases")) == 1


def test_promotion_refuses_existing_published_release_without_mutation(
    tmp_path: Path,
) -> None:
    root, sha, dirs, files = _fixture(tmp_path)
    api = _GitHub(root)
    api.release = {
        "id": 71,
        "tag_name": "v1.2.3",
        "draft": False,
        "prerelease": False,
        "immutable": True,
    }
    api.release_source = sha
    with pytest.raises(guard.ReleaseIdentityError, match="expected mutable draft"):
        _promote(root, sha, dirs, files, api)
    assert not any(method in {"POST", "PATCH"} for method, _ in api.calls)


def test_published_event_verification_is_read_only(tmp_path: Path) -> None:
    root, sha, dirs, files = _fixture(tmp_path)
    api = _GitHub(root)
    api.release_source = sha
    # Simulate the complete release already published by the promotion run.
    for path in [*(item for directory in dirs for item in directory.iterdir()), *files]:
        api.assets[path.name] = {
            "name": path.name,
            "digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
            "state": "uploaded",
        }
    api.release = {
        "id": 71,
        "tag_name": "v1.2.3",
        "draft": False,
        "prerelease": False,
        "immutable": True,
    }

    result = guard.verify_published_release(
        repository="Capsize-Games/airunner",
        tag="v1.2.3",
        source_sha=sha,
        token="fixture-token",
        root=root,
        opener=api,
    )

    assert result["immutable"] is True
    assert all(method == "GET" for method, _ in api.calls)


def test_draft_lookup_reaches_later_release_pages() -> None:
    def opener(request, timeout):
        url = request.full_url
        if "/releases/tags/" in url:
            raise HTTPError(url, 404, "draft omitted", Message(), None)
        page = parse_qs(urlparse(url).query)["page"][0]
        if page == "1":
            return _Response([{"id": n, "tag_name": f"v-old-{n}"} for n in range(100)])
        assert page == "2"
        return _Response([{"id": 101, "tag_name": "v1", "draft": True}])

    assert guard._release_by_tag("Capsize-Games/airunner", "v1", "fixture-token", opener=opener)["id"] == 101


def test_draft_lookup_does_not_hide_authorization_failure() -> None:
    def opener(request, timeout):
        raise HTTPError(request.full_url, 403, "denied", Message(), None)

    with pytest.raises(guard.ReleaseIdentityError, match="request failed"):
        guard._release_by_tag("Capsize-Games/airunner", "v1", "fixture-token", opener=opener)


def test_promotion_requires_immutable_policy_before_any_mutation(tmp_path: Path) -> None:
    root, sha, dirs, files = _fixture(tmp_path)
    api = _GitHub(root)
    api.immutable_releases_enabled = False
    with pytest.raises(guard.ReleaseIdentityError, match="enabled before promotion"):
        _promote(root, sha, dirs, files, api)
    assert not any(method in {"POST", "PATCH", "PUT", "DELETE"} for method, _ in api.calls)
