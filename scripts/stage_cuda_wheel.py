"""Fetch and verify the fixed reviewed CUDA wheel artifact for lock work.

This stages a hosted build candidate only. It verifies hashes and wheel
metadata without importing or installing the package.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HANDOFF_PATH = REPOSITORY_ROOT / "package" / "cuda-wheel-handoff.json"
DEFAULT_DESTINATION = REPOSITORY_ROOT / ".ci-inputs" / "cuda-wheel"
CHUNK_SIZE = 1024 * 1024


class HandoffError(RuntimeError):
    """The hosted artifact did not match its reviewed handoff manifest."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_archive_name(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and bool(path.parts)


def _manifest_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("== "):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key or not value:
            continue
        previous = values.get(key)
        if previous is not None and previous != value:
            raise HandoffError(f"build manifest has conflicting {key} values")
        values[key] = value
    return values


def _verify_build_manifest(text: str, handoff: Mapping[str, Any]) -> None:
    expected = dict(handoff["build"])
    values = _manifest_values(text)
    for key in (
        "wrapper_commit",
        "llama_cpp_commit",
        "cuda_image",
        "cuda_arch",
        "network_during_compile",
        "model_or_gpu_execution",
        "source_date_epoch",
        "cmake_archive_sha256",
    ):
        if values.get(key) != expected.get(key):
            raise HandoffError(f"build manifest mismatch for {key}")
    for key in ("wrapper_patch_sha256", "wrapper_version"):
        if key in expected and values.get(key) != expected[key]:
            raise HandoffError(f"build manifest mismatch for {key}")
    if "+capsize." in handoff["wheel"]["version"] and (
        not expected.get("wrapper_patch_sha256")
        or expected.get("wrapper_version") != handoff["wheel"]["version"]
    ):
        raise HandoffError("patched wrapper lacks source patch/version provenance")

    wheel = handoff["wheel"]
    wheel_matches = []
    backend_matches: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([0-9a-f]{64})\s+(.+)$", line)
        if not match:
            continue
        digest, raw_path = match.groups()
        basename = PurePosixPath(raw_path).name
        if basename == wheel["filename"]:
            wheel_matches.append(digest)
        elif basename in expected["backend_wheels"]:
            backend_matches[basename] = digest
    if wheel_matches != [wheel["sha256"]]:
        raise HandoffError("build manifest does not bind the exact wheel digest")
    if backend_matches != expected["backend_wheels"]:
        raise HandoffError("build manifest backend wheel hashes do not match")


