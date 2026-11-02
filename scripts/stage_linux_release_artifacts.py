"""Stage the exact V4 Linux wheels without installing or importing them.

Direct HTTPS inputs are pinned to canonical artifact URLs and SHA-256 digests.
Hosted build inputs are fetched by immutable GitHub Actions artifact ID through
the authenticated API; signed redirect URLs are used only in memory. The
manifest deliberately contains no machine-local paths or signed URLs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "package/linux-release-v4-artifact-sources.json"
CHUNK = 1024 * 1024
ALLOWED_HOSTS = {
    "files.pythonhosted.org", "download.pytorch.org", "download-r2.pytorch.org",
    "github.com", "release-assets.githubusercontent.com",
}
GITHUB_ACTIONS_HOSTS = {
    "api.github.com", "github.com", "pipelines.actions.githubusercontent.com",
    "results-receiver.actions.githubusercontent.com", "artifactcache.actions.githubusercontent.com",
}


class StageError(RuntimeError):
    pass


class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    """Check each redirect target before urllib makes the next request."""

    def __init__(self, allowed_hosts: set[str], allow_githubusercontent: bool = False,
                 allow_actions_storage: bool = False) -> None:
        super().__init__()
        self.allowed_hosts = allowed_hosts
        self.allow_githubusercontent = allow_githubusercontent
        self.allow_actions_storage = allow_actions_storage

    def redirect_request(self, request, response, code, message, headers, new_url):
        from urllib.parse import urlsplit

        target = urlsplit(new_url)
        host_ok = target.hostname in self.allowed_hosts if target.hostname else False
        if self.allow_actions_storage and target.hostname:
            host_ok = host_ok or _actions_redirect_allowed(target)
        if target.scheme != "https" or target.username or target.password or not host_ok:
            raise StageError("redirect target is outside the HTTPS artifact host allowlist")
        if not self.allow_actions_storage and target.query and target.hostname != "release-assets.githubusercontent.com":
            raise StageError("redirect query parameters are allowed only for canonical release-asset redirects")
        if self.allow_actions_storage and not _actions_redirect_allowed(target) and target.query:
            raise StageError("signed query parameters are allowed only on the scoped Actions storage redirect")
        safe_headers = {
            key: value for key, value in request.header_items()
            if key.lower() in {"accept", "user-agent", "x-github-api-version"}
        }
        return urllib.request.Request(new_url, headers=safe_headers, method="GET")


def _actions_redirect_allowed(target) -> bool:
    from urllib.parse import parse_qs

    if target.scheme != "https" or target.username or target.password or not target.hostname:
        return False
    if target.hostname in GITHUB_ACTIONS_HOSTS:
        return not target.query
    storage_host = bool(re.fullmatch(r"productionresultssa[0-9]+\.blob\.core\.windows\.net", target.hostname))
    uuid = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    scoped_path = re.fullmatch(
        rf"/actions-results/{uuid}/workflow-job-run-{uuid}/artifacts/[0-9a-f]{{64}}\.zip",
        target.path,
    )
    query_keys = set(parse_qs(target.query, keep_blank_values=True))
    return bool(storage_host and scoped_path and len(target.query) <= 8192
                and {"sig", "se", "sv", "sr", "sp"}.issubset(query_keys) and not target.fragment)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def check_spec(spec: dict[str, Any]) -> None:
    filename = spec["filename"]
    if (not isinstance(filename, str) or Path(filename).name != filename or "\\" in filename
            or "/" in filename or ":" in filename or "\0" in filename or not filename.endswith(".whl")):
        raise StageError("manifest contains an unsafe wheel filename")
    if not re.fullmatch(r"[0-9a-f]{64}", spec["sha256"]):
        raise StageError("manifest contains an invalid wheel digest")
    if not isinstance(spec["size_bytes"], int) or not 0 < spec["size_bytes"] <= 2_147_483_648:
        raise StageError("manifest contains an invalid wheel size")


def copy_checked(source: Path, target: Path, spec: dict[str, Any]) -> None:
    if source.is_symlink() or not source.is_file():
        raise StageError(f"wheel input is not a regular file: {spec['filename']}")
    if source.stat().st_size != spec["size_bytes"] or sha256_file(source) != spec["sha256"]:
        raise StageError(f"wheel size or digest mismatch: {spec['filename']}")
    shutil.copyfile(source, target)


def download_https(url: str, target: Path, spec: dict[str, Any]) -> None:
    from urllib.parse import urlsplit

    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
            or parsed.username or parsed.password or parsed.fragment or parsed.query):
        raise StageError("manifest HTTPS URL is not an approved canonical source")
    request = urllib.request.Request(url, headers={"User-Agent": "airunner-release-stager/1"})
    digest = hashlib.sha256()
    size = 0
    created_target = False
    try:
        opener = urllib.request.build_opener(RestrictedRedirect(ALLOWED_HOSTS))
        with opener.open(request, timeout=120) as response:
            final = urlsplit(response.geturl())
            if (final.scheme != "https" or final.hostname not in ALLOWED_HOSTS or final.username
                    or final.password or (final.query and final.hostname != "release-assets.githubusercontent.com")):
                raise StageError("HTTPS input redirected outside approved artifact hosts")
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    announced_size = int(content_length)
                except ValueError as error:
                    raise StageError("download has a malformed Content-Length") from error
                if announced_size != spec["size_bytes"]:
                    raise StageError("download Content-Length differs from its pinned wheel size")
            with target.open("xb") as output:
                created_target = True
                while block := response.read(CHUNK):
                    size += len(block)
                    if size > spec["size_bytes"]:
                        raise StageError("download exceeds the pinned wheel size")
                    digest.update(block)
                    output.write(block)
    except (OSError, urllib.error.URLError, StageError) as error:
        if created_target:
            target.unlink(missing_ok=True)
        if isinstance(error, StageError):
            raise
        raise StageError(f"could not fetch {spec['filename']}") from error
    if size != spec["size_bytes"] or digest.hexdigest() != spec["sha256"]:
        if created_target:
            target.unlink(missing_ok=True)
        raise StageError(f"download size or digest mismatch: {spec['filename']}")


class RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise StageError("GitHub artifact metadata endpoint unexpectedly redirected")


def verify_actions_metadata(source: dict[str, Any], token: str) -> int:
    repo = source["repo"]
    artifact_id = source["artifact_id"]
    url = f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "airunner-release-stager/1",
    })
    opener = urllib.request.build_opener(RejectRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            body = response.read(64 * 1024 + 1)
    except (OSError, urllib.error.URLError, StageError) as error:
        if isinstance(error, StageError):
            raise
        raise StageError(f"could not verify Actions artifact metadata {artifact_id}") from error
    if len(body) > 64 * 1024:
        raise StageError("Actions artifact metadata response exceeded its size limit")
    try:
        metadata = json.loads(body)
    except json.JSONDecodeError as error:
        raise StageError("Actions artifact metadata is malformed") from error
    workflow = metadata.get("workflow_run") or {}
    if (metadata.get("id") != artifact_id or metadata.get("name") != source.get("artifact_name")
            or metadata.get("expired") is not False or workflow.get("id") != source.get("run_id")
            or workflow.get("head_sha") != source.get("source_revision")):
        raise StageError("Actions artifact identity, source revision, or expiry state differs from manifest")
    size = metadata.get("size_in_bytes")
    if not isinstance(size, int) or size <= 0 or size > source["max_archive_bytes"]:
        raise StageError("Actions artifact metadata has an invalid or oversized archive")
    return size


def actions_zip(source: dict[str, Any], token: str, expected_size: int):
    if source["kind"] == "actions_artifact_pending":
        raise StageError(f"Actions artifact handoff is not bound yet: {source['filename']}")
    repo = source["repo"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise StageError("invalid Actions artifact repository")
    artifact_id = source["artifact_id"]
    if not isinstance(artifact_id, int) or artifact_id <= 0:
        raise StageError("invalid Actions artifact ID")
    url = f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "airunner-release-stager/1",
    })
    max_bytes = source.get("max_archive_bytes")
    if not isinstance(max_bytes, int) or not 1 <= max_bytes <= 2_147_483_648:
        raise StageError("Actions artifact has no safe archive size bound")
    payload = tempfile.SpooledTemporaryFile(max_size=64 * 1024 * 1024, mode="w+b")
    digest = hashlib.sha256()
    size = 0
    try:
        opener = urllib.request.build_opener(RestrictedRedirect(GITHUB_ACTIONS_HOSTS,
                                                                 allow_actions_storage=True))
        with opener.open(request, timeout=120) as response:
            from urllib.parse import urlsplit

            final = urlsplit(response.geturl())
            if not _actions_redirect_allowed(final):
                raise StageError("Actions artifact redirected outside GitHub's HTTPS artifact hosts")
            content_length = response.headers.get("Content-Length")
            try:
                announced_size = int(content_length) if content_length is not None else None
            except ValueError as error:
                raise StageError("Actions archive has malformed Content-Length") from error
            if announced_size is None or announced_size != expected_size:
                raise StageError("Actions archive Content-Length differs from authenticated metadata")
            while block := response.read(CHUNK):
                size += len(block)
                if size > max_bytes:
                    raise StageError("Actions artifact exceeds its maximum archive size")
                digest.update(block)
                payload.write(block)
    except (OSError, urllib.error.URLError, StageError) as error:
        payload.close()
        if isinstance(error, StageError):
            raise
        raise StageError(f"could not retrieve Actions artifact {artifact_id}") from error
    try:
        verify_actions_archive_digest(digest.hexdigest(), source["archive_sha256"])
    except StageError:
        payload.close()
        raise StageError(f"Actions artifact archive digest mismatch: {artifact_id}") from None
    payload.seek(0)
    return payload


def extract_actions_wheels(payload, expected: list[dict[str, Any]], destination: Path) -> list[dict[str, Any]]:
    expected_by_name = {row["filename"]: row for row in expected}
    extracted: set[str] = set()
    try:
        with zipfile.ZipFile(payload) as archive:
            names: set[str] = set()
            for info in archive.infolist():
                name = info.filename
                path = PurePosixPath(name)
                mode = (info.external_attr >> 16) & 0o170000
                if (not name or "\\" in name or path.is_absolute() or ".." in path.parts
                        or (path.parts and path.parts[0].endswith(":")) or "\0" in name
                        or any(part in {"", "."} for part in name.rstrip("/").split("/"))
                        or mode not in {0, stat.S_IFREG, stat.S_IFDIR} or name in names):
                    raise StageError("Actions artifact contains an unsafe or duplicate path")
                names.add(name)
            for info in archive.infolist():
                basename = PurePosixPath(info.filename).name
                if basename not in expected_by_name:
                    continue
                if basename in extracted:
                    raise StageError("Actions artifact contains duplicate expected wheel names")
                row = expected_by_name[basename]
                target = destination / basename
                with archive.open(info) as source, target.open("xb") as output:
                    digest = hashlib.sha256()
                    size = 0
                    while block := source.read(CHUNK):
                        size += len(block)
                        if size > row["size_bytes"]:
                            raise StageError("Actions wheel exceeds its pinned size")
                        digest.update(block)
                        output.write(block)
                if size != row["size_bytes"] or digest.hexdigest() != row["sha256"]:
                    target.unlink(missing_ok=True)
                    raise StageError(f"Actions wheel digest mismatch: {basename}")
                extracted.add(basename)
    except zipfile.BadZipFile as error:
        raise StageError("Actions artifact is not a valid ZIP") from error
    if extracted != set(expected_by_name):
        raise StageError("Actions artifact is missing one or more pinned wheels")
    return [{"filename": name, "sha256": expected_by_name[name]["sha256"], "size_bytes": expected_by_name[name]["size_bytes"]}
            for name in sorted(extracted)]


def validate_lock(manifest: dict[str, Any], lockfile: Path) -> None:
    rows = manifest.get("artifact_sources")
    count = manifest.get("selected_count")
    if not isinstance(rows, list) or not isinstance(count, int) or count < 1 or len(rows) != count:
        raise StageError("manifest rows do not match its selected_count")
    if not re.fullmatch(r"[0-9a-f]{64}", manifest.get("selected_lock_sha256", "")):
        raise StageError("manifest selected-lock digest is invalid")
    if lockfile.is_symlink() or not lockfile.is_file() or sha256_file(lockfile) != manifest["selected_lock_sha256"]:
        raise StageError("selected requirements file does not match the manifest lock digest")
    lock_text = lockfile.read_text(encoding="utf-8")
    if " @ " in lock_text or "https://" in lock_text or "file:" in lock_text or "--index-url" in lock_text:
        raise StageError("selected lock contains direct URLs or index configuration")
    locked: dict[str, tuple[str, list[str]]] = {}
    current_name: str | None = None
    current_version: str | None = None
    current_hashes: list[str] = []

    def finish() -> None:
        nonlocal current_name, current_version, current_hashes
        if current_name is None or current_version is None:
            return
        if current_name in locked:
            raise StageError("selected lock repeats a package")
        locked[current_name] = (current_version, current_hashes)
        current_name = current_version = None
        current_hashes = []

    for line in lock_text.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        if candidate.endswith("\\"):
            candidate = candidate[:-1].rstrip()
        if candidate.startswith("--hash=sha256:"):
            if current_name is None or not re.fullmatch(r"--hash=sha256:[0-9a-f]{64}", candidate):
                raise StageError("selected lock has an unexpected or malformed hash option")
            current_hashes.append(candidate.rsplit(":", 1)[1])
            continue
        if candidate.startswith("-"):
            raise StageError("selected lock contains an unsupported option")
        finish()
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s]+)", candidate)
        if not match:
            raise StageError("selected lock contains a non-pinned or malformed requirement")
        current_name, current_version = match.groups()
    finish()
    normalized = {name.lower().replace("_", "-"): (version, hashes) for name, (version, hashes) in locked.items()}
    if len(normalized) != count:
        raise StageError(f"selected lock does not contain {count} unique name==version rows")
    expected_pins = {row["name"].lower().replace("_", "-"): (row["version"], [row["sha256"]]) for row in rows}
    if normalized != expected_pins:
        raise StageError("selected lock pins or hashes do not match the artifact manifest")


def checked_repo_wheel_path(value: str) -> PurePosixPath:
    if (not isinstance(value, str) or "\\" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise StageError("unsafe repository wheelhouse path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != "package":
        raise StageError("unsafe repository wheelhouse path")
    return relative


def verify_actions_archive_digest(actual_sha256: str, expected_sha256: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or actual_sha256 != expected_sha256:
        raise StageError("Actions artifact archive digest mismatch")


def stage(manifest_path: Path, lockfile: Path, destination: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("status") != "candidate-only; not activated":
        raise StageError("unsupported or non-candidate manifest")
    rows = manifest.get("artifact_sources")
    validate_lock(manifest, lockfile)
    if len({row.get("filename") for row in rows}) != len(rows) or len({row.get("name") for row in rows}) != len(rows):
        raise StageError("manifest repeats a distribution or wheel filename")
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        spec = {key: row[key] for key in ("filename", "sha256", "size_bytes")}
        check_spec(spec)
        source = row["source"]
        kind = source.get("kind")
        if kind == "repo_wheelhouse":
            relative = checked_repo_wheel_path(source.get("path", ""))
            local_path = ROOT.joinpath(*relative.parts)
            if local_path.is_symlink() or not local_path.is_file() or local_path.stat().st_size != spec["size_bytes"] or sha256_file(local_path) != spec["sha256"]:
                raise StageError(f"repository wheelhouse source mismatch: {spec['filename']}")
        elif kind == "https":
            from urllib.parse import urlsplit

            parsed = urlsplit(source.get("url", ""))
            if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username
                    or parsed.password or parsed.fragment or parsed.query):
                raise StageError("manifest contains a noncanonical or unapproved HTTPS URL")
        elif kind == "actions_artifact":
            archive_hash = source.get("archive_sha256", "")
            max_archive_bytes = source.get("max_archive_bytes")
            if (not isinstance(source.get("repo"), str)
                    or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source["repo"])
                    or not isinstance(source.get("artifact_id"), int) or source["artifact_id"] <= 0
                    or not isinstance(source.get("run_id"), int) or source["run_id"] <= 0
                    or not isinstance(source.get("artifact_name"), str) or not source["artifact_name"]
                    or not re.fullmatch(r"[0-9a-f]{40}", source.get("source_revision", ""))
                    or not re.fullmatch(r"[0-9a-f]{64}", archive_hash)
                    or not isinstance(max_archive_bytes, int) or not 1 <= max_archive_bytes <= 2_147_483_648):
                raise StageError("manifest contains an invalid Actions artifact pin or size bound")
            groups.setdefault((source["repo"], source["artifact_id"]), []).append(row)
        elif kind == "actions_artifact_pending":
            raise StageError(f"Actions artifact handoff is not bound yet: {spec['filename']}")
        else:
            raise StageError(f"unknown source route for {spec['filename']}")

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if groups and not token:
        raise StageError("GH_TOKEN or GITHUB_TOKEN is required for hosted build artifacts")
    if destination.is_symlink():
        raise StageError("output directory must not be a symbolic link")
    if destination.exists() and any(destination.iterdir()):
        raise StageError("output directory must be empty")
    action_sizes = {}
    for key, grouped_rows in groups.items():
        source = grouped_rows[0]["source"]
        binding = (source["archive_sha256"], source["max_archive_bytes"], source["run_id"],
                   source["artifact_name"], source["source_revision"])
        if any((item["source"]["archive_sha256"], item["source"]["max_archive_bytes"],
                item["source"]["run_id"], item["source"]["artifact_name"],
                item["source"]["source_revision"]) != binding for item in grouped_rows):
            raise StageError("one Actions artifact ID has conflicting identity or digest bindings")
        action_sizes[key] = verify_actions_metadata(source, token or "")
    destination.mkdir(parents=True, exist_ok=True)

    results = []
    for row in rows:
        spec = {key: row[key] for key in ("filename", "sha256", "size_bytes")}
        check_spec(spec)
        source = row["source"]
        kind = source["kind"]
        target = destination / spec["filename"]
        if kind == "repo_wheelhouse":
            relative = checked_repo_wheel_path(source["path"])
            copy_checked(ROOT.joinpath(*relative.parts), target, spec)
        elif kind == "https":
            download_https(source["url"], target, spec)
        elif kind == "actions_artifact":
            continue
        else:
            raise StageError(f"unknown source route for {spec['filename']}")
        results.append({"filename": spec["filename"], "sha256": spec["sha256"], "size_bytes": spec["size_bytes"], "source_kind": kind})

    by_group = {}
    for key, grouped_rows in groups.items():
        source = grouped_rows[0]["source"]
        payload = actions_zip(source, token or "", action_sizes[key])
        artifact_rows = [{"filename": item["filename"], "sha256": item["sha256"], "size_bytes": item["size_bytes"]} for item in grouped_rows]
        try:
            verified = extract_actions_wheels(payload, artifact_rows, destination)
        finally:
            payload.close()
        by_group[str(key[1])] = verified
        results.extend({**item, "source_kind": "actions_artifact", "artifact_id": key[1]} for item in verified)

    expected_names = {row["filename"] for row in rows}
    actual_names = {path.name for path in destination.iterdir() if path.is_file() and path.name != "staging-receipt.json"}
    if actual_names != expected_names:
        raise StageError("staged directory does not exactly match selected artifact manifest")
    requirements = destination / "requirements.txt"
    shutil.copyfile(lockfile, requirements)
    receipt = {
        "schema_version": 1,
        "status": "verified wheel inputs; not installed or imported",
        "selected_lock_sha256": manifest["selected_lock_sha256"],
        "manifest_sha256": sha256_file(manifest_path),
        "requirements_sha256": sha256_file(requirements),
        "selected_count": len(results),
        "actions_artifacts": by_group,
        "wheels": sorted(results, key=lambda item: item["filename"]),
    }
    (destination / "staging-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--selected-lockfile", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        stage(args.manifest, args.selected_lockfile, args.output_dir)
    except (OSError, json.JSONDecodeError, KeyError, StageError) as error:
        print(f"Linux release artifact staging failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
