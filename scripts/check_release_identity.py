"""Fail closed when a promoted package/tag/artifact identity is inconsistent."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import hashlib
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


class ReleaseIdentityError(ValueError):
    """A release tag, source, version, or existing asset conflicts."""


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_WORKFLOW = ".github/workflows/pypi-dispatch.yml"
_PROMOTION_JOB = "publish-release-assets"


def _git(root: Path, *args: str) -> str:
    """Run a read-only git query and return trimmed output."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReleaseIdentityError("cannot inspect release git identity") from exc
    return result.stdout.strip()


def read_service_release_version(root: Path) -> str:
    """Read the literal version constant without executing setup.py."""
    setup_path = root / "services" / "setup.py"
    try:
        tree = ast.parse(setup_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        raise ReleaseIdentityError("cannot read the services package version") from exc
    versions = [
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "_RELEASE_VERSION"
            for target in node.targets
        )
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ]
    if len(versions) != 1 or not versions[0]:
        raise ReleaseIdentityError("services setup version must be one literal")
    return versions[0]


def verify_release_identity(
    *,
    event_name: str,
    ref: str,
    source_sha: str,
    service_version: str | None,
    publish_pypi: bool,
    promote_release: bool = False,
    root: Path,
    repository: str | None = None,
    token: str | None = None,
    opener: Callable[..., Any] = urlopen,
) -> str | None:
    """Verify annotated vX.Y.Z tag, source commit, and service version.

    Non-promoting workflow_dispatch runs intentionally keep supporting branch
    builds. GitHub Release promotion and PyPI publication require an annotated
    tag matching the services distribution version.
    """
    if event_name != "release" and not publish_pypi and not promote_release:
        return None
    service_version = service_version or read_service_release_version(root)
    if not _SHA_RE.fullmatch(source_sha):
        raise ReleaseIdentityError("source SHA must be a full lowercase commit SHA")
    if not service_version or ref != f"refs/tags/v{service_version}":
        raise ReleaseIdentityError(
            "promotion requires the annotated v<services-version> tag"
        )

    tag_name = ref.removeprefix("refs/tags/")
    tag_ref = ref
    tag_type = _git(root, "cat-file", "-t", tag_ref)
    if tag_type != "tag":
        raise ReleaseIdentityError("promotion tag must be annotated")
    local_tag_object = _git(root, "rev-parse", "--verify", tag_ref)
    tag_commit = _git(root, "rev-parse", "--verify", f"{tag_ref}^{{commit}}")
    head_commit = _git(root, "rev-parse", "--verify", "HEAD^{commit}")
    if head_commit != source_sha:
        raise ReleaseIdentityError("checked-out source does not match event SHA")
    if tag_commit != source_sha:
        raise ReleaseIdentityError("current tag target does not match event SHA")
    if repository or token:
        if not repository or not token:
            raise ReleaseIdentityError("remote tag inspection needs repository auth")
        remote_ref = _github_json(
            f"https://api.github.com/repos/{repository}/git/ref/tags/"
            f"{quote(tag_name, safe='')}",
            token,
            opener=opener,
        )
        remote_object = remote_ref.get("object") if isinstance(remote_ref, dict) else None
        if (
            not isinstance(remote_ref, dict)
            or remote_ref.get("ref") != ref
            or not isinstance(remote_object, dict)
            or remote_object.get("type") != "tag"
            or remote_object.get("sha") != local_tag_object
        ):
            raise ReleaseIdentityError(
                "remote annotated tag object changed since checkout"
            )
    return tag_name


