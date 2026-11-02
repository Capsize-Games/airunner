"""Build a candidate Triton wheel without bundled NVIDIA toolchain payloads.

The output keeps Triton's CUDA backend and JIT code. It requires the exact
external tools, headers, and CUPTI libraries described by the companion
manifest. The script does not install or import Triton and does not execute any
NVIDIA binary.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


DEFAULT_MANIFEST = (
    Path(__file__).resolve().parent.parent / "package" / "triton-external-toolchain-subset.json"
)
CHUNK_SIZE = 1024 * 1024
EXPECTED_MANIFEST_SHA256 = "ff68281c53526986f054b52d66211dd6f771085e0e0230331430698a7e953958"


class WheelError(ValueError):
    """Raised when a source wheel does not satisfy its pinned contract."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with archive.open(info, "r") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _check_zip_inventory(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    inventory: dict[str, zipfile.ZipInfo] = {}
    for info in archive.infolist():
        name = info.filename
        path = PurePosixPath(name)
        mode = info.external_attr >> 16
        file_type = stat.S_IFMT(mode)
        raw_parts = (name[:-1] if info.is_dir() else name).split("/")
        if (
            not name
            or info.orig_filename != name
            or any(part in {"", ".", ".."} for part in raw_parts)
            or "\\" in name
            or path.is_absolute()
            or ".." in path.parts
            or (path.parts and path.parts[0].endswith(":"))
            or file_type not in (0, stat.S_IFREG, stat.S_IFDIR)
        ):
            raise WheelError("wheel contains an unsafe member path or file type")
        if name in inventory:
            raise WheelError("wheel contains duplicate member names")
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise WheelError("wheel uses an unsupported compression method")
        inventory[name] = info
    return inventory


def _verify_record(archive: zipfile.ZipFile, inventory: dict[str, zipfile.ZipInfo]) -> str:
    record_names = [name for name in inventory if name.endswith(".dist-info/RECORD")]
    if len(record_names) != 1:
        raise WheelError("wheel must contain exactly one RECORD")
    record_name = record_names[0]
    rows = list(csv.reader(io.StringIO(archive.read(record_name).decode("utf-8"))))
    recorded: set[str] = set()
    for row in rows:
        if len(row) != 3:
            raise WheelError("wheel RECORD has a malformed row")
        name, encoded_hash, encoded_size = row
        if name in recorded or name not in inventory:
            raise WheelError("wheel RECORD has a duplicate or missing member")
        recorded.add(name)
        if name == record_name:
            if encoded_hash or encoded_size:
                raise WheelError("wheel RECORD must not hash itself")
            continue
        if not encoded_hash or not encoded_hash.startswith("sha256=") or not encoded_size:
            raise WheelError("wheel RECORD has an unhashed member")
        try:
            expected_digest = base64.urlsafe_b64decode(encoded_hash[7:] + "==").hex()
            expected_size = int(encoded_size)
        except (ValueError, TypeError):
            raise WheelError("wheel RECORD has an invalid hash or size") from None
        actual_digest, actual_size = _hash_member(archive, inventory[name])
        if actual_digest != expected_digest or actual_size != expected_size:
            raise WheelError("wheel RECORD does not match its member bytes")
    files = {name for name, info in inventory.items() if not info.is_dir()}
    if recorded != files:
        raise WheelError("wheel RECORD does not cover every file")
    return record_name


def _record_row(name: str, content_hash: str | None, size: int | None) -> tuple[str, str, str]:
    if content_hash is None:
        return (name, "", "")
    encoded = base64.urlsafe_b64encode(bytes.fromhex(content_hash)).decode("ascii").rstrip("=")
    return (name, f"sha256={encoded}", str(size))


