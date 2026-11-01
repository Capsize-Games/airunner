"""Fail closed when a promoted package/tag/artifact identity is inconsistent."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class ReleaseIdentityError(ValueError):
    """A release tag, source, version, or existing asset conflicts."""


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


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
    root: Path,
    repository: str | None = None,
    token: str | None = None,
    opener: Callable[..., Any] = urlopen,
) -> str | None:
    """Verify annotated vX.Y.Z tag, source commit, and service version.

    Non-promoting workflow_dispatch runs intentionally keep supporting branch
    builds. Release events and dispatches that publish to PyPI must run from an
    annotated tag matching the services distribution version.
    """
    if event_name != "release" and not publish_pypi:
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
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with opener(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseIdentityError("cannot read existing release assets") from exc


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
    parser.add_argument("--check-release-assets", action="store_true")
    parser.add_argument("--repository")
    parser.add_argument("--asset-dir", action="append", type=Path, default=[])
    parser.add_argument("--asset-file", action="append", type=Path, default=[])
    args = parser.parse_args(argv)
    try:
        tag = verify_release_identity(
            event_name=args.event,
            ref=args.ref,
            source_sha=args.source_sha,
            service_version=args.service_version
            or read_service_release_version(Path.cwd()),
            publish_pypi=args.publish_pypi == "true",
            root=Path.cwd(),
            repository=os.environ.get("GITHUB_REPOSITORY"),
            token=os.environ.get("GITHUB_TOKEN"),
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
