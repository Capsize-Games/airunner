"""Verify pinned native sidecar archives and stage selected files safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile


_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
_TAG = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+\Z")
_COMMIT = re.compile(r"[a-f0-9]{40}\Z")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*\Z")
_MAX_ARCHIVE_BYTES = 8 * 1024**3
_MAX_TREE_BYTES = 8 * 1024**3
_MAX_TREE_ENTRIES = 20_000
_CPU_REQUIRED_FILES = {
    ".airunner-native-owned",
    "bin/llama-server",
    "bin/whisper-server",
    "share/airunner/licenses/llama.cpp-LICENSE",
    "share/airunner/licenses/whisper.cpp-LICENSE",
    "share/airunner/runtime_manifest.env",
    "share/airunner/runtime_pins.env",
    "share/airunner/source_provenance.env",
}


class SidecarArchiveError(ValueError):
    """A pin, archive member, or destination is invalid."""


def _pin_record(
    metadata_path: Path, tag_file: Path, platform: str
) -> tuple[str, str]:
    """Return the independently recorded tag and expected digest."""
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise SidecarArchiveError("sidecar checksum metadata must be an object")
    tag = metadata.get("tag")
    commit = metadata.get("source_commit")
    if not isinstance(tag, str) or not _TAG.fullmatch(tag):
        raise SidecarArchiveError("sidecar metadata tag is invalid")
    if tag_file.read_text(encoding="utf-8").strip() != tag:
        raise SidecarArchiveError("sidecar tag pin does not match checksum metadata")
    if not isinstance(commit, str) or not _COMMIT.fullmatch(commit):
        raise SidecarArchiveError("sidecar source commit pin is invalid")
    if metadata.get("provenance_status") != "verified":
        raise SidecarArchiveError(
            "sidecar archive provenance is pending verification; refusing use"
        )
    archives = metadata.get("archives")
    record = archives.get(platform) if isinstance(archives, dict) else None
    if not isinstance(record, dict):
        raise SidecarArchiveError(f"no sidecar archive record for {platform}")
    expected_name = f"runtime-sidecars-{platform}.tar.gz"
    if record.get("asset") != expected_name:
        raise SidecarArchiveError(f"sidecar archive asset name is invalid for {platform}")
    expected = record.get("sha256")
    if expected is None:
        raise SidecarArchiveError(
            f"expected SHA-256 for {platform} sidecar archive is pending "
            "provenance verification; refusing use"
        )
    if not isinstance(expected, str) or not _SHA256.fullmatch(expected):
        raise SidecarArchiveError(f"expected SHA-256 for {platform} sidecar archive is invalid")
    return tag, expected


def _source_record(metadata_path: Path, tag_file: Path) -> tuple[str, str]:
    """Return source identity only after explicit source-review readiness."""
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise SidecarArchiveError("sidecar checksum metadata must be an object")
    tag = metadata.get("tag")
    commit = metadata.get("source_commit")
    if not isinstance(tag, str) or not _TAG.fullmatch(tag):
        raise SidecarArchiveError("sidecar metadata tag is invalid")
    if tag_file.read_text(encoding="utf-8").strip() != tag:
        raise SidecarArchiveError("sidecar tag pin does not match checksum metadata")
    if not isinstance(commit, str) or not _COMMIT.fullmatch(commit):
        raise SidecarArchiveError("sidecar source commit pin is invalid")
    if metadata.get("source_review_status") != "reviewed":
        raise SidecarArchiveError(
            "native sidecar source review is pending; refusing clone or build"
        )
    return tag, commit


def verify_archive(
    archive_path: Path,
    metadata_path: Path,
    tag_file: Path,
    platform: str,
) -> str:
    """Verify the exact archive bytes against the independently pinned digest."""
    _, expected = _pin_record(metadata_path, tag_file, platform)
    digest = hashlib.sha256()
    total = 0
    with archive_path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            total += len(block)
            if total > _MAX_ARCHIVE_BYTES:
                raise SidecarArchiveError("sidecar archive exceeds the size limit")
            digest.update(block)
    actual = digest.hexdigest()
    if actual != expected:
        raise SidecarArchiveError(
            f"{platform} sidecar archive SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def stage_full_bundle(
    archive_path: Path,
    output_dir: Path,
    metadata_path: Path,
    tag_file: Path,
    platform: str,
) -> str:
    """Verify and atomically extract the complete CPU runtime archive.

    All notices and provenance records in the reviewed archive are retained.
    Existing output paths are never overwritten.
    """
    digest = verify_archive(archive_path, metadata_path, tag_file, platform)
    output = Path(os.path.abspath(output_dir))
    if output.exists() or output.is_symlink():
        raise SidecarArchiveError("sidecar bundle destination already exists")
    parent = output.parent
    _require_real_directory_chain(parent)
    with tarfile.open(archive_path, "r:gz") as archive:
        members = _read_full_bundle_members(archive)
        directories = _validate_full_bundle_inventory(members)
        _extract_full_bundle(archive, members, directories, output, parent)
    return digest


def _read_full_bundle_members(
    archive: tarfile.TarFile,
) -> dict[str, tuple[tarfile.TarInfo, bool]]:
    members: dict[str, tuple[tarfile.TarInfo, bool]] = {}
    total_size = 0
    for index, member in enumerate(archive):
        if index >= _MAX_TREE_ENTRIES:
            raise SidecarArchiveError("sidecar archive contains too many entries")
        relative = _normalized_member_path(member).as_posix()
        if relative in members:
            raise SidecarArchiveError("sidecar archive contains duplicate paths")
        is_directory = member.isdir()
        mode = member.mode & 0o7777
        if mode & (stat.S_ISUID | stat.S_ISGID):
            raise SidecarArchiveError("sidecar archive contains setuid or setgid mode")
        if is_directory and (mode != 0o755 or member.size != 0):
            raise SidecarArchiveError("sidecar archive directory mode or size is invalid")
        if not is_directory:
            if mode not in (0o644, 0o755) or member.size < 0:
                raise SidecarArchiveError("sidecar archive file mode or size is invalid")
            total_size += member.size
            if total_size > _MAX_TREE_BYTES:
                raise SidecarArchiveError("sidecar archive expands beyond the size limit")
        if relative not in {".", "bin", "share"} and not (
            relative == ".airunner-native-owned"
            or relative.startswith("bin/")
            or relative.startswith("share/")
        ):
            raise SidecarArchiveError("sidecar archive contains an unexpected root path")
        members[relative] = (member, is_directory)
    return members


def _validate_full_bundle_inventory(
    members: dict[str, tuple[tarfile.TarInfo, bool]],
) -> set[str]:
    files = {name for name, (_member, is_dir) in members.items() if not is_dir}
    directories = {
        name for name, (_member, is_dir) in members.items() if is_dir and name != "."
    }
    expected_directories = {
        parent.as_posix()
        for name in files
        for parent in PurePosixPath(name).parents
        if parent.as_posix() != "."
    }
    if not _CPU_REQUIRED_FILES.issubset(files):
        raise SidecarArchiveError("sidecar archive lacks required CPU binaries or provenance")
    if directories != expected_directories:
        raise SidecarArchiveError("sidecar archive has unlisted or missing directories")
    return directories


def _extract_full_bundle(
    archive: tarfile.TarFile,
    members: dict[str, tuple[tarfile.TarInfo, bool]],
    directories: set[str],
    output: Path,
    parent: Path,
) -> None:
    temporary = Path(tempfile.mkdtemp(prefix=".sidecar-bundle-", dir=parent))
    try:
        for relative in sorted(directories, key=lambda value: (value.count("/"), value)):
            (temporary / PurePosixPath(relative)).mkdir(mode=0o755)
        for relative, (member, is_directory) in members.items():
            if is_directory or relative == ".":
                continue
            source = archive.extractfile(member)
            if source is None:
                raise SidecarArchiveError("cannot read sidecar archive file")
            destination = temporary / PurePosixPath(relative)
            with source, destination.open("xb") as destination_stream:
                shutil.copyfileobj(source, destination_stream)
            destination.chmod(member.mode & 0o777)
        if output.exists() or output.is_symlink():
            raise SidecarArchiveError("sidecar bundle destination appeared during staging")
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _require_real_directory_chain(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError as error:
            raise SidecarArchiveError("sidecar bundle parent is incomplete") from error
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise SidecarArchiveError("sidecar bundle parent must be a real directory")


def verify_source_checkout(
    repository: Path, metadata_path: Path, tag_file: Path
) -> str:
    """Require a source checkout to match the independently pinned commit."""
    _, commit = _source_record(metadata_path, tag_file)
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    actual = result.stdout.strip()
    if actual != commit:
        raise SidecarArchiveError(
            f"native sidecar checkout mismatch: expected {commit}, got {actual}"
        )
    dirty = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    )
    if dirty.stdout.strip():
        raise SidecarArchiveError("native sidecar checkout contains local changes")
    return actual


def _normalized_member_path(member: tarfile.TarInfo) -> PurePosixPath:
    """Validate one archive path and allow only regular files/directories."""
    name = member.name
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or "\x00" in name
        or not (member.isdir() or member.isfile())
    ):
        raise SidecarArchiveError("sidecar archive contains an unsafe entry")
    normalized = PurePosixPath(*(part for part in path.parts if part not in {"", "."}))
    if normalized == PurePosixPath(".") and member.isfile():
        raise SidecarArchiveError("sidecar archive contains a file without a path")
    return normalized


def extract_named_files(
    archive_path: Path, output_dir: Path, names: list[str]
) -> list[Path]:
    """Copy only uniquely named regular files; never extract archive paths."""
    if not names or any(not _NAME.fullmatch(name) for name in names):
        raise SidecarArchiveError("invalid sidecar names")
    if len(set(names)) != len(names):
        raise SidecarArchiveError("duplicate requested sidecar names")
    if output_dir.is_symlink() or not output_dir.is_dir():
        raise SidecarArchiveError("sidecar output directory is not a real directory")
    if any((output_dir / name).exists() or (output_dir / name).is_symlink() for name in names):
        raise SidecarArchiveError("sidecar output already contains a requested binary")

    with tarfile.open(archive_path, "r:gz") as archive:
        selected: dict[str, tarfile.TarInfo] = {}
        seen: set[str] = set()
        for member in archive:
            path = _normalized_member_path(member)
            normalized = path.as_posix() or "."
            if normalized in seen:
                raise SidecarArchiveError("sidecar archive contains duplicate paths")
            seen.add(normalized)
            if path.name in names:
                if not member.isfile() or path.name in selected:
                    raise SidecarArchiveError(
                        "sidecar name is ambiguous or not a regular file"
                    )
                selected[path.name] = member
        if set(selected) != set(names):
            raise SidecarArchiveError("sidecar archive is missing a requested binary")

        with tempfile.TemporaryDirectory(prefix=".sidecar-stage-", dir=output_dir) as tmp:
            work = Path(tmp)
            staged: list[Path] = []
            for name in names:
                source = archive.extractfile(selected[name])
                if source is None:
                    raise SidecarArchiveError("cannot read sidecar payload")
                target = work / name
                with source, target.open("xb") as destination:
                    shutil.copyfileobj(source, destination)
                target.chmod(0o755)
                staged.append(target)
            # output_dir is task-owned/fresh for the installer and candidates
            # preflight destination conflicts before calling this helper.
            for name in names:
                if (output_dir / name).exists() or (output_dir / name).is_symlink():
                    raise SidecarArchiveError("sidecar output changed during staging")
            result = []
            for name, source in zip(names, staged, strict=True):
                destination = output_dir / name
                os.replace(source, destination)
                result.append(destination)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (
        "check-pin", "verify", "stage", "stage-bundle", "check-source-pin", "verify-source"
    ):
        sub = subparsers.add_parser(command)
        sub.add_argument("--checksums", type=Path, required=True)
        sub.add_argument("--tag-file", type=Path, required=True)
        if command == "verify-source":
            sub.add_argument("--repository", type=Path, required=True)
        elif command not in {"check-pin", "check-source-pin"}:
            sub.add_argument("--tarball", type=Path, required=True)
        if command not in {"verify-source", "check-source-pin"}:
            sub.add_argument("--platform", choices=("linux", "windows"), required=True)
        if command in {"stage", "stage-bundle"}:
            sub.add_argument("--output-dir", type=Path, required=True)
            if command == "stage":
                sub.add_argument("names", nargs="+")
    return parser


def main() -> int:
    """Validate the selected archive operation and report its result."""
    args = _parser().parse_args()
    try:
        if args.command == "verify-source":
            identity = verify_source_checkout(
                args.repository, args.checksums, args.tag_file
            )
            print(f"sidecar source verified: commit={identity}")
            return 0
        if args.command == "check-source-pin":
            _, commit = _source_record(args.checksums, args.tag_file)
            print(f"sidecar source review ready: commit={commit}")
            return 0
        if args.command == "check-pin":
            _, digest = _pin_record(args.checksums, args.tag_file, args.platform)
            print(f"sidecar archive pin ready: {args.platform} sha256={digest}")
            return 0
        if args.command == "stage-bundle":
            digest = stage_full_bundle(
                args.tarball,
                args.output_dir,
                args.checksums,
                args.tag_file,
                args.platform,
            )
        else:
            digest = verify_archive(
                args.tarball, args.checksums, args.tag_file, args.platform
            )
        if args.command == "stage":
            extract_named_files(args.tarball, args.output_dir, args.names)
        print(f"sidecar archive verified: {args.platform} sha256={digest}")
    except (OSError, ValueError, tarfile.TarError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"sidecar archive: error: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
