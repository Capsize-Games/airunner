"""Place a built desktop chat client bundle in the release output directory.

The desktop chat surface is the cloud-excluded React build produced by the
web repo's ``airunner-desktop`` target (#2230). A release must ship that
build *and* make the daemon able to find it, otherwise the operator has to
hand-set ``AIRUNNER_CLIENT_BUNDLE`` on every machine. This script is that
packaging step: it copies a built ``dist/`` into the designated build
output directory under :data:`BUNDLE_SUBDIR`, verifies the result, and
writes a manifest so a release can be audited later.

The output directory is ``/media/joe/Megatron/airunner-desktop-builds/``
(the owner's designated build output location), overridable with
``AIRUNNER_DESKTOP_BUILD_DIR`` -- the same variable and default the daemon
uses to *find* the bundle, so packaging and discovery cannot drift apart.

Usage::

    venv/bin/python scripts/package_desktop_client.py \\
        --source /path/to/airunner-desktop/client/dist

    # verify an existing install without writing anything
    venv/bin/python scripts/package_desktop_client.py --verify-only

Nothing here is committed to git: the output directory lives outside the
repository (and is ignored if anyone points it inside one).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, List

from airunner_services.api.routes.client_bundle import (
    BUNDLE_SUBDIR,
    INDEX_FILE,
    build_output_directory,
    packaged_bundle_directory,
)

MANIFEST_NAME = "bundle-manifest.json"


def _relative_files(directory: Path) -> List[Path]:
    """Return every file under ``directory``, relative and sorted."""
    return sorted(
        path.relative_to(directory)
        for path in directory.rglob("*")
        if path.is_file() and path.name != MANIFEST_NAME
    )


def _sha256(path: Path) -> str:
    """Return the hex SHA-256 of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(directory: Path) -> Dict[str, object]:
    """Build the manifest describing one packaged bundle."""
    entries = [
        {
            "path": relative.as_posix(),
            "sha256": _sha256(directory / relative),
        }
        for relative in _relative_files(directory)
    ]
    return {
        "bundle": BUNDLE_SUBDIR,
        "index": INDEX_FILE,
        "files": entries,
    }


def _validate_source(source: Path) -> Path:
    """Return the resolved source directory or raise ``SystemExit``."""
    if not source.is_dir():
        raise SystemExit(f"source is not a directory: {source}")
    if not (source / INDEX_FILE).is_file():
        raise SystemExit(f"source has no {INDEX_FILE}: {source}")
    return source.resolve()


def _package(source: Path, destination: Path) -> Dict[str, object]:
    """Copy the built bundle into ``destination`` and write its manifest."""
    destination.mkdir(parents=True, exist_ok=True)
    for child in destination.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    shutil.copytree(source, destination, dirs_exist_ok=True)
    manifest = _manifest(destination)
    (destination / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def _report(destination: Path, manifest: Dict[str, object]) -> None:
    """Print where the bundle landed and how the daemon finds it."""
    print(f"packaged {len(manifest['files'])} files into {destination}")
    print(f"manifest: {destination / MANIFEST_NAME}")
    print("the daemon discovers this bundle with no environment set:")
    print(f"  build root: {build_output_directory()}")


def _verify() -> int:
    """Report whether the installed bundle is present and complete."""
    destination = packaged_bundle_directory()
    if not (destination / INDEX_FILE).is_file():
        print(f"FAIL: no {INDEX_FILE} under {destination}")
        return 1
    print(f"OK: {INDEX_FILE} present under {destination}")
    if not (destination / MANIFEST_NAME).is_file():
        print(f"WARN: no {MANIFEST_NAME} (bundle was not packaged here)")
        return 0
    recorded = json.loads(
        (destination / MANIFEST_NAME).read_text(encoding="utf-8")
    )
    return _verify_files(destination, recorded)


def _verify_files(destination: Path, recorded: Dict[str, object]) -> int:
    """Compare recorded manifest entries against the installed files."""
    pending = list(recorded.get("files") or [])
    if not pending:
        print("FAIL: manifest records no files")
        return 1
    for entry in pending:
        path = destination / str(entry["path"])
        if not path.is_file():
            print(f"FAIL: missing {entry['path']}")
            return 1
        if _sha256(path) != entry["sha256"]:
            print(f"FAIL: changed {entry['path']}")
            return 1
    print(f"OK: all {len(pending)} recorded files match")
    return 0


def main() -> int:
    """Package or verify the desktop client bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--destination", type=Path, default=None)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    if args.verify_only:
        return _verify()
    if args.source is None:
        parser.error("--source is required unless --verify-only is given")
    destination = args.destination or packaged_bundle_directory()
    manifest = _package(_validate_source(args.source), destination)
    _report(destination, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
