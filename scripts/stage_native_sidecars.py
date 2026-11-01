"""Stage named regular-file sidecars without extracting archive paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile


_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*\Z")


class StagingError(ValueError):
    """A sidecar archive or destination cannot be staged safely."""


def _archive_path(member: tarfile.TarInfo) -> PurePosixPath:
    name = member.name
    path = PurePosixPath(name)
    # Native bundles use tar -C <root> ... ., which emits ./ prefixes.
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or "\x00" in name
        or not (member.isdir() or member.isfile())
    ):
        raise StagingError("sidecar archive contains an unsafe entry")
    return path


def stage_sidecars(
    archive_path: Path, bundle: Path, manifest_name: str, names: list[str]
) -> None:
    """Validate all requested payloads and the manifest before staging files.

    Archive member paths are never passed to filesystem extraction. A sidecar
    name must identify exactly one regular file in the archive. Existing
    payloads and recorded manifest paths cannot be overwritten.
    """
    if not names or any(not _NAME.fullmatch(name) for name in names):
        raise StagingError("invalid sidecar names")
    if len(set(names)) != len(names) or not _NAME.fullmatch(manifest_name):
        raise StagingError("duplicate sidecar or invalid manifest name")
    manifest_path = bundle / manifest_name
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise StagingError("bundle manifest is not a regular file")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise StagingError("bundle manifest files are invalid")
    recorded: set[str] = set()
    for entry in manifest["files"]:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("path"), str)
            or entry["path"] in recorded
        ):
            raise StagingError("bundle manifest has invalid or duplicate entries")
        recorded.add(entry["path"])
    bin_dir = bundle / "bin"
    if bin_dir.is_symlink() or (bin_dir.exists() and not bin_dir.is_dir()):
        raise StagingError("bundle bin destination is not a directory")
    for name in names:
        destination = bin_dir / name
        if f"bin/{name}" in recorded or destination.exists() or destination.is_symlink():
            raise StagingError(f"bundle already contains sidecar {name}")

    with tarfile.open(archive_path, "r:gz") as archive:
        selected: dict[str, tarfile.TarInfo] = {}
        seen: set[str] = set()
        for member in archive:
            member_path = _archive_path(member)
            normalized = member_path.as_posix()
            if normalized in seen:
                raise StagingError("sidecar archive contains duplicate paths")
            seen.add(normalized)
            if member_path.name in names:
                if not member.isfile() or member_path.name in selected:
                    raise StagingError("sidecar name is ambiguous or not a regular file")
                selected[member_path.name] = member
        if set(selected) != set(names):
            raise StagingError("sidecar archive is missing a requested binary")

        with tempfile.TemporaryDirectory(prefix=".stage-sidecars-", dir=bundle) as temporary:
            work = Path(temporary)
            for name in names:
                source = archive.extractfile(selected[name])
                if source is None:
                    raise StagingError("cannot read sidecar payload")
                staged = work / name
                with source, staged.open("xb") as target:
                    shutil.copyfileobj(source, target)
                staged.chmod(0o755)
                with staged.open("rb") as payload:
                    digest = hashlib.file_digest(payload, "sha256").hexdigest()
                manifest["files"].append({
                    "path": f"bin/{name}",
                    "sha256": digest,
                })
            manifest["files"].sort(key=lambda entry: entry["path"])
            staged_manifest = work / "manifest.json"
            staged_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            bin_dir.mkdir(exist_ok=True)
            for name in names:
                os.replace(work / name, bin_dir / name)
            os.replace(staged_manifest, manifest_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tarball", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--manifest", default="bundle-manifest.json")
    parser.add_argument("names", nargs="+")
    args = parser.parse_args()
    try:
        stage_sidecars(args.tarball, args.bundle, args.manifest, args.names)
    except (OSError, ValueError, tarfile.TarError) as exc:
        parser.exit(1, f"stage-sidecars: error: {exc}\n")
    print("stage-sidecars: staged " + " ".join(f"bin/{name}" for name in args.names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