def _github_json(
    url: str,
    token: str,
    *,
    opener: Callable[..., Any] = urlopen,
) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2026-03-10",
        },
    )
    try:
        with opener(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseIdentityError("cannot read existing release assets") from exc


class _NoRedirect(HTTPRedirectHandler):
    """Do not forward a write token or release bytes through redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _api_request(
    url: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | bytes | None = None,
    content_type: str = "application/vnd.github+json",
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any] | list[Any]:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"api.github.com", "uploads.github.com"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ReleaseIdentityError("GitHub API URL is outside the allowed HTTPS services")
    if not token:
        raise ReleaseIdentityError("GitHub release mutation needs workflow authentication")
    data = payload if isinstance(payload, bytes) else (
        json.dumps(payload).encode("utf-8") if payload is not None else None
    )
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "airunner-release-promoter",
            "Content-Type": content_type,
        },
    )
    try:
        client = opener or build_opener(_NoRedirect()).open
        with client(request, timeout=60) as response:
            raw = response.read()
        if not raw:
            return {}
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, (dict, list)):
            raise ReleaseIdentityError("GitHub API response shape is invalid")
        return value
    except (HTTPError, URLError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseIdentityError("GitHub release promotion request failed") from exc


def _release_by_tag(
    repository: str,
    tag: str,
    token: str,
    *,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any] | None:
    url = f"https://api.github.com/repos/{repository}/releases/tags/{quote(tag, safe='')}"
    try:
        result = _api_request(url, token, opener=opener)
    except ReleaseIdentityError as exc:
        cause = exc.__cause__
        if not isinstance(cause, HTTPError) or cause.code != 404:
            raise
        # GitHub omits drafts from tag lookup; authenticated listing can find
        # a partial draft left by an interrupted promotion.
        for page in range(1, 101):
            releases = _api_request(
                f"https://api.github.com/repos/{repository}/releases?per_page=100&page={page}",
                token, opener=opener,
            )
            if not isinstance(releases, list) or any(
                not isinstance(item, dict) for item in releases
            ):
                raise ReleaseIdentityError("GitHub release list is invalid")
            matches = [item for item in releases if item.get("tag_name") == tag]
            if len(matches) > 1:
                raise ReleaseIdentityError("GitHub release tag is ambiguous")
            if matches:
                result = matches[0]
                break
            if len(releases) < 100:
                return None
        else:
            raise ReleaseIdentityError("GitHub release lookup exceeded page limit")
    if not isinstance(result, dict) or not isinstance(result.get("id"), int):
        raise ReleaseIdentityError("GitHub release response is invalid")
    return result


def _release_assets(
    repository: str,
    release_id: int,
    token: str,
    *,
    opener: Callable[..., Any] | None = None,
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    page = 1
    while page <= 100:
        value = _api_request(
            f"https://api.github.com/repos/{repository}/releases/{release_id}/assets?per_page=100&page={page}",
            token,
            opener=opener,
        )
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise ReleaseIdentityError("GitHub release asset listing is invalid")
        assets.extend(value)
        if len(value) < 100:
            return assets
        page += 1
    raise ReleaseIdentityError("GitHub release asset listing exceeds the safety limit")


def _asset_digest_map(assets: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for asset in assets:
        name = asset.get("name")
        digest = asset.get("digest")
        if (
            not isinstance(name, str)
            or not name
            or name in result
            or not isinstance(digest, str)
            or not digest.startswith("sha256:")
            or not _HEX_RE.fullmatch(digest.removeprefix("sha256:"))
            or asset.get("state") not in (None, "uploaded")
        ):
            raise ReleaseIdentityError("GitHub release asset identity is invalid")
        result[name] = digest
    return result


def _local_asset_digests(paths: list[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        if path.is_symlink() or not path.is_file() or path.name in result:
            raise ReleaseIdentityError("planned release asset is missing, unsafe, or duplicated")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result[path.name] = f"sha256:{digest}"
    return result


def _verify_checksum_manifest(paths: list[Path]) -> None:
    checksum_paths = [path for path in paths if path.name == "SHA256SUMS"]
    if len(checksum_paths) != 1:
        raise ReleaseIdentityError("promotion needs exactly one SHA256SUMS asset")
    checksum_path = checksum_paths[0]
    expected: dict[str, str] = {}
    try:
        lines = checksum_path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ReleaseIdentityError("release checksum manifest is invalid") from exc
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._+-]+)", line)
        if match is None or match.group(2) in expected:
            raise ReleaseIdentityError("release checksum manifest is malformed")
        expected[match.group(2)] = match.group(1)
    actual_paths = {path.name: path for path in paths if path != checksum_path}
    if set(expected) != set(actual_paths):
        raise ReleaseIdentityError("release checksum manifest asset set differs")
    for name, path in actual_paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
            raise ReleaseIdentityError("release checksum manifest digest differs")


def _require_promotion_groups(
    paths: list[Path], *, tag: str, source_sha: str, root: Path
) -> None:
    names = {path.name for path in paths}
    by_group = {
        group: [path for path in paths if path.parent.name == group]
        for group in (
            "python-dist", "sidecars", "linux-candidate", "debian", "runtime-wheels"
        )
    }
    python_names = {path.name for path in by_group["python-dist"]}
    for distribution in ("airunner_services", "airunner_native"):
        distribution_names = {
            name for name in python_names if name.startswith(distribution + "-")
        }
        if (
            sum(name.endswith(".whl") for name in distribution_names) != 1
            or sum(name.endswith(".tar.gz") for name in distribution_names) != 1
            or len(distribution_names) != 2
        ):
            raise ReleaseIdentityError("promotion is missing a Python distribution")
    if (
        not by_group["sidecars"] or not by_group["linux-candidate"]
        or not by_group["debian"] or not by_group["runtime-wheels"]
    ):
        raise ReleaseIdentityError("promotion is missing a required asset group")
    try:
        from linux_release_wheel_assets import (
            verify_assets as verify_runtime_wheel_assets,
        )

        verify_runtime_wheel_assets(
            by_group["runtime-wheels"][0].parent,
            source_manifest=root / "package/linux-release-v4-artifact-sources.json",
            selected_lock=root / "package/constraints-linux-nvidia-cu129-linux-release.txt",
            application_version=tag.removeprefix("v"),
            source_sha=source_sha,
        )
    except (ImportError, OSError, ValueError) as exc:
        raise ReleaseIdentityError(
            "runtime wheel release assets do not match the reviewed pin and provenance"
        ) from exc
    for name in ("runtime-sidecars-linux.tar.gz", "runtime-sidecars-windows.tar.gz"):
        if name not in names:
            raise ReleaseIdentityError("promotion is missing a verified sidecar archive")
    candidate_name = f"airunner-services-linux-{tag[1:]}-{source_sha[:12]}.tar.gz"
    if [path.name for path in by_group["linux-candidate"]] != [candidate_name]:
        raise ReleaseIdentityError("promotion needs exactly one Linux candidate archive")
    debs = [path for path in by_group["debian"] if path.name.startswith("airunner_") and path.name.endswith("_amd64.deb")]
    manifests = [path for path in by_group["debian"] if path.name == "airunner-apt-release.json"]
    if len(debs) != 1 or len(manifests) != 1 or len(by_group["debian"]) != 2:
        raise ReleaseIdentityError("promotion needs exactly one Debian package")
    if "airunner-apt-release.json" not in names or "SHA256SUMS" not in names:
        raise ReleaseIdentityError("promotion is missing the Debian manifest or checksum file")
    try:
        manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseIdentityError("Debian release manifest is invalid") from exc
    version = manifest.get("version") if isinstance(manifest, dict) else None
    upstream_version = version.rsplit(":", 1)[-1].split("-", 1)[0] if isinstance(version, str) else ""
    deb = debs[0]
    if (
        manifest.get("schema") != 2
        or manifest.get("repository") != "Capsize-Games/airunner"
        or manifest.get("tag") != tag
        or manifest.get("source_commit") != source_sha
        or manifest.get("workflow") != _WORKFLOW
        or manifest.get("workflow_event") != "workflow_dispatch"
        or manifest.get("promotion_job") != _PROMOTION_JOB
        or not isinstance(version, str)
        or not version.startswith(tag[1:])
        or upstream_version != tag[1:]
        or manifest.get("package") != "airunner"
        or manifest.get("architecture") != "amd64"
        or manifest.get("filename") != deb.name
        or manifest.get("size") != deb.stat().st_size
        or manifest.get("sha256") != hashlib.sha256(deb.read_bytes()).hexdigest()
    ):
        raise ReleaseIdentityError("Debian manifest does not bind this tag/source/package")


def _assert_release_draft(release: dict[str, Any], tag: str) -> None:
    if (
        release.get("tag_name") != tag
        or release.get("draft") is not True
        or release.get("prerelease") is not False
        or release.get("immutable") is True
    ):
        raise ReleaseIdentityError("existing release is not the expected mutable draft")


def promote_release_assets(
    *,
    repository: str,
    tag: str,
    source_sha: str,
    token: str,
    root: Path,
    asset_dirs: list[Path],
    asset_files: list[Path],
    expected_run_id: int,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Create or resume one draft, attach verified assets, then publish once."""
    if repository != "Capsize-Games/airunner":
        raise ReleaseIdentityError("release promotion repository is invalid")
    if not token:
        raise ReleaseIdentityError("release promotion needs workflow authentication")
    if not tag or not _SHA_RE.fullmatch(source_sha):
        raise ReleaseIdentityError("release promotion source identity is invalid")
    policy = _api_request(
        f"https://api.github.com/repos/{repository}/immutable-releases",
        token, opener=opener,
    )
    if not isinstance(policy, dict) or policy.get("enabled") is not True:
        raise ReleaseIdentityError("immutable releases must be enabled before promotion")
    if verify_release_identity(
        event_name="workflow_dispatch",
        ref=f"refs/tags/{tag}",
        source_sha=source_sha,
        service_version=None,
        publish_pypi=False,
        promote_release=True,
        root=root,
        repository=repository,
        token=token,
        opener=opener or urlopen,
    ) != tag:
        raise ReleaseIdentityError("release promotion requires its exact annotated version tag")

    paths = _asset_paths(asset_dirs, asset_files)
    _require_promotion_groups(paths, tag=tag, source_sha=source_sha, root=root)
    manifest_paths = [path for path in paths if path.name == "airunner-apt-release.json"]
    if len(manifest_paths) != 1:
        raise ReleaseIdentityError("promotion needs exactly one Debian manifest")
    try:
        deb_manifest = json.loads(manifest_paths[0].read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseIdentityError("Debian release manifest is invalid") from exc
    if (
        not isinstance(expected_run_id, int)
        or isinstance(expected_run_id, bool)
        or expected_run_id <= 0
        or not isinstance(deb_manifest, dict)
        or deb_manifest.get("workflow_run_id") != expected_run_id
    ):
        raise ReleaseIdentityError("Debian manifest is not bound to this promotion run")
    _verify_checksum_manifest(paths)
    expected = _local_asset_digests(paths)
    api_root = f"https://api.github.com/repos/{repository}"
    release = _release_by_tag(repository, tag, token, opener=opener)
    if release is None:
        release = _api_request(
            f"{api_root}/releases",
            token,
            method="POST",
            payload={
                "tag_name": tag,
                "target_commitish": source_sha,
                "name": tag,
                "body": "",
                "draft": True,
                "prerelease": False,
                "make_latest": "false",
            },
            opener=opener,
        )
        if not isinstance(release, dict) or not isinstance(release.get("id"), int):
            raise ReleaseIdentityError("GitHub did not create the expected release draft")
    _assert_release_draft(release, tag)
    release_id = release["id"]
    current_assets = _release_assets(repository, release_id, token, opener=opener)
    present = _asset_digest_map(current_assets)
    if set(present) - set(expected) or any(present[name] != expected[name] for name in present):
        raise ReleaseIdentityError("draft release contains an unexpected or changed asset")

    for path in paths:
        if path.name in present:
            continue
        upload_url = (
            f"https://uploads.github.com/repos/{repository}/releases/{release_id}/assets"
            f"?name={quote(path.name, safe='')}"
        )
        uploaded = _api_request(
            upload_url,
            token,
            method="POST",
            payload=path.read_bytes(),
            content_type="application/octet-stream",
            opener=opener,
        )
        if not isinstance(uploaded, dict) or (
            uploaded.get("name") != path.name or uploaded.get("digest") != expected[path.name]
        ):
            raise ReleaseIdentityError("uploaded release asset identity differs")

    current_assets = _release_assets(repository, release_id, token, opener=opener)
    if _asset_digest_map(current_assets) != expected:
        raise ReleaseIdentityError("draft assets do not match the complete verified asset set")
    published = _api_request(
        f"{api_root}/releases/{release_id}",
        token,
        method="PATCH",
        payload={"draft": False},
        opener=opener,
    )
    if not isinstance(published, dict) or (
        published.get("id") != release_id
        or published.get("tag_name") != tag
        or published.get("draft") is not False
        or published.get("prerelease") is not False
        or published.get("immutable") is not True
    ):
        raise ReleaseIdentityError("published GitHub release is not the expected immutable release")
    final = _release_by_tag(repository, tag, token, opener=opener)
    if final is None or final.get("id") != release_id or final.get("immutable") is not True:
        raise ReleaseIdentityError("published immutable release could not be verified")
    if _asset_digest_map(_release_assets(repository, release_id, token, opener=opener)) != expected:
        raise ReleaseIdentityError("published release asset digests changed")
    return final


def verify_published_release(
    *,
    repository: str,
    tag: str,
    source_sha: str,
    token: str,
    root: Path,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Read-only check for the release-published event; never appends assets."""
    if repository != "Capsize-Games/airunner":
        raise ReleaseIdentityError("published release repository is invalid")
    verify_release_identity(
        event_name="release",
        ref=f"refs/tags/{tag}",
        source_sha=source_sha,
        service_version=None,
        publish_pypi=False,
        root=root,
        repository=repository,
        token=token,
        opener=opener or urlopen,
    )
    release = _release_by_tag(repository, tag, token, opener=opener)
    if release is None or (
        release.get("draft") is not False
        or release.get("prerelease") is not False
        or release.get("immutable") is not True
    ):
        raise ReleaseIdentityError("published release is not immutable and stable")
    assets = _asset_digest_map(_release_assets(repository, release["id"], token, opener=opener))
    required = {"SHA256SUMS", "airunner-apt-release.json", "runtime-sidecars-linux.tar.gz", "runtime-sidecars-windows.tar.gz"}
    version = read_service_release_version(root)
    candidate = f"airunner-services-linux-{version}-{source_sha[:12]}.tar.gz"
    distributions = ("airunner_services", "airunner_native")
    has_python_packages = all(
        sum(name.startswith(distribution + "-") and name.endswith(".whl") for name in assets) == 1
        and sum(name.startswith(distribution + "-") and name.endswith(".tar.gz") for name in assets) == 1
        for distribution in distributions
    )
    has_deb = sum(
        name.startswith("airunner_") and name.endswith("_amd64.deb") for name in assets
    ) == 1
    if not required <= set(assets) or candidate not in assets or not has_deb or not has_python_packages:
        raise ReleaseIdentityError("published immutable release is missing required assets")
    return release


def list_release_asset_names(
    *,
    repository: str,
    tag: str,
    token: str,
    opener: Callable[..., Any] = urlopen,
) -> set[str]:
    """Read all existing asset names for one GitHub release tag."""
    if not repository or "/" not in repository or not token:
        raise ReleaseIdentityError("release asset inspection needs repository auth")
    api_root = f"https://api.github.com/repos/{repository}"
    release = _github_json(
        f"{api_root}/releases/tags/{quote(tag, safe='')}", token, opener=opener
    )
    if not isinstance(release, dict) or not isinstance(release.get("id"), int):
        raise ReleaseIdentityError("GitHub release response is invalid")
    names: set[str] = set()
    page = 1
    while True:
        assets = _github_json(
            f"{api_root}/releases/{release['id']}/assets?per_page=100&page={page}",
            token,
            opener=opener,
        )
        if not isinstance(assets, list):
            raise ReleaseIdentityError("GitHub release asset list is invalid")
        for asset in assets:
            name = asset.get("name") if isinstance(asset, dict) else None
            if not isinstance(name, str) or not name:
                raise ReleaseIdentityError("GitHub release asset entry is invalid")
            names.add(name)
        if len(assets) < 100:
            return names
        if page >= 100:
            raise ReleaseIdentityError("GitHub release asset listing is too large")
        page += 1


def preflight_release_assets(
    *,
    existing_names: set[str],
    planned_paths: list[Path],
    service_version: str,
    source_sha: str,
) -> None:
    """Reject a retargeted candidate or filename collisions before upload."""
    if not _SHA_RE.fullmatch(source_sha):
        raise ReleaseIdentityError("source SHA must be a full lowercase commit SHA")
    expected_archive_prefix = f"airunner-services-linux-{service_version}-"
    candidate_name_re = re.compile(
        rf"^{re.escape(expected_archive_prefix)}([0-9a-f]{{12}})\.tar\.gz$"
    )
    for name in existing_names:
        if name.startswith(expected_archive_prefix) and name.endswith(".tar.gz"):
            match = candidate_name_re.fullmatch(name)
            if match is None or match.group(1) != source_sha[:12]:
                raise ReleaseIdentityError(
                    "release already contains a candidate for this version "
                    "from a different source SHA"
                )

    planned_names: set[str] = set()
    for path in planned_paths:
        if not path.is_file() or path.is_symlink():
            raise ReleaseIdentityError("planned release asset is missing or unsafe")
        if path.name in planned_names:
            raise ReleaseIdentityError("planned release assets have duplicate names")
        planned_names.add(path.name)
    collisions = planned_names & existing_names
    if collisions:
        raise ReleaseIdentityError(
            "release already contains planned asset names; refusing partial upload"
        )


def _asset_paths(directories: list[Path], files: list[Path]) -> list[Path]:
    paths = list(files)
    for directory in directories:
        if not directory.is_dir():
            raise ReleaseIdentityError("release asset directory is missing")
        for path in directory.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ReleaseIdentityError("planned release asset is missing or unsafe")
            paths.append(path)
    return sorted(paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--service-version")
    parser.add_argument("--publish-pypi", choices=("true", "false"), default="false")
    parser.add_argument("--promote-release", choices=("true", "false"), default="false")
    parser.add_argument("--promote-release-assets", action="store_true")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--verify-published-release", action="store_true")
    parser.add_argument("--check-release-assets", action="store_true")
    parser.add_argument("--repository")
    parser.add_argument("--asset-dir", action="append", type=Path, default=[])
    parser.add_argument("--asset-file", action="append", type=Path, default=[])
    args = parser.parse_args(argv)
    try:
        token = os.environ.get("GITHUB_TOKEN", "")
        repository = args.repository or os.environ.get("GITHUB_REPOSITORY", "")
        if args.promote_release_assets:
            tag = args.ref.removeprefix("refs/tags/")
            release = promote_release_assets(
                repository=repository,
                tag=tag,
                source_sha=args.source_sha,
                token=token,
                root=Path.cwd(),
                asset_dirs=args.asset_dir,
                asset_files=args.asset_file,
                expected_run_id=args.run_id or 0,
            )
            print(f"published immutable release {release['tag_name']}")
            return 0
        if args.verify_published_release:
            tag = args.ref.removeprefix("refs/tags/")
            release = verify_published_release(
                repository=repository,
                tag=tag,
                source_sha=args.source_sha,
                token=token,
                root=Path.cwd(),
            )
            print(f"verified immutable release {release['tag_name']}")
            return 0
        tag = verify_release_identity(
            event_name=args.event,
            ref=args.ref,
            source_sha=args.source_sha,
            service_version=args.service_version
            or read_service_release_version(Path.cwd()),
            publish_pypi=args.publish_pypi == "true",
            promote_release=args.promote_release == "true",
            root=Path.cwd(),
            repository=repository,
            token=token,
        )
        if args.check_release_assets:
            if tag is None:
                raise ReleaseIdentityError(
                    "asset preflight is only valid for release promotion"
                )
            token = os.environ.get("GITHUB_TOKEN", "")
            existing = list_release_asset_names(
                repository=args.repository or "",
                tag=tag,
                token=token,
            )
            planned = _asset_paths(args.asset_dir, args.asset_file)
            preflight_release_assets(
                existing_names=existing,
                planned_paths=planned,
                service_version=args.service_version
                or read_service_release_version(Path.cwd()),
                source_sha=args.source_sha,
            )
        if tag is None:
            print("release identity check not required for this build")
        else:
            print(f"release identity verified for {tag}")
    except ReleaseIdentityError as exc:
        print(f"release identity error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
