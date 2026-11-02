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
_URL_RE = re.compile(r"(?:https?|file)://|(?:^|\s)[^\s/@]+@[^\s/:]+:", re.IGNORECASE)
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


def _manifest_record(
    manifest_bytes: bytes,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
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
            "source_distribution",
            "selected_wheel",
            "files",
        },
        {"excluded_source_notice", "package_source_evidence"},
        "source notice manifest",
    )
    name = top["distribution"]
    version = top["version"]
    exact_pin = top["exact_pin"]
    if (
        not isinstance(name, str)
        or not _NAME_RE.fullmatch(name)
        or not isinstance(version, str)
        or not _VERSION_RE.fullmatch(version)
        or not isinstance(exact_pin, str)
        or _normalized_name(name) != _normalized_name(exact_pin.partition("==")[0])
        or exact_pin != f"{name}=={version}"
    ):
        _fail("source notice manifest package identity is invalid")
    if not isinstance(top["license_source"], str) or not top["license_source"].strip():
        _fail("source notice manifest license source is invalid")

    source = _keys(
        top["source_distribution"],
        {"filename", "sha256"},
        set(),
        "source distribution record",
    )
    wheel = _keys(
        top["selected_wheel"],
        {"filename", "sha256"},
        set(),
        "selected wheel record",
    )
    for record, label, suffix in (
        (source, "source distribution", (".tar.gz", ".zip", ".tgz")),
        (wheel, "selected wheel", (".whl",)),
    ):
        filename = record["filename"]
        if (
            not isinstance(filename, str)
            or not filename
            or "/" in filename
            or "\\" in filename
        ):
            _fail(f"source notice manifest {label} filename is invalid")
        if (
            not filename.endswith(suffix)
            or not isinstance(record["sha256"], str)
            or not _HEX_RE.fullmatch(record["sha256"])
        ):
            _fail(f"source notice manifest {label} identity is invalid")
    source_filename = source["filename"]
    source_suffix = next(
        suffix
        for suffix in (".tar.gz", ".tgz", ".zip")
        if source_filename.endswith(suffix)
    )
    source_stem = source_filename[: -len(source_suffix)]
    version_suffix = f"-{version}"
    wheel_parts = wheel["filename"][:-4].split("-")
    if (
        not source_stem.endswith(version_suffix)
        or _normalized_name(source_stem[: -len(version_suffix)])
        != _normalized_name(name)
        or len(wheel_parts) < 5
        or _normalized_name(wheel_parts[0]) != _normalized_name(name)
        or wheel_parts[1] != version
    ):
        _fail(
            "source notice manifest artifact filenames differ from its package identity"
        )

    package_source_evidence = None
    if "package_source_evidence" in top:
        evidence = _keys(
            top["package_source_evidence"],
            {"path", "sha256"},
            set(),
            "package source evidence record",
        )
        evidence_path = _safe_relative(
            evidence["path"], "package source evidence path"
        )
        evidence_root = evidence_path.parts[0]
        if (
            not evidence_root.endswith(version_suffix)
            or _normalized_name(evidence_root[: -len(version_suffix)])
            != _normalized_name(name)
        ):
            _fail("package source evidence path does not map to its exact distribution")
        if not isinstance(evidence["sha256"], str) or not _HEX_RE.fullmatch(
            evidence["sha256"]
        ):
            _fail("package source evidence SHA-256 is invalid")
        package_source_evidence = {
            "path": evidence_path.as_posix(),
            "sha256": evidence["sha256"],
        }

    raw_files = top["files"]
    if (
        not isinstance(raw_files, list)
        or not raw_files
        or len(raw_files) > _MAX_NOTICE_FILES
    ):
        _fail("source notice manifest file list is empty or exceeds its limit")
    files: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    seen_basenames: set[str] = set()
    seen_archive_paths: set[str] = set()
    package_total = 0
    for item in raw_files:
        file = _keys(
            item,
            {"path", "size_bytes", "sha256"},
            {"source_archive_path", "upstream_source"},
            "source notice file record",
        )
        if ("source_archive_path" in file) == ("upstream_source" in file):
            _fail(
                "source notice file must identify exactly one package-archive or upstream source"
            )
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
        if "source_archive_path" in file:
            archive_path = _safe_relative(
                file["source_archive_path"], "source archive notice path"
            )
            archive_canonical = archive_path.as_posix()
            archive_root = archive_path.parts[0]
            if (
                not archive_root.endswith(version_suffix)
                or _normalized_name(archive_root[: -len(version_suffix)])
                != _normalized_name(name)
            ):
                _fail("source archive notice path does not map to its exact distribution")
            if archive_canonical in seen_archive_paths:
                _fail("source notice manifest repeats a source archive path")
            seen_archive_paths.add(archive_canonical)
            source_evidence = {"source_archive_path": archive_canonical}
        else:
            if package_source_evidence is None:
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
            source_evidence = {
                "upstream_source": {
                    "repository": upstream["repository"],
                    "revision": upstream["revision"],
                    "path": upstream_path.as_posix(),
                    "sha256": upstream_digest,
                    "size_bytes": upstream_size,
                },
                "package_source_evidence": package_source_evidence,
            }
        package_total += size
        if package_total > _MAX_PACKAGE_NOTICE_BYTES:
            _fail("source notice manifest exceeds its package size limit")
        files.append(
            {
                "repo_path": canonical,
                "basename": basename,
                "size_bytes": size,
                "sha256": digest,
                **source_evidence,
            }
        )

    if "excluded_source_notice" in top:
        excluded = _keys(
            top["excluded_source_notice"],
            {"source_archive_path", "reason"},
            set(),
            "excluded source notice record",
        )
        _safe_relative(excluded["source_archive_path"], "excluded source notice path")
        if not isinstance(excluded["reason"], str) or not excluded["reason"].strip():
            _fail("excluded source notice reason is invalid")
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
    config = spec.get("dependency_notices", {})
    if not isinstance(config, dict):
        _fail("dependency notice configuration is invalid")
    manifest_paths = config.get("source_supplements", [])
    if not isinstance(manifest_paths, list):
        _fail("source notice supplement configuration must be a list")
    if not manifest_paths:
        return {}

    root_input = Path(repo_root)
    if root_input.is_symlink():
        _fail("repository root is a symlink")
    try:
        root = root_input.resolve(strict=True)
    except OSError as exc:
        raise SourceNoticeSupplementError("repository root is missing") from exc
    if not root.is_dir():
        _fail("repository root is not a directory")
    destination = _safe_relative(str(bundle_dest), "dependency notice output directory")
    selected = _locked_packages(packages)

    seen_manifest_paths: set[str] = set()
    seen_distributions: set[str] = set()
    result: dict[str, tuple[list[dict[str, Any]], list[tuple[str, bytes]]]] = {}
    all_total = 0
    for manifest_text in manifest_paths:
        manifest_rel, _manifest_file, manifest_bytes = _safe_repo_file(
            root,
            manifest_text,
            "source notice manifest path",
            max_bytes=_MAX_MANIFEST_BYTES,
        )
        canonical_manifest = manifest_rel.as_posix()
        if canonical_manifest in seen_manifest_paths:
            _fail("source notice manifest path is duplicated")
        seen_manifest_paths.add(canonical_manifest)
        top, files = _manifest_record(manifest_bytes)
        normalized = _normalized_name(top["distribution"])
        if normalized in seen_distributions:
            _fail("source notice manifests repeat a distribution")
        seen_distributions.add(normalized)
        package = selected.get(normalized)
        if package is None:
            continue
        if (
            top["version"] != package.version
            or top["exact_pin"]
            != f"{top['distribution']}=={package.version}"
        ):
            _fail(f"source notice manifest version differs from lock: {normalized}")
        if top["selected_wheel"]["sha256"] not in set(package.hashes):
            _fail(f"source notice wheel hash is not selected by lock: {normalized}")
        source_sha = top["source_distribution"]["sha256"]
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        slug = f"{normalized}-{package.version}"
        output_records: list[dict[str, Any]] = []
        output_files: list[tuple[str, bytes]] = []
        package_total = 0
        for file in files:
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
            package_total += len(content)
            all_total += len(content)
            if all_total > _MAX_ALL_NOTICE_BYTES:
                _fail("source notice supplements exceed total size limit")
            bundle_path = (
                destination / slug / "source-supplements" / file["basename"]
            ).as_posix()
            if any(existing[0] == bundle_path for existing in output_files):
                _fail("source notice output path is duplicated")
            output_files.append((bundle_path, content))
            record = {
                "source_path": f"source-supplements/{file['basename']}",
                "bundle_path": bundle_path,
                "sha256": file["sha256"],
                "size": len(content),
                "manifest_path": canonical_manifest,
                "manifest_sha256": manifest_sha,
                "supplement_path": file["repo_path"],
                "source_archive_filename": top["source_distribution"]["filename"],
                "source_archive_sha256": source_sha,
            }
            if "source_archive_path" in file:
                record.update(
                    {
                        "provenance": "reviewed-source-supplement",
                        "source_archive_path": file["source_archive_path"],
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
            output_records.append(record)
        if package_total <= 0:
            _fail(f"source notice supplement contains no files: {normalized}")
        pin_key = f"{normalized}=={package.version}"
        result[pin_key] = (output_records, output_files)
    return dict(sorted(result.items()))