def _verify_wheel(path: Path, spec: Mapping[str, Any]) -> int:
    if path.is_symlink() or not path.is_file():
        raise HandoffError("wheel input is not a regular file")
    if path.stat().st_size != spec["size_bytes"]:
        raise HandoffError("wheel size does not match the handoff manifest")
    if _sha256_file(path) != spec["sha256"]:
        raise HandoffError("wheel SHA-256 does not match the handoff manifest")

    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise HandoffError("wheel is not a valid ZIP archive") from exc

    with archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise HandoffError("wheel contains duplicate ZIP paths")
        for info in infos:
            if not _safe_archive_name(info.filename):
                raise HandoffError("wheel contains an unsafe ZIP path")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise HandoffError("wheel contains a symbolic link")

        metadata_names = [
            name for name in names if name.endswith(".dist-info/METADATA")
        ]
        wheel_names = [
            name for name in names if name.endswith(".dist-info/WHEEL")
        ]
        record_names = [
            name for name in names if name.endswith(".dist-info/RECORD")
        ]
        if len(metadata_names) != 1 or len(wheel_names) != 1 or len(record_names) != 1:
            raise HandoffError("wheel metadata layout is invalid")

        metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
        if metadata.get("Name", "").lower().replace("_", "-") != spec["name"].replace("_", "-"):
            raise HandoffError("wheel distribution name does not match")
        if metadata.get("Version") != spec["version"]:
            raise HandoffError("wheel version does not match")
        if metadata.get("Requires-Python") != spec["requires_python"]:
            raise HandoffError("wheel Python requirement does not match")
        license_value = metadata.get("License-Expression") or metadata.get("License")
        if license_value != spec["license"]:
            raise HandoffError("wheel license metadata does not match")
        required = set(spec["required_runtime_dependencies"])
        declared = set(metadata.get_all("Requires-Dist", []))
        if not required <= declared:
            raise HandoffError("wheel base runtime requirements do not match")
        optional = set(spec.get("optional_runtime_dependencies", []))
        if not optional <= declared:
            raise HandoffError("wheel optional runtime requirements do not match")
        isolated_names = set(spec.get("isolated_dependency_names", []))
        for requirement in declared:
            name = re.split(r"[<>=!~;\s\[]", requirement.strip(), maxsplit=1)[0]
            normalized = name.lower().replace("_", "-")
            if normalized in isolated_names and requirement not in optional:
                raise HandoffError("wheel activates an isolated optional dependency")

        wheel_text = archive.read(wheel_names[0]).decode("utf-8")
        if f"Tag: {spec['tag']}" not in wheel_text.splitlines():
            raise HandoffError("wheel platform tag does not match")
        if "llama_cpp/lib/libggml-cuda.so" not in names:
            raise HandoffError("wheel has no bundled CUDA backend library")

        record_name = record_names[0]
        record_rows = list(
            csv.reader(io.StringIO(archive.read(record_name).decode("utf-8")))
        )
        records: dict[str, tuple[str, str]] = {}
        for row in record_rows:
            if len(row) != 3 or row[0] in records:
                raise HandoffError("wheel RECORD layout is invalid")
            records[row[0]] = (row[1], row[2])
        if len(record_rows) != spec["record_entries"]:
            raise HandoffError("wheel RECORD entry count does not match")
        if set(records) != set(names):
            raise HandoffError("wheel RECORD does not cover its ZIP contents")

        by_name = {info.filename: info for info in infos}
        for name, (record_hash, record_size) in records.items():
            if name == record_name:
                if record_hash or record_size:
                    raise HandoffError("wheel RECORD self row is not empty")
                continue
            info = by_name[name]
            if not record_hash.startswith("sha256=") or not record_size:
                raise HandoffError("wheel RECORD entry lacks SHA-256 or size")
            expected_digest = record_hash.partition("=")[2]
            digest = hashlib.sha256()
            size = 0
            with archive.open(info) as stream:
                for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
                    digest.update(chunk)
                    size += len(chunk)
            actual_digest = base64.urlsafe_b64encode(digest.digest()).rstrip(b"=").decode("ascii")
            if actual_digest != expected_digest or size != int(record_size):
                raise HandoffError(f"wheel RECORD integrity mismatch for {name}")

        return len(record_rows)


def verify_artifact_directory(
    directory: Path, handoff: Mapping[str, Any]
) -> dict[str, Any]:
    """Verify an extracted Actions artifact without importing its wheel."""
    if directory.is_symlink() or not directory.is_dir():
        raise HandoffError("artifact directory must be a regular directory")
    wheel_spec = handoff["wheel"]
    expected_names = {"BUILD-MANIFEST.txt", wheel_spec["filename"]}
    entries = list(directory.iterdir())
    if any(entry.is_symlink() or not entry.is_file() for entry in entries):
        raise HandoffError("artifact contains a non-regular entry")
    if {entry.name for entry in entries} != expected_names:
        raise HandoffError("artifact file set does not match the handoff manifest")

    build_text = (directory / "BUILD-MANIFEST.txt").read_text(encoding="utf-8")
    _verify_build_manifest(build_text, handoff)
    record_entries = _verify_wheel(directory / wheel_spec["filename"], wheel_spec)
    return {
        "wheel": wheel_spec["filename"],
        "wheel_sha256": wheel_spec["sha256"],
        "record_entries": record_entries,
        "source_revision": handoff["artifact"]["source_revision"],
        "artifact_id": handoff["artifact"]["id"],
    }


