"""Source-bound Debian release publication tests using temporary fixtures."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.request import Request

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "packaging" / "apt"))

import publisher  # noqa: E402
import release_manifest  # noqa: E402


def _manifest() -> dict[str, object]:
    return {
        "schema": 2,
        "repository": "Capsize-Games/airunner",
        "tag": "v6.1.9",
        "source_commit": "a" * 40,
        "workflow": ".github/workflows/pypi-dispatch.yml",
        "workflow_event": "workflow_dispatch",
        "promotion_job": "publish-release-assets",
        "workflow_run_id": 124,
        "package": "airunner",
        "version": "6.1.9-1",
        "architecture": "amd64",
        "filename": "airunner_6.1.9-1_amd64.deb",
        "size": 13,
        "sha256": hashlib.sha256(b"fixture-deb\n").hexdigest(),
    }


def _run() -> dict[str, object]:
    return {
        "id": 124,
        "path": ".github/workflows/pypi-dispatch.yml",
        "event": "workflow_dispatch",
        "head_branch": "v6.1.9",
        "head_sha": "a" * 40,
        "status": "completed",
        "conclusion": "success",
    }


def _run_jobs() -> dict[str, object]:
    return {
        "jobs": [
            {
                "name": "publish-release-assets",
                "status": "completed",
                "conclusion": "success",
            }
        ]
    }


def test_manifest_binds_deb_version_source_tag_run_and_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Manifest generation reads package metadata and records exact bytes."""
    deb = tmp_path / "airunner_6.1.9-1_amd64.deb"
    deb.write_bytes(b"fixture-deb\n")
    tool_dir = tmp_path / "bin"
    tool_dir.mkdir()
    fake_dpkg = tool_dir / "dpkg-deb"
    fake_dpkg.write_text(
        "#!/bin/sh\n"
        'case "$3" in\n'
        '  Package) echo airunner ;;\n'
        '  Version) echo 6.1.9-1 ;;\n'
        '  Architecture) echo amd64 ;;\n'
        '  *) exit 2 ;;\n'
        "esac\n",
        encoding="utf-8",
    )
    fake_dpkg.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tool_dir}{os.pathsep}{os.environ['PATH']}")

    value = release_manifest.create_manifest(
        deb,
        repository="Capsize-Games/airunner",
        tag="v6.1.9",
        source_commit="a" * 40,
        workflow=".github/workflows/pypi-dispatch.yml",
        workflow_event="workflow_dispatch",
        promotion_job="publish-release-assets",
        run_id="124",
        expected_debian_version="6.1.9-1",
    )
    assert value["filename"] == deb.name
    assert value["sha256"] == hashlib.sha256(deb.read_bytes()).hexdigest()
    assert value["size"] == deb.stat().st_size
    assert value["workflow_run_id"] == 124


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tag", "v6.1.90"),
        ("repository", "Other/airunner"),
        ("workflow", ".github/workflows/other.yml"),
        ("source_commit", "A" * 40),
    ],
)
def test_manifest_generation_rejects_identity_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    """A Debian package cannot be rebound to a different tag or source."""
    deb = tmp_path / "airunner_6.1.9-1_amd64.deb"
    deb.write_bytes(b"fixture-deb\n")
    tool_dir = tmp_path / "bin"
    tool_dir.mkdir()
    fake_dpkg = tool_dir / "dpkg-deb"
    fake_dpkg.write_text(
        "#!/bin/sh\ncase \"$3\" in Package) echo airunner;; "
        "Version) echo 6.1.9-1;; Architecture) echo amd64;; esac\n",
        encoding="utf-8",
    )
    fake_dpkg.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tool_dir}{os.pathsep}{os.environ['PATH']}")
    kwargs: dict[str, str] = {
        "repository": "Capsize-Games/airunner",
        "tag": "v6.1.9",
        "source_commit": "a" * 40,
        "workflow": ".github/workflows/pypi-dispatch.yml",
        "workflow_event": "workflow_dispatch",
        "promotion_job": "publish-release-assets",
        "run_id": "124",
    }
    kwargs[field] = value
    with pytest.raises(release_manifest.ManifestError):
        release_manifest.create_manifest(deb, **kwargs, expected_debian_version="6.1.9-1")


