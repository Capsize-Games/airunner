"""Tests for immutable release tag and asset identity guards."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import check_release_identity as guard  # noqa: E402


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "services").mkdir()
    (root / "services" / "setup.py").write_text(
        '_RELEASE_VERSION = "1.2.3"\n', encoding="utf-8"
    )
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Release Test")
    _git(root, "config", "user.email", "release-test@example.invalid")
    _git(root, "add", "services/setup.py")
    _git(root, "commit", "-qm", "release fixture")
    source_sha = _git(root, "rev-parse", "HEAD")
    _git(root, "tag", "-a", "v1.2.3", "-m", "v1.2.3")
    return root, source_sha


def test_release_identity_requires_annotated_version_tag_and_event_head(
    tmp_path: Path,
) -> None:
    root, source_sha = _repo(tmp_path)
    assert guard.verify_release_identity(
        event_name="release",
        ref="refs/tags/v1.2.3",
        source_sha=source_sha,
        service_version=None,
        publish_pypi=False,
        root=root,
    ) == "v1.2.3"

    with pytest.raises(guard.ReleaseIdentityError, match="event SHA"):
        guard.verify_release_identity(
            event_name="release",
            ref="refs/tags/v1.2.3",
            source_sha="1" * 40,
            service_version="1.2.3",
            publish_pypi=False,
            root=root,
        )


def test_release_identity_rejects_version_mismatch_and_retargeted_tag(
    tmp_path: Path,
) -> None:
    root, source_sha = _repo(tmp_path)
    with pytest.raises(guard.ReleaseIdentityError, match="v<services-version>"):
        guard.verify_release_identity(
            event_name="release",
            ref="refs/tags/v1.2.4",
            source_sha=source_sha,
            service_version="1.2.3",
            publish_pypi=False,
            root=root,
        )

    (root / "extra.txt").write_text("second commit", encoding="utf-8")
    _git(root, "add", "extra.txt")
    _git(root, "commit", "-qm", "retarget fixture")
    retargeted_sha = _git(root, "rev-parse", "HEAD")
    _git(root, "reset", "--hard", source_sha)
    _git(root, "tag", "-fa", "v1.2.3", retargeted_sha, "-m", "retagged")
    with pytest.raises(guard.ReleaseIdentityError, match="tag target"):
        guard.verify_release_identity(
            event_name="release",
            ref="refs/tags/v1.2.3",
            source_sha=source_sha,
            service_version="1.2.3",
            publish_pypi=False,
            root=root,
        )


def test_release_identity_compares_remote_annotated_tag_object(
    tmp_path: Path,
) -> None:
    root, source_sha = _repo(tmp_path)
    local_tag_object = _git(root, "rev-parse", "refs/tags/v1.2.3")

    def remote_tag_response(tag_object: str):
        def opener(request, timeout: int):
            assert timeout == 15
            assert request.full_url.endswith("/git/ref/tags/v1.2.3")
            return _Response(
                {
                    "ref": "refs/tags/v1.2.3",
                    "object": {"sha": tag_object, "type": "tag"},
                }
            )

        return opener

    assert guard.verify_release_identity(
        event_name="release",
        ref="refs/tags/v1.2.3",
        source_sha=source_sha,
        service_version="1.2.3",
        publish_pypi=False,
        root=root,
        repository="org/project",
        token="read-token",
        opener=remote_tag_response(local_tag_object),
    ) == "v1.2.3"
    with pytest.raises(guard.ReleaseIdentityError, match="remote annotated tag"):
        guard.verify_release_identity(
            event_name="release",
            ref="refs/tags/v1.2.3",
            source_sha=source_sha,
            service_version="1.2.3",
            publish_pypi=False,
            root=root,
            repository="org/project",
            token="read-token",
            opener=remote_tag_response("f" * 40),
        )


def test_branch_dispatch_remains_available_but_publish_requires_tag(
    tmp_path: Path,
) -> None:
    root, source_sha = _repo(tmp_path)
    assert guard.verify_release_identity(
        event_name="workflow_dispatch",
        ref="refs/heads/main",
        source_sha=source_sha,
        service_version=None,
        publish_pypi=False,
        root=root,
    ) is None
    with pytest.raises(guard.ReleaseIdentityError, match="annotated v<services-version>"):
        guard.verify_release_identity(
            event_name="workflow_dispatch",
            ref="refs/heads/main",
            source_sha=source_sha,
            service_version="1.2.3",
            publish_pypi=True,
            root=root,
        )


def test_release_promotion_dispatch_requires_the_annotated_version_tag(
    tmp_path: Path,
) -> None:
    root, source_sha = _repo(tmp_path)
    assert guard.verify_release_identity(
        event_name="workflow_dispatch",
        ref="refs/tags/v1.2.3",
        source_sha=source_sha,
        service_version="1.2.3",
        publish_pypi=False,
        promote_release=True,
        root=root,
    ) == "v1.2.3"
    with pytest.raises(guard.ReleaseIdentityError, match="annotated v<services-version>"):
        guard.verify_release_identity(
            event_name="workflow_dispatch",
            ref="refs/heads/main",
            source_sha=source_sha,
            service_version="1.2.3",
            publish_pypi=False,
            promote_release=True,
            root=root,
        )


class _Response:
    def __init__(self, value: Any) -> None:
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.value).encode()


def test_release_asset_listing_uses_read_only_api_and_paginates() -> None:
    urls: list[str] = []
    pages = {
        "https://api.github.com/repos/org/project/releases/tags/v1.2.3": {
            "id": 9
        },
        "https://api.github.com/repos/org/project/releases/9/assets?per_page=100&page=1": [
            {"name": f"asset-{index}"} for index in range(100)
        ],
        "https://api.github.com/repos/org/project/releases/9/assets?per_page=100&page=2": [
            {"name": "last-asset"}
        ],
    }

    def opener(request, timeout: int):
        assert timeout == 15
        assert request.get_header("Authorization") == "Bearer read-token"
        urls.append(request.full_url)
        return _Response(pages[request.full_url])

    names = guard.list_release_asset_names(
        repository="org/project",
        tag="v1.2.3",
        token="read-token",
        opener=opener,
    )
    assert len(names) == 101
    assert "last-asset" in names
    assert urls[-1].endswith("page=2")


def test_candidate_preflight_rejects_different_sha_and_any_name_collision(
    tmp_path: Path,
) -> None:
    source_sha = "a" * 40
    planned = tmp_path / guard_candidate_name("1.2.3", source_sha)
    planned.write_bytes(b"verified candidate")
    old_candidate = guard_candidate_name("1.2.3", "b" * 40)
    with pytest.raises(guard.ReleaseIdentityError, match="different source SHA"):
        guard.preflight_release_assets(
            existing_names={old_candidate},
            planned_paths=[planned],
            service_version="1.2.3",
            source_sha=source_sha,
        )

    with pytest.raises(guard.ReleaseIdentityError, match="partial upload"):
        guard.preflight_release_assets(
            existing_names={planned.name},
            planned_paths=[planned],
            service_version="1.2.3",
            source_sha=source_sha,
        )


def guard_candidate_name(version: str, source_sha: str) -> str:
    """Mirror the archive identity format without depending on its helper."""
    return f"airunner-services-linux-{version}-{source_sha[:12]}.tar.gz"
