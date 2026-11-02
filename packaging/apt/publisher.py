"""Pull verified Debian release assets into an existing signed apt repository."""

from __future__ import annotations

import argparse
import fcntl
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

_REPOSITORY = "Capsize-Games/airunner"
_WORKFLOW = ".github/workflows/pypi-dispatch.yml"
_PROMOTION_JOB = "publish-release-assets"
_MANIFEST_ASSET = "airunner-apt-release.json"
_MAX_CANDIDATES_PER_POLL = 20
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[0-9][A-Za-z0-9.+:~_-]{0,127}$")
_SAFE_TAG_RE = re.compile(r"^v[0-9][A-Za-z0-9.+_-]{0,126}$")
_REQUIRED_MANIFEST_KEYS = {
    "schema",
    "repository",
    "tag",
    "source_commit",
    "workflow",
    "workflow_event",
    "promotion_job",
    "workflow_run_id",
    "package",
    "version",
    "architecture",
    "filename",
    "size",
    "sha256",
}


class PublisherError(RuntimeError):
    """A release candidate or publication transaction is invalid."""


class _BoundedHTTPSRedirectHandler(HTTPRedirectHandler):
    """Follow redirects only to explicitly allowed HTTPS origins."""

    def __init__(self, origins: set[tuple[str, int]]):
        super().__init__()
        self.origins = origins

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlparse(urljoin(req.full_url, newurl))
        try:
            port = target.port if target.port is not None else 443
        except ValueError:
            return None
        if (
            target.scheme != "https"
            or target.hostname is None
            or (target.hostname.lower(), port) not in self.origins
            or target.username is not None
            or target.password is not None
        ):
            return None
        return super().redirect_request(req, fp, code, msg, headers, target.geturl())


def _open_https(
    request: Request,
    *,
    origins: set[tuple[str, int]],
    timeout: int,
    opener: Callable[..., Any] | None = None,
):
    if opener is not None:
        return opener(request, timeout=timeout)
    return build_opener(_BoundedHTTPSRedirectHandler(origins)).open(request, timeout=timeout)


@dataclass(frozen=True)
class Config:
    """Private runtime configuration, supplied outside the source tree."""

    api_base: str
    apt_base_url: str
    suite: str
    repo_root: Path
    gnupg_home: Path
    publish_script: Path
    compose_file: Path
    compose_project_dir: Path
    container_name: str
    work_dir: Path
    state_dir: Path
    public_key_file: Path
    verification_image: str
    timeout_seconds: int = 900
    retry_interval_seconds: int = 15

    @classmethod
    def load(cls, path: Path) -> "Config":
        try:
            info = path.lstat()
        except OSError as exc:
            raise PublisherError("publisher configuration is unavailable") from exc
        if (
            path.is_symlink()
            or not path.is_file()
            or info.st_mode & 0o077
            or (hasattr(os, "geteuid") and os.geteuid() == 0 and info.st_uid != 0)
        ):
            raise PublisherError("publisher configuration permissions are unsafe")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PublisherError("publisher configuration is unavailable") from exc
        expected = {
            "apt_base_url",
            "suite",
            "repo_root",
            "gnupg_home",
            "publish_script",
            "compose_file",
            "compose_project_dir",
            "container_name",
            "work_dir",
            "state_dir",
            "public_key_file",
            "verification_image",
            "timeout_seconds",
            "retry_interval_seconds",
        }
        if not isinstance(raw, dict) or set(raw) != expected:
            raise PublisherError("publisher configuration keys are invalid")
        api_base = f"https://api.github.com/repos/{_REPOSITORY}"
        apt_url = raw["apt_base_url"]
        if not isinstance(apt_url, str):
            raise PublisherError("apt base URL must be a credential-free HTTPS origin")
        try:
            parsed = urlparse(apt_url)
            port = parsed.port
        except ValueError as exc:
            raise PublisherError("apt base URL must be an HTTPS origin") from exc
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.path not in ("", "/")
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or port not in (None, 443)
            or any(character.isspace() or ord(character) < 32 for character in apt_url)
        ):
            raise PublisherError("apt base URL must be a credential-free HTTPS origin")
        image = raw["verification_image"]
        if not isinstance(image, str) or not re.fullmatch(
            r"[A-Za-z0-9._:/@-]+@sha256:[0-9a-f]{64}", image
        ):
            raise PublisherError("verification image must be pinned by digest")
        suite = raw["suite"]
        container = raw["container_name"]
        if not isinstance(suite, str) or not re.fullmatch(r"[a-z0-9-]{1,32}", suite):
            raise PublisherError("apt suite is invalid")
        if not isinstance(container, str) or not re.fullmatch(
            r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}", container
        ):
            raise PublisherError("container name is invalid")
        timeout = raw["timeout_seconds"]
        interval = raw["retry_interval_seconds"]
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, int)
            or not 60 <= timeout <= 900
            or isinstance(interval, bool)
            or not isinstance(interval, int)
            or not 1 <= interval <= 60
        ):
            raise PublisherError("publisher timeout settings are invalid")
        paths = {}
        for name in (
            "repo_root",
            "gnupg_home",
            "publish_script",
            "compose_file",
            "compose_project_dir",
            "work_dir",
            "state_dir",
            "public_key_file",
        ):
            value = raw[name]
            if not isinstance(value, str) or not value.startswith("/"):
                raise PublisherError("publisher runtime paths must be absolute")
            paths[name] = Path(value)
        return cls(
            api_base=api_base,
            apt_base_url=apt_url.rstrip("/"),
            suite=suite,
            container_name=container,
            verification_image=image,
            timeout_seconds=timeout,
            retry_interval_seconds=interval,
            **paths,
        )