def test_manifest_file_is_created_without_replacement(tmp_path: Path) -> None:
    """A repeated release build cannot silently replace manifest bytes."""
    path = tmp_path / "release.json"
    release_manifest.write_manifest(_manifest(), path)
    original = path.read_bytes()
    with pytest.raises(release_manifest.ManifestError):
        release_manifest.write_manifest(_manifest(), path)
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "apt_url",
    [
        "http://apt.example.invalid",
        "https://user:secret@apt.example.invalid",
        "https://apt.example.invalid?token=secret",
        "https://apt.example.invalid/#fragment",
        "https://apt.example.invalid:8443",
        "https://apt.example.invalid\nHost: attacker.invalid",
    ],
)
def test_config_rejects_non_origin_or_credential_bearing_apt_urls(
    tmp_path: Path, apt_url: str
) -> None:
    config_path = tmp_path / "publisher.json"
    config_path.write_text(
        json.dumps(
            {
                "apt_base_url": apt_url,
                "suite": "stable",
                "repo_root": str(tmp_path / "repo"),
                "gnupg_home": str(tmp_path / "gnupg"),
                "publish_script": str(tmp_path / "publish.sh"),
                "compose_file": str(tmp_path / "compose.yml"),
                "compose_project_dir": str(tmp_path),
                "container_name": "nginx",
                "work_dir": str(tmp_path / "work"),
                "state_dir": str(tmp_path / "state"),
                "public_key_file": str(tmp_path / "public.gpg"),
                "verification_image": "ubuntu:26.04@sha256:" + "c" * 64,
                "timeout_seconds": 900,
                "retry_interval_seconds": 15,
            }
        ),
        encoding="utf-8",
    )
    config_path.chmod(0o600)
    with pytest.raises(publisher.PublisherError, match="HTTPS origin"):
        publisher.Config.load(config_path)


def test_publisher_timeout_limit_fits_systemd_transaction_budget(tmp_path: Path) -> None:
    config_path = tmp_path / "publisher.json"
    values = {
        "apt_base_url": "https://apt.example.invalid",
        "suite": "stable",
        "repo_root": str(tmp_path / "repo"),
        "gnupg_home": str(tmp_path / "gnupg"),
        "publish_script": str(tmp_path / "publish.sh"),
        "compose_file": str(tmp_path / "compose.yml"),
        "compose_project_dir": str(tmp_path),
        "container_name": "nginx",
        "work_dir": str(tmp_path / "work"),
        "state_dir": str(tmp_path / "state"),
        "public_key_file": str(tmp_path / "public.gpg"),
        "verification_image": "ubuntu:26.04@sha256:" + "c" * 64,
        "timeout_seconds": 900,
        "retry_interval_seconds": 15,
    }
    config_path.write_text(json.dumps(values), encoding="utf-8")
    config_path.chmod(0o600)
    assert publisher.Config.load(config_path).timeout_seconds == 900

    values["timeout_seconds"] = 901
    config_path.write_text(json.dumps(values), encoding="utf-8")
    config_path.chmod(0o600)
    with pytest.raises(publisher.PublisherError, match="timeout settings"):
        publisher.Config.load(config_path)

    unit = (Path(__file__).resolve().parents[2] / "deployment/apt/airunner-apt-publisher.service").read_text(encoding="utf-8")
    assert "TimeoutStartSec=4h" in unit