def _manifest_source_and_excludes(manifest: dict[str, Any]) -> tuple[str, dict[str, dict[str, Any]]]:
    source = manifest.get("source", {}).get("hardening_candidate", {})
    if not source.get("filename") or not re.fullmatch(r"[0-9a-f]{64}", source.get("sha256", "")):
        raise WheelError("manifest does not pin the hardened source candidate")
    excluded = manifest.get("subset", {}).get("exclude_members")
    if not isinstance(excluded, list) or not excluded:
        raise WheelError("manifest has no excluded NVIDIA member inventory")
    by_path: dict[str, dict[str, Any]] = {}
    for item in excluded:
        path = item.get("path")
        if not isinstance(path, str) or path in by_path or not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")):
            raise WheelError("manifest has an invalid or duplicate excluded member")
        by_path[path] = item
    return source["sha256"], by_path


def _metadata_transform(content: bytes, old_version: str, new_version: str) -> bytes:
    old_line = f"Version: {old_version}".encode("ascii")
    new_line = f"Version: {new_version}".encode("ascii")
    if content.count(old_line) != 1:
        raise WheelError("wheel METADATA version does not match the candidate version")
    return content.replace(old_line, new_line, 1)


def build_candidate(
    source: Path,
    output: Path,
    manifest: dict[str, Any],
    *,
    expected_output_sha256: str | None = None,
) -> dict[str, Any]:
    source_sha256, excluded = _manifest_source_and_excludes(manifest)
    if source.name != manifest["source"]["hardening_candidate"]["filename"]:
        raise WheelError("input wheel filename does not match the pinned hardening candidate")
    if _sha256_file(source) != source_sha256:
        raise WheelError("input wheel digest does not match the pinned hardening candidate")
    if output.exists():
        raise WheelError("output wheel already exists")
    output.parent.mkdir(parents=True, exist_ok=True)

    output_version = manifest["subset"]["output_version"]
    output_filename = manifest["subset"]["output_filename"]
    if Path(output_filename).name != output_filename or output.name != output_filename:
        raise WheelError("output filename does not match the pinned subset manifest")
    if not output_version.startswith("3.7.1+"):
        raise WheelError("output version is outside the reviewed Triton release")

    temp_name = None
    created_output = False
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False) as temp:
            temp_name = temp.name
        with zipfile.ZipFile(source, "r") as src:
            inventory = _check_zip_inventory(src)
            old_record = _verify_record(src, inventory)
            for member, expected in excluded.items():
                info = inventory.get(member)
                if info is None:
                    raise WheelError("pinned excluded member is missing from the source wheel")
                digest, size = _hash_member(src, info)
                if digest != expected["sha256"] or size != expected["size_bytes"]:
                    raise WheelError("pinned excluded member bytes changed")

            dist_info = old_record.rsplit("/", 1)[0]
            metadata_name = f"{dist_info}/METADATA"
            if metadata_name not in inventory:
                raise WheelError("wheel METADATA is missing")
            metadata = _metadata_transform(
                src.read(metadata_name), manifest["subset"]["input_version"], output_version
            )
            new_dist_info = f"triton-{output_version}.dist-info"
            new_record = f"{new_dist_info}/RECORD"

            rename: dict[str, str] = {}
            content_overrides = {metadata_name: metadata}
            rows: list[tuple[str, str, str]] = []
            for name, info in inventory.items():
                if name in excluded or name == old_record:
                    continue
                new_name = new_dist_info + name[len(dist_info):] if name.startswith(dist_info + "/") else name
                if new_name in rename.values():
                    raise WheelError("dist-info rename creates a duplicate wheel member")
                rename[name] = new_name
                if name == metadata_name:
                    digest = hashlib.sha256(metadata).hexdigest()
                    size = len(metadata)
                else:
                    digest, size = _hash_member(src, info)
                rows.append(_record_row(new_name, digest, size))
            if metadata_name not in rename:
                raise WheelError("wheel metadata was excluded")
            rows.append(_record_row(new_record, None, None))
            record_stream = io.StringIO(newline="")
            csv.writer(record_stream, lineterminator="\n").writerows(rows)
            record_bytes = record_stream.getvalue().encode("utf-8")

            temp_path = Path(temp_name)
            with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as dst:
                for name in sorted(rename, key=lambda value: rename[value]):
                    info = inventory[name]
                    clone = zipfile.ZipInfo(rename[name], info.date_time)
                    clone.compress_type = info.compress_type
                    clone.comment = info.comment
                    clone.extra = info.extra
                    clone.create_system = info.create_system
                    clone.create_version = info.create_version
                    clone.extract_version = info.extract_version
                    clone.flag_bits = info.flag_bits
                    clone.internal_attr = info.internal_attr
                    clone.external_attr = info.external_attr
                    clone.file_size = len(content_overrides[name]) if name in content_overrides else info.file_size
                    with dst.open(clone, "w") as target:
                        if name in content_overrides:
                            target.write(content_overrides[name])
                        else:
                            with src.open(info, "r") as reader:
                                while chunk := reader.read(CHUNK_SIZE):
                                    target.write(chunk)
                record_info = zipfile.ZipInfo(new_record, (1980, 1, 1, 0, 0, 0))
                record_info.compress_type = zipfile.ZIP_DEFLATED
                record_info.external_attr = (stat.S_IFREG | 0o644) << 16
                dst.writestr(record_info, record_bytes, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

        with zipfile.ZipFile(temp_name, "r") as result:
            output_inventory = _check_zip_inventory(result)
            _verify_record(result, output_inventory)
            remaining = set(output_inventory)
            if remaining.intersection(excluded):
                raise WheelError("subset candidate still contains excluded NVIDIA members")
            for prefix in (
                "triton/backends/nvidia/bin/",
                "triton/backends/nvidia/include/",
                "triton/backends/nvidia/lib/cupti/",
            ):
                if any(name.startswith(prefix) for name in remaining):
                    raise WheelError("subset candidate still contains a blocked NVIDIA payload")
            libdevice = manifest["subset"]["retain_members"][0]
            retained = output_inventory.get(libdevice["path"])
            if retained is None:
                raise WheelError("subset candidate lost the redistributable libdevice member")
            digest, size = _hash_member(result, retained)
            if digest != libdevice["sha256"] or size != libdevice["size_bytes"]:
                raise WheelError("subset candidate changed the retained libdevice member")
            actual_metadata = result.read(f"triton-{output_version}.dist-info/METADATA")
            if f"Version: {output_version}".encode("ascii") not in actual_metadata:
                raise WheelError("subset candidate metadata version is incorrect")
            crc_bad = result.testzip()
            if crc_bad is not None:
                raise WheelError("subset candidate failed ZIP CRC validation")

        output_sha256 = _sha256_file(Path(temp_name))
        if expected_output_sha256 is not None and output_sha256 != expected_output_sha256:
            raise WheelError("subset candidate digest differs from the pinned output")
        os.link(temp_name, output)
        created_output = True
        Path(temp_name).unlink()
        temp_name = None
        return {
            "schema_version": 1,
            "status": "candidate-only; not installed/imported/loaded",
            "input_filename": source.name,
            "input_sha256": source_sha256,
            "output_filename": output.name,
            "output_sha256": output_sha256,
            "output_size_bytes": output.stat().st_size,
            "excluded_members": len(excluded),
            "record_verified": True,
            "zip_crc_verified": True,
            "retained_libdevice_sha256": manifest["subset"]["retain_members"][0]["sha256"],
            "external_toolchain_manifest_sha256": hashlib.sha256(
                DEFAULT_MANIFEST.read_bytes()
            ).hexdigest(),
        }
    except Exception:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        if created_output:
            output.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    try:
        manifest_bytes = args.manifest.read_bytes()
        if hashlib.sha256(manifest_bytes).hexdigest() != EXPECTED_MANIFEST_SHA256:
            raise WheelError("toolchain subset manifest digest is not the reviewed value")
        manifest = json.loads(manifest_bytes)
        output = args.output_dir / manifest["subset"]["output_filename"]
        report = output.with_suffix(output.suffix + ".report.json")
        if report.exists():
            raise WheelError("output report already exists")
        expected_output_sha256 = manifest["subset"].get("expected_candidate_sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", expected_output_sha256 or ""):
            raise WheelError("manifest does not pin the expected subset candidate digest")
        receipt = build_candidate(
            args.input, output, manifest, expected_output_sha256=expected_output_sha256
        )
        report.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, KeyError, WheelError, zipfile.BadZipFile) as error:
        print(f"Triton subset candidate: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