def _load_handoff(path: Path = HANDOFF_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError("CUDA wheel handoff manifest is unavailable") from exc
    if value.get("schema_version") != 1:
        raise HandoffError("unsupported CUDA wheel handoff manifest version")
    return value


def _download_archive(archive_path: Path, handoff: Mapping[str, Any]) -> None:
    # gh accepts either its existing authenticated account or a workflow token.
    # Let the actual API request establish access rather than requiring a new
    # environment credential when the CLI already has a working login.
    artifact_id = handoff["artifact"]["id"]
    endpoint = (
        f"repos/{handoff['repository']}/actions/artifacts/{artifact_id}/zip"
    )
    try:
        with archive_path.open("wb") as output:
            subprocess.run(
                ["gh", "api", endpoint],
                check=True,
                stdout=output,
                stderr=subprocess.PIPE,
                text=False,
                timeout=600,
            )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HandoffError("GitHub Actions artifact download failed") from exc
    if _sha256_file(archive_path) != handoff["artifact"]["zip_sha256"]:
        raise HandoffError("Actions artifact ZIP SHA-256 does not match")


def _extract_archive(
    archive_path: Path, destination: Path, handoff: Mapping[str, Any]
) -> None:
    expected_names = {"BUILD-MANIFEST.txt", handoff["wheel"]["filename"]}
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            if {info.filename for info in infos} != expected_names:
                raise HandoffError("Actions artifact ZIP file set does not match")
            for info in infos:
                mode = (info.external_attr >> 16) & 0o170000
                if (
                    not _safe_archive_name(info.filename)
                    or info.is_dir()
                    or mode == 0o120000
                ):
                    raise HandoffError("Actions artifact ZIP contains an unsafe path")
            destination.mkdir(parents=True, exist_ok=False)
            for info in infos:
                target = destination / info.filename
                with archive.open(info) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, length=CHUNK_SIZE)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise HandoffError("Actions artifact ZIP could not be safely extracted") from exc


def stage_cuda_wheel(
    destination: Path = DEFAULT_DESTINATION,
    handoff_path: Path = HANDOFF_PATH,
) -> dict[str, Any]:
    """Download the fixed artifact, verify it, and stage only its two files."""
    handoff = _load_handoff(handoff_path)
    if destination.exists():
        try:
            return verify_artifact_directory(destination, handoff)
        except HandoffError as exc:
            raise HandoffError(
                "existing CUDA wheel staging directory is not the pinned artifact"
            ) from exc
    if destination.is_symlink():
        raise HandoffError("refusing a symbolic-link staging directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="airunner-cuda-wheel-", dir=destination.parent) as temp:
        archive_path = Path(temp) / "artifact.zip"
        extracted = Path(temp) / "extracted"
        _download_archive(archive_path, handoff)
        _extract_archive(archive_path, extracted, handoff)
        verified = verify_artifact_directory(extracted, handoff)
        extracted.rename(destination)
    return verified


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination", type=Path, default=DEFAULT_DESTINATION,
        help="directory to hold the verified wheel and BUILD-MANIFEST.txt",
    )
    parser.add_argument(
        "--verify-only", type=Path,
        help="verify an already extracted artifact directory without downloading",
    )
    args = parser.parse_args(argv)
    try:
        handoff = _load_handoff()
        result = (
            verify_artifact_directory(args.verify_only, handoff)
            if args.verify_only
            else stage_cuda_wheel(args.destination)
        )
    except HandoffError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        "verified CUDA wheel artifact "
        f"{result['artifact_id']} from {result['source_revision']}; "
        f"{result['wheel']} sha256={result['wheel_sha256']} "
        f"RECORD entries={result['record_entries']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