def test_config_rejects_malformed_apt_url_as_publisher_error(tmp_path: Path) -> None:
    config_path = tmp_path / "publisher.json"
    values = {
        "apt_base_url": None,
        "suite": "stable",
        "repo_root": str(tmp_path / "repo"),
        "gnupg_home": str(tmp_path / "gnupg"),
        "publish_script": str(tmp_path / "publish.sh"),
        "compose_file": str(tmp_path / "compose.yml"),
        "compose_project_dir": str(tmp_path),
        "container_name": "nginx",
        "work_dir": str(tmp_path / "work"),
        "state_dir": str(tmp_path / "state"),
        "public_key_file": str(tmp_path / "public.gpg"),
        "verification_image": "ubuntu:26.04@sha256:" + "c" * 64,
        "timeout_seconds": 900,
        "retry_interval_seconds": 15,
    }
    config_path.write_text(json.dumps(values), encoding="utf-8")
    config_path.chmod(0o600)
    with pytest.raises(publisher.PublisherError, match="HTTPS origin"):
        publisher.Config.load(config_path)

    values["apt_base_url"] = "https://[malformed"
    config_path.write_text(json.dumps(values), encoding="utf-8")
    config_path.chmod(0o600)
    with pytest.raises(publisher.PublisherError, match="HTTPS origin"):
        publisher.Config.load(config_path)


def test_redirect_handler_allows_only_approved_https_origins() -> None:
    handler = publisher._BoundedHTTPSRedirectHandler({("apt.example.invalid", 443)})
    request = Request("https://apt.example.invalid/dists/stable/InRelease")
    accepted = handler.redirect_request(
        request, None, 302, "Found", {}, "/cached/InRelease"
    )
    assert accepted is not None
    assert accepted.full_url == "https://apt.example.invalid/cached/InRelease"
    assert handler.redirect_request(
        request, None, 302, "Found", {}, "http://apt.example.invalid/InRelease"
    ) is None
    assert handler.redirect_request(
        request, None, 302, "Found", {}, "https://evil.example/InRelease"
    ) is None
    assert handler.redirect_request(
        request, None, 302, "Found", {}, "https://user@apt.example.invalid/InRelease"
    ) is None


def test_github_api_request_does_not_forward_authorization_headers() -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"ok":true}'

    requests: list[Request] = []

    def fake_open(request: Request, *, timeout: int):
        requests.append(request)
        assert timeout == 20
        return Response()

    assert publisher._api_json(
        "https://api.github.com/repos/Capsize-Games/airunner", opener=fake_open
    ) == {"ok": True}
    assert len(requests) == 1
    assert requests[0].get_header("Authorization") is None


def test_publisher_accepts_only_successful_matching_promotion_identity() -> None:
    """The exact dispatch run and successful promotion job must agree."""
    accepted = publisher.validate_manifest(
        _manifest(),
        release={"tag_name": "v6.1.9", "draft": False, "prerelease": False, "immutable": True},
        run=_run(),
        run_jobs=_run_jobs(),
        expected_run_id=124,
    )
    assert accepted["source_commit"] == "a" * 40

    cases = [
        ({**_run(), "conclusion": "failure"}, 124),
        ({**_run(), "event": "push"}, 124),
        ({**_run(), "head_sha": "b" * 40}, 124),
        ({**_run(), "path": ".github/workflows/other.yml"}, 124),
        (_run(), 125),
    ]
    for run, run_id in cases:
        with pytest.raises(publisher.PublisherError):
            publisher.validate_manifest(
                _manifest(),
                release={"tag_name": "v6.1.9", "draft": False, "prerelease": False, "immutable": True},
                run=run,
                run_jobs=_run_jobs(),
                expected_run_id=run_id,
            )
    with pytest.raises(publisher.PublisherError, match="promotion job"):
        publisher.validate_manifest(
            _manifest(),
            release={"tag_name": "v6.1.9", "draft": False, "prerelease": False, "immutable": True},
            run=_run(),
            run_jobs={"jobs": [{"name": "publish-release-assets", "status": "completed", "conclusion": "failure"}]},
            expected_run_id=124,
        )


