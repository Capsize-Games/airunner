"""Verify and stage an explicitly pinned Linux CUDA runtime profile.

This tool never downloads or runs the supplied artifact. Callers must provide
the archive digest and every source/producer identity from an independent,
reviewed record. The artifact must contain one
``airunner-native-runtime-cuda-sm120a/`` root with a verified profile manifest.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import tempfile
from typing import Any, Iterator


ARCHIVE_ROOT = "airunner-native-runtime-cuda-sm120a"
PROFILE_RELATIVE = Path("share/airunner/native-runtimes/cuda-sm120a")
MANIFEST_NAME = "profile-manifest.json"
SCHEMA = "airunner-native-runtime-profile-v1"
MAX_ARCHIVE_BYTES = 8 * 1024**3
MAX_TREE_BYTES = 8 * 1024**3
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_MEMBERS = 20_001
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class StageError(ValueError):
    """A CUDA profile archive or destination failed validation."""


@dataclass(frozen=True)
class _ValidatedArchive:
    """Validated members held open for verification or staging."""

    tar: tarfile.TarFile
    members: dict[str, tuple[tarfile.TarInfo, bool]]
    manifest_bytes: bytes
    files: dict[str, tuple[str, int]]
    entrypoint: str
    archive_sha256: str


def sha256_file(path: Path) -> str:
    """Hash a bounded archive using a fixed memory buffer."""
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            total += len(block)
            if total > MAX_ARCHIVE_BYTES:
                raise StageError("CUDA profile archive exceeds the size limit")
            digest.update(block)
    return digest.hexdigest()


def _hex(value: Any, pattern: re.Pattern[str]) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _safe_relative(value: Any) -> str:
    if not isinstance(value, str):
        raise StageError("profile file path is invalid")
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or "\\" in value
        or "\x00" in value
        or path.as_posix() != value
        or not path.parts
    ):
        raise StageError("profile file path is unsafe")
    return value


def _validate_manifest(
    raw: bytes,
    *,
    artifact_id: str,
    source_repository: str,
    source_commit: str,
    source_tree: str,
    producer_commit: str,
    recipe_sha256: str,
) -> tuple[dict[str, tuple[str, int]], str]:
    if len(raw) > MAX_MANIFEST_BYTES:
        raise StageError("profile manifest exceeds the size limit")
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise StageError("profile manifest is invalid JSON") from exc
    if not isinstance(manifest, dict):
        raise StageError("profile manifest root is invalid")
    _validate_manifest_identity(
        manifest,
        artifact_id=artifact_id,
        source_repository=source_repository,
        source_commit=source_commit,
        source_tree=source_tree,
        producer_commit=producer_commit,
        recipe_sha256=recipe_sha256,
    )
    files = _validate_manifest_files(manifest.get("files"))
    entrypoint = manifest.get("entrypoint")
    if entrypoint != "bin/llama-server-cuda" or entrypoint not in files:
        raise StageError("profile entrypoint is invalid")
    return files, entrypoint


def _validate_manifest_identity(
    manifest: dict[str, Any],
    *,
    artifact_id: str,
    source_repository: str,
    source_commit: str,
    source_tree: str,
    producer_commit: str,
    recipe_sha256: str,
) -> None:
    """Check the release target and all identities against external pins."""
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        raise StageError("external artifact identity is missing")
    if not isinstance(source_repository, str) or not source_repository:
        raise StageError("external source repository is missing")
    if not all((
        _hex(source_commit, _HEX40),
        _hex(source_tree, _HEX40),
        _hex(producer_commit, _HEX40),
        _hex(recipe_sha256, _HEX64),
    )):
        raise StageError("external source or producer identity is malformed")
    if (
        manifest.get("schema") != SCHEMA
        or manifest.get("status") != "verified"
        or manifest.get("profile") != "cuda-sm120a"
        or manifest.get("platform") != "linux-x86_64"
        or manifest.get("abi") != "ubuntu-24.04"
        or manifest.get("compute_capability") != "12.0"
    ):
        raise StageError("profile manifest is not a verified Ubuntu 24.04 SM120a profile")
    if manifest.get("artifact_id") != artifact_id:
        raise StageError("profile artifact identity does not match the external pin")
    source = manifest.get("source")
    if not isinstance(source, dict) or (
        source.get("repository") != source_repository
        or source.get("commit") != source_commit
        or source.get("tree") != source_tree
    ):
        raise StageError("profile source identity does not match the external pin")
    producer = manifest.get("producer")
    if not isinstance(producer, dict) or (
        producer.get("commit") != producer_commit
        or producer.get("recipe_sha256") != recipe_sha256
    ):
        raise StageError("profile producer identity does not match the external pin")
def _validate_manifest_files(entries: Any) -> dict[str, tuple[str, int]]:
    """Validate the bounded, canonical file inventory from the manifest."""
    if not isinstance(entries, list) or not entries or len(entries) > 10_000:
        raise StageError("profile manifest file inventory is invalid")
    files: dict[str, tuple[str, int]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise StageError("profile manifest file entry is invalid")
        relative = _safe_relative(entry.get("path"))
        if relative == MANIFEST_NAME:
            raise StageError("profile manifest cannot inventory itself")
        digest = entry.get("sha256")
        mode = entry.get("mode")
        if not _hex(digest, _HEX64) or mode not in (0o644, 0o755):
            raise StageError("profile manifest file hash or mode is invalid")
        if relative in files:
            raise StageError("profile manifest has duplicate paths")
        files[relative] = (digest, mode)
    return files


def _member_path(member: tarfile.TarInfo) -> tuple[str, bool]:
    name = member.name
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or "\\" in name
        or "\x00" in name
        or path.as_posix() != name.rstrip("/")
        or not (member.isfile() or member.isdir())
        or (member.isfile() and name.endswith("/"))
    ):
        raise StageError("archive contains an unsafe path or non-regular entry")
    normalized = name.rstrip("/")
    prefix = ARCHIVE_ROOT + "/"
    if normalized != ARCHIVE_ROOT and not normalized.startswith(prefix):
        raise StageError("archive entry is outside the expected artifact root")
    return ("" if normalized == ARCHIVE_ROOT else normalized[len(prefix):], member.isdir())


def _check_destination(bundle: Path) -> tuple[Path, Path]:
    bundle_abs = Path(os.path.abspath(bundle))
    if not bundle_abs.is_dir() or bundle_abs.is_symlink():
        raise StageError("bundle destination must be an existing real directory")
    target = bundle_abs / PROFILE_RELATIVE
    if target.exists() or target.is_symlink():
        raise StageError("CUDA profile destination already exists")
    current = Path(bundle_abs.anchor)
    for part in bundle_abs.parts[1:]:
        current /= part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                raise StageError("bundle destination path contains a symlink")
        except FileNotFoundError:
            raise StageError("bundle destination path is incomplete") from None
    current = bundle_abs
    for component in target.parent.relative_to(bundle_abs).parts:
        current /= component
        try:
            info = current.lstat()
        except FileNotFoundError:
            break
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise StageError("CUDA profile parent contains a symlink or non-directory")
    return target, target.parent


def _ensure_profile_parent(bundle: Path, parent: Path) -> None:
    """Create only missing profile parents after archive validation."""
    bundle_info = bundle.lstat()
    if stat.S_ISLNK(bundle_info.st_mode) or not stat.S_ISDIR(bundle_info.st_mode):
        raise StageError("bundle destination changed during staging")
    current = bundle
    for component in parent.relative_to(bundle).parts:
        current /= component
        try:
            info = current.lstat()
        except FileNotFoundError:
            current.mkdir(mode=0o755)
            info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise StageError("CUDA profile parent changed during creation")


def _read_archive_members(
    archive: tarfile.TarFile,
) -> dict[str, tuple[tarfile.TarInfo, bool]]:
    """Index only bounded, regular-file and directory archive members."""
    members: dict[str, tuple[tarfile.TarInfo, bool]] = {}
    total_size = 0
    for index, member in enumerate(archive):
        if index >= MAX_MEMBERS:
            raise StageError("CUDA profile archive contains too many entries")
        relative, is_directory = _member_path(member)
        if relative in members:
            raise StageError("CUDA profile archive contains duplicate paths")
        mode = member.mode & 0o7777
        if mode & (stat.S_ISUID | stat.S_ISGID):
            raise StageError("CUDA profile archive contains setuid or setgid mode")
        if is_directory:
            if mode != 0o755 or member.size != 0:
                raise StageError("CUDA profile directory mode or size is invalid")
        else:
            if mode not in (0o644, 0o755) or member.size < 0:
                raise StageError("CUDA profile file mode or size is invalid")
            total_size += member.size
            if total_size > MAX_TREE_BYTES:
                raise StageError("CUDA profile archive expands beyond the size limit")
        members[relative] = (member, is_directory)
    if "" not in members or not members[""][1]:
        raise StageError("CUDA profile archive root directory is missing")
    return members


def _read_manifest_bytes(
    archive: tarfile.TarFile,
    members: dict[str, tuple[tarfile.TarInfo, bool]],
) -> bytes:
    """Read the bounded root manifest after validating its tar mode."""
    record = members.get(MANIFEST_NAME)
    if record is None or record[1]:
        raise StageError("CUDA profile archive has no root profile manifest")
    info = record[0]
    if info.mode & 0o7777 != 0o644 or info.size > MAX_MANIFEST_BYTES:
        raise StageError("CUDA profile manifest mode or size is invalid")
    stream = archive.extractfile(info)
    if stream is None:
        raise StageError("CUDA profile manifest cannot be read")
    with stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise StageError("profile manifest exceeds the size limit")
    return raw


def _validate_archive_inventory(
    members: dict[str, tuple[tarfile.TarInfo, bool]],
    listed: dict[str, tuple[str, int]],
) -> None:
    """Require exact equality between tar paths and manifest inventory."""
    expected_files = set(listed) | {MANIFEST_NAME}
    expected_dirs = {
        parent.as_posix()
        for name in listed
        for parent in PurePosixPath(name).parents
        if parent.as_posix() != "."
    }
    actual_files = {name for name, (_member, is_dir) in members.items() if not is_dir}
    actual_dirs = {
        name for name, (_member, is_dir) in members.items() if is_dir and name
    }
    if actual_files != expected_files or actual_dirs != expected_dirs:
        raise StageError("CUDA profile archive tree does not match its manifest inventory")


def _read_member_bytes(
    archive: tarfile.TarFile, member: tarfile.TarInfo, limit: int
) -> bytes:
    """Read one regular member within a strict caller-provided bound."""
    stream = archive.extractfile(member)
    if stream is None:
        raise StageError("CUDA profile file cannot be read")
    with stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise StageError("CUDA profile wrapper exceeds the size limit")
    return data


def _validate_archive_payload(
    archive: tarfile.TarFile,
    members: dict[str, tuple[tarfile.TarInfo, bool]],
    listed: dict[str, tuple[str, int]],
    entrypoint: str,
) -> None:
    """Check all file modes, hashes, and wrapper bytes before destination writes."""
    for relative, (expected_hash, expected_mode) in listed.items():
        member = members[relative][0]
        if member.mode & 0o7777 != expected_mode:
            raise StageError("CUDA profile file mode does not match its manifest")
        stream = archive.extractfile(member)
        if stream is None:
            raise StageError("CUDA profile file cannot be read")
        digest = hashlib.sha256()
        with stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        if digest.hexdigest() != expected_hash:
            raise StageError("CUDA profile file hash does not match its manifest")
    wrapper = _read_member_bytes(archive, members[entrypoint][0], 64 * 1024)
    try:
        wrapper_text = wrapper.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StageError("CUDA wrapper is not valid UTF-8") from exc
    fragments = (
        "server_dir=", "$server_dir/../lib", "export LD_LIBRARY_PATH", "cd /",
        'exec "$server_dir/llama-server" "$@"',
    )
    if not all(fragment in wrapper_text for fragment in fragments):
        raise StageError("CUDA wrapper lacks library and working-directory confinement")


def _extract_archive_profile(
    archive: tarfile.TarFile,
    members: dict[str, tuple[tarfile.TarInfo, bool]],
    listed: dict[str, tuple[str, int]],
    manifest_bytes: bytes,
    temporary: Path,
) -> None:
    """Extract previously validated members into a private sibling tree."""
    directories = {
        parent.as_posix()
        for name in listed
        for parent in PurePosixPath(name).parents
        if parent.as_posix() != "."
    }
    for relative in sorted(directories, key=lambda value: (value.count("/"), value)):
        (temporary / PurePosixPath(relative)).mkdir(mode=0o755)
    for relative, (member, is_directory) in members.items():
        if relative == MANIFEST_NAME or is_directory:
            continue
        expected_hash, expected_mode = listed[relative]
        source = archive.extractfile(member)
        if source is None:
            raise StageError("CUDA profile file cannot be read")
        destination = temporary / PurePosixPath(relative)
        digest = hashlib.sha256()
        with source, destination.open("xb") as output:
            while block := source.read(1024 * 1024):
                digest.update(block)
                output.write(block)
        if digest.hexdigest() != expected_hash:
            raise StageError("CUDA profile file changed after validation")
        os.chmod(destination, expected_mode)
    manifest_path = temporary / MANIFEST_NAME
    with manifest_path.open("xb") as output:
        output.write(manifest_bytes)
    os.chmod(manifest_path, 0o644)


@contextmanager
def _validated_archive(
    archive: Path,
    *,
    expected_sha256: str,
    artifact_id: str,
    source_repository: str,
    source_commit: str,
    source_tree: str,
    producer_commit: str,
    recipe_sha256: str,
) -> Iterator[_ValidatedArchive]:
    """Open one pinned archive and validate all content before yielding."""
    if not _hex(expected_sha256, _HEX64):
        raise StageError("external archive SHA-256 is malformed")
    actual_sha256 = sha256_file(archive)
    if actual_sha256 != expected_sha256:
        raise StageError("CUDA profile archive SHA-256 does not match the external pin")
    try:
        tar = tarfile.open(archive, mode="r:gz")
    except Exception as exc:
        raise StageError("CUDA profile archive cannot be read") from exc
    with tar:
        try:
            members = _read_archive_members(tar)
            manifest_bytes = _read_manifest_bytes(tar, members)
            files, entrypoint = _validate_manifest(
                manifest_bytes,
                artifact_id=artifact_id,
                source_repository=source_repository,
                source_commit=source_commit,
                source_tree=source_tree,
                producer_commit=producer_commit,
                recipe_sha256=recipe_sha256,
            )
            _validate_archive_inventory(members, files)
            _validate_archive_payload(tar, members, files, entrypoint)
        except StageError:
            raise
        except Exception as exc:
            raise StageError("CUDA profile archive is malformed") from exc
        yield _ValidatedArchive(
            tar=tar,
            members=members,
            manifest_bytes=manifest_bytes,
            files=files,
            entrypoint=entrypoint,
            archive_sha256=actual_sha256,
        )


def verify_cuda_profile_archive(
    archive: Path,
    *,
    expected_sha256: str,
    artifact_id: str,
    source_repository: str,
    source_commit: str,
    source_tree: str,
    producer_commit: str,
    recipe_sha256: str,
) -> dict[str, str]:
    """Validate an archive read-only without staging or executing its files."""
    with _validated_archive(
        archive,
        expected_sha256=expected_sha256,
        artifact_id=artifact_id,
        source_repository=source_repository,
        source_commit=source_commit,
        source_tree=source_tree,
        producer_commit=producer_commit,
        recipe_sha256=recipe_sha256,
    ) as verified:
        return {
            "archive_sha256": verified.archive_sha256,
            "artifact_id": artifact_id,
            "manifest_sha256": hashlib.sha256(verified.manifest_bytes).hexdigest(),
        }


def stage_cuda_profile(
    archive: Path,
    bundle: Path,
    *,
    expected_sha256: str,
    artifact_id: str,
    source_repository: str,
    source_commit: str,
    source_tree: str,
    producer_commit: str,
    recipe_sha256: str,
) -> Path:
    """Verify every archive and profile identity before an atomic stage."""
    target, parent = _check_destination(bundle)
    with _validated_archive(
        archive,
        expected_sha256=expected_sha256,
        artifact_id=artifact_id,
        source_repository=source_repository,
        source_commit=source_commit,
        source_tree=source_tree,
        producer_commit=producer_commit,
        recipe_sha256=recipe_sha256,
    ) as verified:
        _check_destination(bundle)
        _ensure_profile_parent(Path(os.path.abspath(bundle)), parent)
        if target.exists() or target.is_symlink():
            raise StageError("CUDA profile destination appeared during validation")
        temporary_name = tempfile.mkdtemp(prefix=".cuda-profile-stage-", dir=parent)
        temporary = Path(temporary_name)
        try:
            _extract_archive_profile(
                verified.tar,
                verified.members,
                verified.files,
                verified.manifest_bytes,
                temporary,
            )
            temporary.chmod(0o755)
            if target.exists() or target.is_symlink():
                raise StageError("CUDA profile destination appeared during staging")
            os.replace(temporary, target)
            return target
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--producer-commit", required=True)
    parser.add_argument("--recipe-sha256", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Stage an explicitly pinned CUDA archive without downloading or running it."""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        destination = stage_cuda_profile(
            args.archive, args.bundle,
            expected_sha256=args.expected_sha256,
            artifact_id=args.artifact_id,
            source_repository=args.source_repository,
            source_commit=args.source_commit,
            source_tree=args.source_tree,
            producer_commit=args.producer_commit,
            recipe_sha256=args.recipe_sha256,
        )
    except (OSError, StageError, tarfile.TarError) as exc:
        parser.exit(1, f"stage-cuda-runtime-profile: error: {exc}\n")
    print(f"stage-cuda-runtime-profile: staged {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
