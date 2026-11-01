"""Verify and stage pinned sidecars, then extend a candidate manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tarfile
import tempfile

from sidecar_archive import SidecarArchiveError, extract_named_files, verify_archive


_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*\Z")


class StagingError(ValueError):
    """A sidecar archive or destination cannot be staged safely."""


def stage_sidecars(
    archive_path: Path,
    bundle: Path,
    manifest_name: str,
    names: list[str],
    checksums: Path,
    tag_file: Path,
    platform: str,
) -> None:
    """Verify pinned archive bytes before staging binaries and manifest."""
    verify_archive(archive_path, checksums, tag_file, platform)
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
        if (
            f"bin/{name}" in recorded
            or destination.exists()
            or destination.is_symlink()
        ):
            raise StagingError(f"bundle already contains sidecar {name}")

    with tempfile.TemporaryDirectory(prefix=".stage-sidecars-", dir=bundle) as temporary:
        work = Path(temporary)
        extracted = work / "selected"
        extracted.mkdir()
        try:
            binaries = extract_named_files(archive_path, extracted, names)
        except SidecarArchiveError as exc:
            raise StagingError(str(exc)) from exc
        for binary in binaries:
            with binary.open("rb") as payload:
                digest = hashlib.file_digest(payload, "sha256").hexdigest()
            manifest["files"].append({
                "path": f"bin/{binary.name}",
                "sha256": digest,
            })
        manifest["files"].sort(key=lambda entry: entry["path"])
        staged_manifest = work / "manifest.json"
        staged_manifest.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        bin_dir.mkdir(exist_ok=True)
        for binary in binaries:
            os.replace(binary, bin_dir / binary.name)
        os.replace(staged_manifest, manifest_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tarball", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--manifest", default="bundle-manifest.json")
    parser.add_argument("--checksums", type=Path, required=True)
    parser.add_argument("--tag-file", type=Path, required=True)
    parser.add_argument("--platform", choices=("linux", "windows"), required=True)
    parser.add_argument("names", nargs="+")
    args = parser.parse_args()
    try:
        stage_sidecars(
            args.tarball,
            args.bundle,
            args.manifest,
            args.names,
            args.checksums,
            args.tag_file,
            args.platform,
        )
    except (OSError, ValueError, tarfile.TarError) as exc:
        parser.exit(1, f"stage-sidecars: error: {exc}\n")
    print("stage-sidecars: staged " + " ".join(f"bin/{name}" for name in args.names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