def test_publisher_rejects_release_tag_retarget_or_prerelease() -> None:
    """Release metadata must name the manifest tag and be stable/published."""
    with pytest.raises(publisher.PublisherError):
        publisher.validate_manifest(
            _manifest(),
            release={"tag_name": "v6.1.8", "draft": False, "prerelease": False, "immutable": True},
            run=_run(),
            run_jobs=_run_jobs(),
            expected_run_id=124,
        )
    with pytest.raises(publisher.PublisherError):
        publisher.validate_manifest(
            _manifest(),
            release={"tag_name": "v6.1.9", "draft": False, "prerelease": True, "immutable": True},
            run=_run(),
            run_jobs=_run_jobs(),
            expected_run_id=124,
        )
    with pytest.raises(publisher.PublisherError, match="immutable"):
        publisher.validate_manifest(
            _manifest(),
            release={"tag_name": "v6.1.9", "draft": False, "prerelease": False, "immutable": False},
            run=_run(),
            run_jobs=_run_jobs(),
            expected_run_id=124,
        )


def test_candidate_fetch_checks_release_run_tag_assets_and_package_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A candidate download follows the exact successful promotion run and tag."""
    manifest = _manifest()
    package_bytes = b"fixture-deb\n"
    manifest["size"] = len(package_bytes)
    manifest["sha256"] = hashlib.sha256(package_bytes).hexdigest()
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest_asset = {
        "id": 41,
        "name": "airunner-apt-release.json",
        "digest": f"sha256:{hashlib.sha256(manifest_bytes).hexdigest()}",
    }
    deb_asset = {
        "id": 42,
        "name": "airunner_6.1.9-1_amd64.deb",
        "digest": f"sha256:{manifest['sha256']}",
    }
    release = {
        "tag_name": "v6.1.9",
        "draft": False,
        "prerelease": False,
        "immutable": True,
        "assets": [manifest_asset, deb_asset],
    }
    config = publisher.Config(
        api_base="https://api.github.com/repos/Capsize-Games/airunner",
        apt_base_url="https://apt.example.invalid",
        suite="stable",
        repo_root=tmp_path / "repo",
        gnupg_home=tmp_path / "gnupg",
        publish_script=tmp_path / "publish.sh",
        compose_file=tmp_path / "compose.yml",
        compose_project_dir=tmp_path,
        container_name="airunner-apt",
        work_dir=tmp_path / "work",
        state_dir=tmp_path / "state",
        public_key_file=tmp_path / "keyring.gpg",
        verification_image="ubuntu:26.04@sha256:" + "c" * 64,
    )
    urls: list[str] = []

    def api(url: str) -> object:
        urls.append(url)
        if url.endswith("/releases?per_page=100&page=1"):
            return [release]
        if url.endswith("/releases?per_page=100&page=2"):
            return []
        if url.endswith("/actions/runs/124"):
            return _run()
        if url.endswith("/actions/runs/124/jobs?per_page=100"):
            return _run_jobs()
        if url.endswith("/git/ref/tags/v6.1.9"):
            return {"object": {"type": "tag", "sha": "d" * 40}}
        if url.endswith("/git/tags/" + "d" * 40):
            return {
                "tag": "v6.1.9",
                "object": {"type": "commit", "sha": "a" * 40},
            }
        if url.endswith("/repos/Capsize-Games/airunner"):
            return {"default_branch": "master"}
        if url.endswith("/compare/master..." + "a" * 40):
            return {"status": "behind"}
        raise AssertionError(f"unexpected API endpoint {url}")

    monkeypatch.setattr(publisher, "_api_json", api)
    monkeypatch.setattr(publisher, "_current_versions", lambda _config: ["6.1.3-3"])
    monkeypatch.setattr(
        publisher,
        "_asset_bytes",
        lambda asset, **_kwargs: manifest_bytes if asset["id"] == 41 else package_bytes,
    )
    monkeypatch.setattr(
        publisher,
        "_run",
        lambda args, **_kwargs: {
            "Package": "airunner",
            "Version": "6.1.9-1",
            "Architecture": "amd64",
        }[args[-1]],
    )

    result = publisher._download_candidate(config)
    assert result is not None
    actual_manifest, deb = result
    assert actual_manifest["source_commit"] == "a" * 40
    assert deb.read_bytes() == package_bytes
    assert any("/compare/" in url for url in urls)


def test_remote_tag_containment_uses_default_branch_as_compare_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested: list[str] = []
    status = "behind"

    def api(url: str) -> object:
        requested.append(url)
        if url.endswith("/git/ref/tags/v6.1.9"):
            return {"object": {"type": "tag", "sha": "d" * 40}}
        if url.endswith("/git/tags/" + "d" * 40):
            return {"tag": "v6.1.9", "object": {"type": "commit", "sha": "a" * 40}}
        if url.endswith("/repos/Capsize-Games/airunner"):
            return {"default_branch": "master"}
        if url.endswith("/compare/master..." + "a" * 40):
            return {"status": status}
        raise AssertionError(f"unexpected API endpoint {url}")

    monkeypatch.setattr(publisher, "_api_json", api)
    publisher._verify_remote_tag(
        "https://api.github.com/repos/Capsize-Games/airunner", "v6.1.9", "a" * 40
    )
    assert any(url.endswith("/compare/master..." + "a" * 40) for url in requested)

    status = "ahead"
    with pytest.raises(publisher.PublisherError, match="not contained"):
        publisher._verify_remote_tag(
            "https://api.github.com/repos/Capsize-Games/airunner", "v6.1.9", "a" * 40
        )


def test_signed_metadata_digest_and_debian_index_are_parsed_strictly() -> None:
    """Signed InRelease index identity and package stanza checks are exact."""
    package_path = "stable/main/binary-amd64/Packages.gz"
    signed = (
        "-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\n"
        "Suite: stable\nSHA256:\n"
        f"{'a' * 64} 123 {package_path}\n"
        "-----BEGIN PGP SIGNATURE-----\nfixture\n"
    ).encode()
    assert publisher._signed_hash(signed, package_path) == ("a" * 64, 123)
    index = (
        "Package: airunner\nVersion: 6.1.9-1\nArchitecture: amd64\n"
        "Filename: pool/main/a/airunner_6.1.9-1_amd64.deb\n"
        f"SHA256: {'b' * 64}\nSize: 10\n"
    ).encode()
    records = publisher._parse_packages(gzip.compress(index))
    assert records[("airunner", "6.1.9-1")]["Architecture"] == "amd64"
    with pytest.raises(publisher.PublisherError):
        publisher._signed_hash(signed, "stable/main/binary-amd64/Release")


def _transaction_config(tmp_path: Path) -> publisher.Config:
    root = tmp_path / "apt-root"
    repo = root / "repo"
    repo.mkdir(parents=True)
    (repo / "marker").write_text("previous", encoding="utf-8")
    public_key = repo / "airunner-apt-keyring.gpg"
    public_key.write_bytes(b"public-keyring-fixture")
    gnupg = root / "gnupg"
    gnupg.mkdir()
    publish_script = root / "publish.sh"
    publish_script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    publish_script.chmod(0o755)
    compose = root / "compose.yml"
    compose.write_text("services: {}\n", encoding="utf-8")
    work = root / "work"
    return publisher.Config(
        api_base="https://api.github.com/repos/Capsize-Games/airunner",
        apt_base_url="https://apt.example.invalid",
        suite="stable",
        repo_root=repo,
        gnupg_home=gnupg,
        publish_script=publish_script,
        compose_file=compose,
        compose_project_dir=root,
        container_name="airunner-apt",
        work_dir=work,
        state_dir=root / "state",
        public_key_file=public_key,
        verification_image="ubuntu:26.04@sha256:" + "c" * 64,
        timeout_seconds=60,
        retry_interval_seconds=1,
    )


def test_clean_install_command_uses_digest_image_and_only_read_only_repo_mounts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The package health check stays inside a throwaway container boundary."""
    config = _transaction_config(tmp_path)
    command: list[str] = []
    monkeypatch.setattr(publisher, "_run", lambda args, **_kwargs: command.extend(args) or "")

    publisher._docker_smoke(
        config,
        repo=config.repo_root,
        version="6.1.9-1",
        source="file:/srv/airunner-apt",
    )

    assert command[0:2] == ["docker", "run"]
    assert "--rm" in command
    assert "--network=bridge" in command
    assert config.verification_image in command
    mounts = [command[index + 1] for index, item in enumerate(command) if item == "--mount"]
    assert len(mounts) == 2
    assert all("readonly" in mount for mount in mounts)
    assert all("docker.sock" not in mount for mount in mounts)
    assert any("apt-get update" in item for item in command)
    assert any("airunner-headless --daemon-config" in item for item in command)


