"""Package and verify the Linux candidate release archive.

The directory bundle is verified before archiving. This helper preserves
executable modes and safe in-tree symlinks while rejecting special files and
symlinks that escape the bundle. Archives carry the candidate version and the
full source SHA in their filename and manifest.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import stat
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.!+_-]{0,127}$")
_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST = "bundle-manifest.json"


class CandidateArtifactError(ValueError):
    """A candidate directory/archive violates release artifact rules."""


def archive_filename(version: str, source_sha: str) -> str:
    """Return the stable version/source-identified archive basename."""
    _validate_identity(version, source_sha)
    return f"airunner-services-linux-{version}-{source_sha[:12]}.tar.gz"


def _validate_identity(version: str, source_sha: str) -> None:
    if not _VERSION_RE.fullmatch(version) or not _SHA_RE.fullmatch(source_sha):
        raise CandidateArtifactError("invalid candidate version or source SHA")


def _relative_name(path: Path) -> str:
    name = path.as_posix()
    parsed = PurePosixPath(name)
    if parsed.is_absolute() or not name or any(
        part in ("", ".", "..") for part in parsed.parts
    ):
        raise CandidateArtifactError("candidate contains an unsafe path")
    return name


def _symlink_target_is_safe(root: Path, path: Path, target: str) -> None:
    if not target or os.path.isabs(target):
        raise CandidateArtifactError("candidate contains an unsafe symlink")
    try:
        resolved = (path.parent / target).resolve(strict=False)
        resolved.relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        raise CandidateArtifactError("candidate symlink escapes its root") from None


def _walk(root: Path) -> list[tuple[Path, str, os.stat_result]]:
    """Return all descendants in archive order, rejecting special entries."""
    entries: list[tuple[Path, str, os.stat_result]] = []
    root = root.resolve()
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as scan:
                children = sorted(scan, key=lambda item: item.name)
        except OSError as exc:
            raise CandidateArtifactError("cannot read candidate directory") from exc
        subdirs: list[Path] = []
        for child in children:
            path = Path(child.path)
            relative = _relative_name(path.relative_to(root))
            try:
                info = path.lstat()
            except OSError as exc:
                raise CandidateArtifactError("cannot inspect candidate entry") from exc
            if stat.S_ISDIR(info.st_mode):
                if info.st_mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
                    raise CandidateArtifactError("candidate has unsafe mode bits")
                entries.append((path, relative, info))
                subdirs.append(path)
            elif stat.S_ISREG(info.st_mode):
                if info.st_mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
                    raise CandidateArtifactError("candidate has unsafe mode bits")
                entries.append((path, relative, info))
            elif stat.S_ISLNK(info.st_mode):
                target = os.readlink(path)
                _symlink_target_is_safe(root, path, target)
                entries.append((path, relative, info))
            else:
                raise CandidateArtifactError("candidate contains a special file")
        pending.extend(reversed(subdirs))
    return sorted(entries, key=lambda item: item[1])


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_directory(root: Path, source_sha: str) -> bytes:
    manifest_path = root / _MANIFEST
    try:
        manifest_info = manifest_path.lstat()
    except OSError as exc:
        raise CandidateArtifactError(
            "candidate manifest is missing or invalid"
        ) from exc
    if not stat.S_ISREG(manifest_info.st_mode):
        raise CandidateArtifactError("candidate manifest is not a regular file")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
    ) as exc:
        raise CandidateArtifactError(
            "candidate manifest is missing or invalid"
        ) from exc
    if not isinstance(manifest, dict) or manifest.get("base") != source_sha:
        raise CandidateArtifactError("candidate manifest source SHA does not match")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise CandidateArtifactError("candidate manifest has no files")
    expected: dict[str, str] = {}
    for item in files:
        if not isinstance(item, dict):
            raise CandidateArtifactError("candidate manifest entry is invalid")
        path_name = item.get("path")
        digest = item.get("sha256")
        if (
            not isinstance(path_name, str)
            or not isinstance(digest, str)
            or not _HEX_RE.fullmatch(digest)
        ):
            raise CandidateArtifactError("candidate manifest entry is invalid")
        parsed = PurePosixPath(path_name)
        if parsed.is_absolute() or not path_name or any(
            part in ("", ".", "..") for part in parsed.parts
        ):
            raise CandidateArtifactError("candidate manifest path is unsafe")
        if path_name == _MANIFEST or path_name in expected:
            raise CandidateArtifactError("candidate manifest has duplicate paths")
        expected[path_name] = digest

    entries = _walk(root)
    actual = {
        name for path, name, _ in entries
        if name != _MANIFEST and path.is_file()
    }
    if actual != set(expected):
        raise CandidateArtifactError("candidate files do not match manifest")
    for path, name, _ in entries:
        if name in expected and _hash_file(path) != expected[name]:
            raise CandidateArtifactError("candidate manifest hash mismatch")
    return manifest_bytes


def _tar_info(
    name: str, info: os.stat_result, *, is_dir: bool = False
) -> tarfile.TarInfo:
    tar_info = tarfile.TarInfo(name + ("/" if is_dir else ""))
    tar_info.uid = 0
    tar_info.gid = 0
    tar_info.uname = ""
    tar_info.gname = ""
    tar_info.mtime = 0
    tar_info.mode = stat.S_IMODE(info.st_mode)
    if is_dir:
        tar_info.type = tarfile.DIRTYPE
    elif stat.S_ISLNK(info.st_mode):
        tar_info.type = tarfile.SYMTYPE
    else:
        tar_info.type = tarfile.REGTYPE
        tar_info.size = info.st_size
    return tar_info


def create_archive(
    bundle_dir: Path, output_dir: Path, version: str, source_sha: str
) -> Path:
    """Verify and create a mode-preserving archive for the candidate."""
    _validate_identity(version, source_sha)
    root = bundle_dir.resolve()
    if not root.is_dir():
        raise CandidateArtifactError("candidate bundle directory is absent")
    _verify_directory(root, source_sha)
    entries = _walk(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / archive_filename(version, source_sha)
    if destination.exists():
        raise CandidateArtifactError("candidate archive destination already exists")

    prefix = destination.name.removesuffix(".tar.gz")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=output_dir, prefix=f".{destination.name}.",
            delete=False,
        ) as raw:
            temporary_path = Path(raw.name)
            with gzip.GzipFile(
                filename="", mode="wb", fileobj=raw, mtime=0
            ) as compressed:
                with tarfile.open(
                    fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT
                ) as archive:
                    for path, relative, info in entries:
                        name = f"{prefix}/{relative}"
                        is_dir = stat.S_ISDIR(info.st_mode)
                        tar_info = _tar_info(name, info, is_dir=is_dir)
                        if stat.S_ISLNK(info.st_mode):
                            tar_info.linkname = os.readlink(path)
                            archive.addfile(tar_info)
                        elif stat.S_ISREG(info.st_mode):
                            with path.open("rb") as content:
                                archive.addfile(tar_info, content)
                        else:
                            archive.addfile(tar_info)
            raw.flush()
            os.fsync(raw.fileno())
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    try:
        verify_archive(destination, version, source_sha)
    except CandidateArtifactError:
        destination.unlink(missing_ok=True)
        raise
    return destination


def _safe_member_name(name: str, prefix: str) -> str:
    parsed = PurePosixPath(name)
    if parsed.is_absolute() or any(part in ("", ".", "..") for part in parsed.parts):
        raise CandidateArtifactError("candidate archive contains an unsafe path")
    parts = parsed.parts
    if not parts or parts[0] != prefix:
        raise CandidateArtifactError("candidate archive has an unexpected root")
    return "/".join(parts[1:])


def _version_from_archive(path: Path, source_sha: str) -> str:
    suffix = f"-{source_sha[:12]}.tar.gz"
    prefix = "airunner-services-linux-"
    if not path.name.startswith(prefix) or not path.name.endswith(suffix):
        raise CandidateArtifactError("candidate archive identity does not match")
    version = path.name[len(prefix):-len(suffix)]
    _validate_identity(version, source_sha)
    return version


def verify_archive(
    path: Path, version: str | None, source_sha: str
) -> None:
    """Validate archive identity, safe members, manifest hashes and modes."""
    version = version or _version_from_archive(path, source_sha)
    _validate_identity(version, source_sha)
    expected_name = archive_filename(version, source_sha)
    if path.name != expected_name or not path.is_file():
        raise CandidateArtifactError("candidate archive identity does not match")
    prefix = expected_name.removesuffix(".tar.gz")
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            members = archive.getmembers()
            by_name: dict[str, tarfile.TarInfo] = {}
            for member in members:
                relative = _safe_member_name(member.name, prefix)
                if not relative:
                    continue
                if relative in by_name:
                    raise CandidateArtifactError(
                        "candidate archive has duplicate entries"
                    )
                if not (member.isfile() or member.isdir() or member.issym()):
                    raise CandidateArtifactError(
                        "candidate archive has a special entry"
                    )
                if member.mode & 0o7000:
                    raise CandidateArtifactError(
                        "candidate archive has unsafe mode bits"
                    )
                if member.issym():
                    _safe_archive_symlink(relative, member.linkname)
                by_name[relative] = member
            symlink_paths = {
                name for name, member in by_name.items() if member.issym()
            }
            for name in by_name:
                parts = PurePosixPath(name).parts
                if any("/".join(parts[:index]) in symlink_paths
                       for index in range(1, len(parts))):
                    raise CandidateArtifactError(
                        "candidate archive has entries beneath a symlink"
                    )
            manifest_member = by_name.get(_MANIFEST)
            if manifest_member is None or not manifest_member.isfile():
                raise CandidateArtifactError("candidate archive manifest is absent")
            stream = archive.extractfile(manifest_member)
            if stream is None:
                raise CandidateArtifactError("candidate archive manifest is unreadable")
            manifest_bytes = stream.read(4 * 1024 * 1024 + 1)
            if len(manifest_bytes) > 4 * 1024 * 1024:
                raise CandidateArtifactError("candidate archive manifest is oversized")
            manifest = json.loads(manifest_bytes.decode("utf-8"))
            if not isinstance(manifest, dict) or manifest.get("base") != source_sha:
                raise CandidateArtifactError(
                    "candidate archive source SHA does not match"
                )
            files = manifest.get("files")
            if not isinstance(files, list) or not files:
                raise CandidateArtifactError("candidate archive manifest has no files")
            expected: dict[str, str] = {}
            for item in files:
                if not isinstance(item, dict):
                    raise CandidateArtifactError(
                        "candidate archive manifest is invalid"
                    )
                file_name, digest = item.get("path"), item.get("sha256")
                if (
                    not isinstance(file_name, str)
                    or not isinstance(digest, str)
                    or not _HEX_RE.fullmatch(digest)
                ):
                    raise CandidateArtifactError(
                        "candidate archive manifest is invalid"
                    )
                parsed = PurePosixPath(file_name)
                if parsed.is_absolute() or not file_name or any(
                    part in ("", ".", "..") for part in parsed.parts
                ):
                    raise CandidateArtifactError(
                        "candidate archive manifest path is unsafe"
                    )
                if file_name == _MANIFEST or file_name in expected:
                    raise CandidateArtifactError(
                        "candidate archive manifest has duplicate paths"
                    )
                expected[file_name] = digest
            actual = {
                name for name, member in by_name.items()
                if member.isfile()
                or (member.issym() and _archive_resolves_to_file(by_name, name))
            }
            actual.discard(_MANIFEST)
            if actual != set(expected):
                raise CandidateArtifactError(
                    "candidate archive files do not match manifest"
                )
            for file_name, digest in expected.items():
                resolved = _resolve_archive_file(by_name, file_name)
                member = by_name[resolved]
                data = archive.extractfile(member)
                if data is None:
                    raise CandidateArtifactError("candidate archive file is unreadable")
                actual_digest = hashlib.sha256()
                for chunk in iter(lambda: data.read(1024 * 1024), b""):
                    actual_digest.update(chunk)
                if actual_digest.hexdigest() != digest:
                    raise CandidateArtifactError("candidate archive hash mismatch")
    except (
        OSError,
        EOFError,
        tarfile.TarError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
    ) as exc:
        raise CandidateArtifactError("candidate archive is invalid") from exc


def _safe_archive_symlink(relative: str, target: str) -> None:
    if not target or target.startswith("/"):
        raise CandidateArtifactError("candidate archive has an unsafe symlink")
    base = list(PurePosixPath(relative).parent.parts)
    for part in PurePosixPath(target).parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not base:
                raise CandidateArtifactError("candidate archive symlink escapes root")
            base.pop()
        else:
            base.append(part)


def _resolve_archive_file(
    members: dict[str, tarfile.TarInfo], name: str, seen: set[str] | None = None
) -> str:
    seen = set() if seen is None else seen
    if name in seen:
        raise CandidateArtifactError("candidate archive has a symlink cycle")
    seen.add(name)
    member = members.get(name)
    if member is None:
        raise CandidateArtifactError("candidate archive symlink target is absent")
    if member.isfile():
        return name
    if not member.issym():
        raise CandidateArtifactError("candidate archive manifest path is not a file")
    parent = list(PurePosixPath(name).parent.parts)
    for part in PurePosixPath(member.linkname).parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not parent:
                raise CandidateArtifactError("candidate archive symlink escapes root")
            parent.pop()
        else:
            parent.append(part)
    return _resolve_archive_file(members, "/".join(parent), seen)


def _archive_resolves_to_file(members: dict[str, tarfile.TarInfo], name: str) -> bool:
    try:
        _resolve_archive_file(members, name)
    except CandidateArtifactError:
        return False
    return True


def write_checksums(paths: list[Path], output: Path) -> None:
    """Write SHA256SUMS for distinct release asset basenames."""
    assets: dict[str, Path] = {}
    for path in paths:
        if path.resolve() == output.resolve():
            continue
        if not path.is_file() or path.name in ("", ".", ".."):
            raise CandidateArtifactError("release asset is absent or invalid")
        if not re.fullmatch(r"[A-Za-z0-9._+-]+", path.name):
            raise CandidateArtifactError("release asset basename is unsafe")
        if path.name in assets:
            raise CandidateArtifactError("release assets have a basename collision")
        assets[path.name] = path
    if not assets:
        raise CandidateArtifactError("no release assets to checksum")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        f"{_hash_file(path)}  {name}\n"
        for name, path in sorted(assets.items())
    )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="ascii", dir=output.parent,
            prefix=f".{output.name}.", delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, output)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--bundle", type=Path, required=True)
    create.add_argument("--output-dir", type=Path, required=True)
    create.add_argument("--version", required=True)
    create.add_argument("--source-sha", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--archive", type=Path, required=True)
    verify.add_argument("--version")
    verify.add_argument("--source-sha", required=True)
    checksums = commands.add_parser("checksums")
    checksums.add_argument("--output", type=Path, required=True)
    checksums.add_argument("assets", nargs="+", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            print(
                create_archive(
                    args.bundle, args.output_dir, args.version, args.source_sha
                )
            )
        elif args.command == "verify":
            verify_archive(args.archive, args.version, args.source_sha)
            print("candidate archive verified")
        else:
            write_checksums(args.assets, args.output)
            print(args.output)
    except CandidateArtifactError as exc:
        print(f"candidate artifact error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
