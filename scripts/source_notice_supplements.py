"""Load reviewed source-license supplements for a locked Linux bundle.

This loader reads only explicit repository manifests and their notice text.
It never imports or installs dependency packages and never treats source
supplements as wheel RECORD entries.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from dependency_notices import (
    DependencyNoticeError,
    LockedDistribution,
    _normalized_name,
)

_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_REV_RE = re.compile(r"^[0-9a-f]{40}$")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.!+_-]*$")
_URL_RE = re.compile(
    r"(?:https?|file)://|(?:^|\s)[^\s/@]+@[^\s/:]+:", re.IGNORECASE
)
_MAX_MANIFEST_BYTES = 2 * 1024 * 1024
_MAX_NOTICE_BYTES = 5 * 1024 * 1024
_MAX_PACKAGE_NOTICE_BYTES = 32 * 1024 * 1024
_MAX_ALL_NOTICE_BYTES = 64 * 1024 * 1024
_MAX_NOTICE_FILES = 512


class SourceNoticeSupplementError(DependencyNoticeError):
    """A reviewed source notice manifest or payload is unsafe or inconsistent."""


def _fail(message: str) -> None:
    raise SourceNoticeSupplementError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("source notice manifest has duplicate JSON keys")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    _fail(f"source notice manifest has invalid JSON constant: {value}")


def _safe_relative(value: Any, label: str) -> PurePosixPath:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\x00" in value
        or value.startswith("/")
        or _URL_RE.search(value)
    ):
        _fail(f"{label} is unsafe")
    pieces = value.split("/")
    if any(piece in {"", ".", ".."} for piece in pieces):
        _fail(f"{label} contains path traversal")
    return PurePosixPath(*pieces)


def _safe_repo_file(
    repo_root: Path,
    value: Any,
    label: str,
    *,
    max_bytes: int,
) -> tuple[PurePosixPath, Path, bytes]:
    relative = _safe_relative(value, label)
    candidate = repo_root.joinpath(*relative.parts)
    current = repo_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            _fail(f"{label} contains a symlink")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repo_root)
    except (OSError, ValueError) as exc:
        raise SourceNoticeSupplementError(
            f"{label} escapes the repository or is missing"
        ) from exc
    if not candidate.is_file():
        _fail(f"{label} is not a regular file")
    try:
        size = candidate.stat().st_size
        if size > max_bytes:
            _fail(f"{label} exceeds its size limit")
        content = candidate.read_bytes()
    except OSError as exc:
        raise SourceNoticeSupplementError(f"{label} cannot be read") from exc
    if len(content) != size:
        _fail(f"{label} changed while being read")
    return relative, candidate, content


def _no_urls(value: Any) -> None:
    if isinstance(value, str):
        if _URL_RE.search(value):
            _fail("source notice manifest contains a URL")
    elif isinstance(value, list):
        for item in value:
            _no_urls(item)
    elif isinstance(value, dict):
        for item in value.values():
            _no_urls(item)


def _keys(
    value: Any,
    required: set[str],
    optional: set[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    keys = set(value)
    if not required.issubset(keys) or keys - required - optional:
        _fail(f"{label} has missing or unknown JSON keys")
    return value


def _parse_manifest(manifest_bytes: bytes) -> dict[str, Any]:
    try:
        data = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except SourceNoticeSupplementError:
        raise
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
    ) as exc:
        raise SourceNoticeSupplementError(
            "source notice manifest is invalid JSON"
        ) from exc
    _no_urls(data)
    top = _keys(
        data,
        {
            "distribution",
            "version",
            "exact_pin",
            "license_source",
            "selected_wheel",
            "files",
        },
        {
            "excluded_source_notice",
            "package_source_evidence",
            "source_distribution",
            "source_snapshot",
        },
        "source notice manifest",
    )
    if ("source_distribution" in top) == ("source_snapshot" in top):
        _fail(
            "source notice manifest must identify exactly one source distribution or Git snapshot"
        )
    if "source_snapshot" in top and "package_source_evidence" in top:
        _fail(
            "Git snapshot source notices cannot also use package source attribution evidence"
        )
    return top


def _manifest_identity(top: dict[str, Any]) -> tuple[str, str]:
    name = top["distribution"]
    version = top["version"]
    exact_pin = top["exact_pin"]
    if (
        not isinstance(name, str)
        or not _NAME_RE.fullmatch(name)
        or not isinstance(version, str)
        or not _VERSION_RE.fullmatch(version)
        or not isinstance(exact_pin, str)
        or _normalized_name(name)
        != _normalized_name(exact_pin.partition("==")[0])
        or exact_pin != f"{name}=={version}"
    ):
        _fail("source notice manifest package identity is invalid")
    if (
        not isinstance(top["license_source"], str)
        or not top["license_source"].strip()
    ):
        _fail("source notice manifest license source is invalid")
    return name, version


def _artifact_record(
    value: Any,
    label: str,
    suffixes: tuple[str, ...],
) -> dict[str, Any]:
    record = _keys(value, {"filename", "sha256"}, set(), f"{label} record")
    filename = record["filename"]
    digest = record["sha256"]
    if (
        not isinstance(filename, str)
        or not filename
        or "/" in filename
        or "\\" in filename
    ):
        _fail(f"source notice manifest {label} filename is invalid")
    if (
        not filename.endswith(suffixes)
        or not isinstance(digest, str)
        or not _HEX_RE.fullmatch(digest)
    ):
        _fail(f"source notice manifest {label} identity is invalid")
    return record


def _validate_selected_wheel(
    top: dict[str, Any], name: str, version: str
) -> dict[str, Any]:
    wheel = _keys(
        top["selected_wheel"],
        {"filename", "sha256"},
        set(),
        "selected wheel record",
    )
    wheel = _artifact_record(wheel, "selected wheel", (".whl",))
    wheel_parts = wheel["filename"][:-4].split("-")
    if (
        len(wheel_parts) < 5
        or _normalized_name(wheel_parts[0]) != _normalized_name(name)
        or wheel_parts[1] != version
    ):
        _fail(
            "source notice manifest wheel filename differs from its package identity"
        )
    return wheel


def _validate_source_distribution(
    top: dict[str, Any], name: str, version: str
) -> dict[str, Any]:
    source = _keys(
        top["source_distribution"],
        {"filename", "sha256"},
        set(),
        "source distribution record",
    )
    source = _artifact_record(
        source, "source distribution", (".tar.gz", ".zip", ".tgz")
    )
    source_filename = source["filename"]
    source_suffix = next(
        suffix
        for suffix in (".tar.gz", ".tgz", ".zip")
        if source_filename.endswith(suffix)
    )
    source_stem = source_filename[: -len(source_suffix)]
    version_suffix = f"-{version}"
    if not source_stem.endswith(version_suffix) or _normalized_name(
        source_stem[: -len(version_suffix)]
    ) != _normalized_name(name):
        _fail(
            "source notice manifest source distribution filenames differ from its package identity"
        )
    return source


def _validate_snapshot_identity(
    identity_value: Any, repository_revision: str, repo_root: Path
) -> dict[str, Any]:
    identity = _keys(
        identity_value,
        {"package_path", "evidence_path", "sha256", "size_bytes"},
        set(),
        "Git source snapshot identity member",
    )
    package_path = _safe_relative(
        identity["package_path"], "Git source snapshot package path"
    ).as_posix()
    evidence_path = _safe_relative(
        identity["evidence_path"], "Git source snapshot evidence path"
    ).as_posix()
    size = identity["size_bytes"]
    digest = identity["sha256"]
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or size <= 0
        or size > _MAX_NOTICE_BYTES
        or not isinstance(digest, str)
        or not _HEX_RE.fullmatch(digest)
    ):
        _fail("Git source snapshot identity hash or size is invalid")
    _, _, content = _safe_repo_file(
        repo_root,
        evidence_path,
        "Git source snapshot identity evidence",
        max_bytes=_MAX_NOTICE_BYTES,
    )
    if (
        len(content) != size
        or hashlib.sha256(content).hexdigest() != digest
        or repository_revision.encode("ascii") not in content
    ):
        _fail(
            "Git source snapshot identity evidence does not bind the selected revision"
        )

    return {
        "package_path": package_path,
        "evidence_path": evidence_path,
        "sha256": digest,
        "size_bytes": size,
    }


def _validate_snapshot_gitlinks(gitlinks: Any) -> list[dict[str, str]]:
    if not isinstance(gitlinks, list) or not gitlinks or len(gitlinks) > 256:
        _fail("Git source snapshot gitlink list is empty or exceeds its limit")
    normalized_gitlinks: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    seen_sources: set[tuple[str, str]] = set()
    for item in gitlinks:
        gitlink = _keys(
            item,
            {"path", "repository", "revision"},
            set(),
            "Git source snapshot gitlink",
        )
        path = _safe_relative(
            gitlink["path"], "Git source snapshot gitlink path"
        ).as_posix()
        linked_repository = gitlink["repository"]
        linked_revision = gitlink["revision"]
        if (
            not isinstance(linked_repository, str)
            or not _REPOSITORY_RE.fullmatch(linked_repository)
            or not isinstance(linked_revision, str)
            or not _GIT_REV_RE.fullmatch(linked_revision)
        ):
            _fail("Git source snapshot gitlink identity is invalid")
        if (
            path in seen_paths
            or (linked_repository, linked_revision) in seen_sources
        ):
            _fail("Git source snapshot repeats a gitlink")
        seen_paths.add(path)
        seen_sources.add((linked_repository, linked_revision))
        normalized_gitlinks.append(
            {
                "path": path,
                "repository": linked_repository,
                "revision": linked_revision,
            }
        )

    return normalized_gitlinks


def _validate_git_snapshot(
    top: dict[str, Any], repo_root: Path
) -> dict[str, Any]:
    snapshot = _keys(
        top["source_snapshot"],
        {"repository", "revision", "identity_member", "gitlinks"},
        set(),
        "Git source snapshot record",
    )
    repository = snapshot["repository"]
    revision = snapshot["revision"]
    if (
        not isinstance(repository, str)
        or not _REPOSITORY_RE.fullmatch(repository)
        or not isinstance(revision, str)
        or not _GIT_REV_RE.fullmatch(revision)
    ):
        _fail("Git source snapshot repository or revision is invalid")
    identity = _validate_snapshot_identity(
        snapshot["identity_member"], revision, repo_root
    )
    gitlinks = _validate_snapshot_gitlinks(snapshot["gitlinks"])
    return {
        "repository": repository,
        "revision": revision,
        "identity_member": identity,
        "gitlinks": gitlinks,
    }


def _package_source_evidence(
    top: dict[str, Any], name: str, version: str
) -> dict[str, str] | None:
    if "package_source_evidence" not in top:
        return None
    evidence = _keys(
        top["package_source_evidence"],
        {"path", "sha256"},
        set(),
        "package source evidence record",
    )
    evidence_path = _safe_relative(
        evidence["path"], "package source evidence path"
    )
    version_suffix = f"-{version}"
    evidence_root = evidence_path.parts[0]
    if not evidence_root.endswith(version_suffix) or _normalized_name(
        evidence_root[: -len(version_suffix)]
    ) != _normalized_name(name):
        _fail(
            "package source evidence path does not map to its exact distribution"
        )
    digest = evidence["sha256"]
    if not isinstance(digest, str) or not _HEX_RE.fullmatch(digest):
        _fail("package source evidence SHA-256 is invalid")
    return {"path": evidence_path.as_posix(), "sha256": digest}


def _source_archive_evidence(
    file: dict[str, Any],
    *,
    name: str,
    version: str,
    seen_archive_paths: set[str],
) -> dict[str, str]:
    archive_path = _safe_relative(
        file["source_archive_path"], "source archive notice path"
    )
    archive_canonical = archive_path.as_posix()
    version_suffix = f"-{version}"
    archive_root = archive_path.parts[0]
    if not archive_root.endswith(version_suffix) or _normalized_name(
        archive_root[: -len(version_suffix)]
    ) != _normalized_name(name):
        _fail(
            "source archive notice path does not map to its exact distribution"
        )
    if archive_canonical in seen_archive_paths:
        _fail("source notice manifest repeats a source archive path")
    seen_archive_paths.add(archive_canonical)
    return {"source_archive_path": archive_canonical}


def _git_snapshot_notice_evidence(
    file: dict[str, Any],
    *,
    size: int,
    digest: str,
    source_snapshot: dict[str, Any],
) -> dict[str, Any]:
    if "gitlink_path" not in file:
        _fail("Git snapshot notice requires a package gitlink path")
    gitlink_path = _safe_relative(
        file["gitlink_path"], "source notice gitlink path"
    ).as_posix()
    upstream = _keys(
        file["upstream_source"],
        {"repository", "revision", "path", "sha256", "size_bytes"},
        set(),
        "Git snapshot upstream notice source record",
    )
    matched = next(
        (
            link
            for link in source_snapshot["gitlinks"]
            if link["path"] == gitlink_path
        ),
        None,
    )
    upstream_path = _safe_relative(
        upstream["path"], "Git snapshot upstream notice path"
    ).as_posix()
    if (
        matched is None
        or upstream["repository"] != matched["repository"]
        or upstream["revision"] != matched["revision"]
    ):
        _fail("Git snapshot notice source differs from its package gitlink")
    if (
        not isinstance(upstream["sha256"], str)
        or not _HEX_RE.fullmatch(upstream["sha256"])
        or upstream["sha256"] != digest
        or not isinstance(upstream["size_bytes"], int)
        or isinstance(upstream["size_bytes"], bool)
        or upstream["size_bytes"] != size
    ):
        _fail("Git snapshot upstream notice bytes differ from the supplement")
    return {
        "gitlink_path": gitlink_path,
        "upstream_source": {
            "repository": matched["repository"],
            "revision": matched["revision"],
            "path": upstream_path,
            "sha256": digest,
            "size_bytes": size,
        },
    }


def _upstream_notice_evidence(
    file: dict[str, Any],
    *,
    size: int,
    digest: str,
    package_evidence: dict[str, str] | None,
) -> dict[str, Any]:
    if package_evidence is None:
        _fail("upstream notice requires package source attribution evidence")
    upstream = _keys(
        file["upstream_source"],
        {"repository", "revision", "path", "sha256", "size_bytes"},
        set(),
        "upstream notice source record",
    )
    if (
        not isinstance(upstream["repository"], str)
        or not _REPOSITORY_RE.fullmatch(upstream["repository"])
        or not isinstance(upstream["revision"], str)
        or not _GIT_REV_RE.fullmatch(upstream["revision"])
    ):
        _fail("upstream notice source repository or revision is invalid")
    upstream_path = _safe_relative(
        upstream["path"], "upstream notice source path"
    )
    upstream_size = upstream["size_bytes"]
    upstream_digest = upstream["sha256"]
    if (
        not isinstance(upstream_size, int)
        or isinstance(upstream_size, bool)
        or upstream_size != size
        or not isinstance(upstream_digest, str)
        or not _HEX_RE.fullmatch(upstream_digest)
        or upstream_digest != digest
    ):
        _fail("upstream notice source bytes differ from the supplement")
    return {
        "upstream_source": {
            "repository": upstream["repository"],
            "revision": upstream["revision"],
            "path": upstream_path.as_posix(),
            "sha256": upstream_digest,
            "size_bytes": upstream_size,
        },
        "package_source_evidence": package_evidence,
    }


def _source_file_evidence(
    file: dict[str, Any],
    *,
    name: str,
    version: str,
    size: int,
    digest: str,
    package_evidence: dict[str, str] | None,
    source_snapshot: dict[str, Any] | None,
    seen_archive_paths: set[str],
) -> dict[str, Any]:
    if "source_archive_path" in file:
        return _source_archive_evidence(
            file,
            name=name,
            version=version,
            seen_archive_paths=seen_archive_paths,
        )

    if source_snapshot is not None:
        return _git_snapshot_notice_evidence(
            file, size=size, digest=digest, source_snapshot=source_snapshot
        )
    return _upstream_notice_evidence(
        file, size=size, digest=digest, package_evidence=package_evidence
    )


def _manifest_file(
    item: Any,
    *,
    name: str,
    version: str,
    package_evidence: dict[str, str] | None,
    source_snapshot: dict[str, Any] | None,
    seen_paths: set[str],
    seen_basenames: set[str],
    seen_archive_paths: set[str],
) -> tuple[dict[str, Any], int]:
    file = _keys(
        item,
        {"path", "size_bytes", "sha256"},
        {"source_archive_path", "upstream_source", "gitlink_path"},
        "source notice file record",
    )
    if source_snapshot is not None:
        if "source_archive_path" in file or "upstream_source" not in file:
            _fail(
                "Git snapshot notice must identify an upstream source and no archive"
            )
    elif ("source_archive_path" in file) == ("upstream_source" in file):
        _fail(
            "source notice file must identify exactly one package-archive or upstream source"
        )
    elif "gitlink_path" in file:
        _fail("Gitlink path is only valid for a Git snapshot source")
    repo_path = _safe_relative(file["path"], "source notice repository path")
    canonical = repo_path.as_posix()
    basename = repo_path.name
    if canonical in seen_paths or basename in seen_basenames:
        _fail("source notice manifest repeats a file path or output basename")
    seen_paths.add(canonical)
    seen_basenames.add(basename)
    size = file["size_bytes"]
    digest = file["sha256"]
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or size <= 0
        or size > _MAX_NOTICE_BYTES
    ):
        _fail("source notice file size is invalid or exceeds its limit")
    if not isinstance(digest, str) or not _HEX_RE.fullmatch(digest):
        _fail("source notice file SHA-256 is invalid")
    source = _source_file_evidence(
        file,
        name=name,
        version=version,
        size=size,
        digest=digest,
        package_evidence=package_evidence,
        source_snapshot=source_snapshot,
        seen_archive_paths=seen_archive_paths,
    )
    return {
        "repo_path": canonical,
        "basename": basename,
        "size_bytes": size,
        "sha256": digest,
        **source,
    }, size


def _manifest_files(
    top: dict[str, Any],
    *,
    name: str,
    version: str,
    package_evidence: dict[str, str] | None,
    source_snapshot: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    raw_files = top["files"]
    if (
        not isinstance(raw_files, list)
        or not raw_files
        or len(raw_files) > _MAX_NOTICE_FILES
    ):
        _fail("source notice manifest file list is empty or exceeds its limit")
    seen_paths: set[str] = set()
    seen_basenames: set[str] = set()
    seen_archive_paths: set[str] = set()
    total = 0
    files = []
    for item in raw_files:
        file, size = _manifest_file(
            item,
            name=name,
            version=version,
            package_evidence=package_evidence,
            source_snapshot=source_snapshot,
            seen_paths=seen_paths,
            seen_basenames=seen_basenames,
            seen_archive_paths=seen_archive_paths,
        )
        total += size
        if total > _MAX_PACKAGE_NOTICE_BYTES:
            _fail("source notice manifest exceeds its package size limit")
        files.append(file)
    return files


def _validate_excluded_source_notice(top: dict[str, Any]) -> None:
    if "excluded_source_notice" not in top:
        return
    excluded = _keys(
        top["excluded_source_notice"],
        {"source_archive_path", "reason"},
        set(),
        "excluded source notice record",
    )
    _safe_relative(
        excluded["source_archive_path"], "excluded source notice path"
    )
    if (
        not isinstance(excluded["reason"], str)
        or not excluded["reason"].strip()
    ):
        _fail("excluded source notice reason is invalid")


def _manifest_record(
    manifest_bytes: bytes,
    repo_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    top = _parse_manifest(manifest_bytes)
    name, version = _manifest_identity(top)
    _validate_selected_wheel(top, name, version)
    package_evidence = _package_source_evidence(top, name, version)
    source_snapshot = None
    if "source_distribution" in top:
        _validate_source_distribution(top, name, version)
    else:
        source_snapshot = _validate_git_snapshot(top, repo_root)
        top["_validated_source_snapshot"] = source_snapshot
    files = _manifest_files(
        top,
        name=name,
        version=version,
        package_evidence=package_evidence,
        source_snapshot=source_snapshot,
    )
    _validate_excluded_source_notice(top)
    return top, files


def _locked_packages(
    packages: Iterable[LockedDistribution],
) -> dict[str, LockedDistribution]:
    selected: dict[str, LockedDistribution] = {}
    for package in packages:
        name = getattr(package, "normalized_name", None)
        version = getattr(package, "version", None)
        hashes = getattr(package, "hashes", None)
        if (
            not isinstance(name, str)
            or not _NAME_RE.fullmatch(name)
            or not isinstance(version, str)
            or not _VERSION_RE.fullmatch(version)
            or not isinstance(hashes, (tuple, list))
            or not hashes
            or any(
                not isinstance(value, str) or not _HEX_RE.fullmatch(value)
                for value in hashes
            )
        ):
            _fail("selected lock package record is invalid")
        normalized = _normalized_name(name)
        if normalized in selected:
            _fail("selected lock repeats a distribution")
        selected[normalized] = package
    return selected


def _configured_manifest_paths(spec: dict[str, Any]) -> list[str]:
    config = spec.get("dependency_notices", {})
    if not isinstance(config, dict):
        _fail("dependency notice configuration is invalid")
    paths = config.get("source_supplements", [])
    if not isinstance(paths, list):
        _fail("source notice supplement configuration must be a list")
    return paths


def _repository_context(
    repo_root: Path,
    bundle_dest: str | Path,
) -> tuple[Path, PurePosixPath]:
    root_input = Path(repo_root)
    if root_input.is_symlink():
        _fail("repository root is a symlink")
    try:
        root = root_input.resolve(strict=True)
    except OSError as exc:
        raise SourceNoticeSupplementError(
            "repository root is missing"
        ) from exc
    if not root.is_dir():
        _fail("repository root is not a directory")
    destination = _safe_relative(
        str(bundle_dest), "dependency notice output directory"
    )
    return root, destination


def _read_manifest_record(
    root: Path,
    manifest_text: str,
    seen_paths: set[str],
    seen_distributions: set[str],
) -> tuple[str, bytes, dict[str, Any], list[dict[str, Any]]]:
    relative, _, raw = _safe_repo_file(
        root,
        manifest_text,
        "source notice manifest path",
        max_bytes=_MAX_MANIFEST_BYTES,
    )
    canonical = relative.as_posix()
    if canonical in seen_paths:
        _fail("source notice manifest path is duplicated")
    seen_paths.add(canonical)
    top, files = _manifest_record(raw, root)
    normalized = _normalized_name(top["distribution"])
    if normalized in seen_distributions:
        _fail("source notice manifests repeat a distribution")
    seen_distributions.add(normalized)
    return canonical, raw, top, files


def _selected_package(
    top: dict[str, Any], selected: dict[str, LockedDistribution]
) -> tuple[str, LockedDistribution] | None:
    normalized = _normalized_name(top["distribution"])
    package = selected.get(normalized)
    if package is None:
        return None
    if (
        top["version"] != package.version
        or top["exact_pin"] != f"{top['distribution']}=={package.version}"
    ):
        _fail(
            f"source notice manifest version differs from lock: {normalized}"
        )
    wheel_hash = top["selected_wheel"]["sha256"]
    if wheel_hash not in set(package.hashes):
        _fail(
            f"source notice wheel hash is not selected by lock: {normalized}"
        )
    return normalized, package


def _notice_record(
    file: dict[str, Any],
    *,
    root: Path,
    destination: PurePosixPath,
    slug: str,
    normalized: str,
    canonical_manifest: str,
    manifest_sha: str,
    source_distribution: dict[str, Any],
    source_snapshot: dict[str, Any] | None,
) -> tuple[dict[str, Any], tuple[str, bytes]]:
    _, _, content = _safe_repo_file(
        root,
        file["repo_path"],
        "source notice file path",
        max_bytes=_MAX_NOTICE_BYTES,
    )
    if (
        len(content) != file["size_bytes"]
        or hashlib.sha256(content).hexdigest() != file["sha256"]
    ):
        _fail(
            f"source notice file differs from reviewed manifest: {normalized}"
        )
    bundle_path = (
        destination / slug / "source-supplements" / file["basename"]
    ).as_posix()
    record = {
        "source_path": f"source-supplements/{file['basename']}",
        "bundle_path": bundle_path,
        "sha256": file["sha256"],
        "size": len(content),
        "manifest_path": canonical_manifest,
        "manifest_sha256": manifest_sha,
        "supplement_path": file["repo_path"],
    }
    if source_snapshot is None:
        record.update(
            {
                "source_archive_filename": source_distribution["filename"],
                "source_archive_sha256": source_distribution["sha256"],
            }
        )
    if "source_archive_path" in file:
        record.update(
            {
                "provenance": "reviewed-source-supplement",
                "source_archive_path": file["source_archive_path"],
            }
        )
    else:
        if source_snapshot is not None:
            record.update(
                {
                    "provenance": "reviewed-git-snapshot-source-supplement",
                    "source_snapshot": source_snapshot,
                    "gitlink_path": file["gitlink_path"],
                    "upstream_source": file["upstream_source"],
                }
            )
        else:
            record.update(
                {
                    "provenance": "reviewed-upstream-source-supplement",
                    "package_source_evidence": file["package_source_evidence"],
                    "upstream_source": file["upstream_source"],
                }
            )
    return record, (bundle_path, content)


def _selected_manifest_notices(
    root: Path,
    destination: PurePosixPath,
    canonical_manifest: str,
    raw_manifest: bytes,
    top: dict[str, Any],
    files: list[dict[str, Any]],
    normalized: str,
    package: LockedDistribution,
    remaining_bytes: int,
) -> tuple[list[dict[str, Any]], list[tuple[str, bytes]], int]:
    manifest_sha = hashlib.sha256(raw_manifest).hexdigest()
    slug = f"{normalized}-{package.version}"
    records: list[dict[str, Any]] = []
    output_files: list[tuple[str, bytes]] = []
    output_paths: set[str] = set()
    total = 0
    for file in files:
        record, output = _notice_record(
            file,
            root=root,
            destination=destination,
            slug=slug,
            normalized=normalized,
            canonical_manifest=canonical_manifest,
            manifest_sha=manifest_sha,
            source_distribution=top.get("source_distribution", {}),
            source_snapshot=top.get("_validated_source_snapshot"),
        )
        if output[0] in output_paths:
            _fail("source notice output path is duplicated")
        output_paths.add(output[0])
        total += record["size"]
        if total > remaining_bytes:
            _fail("source notice supplements exceed total size limit")
        records.append(record)
        output_files.append(output)
    if total <= 0:
        _fail(f"source notice supplement contains no files: {normalized}")
    return records, output_files, total


def load_source_notice_supplements(
    spec: dict[str, Any],
    repo_root: Path,
    packages: Iterable[LockedDistribution],
    bundle_dest: str | Path,
) -> dict[str, tuple[list[dict[str, Any]], list[tuple[str, bytes]]]]:
    """Load explicit, hash-bound source notice supplements for selected pins.

    `packages` is the parsed exact-hash lock set. Unlocked manifests are ignored
    after their config path and JSON schema are checked. Returned bundle paths
    are relative to the bundle root and intentionally carry no wheel RECORD hash.
    """
    paths = _configured_manifest_paths(spec)
    if not paths:
        return {}
    root, destination = _repository_context(repo_root, bundle_dest)
    selected = _locked_packages(packages)
    seen_paths: set[str] = set()
    seen_distributions: set[str] = set()
    result: dict[str, tuple[list[dict[str, Any]], list[tuple[str, bytes]]]] = (
        {}
    )
    total = 0
    for manifest_text in paths:
        canonical, raw_manifest, top, files = _read_manifest_record(
            root, manifest_text, seen_paths, seen_distributions
        )
        locked = _selected_package(top, selected)
        if locked is None:
            continue
        normalized, package = locked
        records, outputs, package_bytes = _selected_manifest_notices(
            root,
            destination,
            canonical,
            raw_manifest,
            top,
            files,
            normalized,
            package,
            _MAX_ALL_NOTICE_BYTES - total,
        )
        total += package_bytes
        result[f"{normalized}=={package.version}"] = (records, outputs)
    return dict(sorted(result.items()))