def test_compose_recreates_only_the_configured_service_without_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _transaction_config(tmp_path)
    command: list[str] = []
    monkeypatch.setattr(publisher, "_run", lambda args, **_kwargs: command.extend(args) or "")

    publisher._compose(config)

    assert command[:2] == ["docker", "compose"]
    assert "--no-deps" in command
    assert "--force-recreate" in command
    assert command[-1] == config.container_name
    assert command.count("up") == 1
    assert "down" not in command


def _candidate(tmp_path: Path) -> tuple[dict[str, object], Path]:
    deb = tmp_path / "airunner_6.1.9-1_amd64.deb"
    deb.write_bytes(b"fixture-deb\n")
    manifest = _manifest()
    manifest["sha256"] = hashlib.sha256(deb.read_bytes()).hexdigest()
    manifest["size"] = deb.stat().st_size
    return manifest, deb


@pytest.mark.parametrize("fail_smoke", [1, 2])
def test_failed_candidate_install_rolls_back_repository_and_container(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fail_smoke: int,
) -> None:
    """Both staging and post-promotion failures preserve and restore the old tree."""
    config = _transaction_config(tmp_path)
    manifest, deb = _candidate(tmp_path)
    compose_calls: list[str] = []
    smoke_calls = 0

    def fake_run(args: list[str], **kwargs: object) -> str:
        if args[0] == str(config.publish_script):
            stage = Path(args[1])
            (stage / "marker").write_text("candidate", encoding="utf-8")
        return ""

    def fake_smoke(*args: object, **kwargs: object) -> None:
        nonlocal smoke_calls
        smoke_calls += 1
        if smoke_calls == fail_smoke:
            raise publisher.PublisherError("synthetic clean-install failure")

    monkeypatch.setattr(publisher, "_run", fake_run)
    monkeypatch.setattr(publisher, "_verify_inrelease", lambda *_: None)
    monkeypatch.setattr(
        publisher,
        "_repository_package",
        lambda *_args, **_kwargs: {"SHA256": manifest["sha256"], "Size": str(manifest["size"])},
    )
    monkeypatch.setattr(publisher, "_docker_smoke", fake_smoke)
    monkeypatch.setattr(publisher, "_compose", lambda _config: compose_calls.append("recreate"))
    monkeypatch.setattr(publisher, "_current_versions", lambda _config: ["6.1.3-3"])
    monkeypatch.setattr(publisher, "_wait_for_live_metadata", lambda *_: None)

    with pytest.raises(publisher.PublisherError, match="synthetic clean-install failure"):
        publisher._publish_transaction(config, manifest, deb)

    assert (config.repo_root / "marker").read_text(encoding="utf-8") == "previous"
    assert compose_calls == ([] if fail_smoke == 1 else ["recreate", "recreate"])
    assert not list(config.repo_root.parent.glob(".airunner-apt-failed-*"))
    assert not list(config.repo_root.parent.glob(".airunner-apt-next-*"))


