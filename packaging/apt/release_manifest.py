"""Create the source-bound manifest attached to an AIRunner Debian release."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_VERSION_RE = re.compile(r"^[0-9][A-Za-z0-9.+:~_-]{0,127}$")
_SAFE_TAG_RE = re.compile(r"^v[0-9][A-Za-z0-9.+_-]{0,126}$")
_WORKFLOW = ".github/workflows/pypi-dispatch.yml"
_PROMOTION_JOB = "publish-release-assets"


class ManifestError(ValueError):
    """A Debian release asset does not match its source identity."""


def _field(deb: Path, field: str) -> str:
    try:
        result = subprocess.run(
            ["dpkg-deb", "--field", str(deb), field],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ManifestError("cannot read Debian package metadata") from exc
    return result.stdout.strip()


def create_manifest(
    deb: Path,
    *,
    repository: str,
    tag: str,
    source_commit: str,
    workflow: str,
    workflow_event: str,
    promotion_job: str,
    run_id: str,
    expected_debian_version: str | None = None,
) -> dict[str, object]:
    """Validate one .deb and bind its bytes to the release workflow run."""
    if repository != "Capsize-Games/airunner":
        raise ManifestError("unexpected release repository")
    if workflow != _WORKFLOW:
        raise ManifestError("unexpected Debian release workflow")
    if workflow_event != "workflow_dispatch" or promotion_job != _PROMOTION_JOB:
        raise ManifestError("Debian release must be bound to the successful promotion run")
    if not _SHA_RE.fullmatch(source_commit):
        raise ManifestError("source commit must be a full lowercase SHA")
    if not _SAFE_TAG_RE.fullmatch(tag):
        raise ManifestError("release tag must be a safe version tag")
    if not run_id.isdecimal() or int(run_id) <= 0:
        raise ManifestError("workflow run id must be a positive integer")
    if not deb.is_file() or deb.is_symlink() or deb.stat().st_size <= 0:
        raise ManifestError("Debian package must be a nonempty regular file")

    package = _field(deb, "Package")
    version = _field(deb, "Version")
    architecture = _field(deb, "Architecture")
    if package != "airunner" or architecture != "amd64":
        raise ManifestError("unexpected Debian package name or architecture")
    if not _VERSION_RE.fullmatch(version):
        raise ManifestError("Debian package version is invalid")
    if expected_debian_version is not None and version != expected_debian_version:
        raise ManifestError("Debian package version differs from the source changelog")
    upstream_version = version.rsplit(":", 1)[-1].split("-", 1)[0]
    if tag[1:] != upstream_version:
        raise ManifestError("release tag and Debian package version disagree")
    if deb.name != f"airunner_{version}_amd64.deb":
        raise ManifestError("Debian package filename is not canonical")

    digest = hashlib.sha256(deb.read_bytes()).hexdigest()
    return {
        "schema": 2,
        "repository": repository,
        "tag": tag,
        "source_commit": source_commit,
        "workflow": workflow,
        "workflow_event": workflow_event,
        "promotion_job": promotion_job,
        "workflow_run_id": int(run_id),
        "package": package,
        "version": version,
        "architecture": architecture,
        "filename": deb.name,
        "size": deb.stat().st_size,
        "sha256": digest,
    }


def write_manifest(manifest: dict[str, object], output: Path) -> None:
    """Write a deterministic manifest without replacing an existing file."""
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
    try:
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except OSError as exc:
        raise ManifestError("cannot create release manifest") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deb", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--workflow-event", required=True)
    parser.add_argument("--promotion-job", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--debian-version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = create_manifest(
            args.deb,
            repository=args.repository,
            tag=args.tag,
            source_commit=args.source_commit,
            workflow=args.workflow,
            workflow_event=args.workflow_event,
            promotion_job=args.promotion_job,
            run_id=args.run_id,
            expected_debian_version=args.debian_version,
        )
        write_manifest(manifest, args.output)
    except ManifestError as exc:
        parser.error(str(exc))
    print(f"Debian release identity recorded for {manifest['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