def _api_json(url: str, *, opener: Callable[..., Any] | None = None) -> Any:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        raise PublisherError("GitHub API URL is outside the configured service")
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "airunner-apt-publisher",
        },
    )
    try:
        with _open_https(
            request,
            origins={("api.github.com", 443)},
            timeout=20,
            opener=opener,
        ) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublisherError("GitHub release metadata could not be read") from exc


def _asset_bytes(
    asset: dict[str, Any], *, limit: int = 512 * 1024 * 1024,
    opener: Callable[..., Any] | None = None,
) -> bytes:
    asset_id = asset.get("id")
    if isinstance(asset_id, bool) or not isinstance(asset_id, int) or asset_id <= 0:
        raise PublisherError("release asset identity is invalid")
    url = f"https://api.github.com/repos/{_REPOSITORY}/releases/assets/{asset_id}"
    request = Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "airunner-apt-publisher",
        },
    )
    try:
        with _open_https(
            request,
            origins={(host, 443) for host in (
                "api.github.com", "github.com", "release-assets.githubusercontent.com"
            )},
            timeout=45,
            opener=opener,
        ) as response:
            if len(response.geturl()) > 2048:
                raise PublisherError("release asset redirect is invalid")
            final = urlparse(response.geturl())
            if final.scheme != "https" or final.hostname not in {
                "api.github.com",
                "github.com",
                "release-assets.githubusercontent.com",
            }:
                raise PublisherError("release asset redirected outside GitHub")
            payload = response.read(limit + 1)
            if len(payload) > limit:
                raise PublisherError("GitHub release asset exceeds the size limit")
            return payload
    except (HTTPError, URLError, OSError) as exc:
        raise PublisherError("release asset could not be downloaded") from exc