def test_failed_stage_copy_removes_partial_stage_and_keeps_live_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _transaction_config(tmp_path)
    manifest, deb = _candidate(tmp_path)
    real_copytree = publisher.shutil.copytree

    def partial_copy(source: Path, destination: Path, **kwargs: object):
        Path(destination).mkdir()
        (Path(destination) / "partial").write_text("incomplete", encoding="utf-8")
        raise OSError("synthetic copy failure")

    monkeypatch.setattr(publisher.shutil, "copytree", partial_copy)
    with pytest.raises(publisher.PublisherError, match="fresh apt repository staging tree"):
        publisher._publish_transaction(config, manifest, deb)
    monkeypatch.setattr(publisher.shutil, "copytree", real_copytree)

    assert (config.repo_root / "marker").read_text(encoding="utf-8") == "previous"
    assert not list(config.repo_root.parent.glob(".airunner-apt-next-*"))


def test_stale_failure_path_blocks_transaction_before_live_tree_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _transaction_config(tmp_path)
    manifest, deb = _candidate(tmp_path)
    failed = config.repo_root.parent / f".airunner-apt-failed-{manifest['version']}-{os.getpid()}"
    failed.mkdir()
    (failed / "preserve").write_text("stale diagnostic", encoding="utf-8")
    called = False

    def unexpected_run(*_args: object, **_kwargs: object) -> str:
        nonlocal called
        called = True
        raise AssertionError("publisher reached an external command")

    monkeypatch.setattr(publisher, "_run", unexpected_run)
    with pytest.raises(publisher.PublisherError, match="transaction path already exists"):
        publisher._publish_transaction(config, manifest, deb)

    assert not called
    assert (config.repo_root / "marker").read_text(encoding="utf-8") == "previous"
    assert (failed / "preserve").read_text(encoding="utf-8") == "stale diagnostic"


def test_state_persistence_failure_rolls_back_promoted_tree_and_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _transaction_config(tmp_path)
    manifest, deb = _candidate(tmp_path)
    compose_calls: list[str] = []

    def fake_run(args: list[str], **_kwargs: object) -> str:
        if args[0] == str(config.publish_script):
            (Path(args[1]) / "marker").write_text("candidate", encoding="utf-8")
        return ""

    monkeypatch.setattr(publisher, "_run", fake_run)
    monkeypatch.setattr(publisher, "_verify_inrelease", lambda *_: None)
    monkeypatch.setattr(
        publisher,
        "_repository_package",
        lambda *_args, **_kwargs: {"SHA256": manifest["sha256"], "Size": str(manifest["size"])},
    )
    monkeypatch.setattr(publisher, "_docker_smoke", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(publisher, "_compose", lambda _config: compose_calls.append("recreate"))
    monkeypatch.setattr(publisher, "_current_versions", lambda _config: ["6.1.3-3"])
    monkeypatch.setattr(publisher, "_wait_for_live_metadata", lambda *_: None)
    monkeypatch.setattr(
        publisher,
        "_write_published_state",
        lambda *_: (_ for _ in ()).throw(publisher.PublisherError("state write failed")),
    )

    with pytest.raises(publisher.PublisherError, match="state write failed"):
        publisher._publish_transaction(config, manifest, deb)

    assert (config.repo_root / "marker").read_text(encoding="utf-8") == "previous"
    assert compose_calls == ["recreate", "recreate"]
    assert not list(config.repo_root.parent.glob(".airunner-apt-failed-*"))
    assert not list(config.repo_root.parent.glob(".airunner-apt-next-*"))


def test_successful_transaction_recreates_only_configured_container_and_keeps_new_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A verified candidate is promoted and the prior snapshot is removed."""
    config = _transaction_config(tmp_path)
    manifest, deb = _candidate(tmp_path)
    compose_calls: list[str] = []

    def fake_run(args: list[str], **kwargs: object) -> str:
        if args[0] == str(config.publish_script):
            (Path(args[1]) / "marker").write_text("candidate", encoding="utf-8")
        return ""

    monkeypatch.setattr(publisher, "_run", fake_run)
    monkeypatch.setattr(publisher, "_verify_inrelease", lambda *_: None)
    monkeypatch.setattr(
        publisher,
        "_repository_package",
        lambda *_args, **_kwargs: {"SHA256": manifest["sha256"], "Size": str(manifest["size"])},
    )
    monkeypatch.setattr(publisher, "_docker_smoke", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(publisher, "_compose", lambda _config: compose_calls.append("recreate"))
    monkeypatch.setattr(publisher, "_wait_for_live_metadata", lambda *_: None)

    publisher._publish_transaction(config, manifest, deb)

    assert (config.repo_root / "marker").read_text(encoding="utf-8") == "candidate"
    assert compose_calls == ["recreate"]
    assert json.loads((config.state_dir / "last-published.json").read_text())["tag"] == "v6.1.9"
    assert not list(config.repo_root.parent.glob(".airunner-apt-previous-*"))