def _strict_json_object(data: bytes) -> dict[str, Any]:
    """Parse one JSON object while rejecting duplicate property names."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise PublisherError("Debian release manifest has duplicate keys")
            result[key] = value
        return result

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublisherError("Debian release manifest is invalid") from exc
    if not isinstance(value, dict):
        raise PublisherError("Debian release manifest is not an object")
    return value


def validate_manifest(
    manifest: Any,
    *,
    release: dict[str, Any],
    run: dict[str, Any],
    run_jobs: Any,
    expected_run_id: int,
) -> dict[str, Any]:
    """Bind release, successful workflow run, source commit, and .deb bytes."""
    if not isinstance(manifest, dict) or set(manifest) != _REQUIRED_MANIFEST_KEYS:
        raise PublisherError("Debian release manifest shape is invalid")
    if not isinstance(release, dict) or not isinstance(run, dict):
        raise PublisherError("GitHub release or workflow metadata is invalid")
    if (
        isinstance(manifest["schema"], bool)
        or not isinstance(manifest["schema"], int)
        or manifest["schema"] != 2
        or manifest["repository"] != _REPOSITORY
    ):
        raise PublisherError("Debian release manifest repository is invalid")
    tag = manifest["tag"]
    sha = manifest["source_commit"]
    version = manifest["version"]
    if (
        not isinstance(tag, str)
        or not _SAFE_TAG_RE.fullmatch(tag)
        or release.get("tag_name") != tag
        or not isinstance(sha, str)
        or not _SHA_RE.fullmatch(sha)
        or not isinstance(version, str)
        or not _VERSION_RE.fullmatch(version)
        or tag[1:] != version.rsplit(":", 1)[-1].split("-", 1)[0]
    ):
        raise PublisherError("release tag, source, or Debian version disagrees")
    if (
        manifest["workflow"] != _WORKFLOW
        or manifest["workflow_event"] != "workflow_dispatch"
        or manifest["promotion_job"] != _PROMOTION_JOB
    ):
        raise PublisherError("release manifest names an unexpected workflow")
    run_id = manifest["workflow_run_id"]
    if isinstance(run_id, bool) or run_id != expected_run_id:
        raise PublisherError("release manifest workflow run does not match")
    if (
        run.get("id") != expected_run_id
        or run.get("path") != _WORKFLOW
        or run.get("event") != "workflow_dispatch"
        or run.get("head_sha") != sha
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
    ):
        raise PublisherError("matching release promotion workflow did not succeed")
    jobs = run_jobs.get("jobs") if isinstance(run_jobs, dict) else None
    promotion_jobs = [
        job for job in jobs
        if isinstance(job, dict) and job.get("name") == _PROMOTION_JOB
    ] if isinstance(jobs, list) else []
    if len(promotion_jobs) != 1 or (
        promotion_jobs[0].get("status") != "completed"
        or promotion_jobs[0].get("conclusion") != "success"
    ):
        raise PublisherError("matching run did not complete the release promotion job")
    if (
        manifest["package"] != "airunner"
        or manifest["architecture"] != "amd64"
        or not isinstance(manifest["filename"], str)
        or Path(manifest["filename"]).name != manifest["filename"]
        or not manifest["filename"].endswith("_amd64.deb")
        or not isinstance(manifest["size"], int)
        or isinstance(manifest["size"], bool)
        or not 1 <= manifest["size"] <= 512 * 1024 * 1024
        or not isinstance(manifest["sha256"], str)
        or not _HEX_RE.fullmatch(manifest["sha256"])
    ):
        raise PublisherError("Debian release manifest package fields are invalid")
    if (
        release.get("draft") is not False
        or release.get("prerelease") is not False
        or release.get("immutable") is not True
    ):
        raise PublisherError("only published immutable stable GitHub releases are accepted")
    return manifest


def _verify_remote_tag(api_base: str, tag: str, sha: str) -> None:
    reference = _api_json(f"{api_base}/git/ref/tags/{quote(tag, safe='')}")
    obj = reference.get("object") if isinstance(reference, dict) else None
    if not isinstance(obj, dict) or obj.get("type") != "tag":
        raise PublisherError("release tag is not annotated")
    tag_object = _api_json(f"{api_base}/git/tags/{quote(str(obj.get('sha')), safe='')}")
    target = tag_object.get("object") if isinstance(tag_object, dict) else None
    if (
        not isinstance(tag_object, dict)
        or tag_object.get("tag") != tag
        or not isinstance(target, dict)
        or target.get("type") != "commit"
        or target.get("sha") != sha
    ):
        raise PublisherError("annotated release tag points to a different commit")
    repository = _api_json(f"{api_base}")
    default_branch = repository.get("default_branch") if isinstance(repository, dict) else None
    if not isinstance(default_branch, str) or not re.fullmatch(r"[A-Za-z0-9._/-]{1,200}", default_branch):
        raise PublisherError("repository default branch is invalid")
    # The release commit is HEAD and the default branch is BASE. A release
    # that is an ancestor of the branch therefore reports behind/identical.
    compare = _api_json(f"{api_base}/compare/{quote(default_branch, safe='')}...{quote(sha, safe='')}")
    if not isinstance(compare, dict) or compare.get("status") not in {"behind", "identical"}:
        raise PublisherError("release source commit is not contained in the default branch")


def _version_gt(left: str, right: str) -> bool:
    try:
        result = subprocess.run(
            ["dpkg", "--compare-versions", left, "gt", right],
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PublisherError("cannot compare Debian versions") from exc
    return result.returncode == 0


def _parse_packages(data: bytes) -> dict[tuple[str, str], dict[str, str]]:
    try:
        text = gzip.decompress(data).decode("utf-8")
    except (OSError, EOFError, UnicodeDecodeError) as exc:
        raise PublisherError("apt package index is invalid") from exc
    entries: dict[tuple[str, str], dict[str, str]] = {}
    for paragraph in text.strip().split("\n\n"):
        fields: dict[str, str] = {}
        current: str | None = None
        for line in paragraph.splitlines():
            if line[:1].isspace() and current:
                fields[current] += "\n" + line
                continue
            name, sep, value = line.partition(":")
            if not sep:
                raise PublisherError("apt package index field is malformed")
            current = name
            fields[name] = value.strip()
        package, version = fields.get("Package"), fields.get("Version")
        if not package or not version or (package, version) in entries:
            raise PublisherError("apt package index contains duplicate or empty identity")
        entries[(package, version)] = fields
    return entries


def _run(args: list[str], *, timeout: int = 120, env: dict[str, str] | None = None) -> str:
    try:
        result = subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PublisherError("a publication command failed") from exc
    return result.stdout.strip()


def _regular_tree(root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        raise PublisherError("apt repository root is not a real directory")
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            entry = Path(directory) / name
            if entry.is_symlink() or not (entry.is_dir() or entry.is_file()):
                raise PublisherError("apt repository contains an unsafe filesystem entry")


def _verify_inrelease(repo: Path, keyring: Path, suite: str = "stable") -> None:
    inrelease = repo / "dists" / suite / "InRelease"
    if not inrelease.is_file() or not keyring.is_file():
        raise PublisherError("signed apt metadata or its public keyring is missing")
    _run(["gpgv", "--keyring", str(keyring), str(inrelease)], timeout=30)


def _signed_hash(inrelease: bytes, relative_path: str) -> tuple[str, int]:
    """Read a SHA256 digest from an already signature-verified InRelease."""
    try:
        text = inrelease.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PublisherError("signed apt metadata is not UTF-8") from exc
    lines = text.splitlines()
    try:
        body_start = lines.index("") + 1
        signature_start = lines.index("-----BEGIN PGP SIGNATURE-----")
        hash_start = lines.index("SHA256:", body_start, signature_start) + 1
    except ValueError as exc:
        raise PublisherError("signed apt metadata has no SHA256 index") from exc
    for line in lines[hash_start:signature_start]:
        pieces = line.split()
        if len(pieces) == 3 and pieces[2] == relative_path:
            digest, size_text, _ = pieces
            if not _HEX_RE.fullmatch(digest) or not size_text.isdecimal():
                break
            return digest, int(size_text)
    raise PublisherError("signed apt metadata omits the requested index")


def _repository_package(
    repo: Path,
    *,
    suite: str,
    package: str,
    version: str,
    expected_sha256: str | None = None,
) -> dict[str, str] | None:
    index = repo / "dists" / suite / "main" / "binary-amd64" / "Packages.gz"
    try:
        entries = _parse_packages(index.read_bytes())
    except OSError as exc:
        raise PublisherError("apt package index is missing") from exc
    record = entries.get((package, version))
    if record is None:
        return None
    filename = record.get("Filename", "")
    parsed = PurePosixPath(filename)
    if parsed.is_absolute() or not filename or any(part in ("", ".", "..") for part in parsed.parts):
        raise PublisherError("apt package filename is unsafe")
    digest = record.get("SHA256", "")
    if not _HEX_RE.fullmatch(digest) or (expected_sha256 and digest != expected_sha256):
        raise PublisherError("apt package index checksum differs from the release asset")
    package_path = repo.joinpath(*parsed.parts)
    if not package_path.is_file() or _file_sha256(package_path) != digest:
        raise PublisherError("published apt package bytes do not match the signed index")
    return record


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _highest_version(versions: list[str]) -> str:
    if not versions:
        raise PublisherError("apt repository has no AIRunner version to restore")
    highest = versions[0]
    for candidate in versions[1:]:
        if _version_gt(candidate, highest):
            highest = candidate
    return highest


def _download_candidate(config: Config) -> tuple[dict[str, Any], Path] | None:
    current = _current_versions(config)
    releases: list[Any] = []
    for page in range(1, 11):
        batch = _api_json(f"{config.api_base}/releases?per_page=100&page={page}")
        if not isinstance(batch, list):
            raise PublisherError("GitHub release list is invalid")
        releases.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise PublisherError("GitHub release history exceeds the safety limit")
    valid: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    inspected_candidates = 0
    for release in releases:
        if (
            not isinstance(release, dict)
            or release.get("draft")
            or release.get("prerelease")
            or release.get("immutable") is not True
        ):
            continue
        tag_hint = release.get("tag_name")
        if not isinstance(tag_hint, str) or not _SAFE_TAG_RE.fullmatch(tag_hint):
            continue
        if current and not all(_version_gt(tag_hint[1:], item) for item in current):
            continue
        assets = release.get("assets")
        if not isinstance(assets, list):
            raise PublisherError("GitHub release asset list is invalid")
        manifests = [item for item in assets if isinstance(item, dict) and item.get("name") == _MANIFEST_ASSET]
        if not manifests:
            continue
        inspected_candidates += 1
        if inspected_candidates > _MAX_CANDIDATES_PER_POLL:
            break
        if len(manifests) != 1:
            raise PublisherError("release has duplicate Debian manifests")
        try:
            raw = _asset_bytes(manifests[0], limit=256 * 1024)
            manifest_digest = manifests[0].get("digest")
            if manifest_digest != f"sha256:{hashlib.sha256(raw).hexdigest()}":
                raise PublisherError("GitHub manifest asset digest is invalid")
            manifest = _strict_json_object(raw)
        except PublisherError:
            raise
        run_id = manifest.get("workflow_run_id") if isinstance(manifest, dict) else None
        if isinstance(run_id, bool) or not isinstance(run_id, int):
            raise PublisherError("Debian release manifest run id is invalid")
        run = _api_json(f"{config.api_base}/actions/runs/{run_id}")
        if isinstance(run, dict) and (
            run.get("status") != "completed" or run.get("conclusion") != "success"
        ):
            continue
        run_jobs = _api_json(
            f"{config.api_base}/actions/runs/{run_id}/jobs?per_page=100"
        )
        candidate = validate_manifest(
            manifest, release=release, run=run, run_jobs=run_jobs,
            expected_run_id=run_id
        )
        debs = [
            item for item in assets
            if isinstance(item, dict) and item.get("name") == candidate["filename"]
        ]
        if len(debs) != 1:
            raise PublisherError("release is missing its exact Debian package asset")
        digest = debs[0].get("digest")
        if not isinstance(digest, str) or digest != f"sha256:{candidate['sha256']}":
            raise PublisherError("GitHub asset digest differs from the release manifest")
        _verify_remote_tag(config.api_base, candidate["tag"], candidate["source_commit"])
        valid.append((release, candidate, debs[0]))
    if not valid:
        return None

    newest: tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None = None
    for item in valid:
        if newest is None or _version_gt(item[1]["version"], newest[1]["version"]):
            newest = item
    assert newest is not None
    _, manifest, asset = newest
    payload = _asset_bytes(asset)
    if len(payload) != manifest["size"] or hashlib.sha256(payload).hexdigest() != manifest["sha256"]:
        raise PublisherError("downloaded Debian bytes differ from the release manifest")
    expected_name = f"airunner_{manifest['version']}_amd64.deb"
    if manifest["filename"] != expected_name:
        raise PublisherError("Debian release package filename is not canonical")
    config.work_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = config.work_dir / expected_name
    if destination.exists() or destination.is_symlink():
        raise PublisherError("candidate package path already exists")
    with destination.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(destination, 0o600)
    try:
        package_fields = {
            field: _run(["dpkg-deb", "--field", str(destination), field], timeout=15)
            for field in ("Package", "Version", "Architecture")
        }
    except PublisherError:
        destination.unlink(missing_ok=True)
        raise
    if package_fields != {
        "Package": "airunner",
        "Version": manifest["version"],
        "Architecture": "amd64",
    }:
        destination.unlink(missing_ok=True)
        raise PublisherError("downloaded Debian package metadata differs from manifest")
    return manifest, destination


def _current_versions(config: Config) -> list[str]:
    text = _run(["reprepro", "-b", str(config.repo_root), "list", config.suite, "airunner"])
    versions = re.findall(r"\bairunner\s+([^\s]+)\s*$", text, flags=re.MULTILINE)
    for version in versions:
        if not _VERSION_RE.fullmatch(version):
            raise PublisherError("current apt package version is invalid")
    return versions


_DAEMON_HEALTH_PROBE = r"""healthy=0
for ((attempt = 0; attempt < 45; attempt++)); do
    status=$(curl --silent --output /dev/null --write-out '%{http_code}' --connect-timeout 2 --max-time 3 http://127.0.0.1:8080/health) || status=
    if [ "$status" = 200 ]; then
        healthy=1
        break
    fi
    sleep 2
done
if [ "$healthy" != 1 ]; then
    echo 'installed daemon did not become healthy' >&2
    exit 1
fi
"""


def _docker_smoke(
    config: Config,
    *,
    repo: Path,
    version: str,
    source: str,
) -> None:
    script = r"""set -euo pipefail
install -d -m 0755 /etc/apt/keyrings
install -m 0644 /run/airunner-apt-keyring.gpg /etc/apt/keyrings/airunner-apt.gpg
printf 'deb [arch=amd64 signed-by=/etc/apt/keyrings/airunner-apt.gpg] %s %s main\n' "$APT_SOURCE" "$APT_SUITE" > /etc/apt/sources.list.d/airunner-apt.list
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod 0755 /usr/sbin/policy-rc.d
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "airunner=$APT_VERSION" curl
test "$(dpkg-query -W -f='${Version}' airunner)" = "$APT_VERSION"
mkdir -p /var/lib/airunner/runtime/configs /var/lib/airunner/runtime/sockets /var/lib/airunner/cache /var/lib/airunner/models /var/log/airunner
chown -R airunner:airunner /var/lib/airunner /var/log/airunner
runuser -u airunner -- env AIRUNNER_HEADLESS=1 AIRUNNER_DATA_DIR=/var/lib/airunner AIRUNNER_BASE_PATH=/var/lib/airunner AIRUNNER_RUNTIME_ROOT=/var/lib/airunner/runtime AIRUNNER_RUNTIME_CONFIG_DIR=/var/lib/airunner/runtime/configs AIRUNNER_RUNTIME_LOG_DIR=/var/log/airunner AIRUNNER_RUNTIME_SOCKET_DIR=/var/lib/airunner/runtime/sockets AIRUNNER_CACHE_DIR=/var/lib/airunner/cache AIRUNNER_MODEL_DIR=/var/lib/airunner/models AIRUNNER_DAEMON_CONFIG=/etc/airunner/daemon.yaml AIRUNNER_RUNTIME_BIND_HOST=127.0.0.1 AIRUNNER_HTTP_HOST=127.0.0.1 AIRUNNER_HTTP_PORT=8080 AIRUNNER_LLM_ON=1 QT_QPA_PLATFORM=offscreen DEV_ENV=0 HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 /usr/bin/airunner-headless --daemon-config /etc/airunner/daemon.yaml >/tmp/airunner-headless.log 2>&1 &
server_pid=$!
finish() { kill "$server_pid" 2>/dev/null || true; wait "$server_pid" 2>/dev/null || true; }
trap finish EXIT
""" + _DAEMON_HEALTH_PROBE
    container = f"airunner-apt-verify-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    args = [
        "docker",
        "run",
        "--rm",
        "--name",
        container,
        "--pull=missing",
        "--network=bridge",
        "--security-opt=no-new-privileges",
        "--cap-drop=ALL",
        "--cap-add=CHOWN",
        "--cap-add=SETUID",
        "--cap-add=SETGID",
        "--cap-add=DAC_OVERRIDE",
        "--pids-limit=128",
        "--memory=2g",
        "--cpus=2",
        "--mount",
        f"type=bind,src={repo.resolve()},dst=/srv/airunner-apt,readonly",
        "--mount",
        f"type=bind,src={config.public_key_file.resolve()},dst=/run/airunner-apt-keyring.gpg,readonly",
        "--env",
        f"APT_SOURCE={source}",
        "--env",
        f"APT_SUITE={config.suite}",
        "--env",
        f"APT_VERSION={version}",
        config.verification_image,
        "/bin/bash",
        "--noprofile",
        "--norc",
        "-euc",
        script,
    ]
    try:
        _run(args, timeout=config.timeout_seconds)
    except PublisherError:
        subprocess.run(
            ["docker", "rm", "--force", container],
            check=False,
            capture_output=True,
            timeout=30,
        )
        raise


def _live_metadata_matches(config: Config, manifest: dict[str, Any]) -> bool:
    url = f"{config.apt_base_url}/dists/{config.suite}/InRelease"
    request = Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "airunner-apt-publisher"})
    parsed_origin = urlparse(config.apt_base_url)
    origin = (parsed_origin.hostname or "", parsed_origin.port or 443)
    try:
        with _open_https(request, origins={origin}, timeout=15) as response:
            inrelease = response.read(8 * 1024 * 1024 + 1)
        if len(inrelease) > 8 * 1024 * 1024:
            return False
        inrelease_path = config.work_dir / "live-InRelease"
        inrelease_path.write_bytes(inrelease)
        _run(["gpgv", "--keyring", str(config.public_key_file), str(inrelease_path)], timeout=20)
        index_path = f"{config.suite}/main/binary-amd64/Packages.gz"
        expected_index_sha, expected_index_size = _signed_hash(inrelease, index_path)
        packages_request = Request(
            f"{config.apt_base_url}/dists/{index_path}",
            headers={"Cache-Control": "no-cache", "User-Agent": "airunner-apt-publisher"},
        )
        with _open_https(packages_request, origins={origin}, timeout=20) as response:
            data = response.read(32 * 1024 * 1024 + 1)
        if len(data) != expected_index_size or hashlib.sha256(data).hexdigest() != expected_index_sha:
            return False
        record = _parse_packages(data).get(("airunner", manifest["version"]))
        if record is None or record.get("SHA256") != manifest["sha256"]:
            return False
        filename = record.get("Filename", "")
        parsed = PurePosixPath(filename)
        if parsed.is_absolute() or any(part in ("", ".", "..") for part in parsed.parts):
            return False
        package_request = Request(
            f"{config.apt_base_url}/{quote(filename, safe='/')}",
            headers={"Cache-Control": "no-cache", "User-Agent": "airunner-apt-publisher"},
        )
        with _open_https(package_request, origins={origin}, timeout=45) as response:
            package_data = response.read(manifest["size"] + 1)
        if (
            len(package_data) != manifest["size"]
            or hashlib.sha256(package_data).hexdigest() != manifest["sha256"]
        ):
            return False
        return True
    except (HTTPError, URLError, OSError, PublisherError):
        return False


def _wait_for_live_metadata(config: Config, manifest: dict[str, Any]) -> None:
    deadline = time.monotonic() + config.timeout_seconds
    while time.monotonic() < deadline:
        if _live_metadata_matches(config, manifest):
            return
        time.sleep(config.retry_interval_seconds)
    raise PublisherError("signed public apt metadata did not converge before timeout")


def _compose(config: Config) -> None:
    _run(
        [
            "docker",
            "compose",
            "--project-directory",
            str(config.compose_project_dir),
            "--file",
            str(config.compose_file),
            "up",
            "--detach",
            "--no-deps",
            "--force-recreate",
            config.container_name,
        ],
        timeout=180,
    )


def _write_published_state(config: Config, manifest: dict[str, Any]) -> None:
    config.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    state_path = config.state_dir / "last-published.json"
    state_tmp = config.state_dir / f".last-published-{os.getpid()}-{uuid.uuid4().hex}.tmp"
    payload = json.dumps(
        {
            "tag": manifest["tag"],
            "source_commit": manifest["source_commit"],
            "version": manifest["version"],
            "sha256": manifest["sha256"],
        },
        sort_keys=True,
    ) + "\n"
    try:
        with state_tmp.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(state_tmp, 0o600)
        os.replace(state_tmp, state_path)
    finally:
        state_tmp.unlink(missing_ok=True)


def _publish_transaction(config: Config, manifest: dict[str, Any], deb: Path) -> None:
    repo = config.repo_root
    _regular_tree(repo)
    parent = repo.parent
    if config.work_dir.resolve().parent != parent.resolve():
        raise PublisherError("staging and repository must share the same parent filesystem")
    stage = parent / f".airunner-apt-next-{manifest['version']}-{os.getpid()}"
    backup = parent / f".airunner-apt-previous-{manifest['version']}-{os.getpid()}"
    failed = parent / f".airunner-apt-failed-{manifest['version']}-{os.getpid()}"
    if any(path.exists() or path.is_symlink() for path in (stage, backup, failed)):
        raise PublisherError("publication transaction path already exists")
    try:
        shutil.copytree(repo, stage, symlinks=False)
    except OSError as exc:
        shutil.rmtree(stage, ignore_errors=True)
        raise PublisherError("cannot create fresh apt repository staging tree") from exc
    promoted = False
    try:
        env = os.environ.copy()
        env["GNUPGHOME"] = str(config.gnupg_home)
        _run(
            [
                str(config.publish_script),
                str(stage),
                str(config.gnupg_home),
                config.suite,
                str(deb),
            ],
            timeout=300,
            env=env,
        )
        _regular_tree(stage)
        _verify_inrelease(stage, config.public_key_file, config.suite)
        record = _repository_package(
            stage,
            suite=config.suite,
            package="airunner",
            version=manifest["version"],
            expected_sha256=manifest["sha256"],
        )
        if record is None:
            raise PublisherError("staged apt index omits the candidate package")
        _docker_smoke(
            config,
            repo=stage,
            version=manifest["version"],
            source="file:/srv/airunner-apt",
        )

        os.replace(repo, backup)
        try:
            os.replace(stage, repo)
            _compose(config)
            promoted = True
            _wait_for_live_metadata(config, manifest)
            _docker_smoke(
                config,
                repo=repo,
                version=manifest["version"],
                source=config.apt_base_url,
            )
            _write_published_state(config, manifest)
        except Exception:
            if repo.exists():
                os.replace(repo, failed)
            os.replace(backup, repo)
            _compose(config)
            _verify_inrelease(repo, config.public_key_file, config.suite)
            previous_versions = _current_versions(config)
            if previous_versions:
                previous_version = _highest_version(previous_versions)
                previous_index = _repository_package(
                    repo,
                    suite=config.suite,
                    package="airunner",
                    version=previous_version,
                )
                if previous_index is None:
                    raise PublisherError("rollback repository omits its previous package")
                previous_manifest = {
                    "version": previous_version,
                    "sha256": previous_index["SHA256"],
                    "size": int(previous_index["Size"]),
                }
                _wait_for_live_metadata(config, previous_manifest)
                _docker_smoke(
                    config,
                    repo=repo,
                    version=previous_version,
                    source=config.apt_base_url,
                )
            shutil.rmtree(failed, ignore_errors=True)
            promoted = False
            raise
        promoted = True
        # The old tree remains available through all validation and state
        # persistence. A cleanup failure must not turn a healthy publication
        # into an apparent rollback; retain any leftover snapshot for repair.
        shutil.rmtree(backup, ignore_errors=True)
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        if backup.exists() and not promoted:
            # A rollback failure deliberately preserves the only known-good
            # snapshot for diagnosis instead of deleting it.
            pass


def run_once(config: Config) -> str:
    """Publish the newest fully verified release candidate, if any."""
    config.work_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = config.state_dir / "publisher.lock"
    config.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with lock_path.open("a", encoding="ascii") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        candidate = _download_candidate(config)
        if candidate is None:
            return "no verified Debian release candidate"
        manifest, deb = candidate
        try:
            current = _current_versions(config)
            if current and not all(_version_gt(manifest["version"], item) for item in current):
                return "apt repository already contains this or a newer version"
            _publish_transaction(config, manifest, deb)
            return f"published and verified airunner {manifest['version']}"
        finally:
            deb.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--once", action="store_true")
    action.add_argument("--validate-config", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = Config.load(args.config)
        if args.validate_config:
            print("publisher configuration is valid")
        else:
            if not hasattr(os, "geteuid") or os.geteuid() != 0:
                raise PublisherError("apt publisher must run as root")
            print(run_once(config))
    except (PublisherError, BlockingIOError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
