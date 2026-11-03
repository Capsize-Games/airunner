"""Stage the reviewed CPU sidecar bundle and optional verified CUDA profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from urllib.parse import quote
from urllib.request import urlopen

from sidecar_archive import (
    SidecarArchiveError,
    _pin_record,
    _require_real_directory_chain,
    stage_full_bundle,
)
from stage_cuda_runtime_profile import StageError, stage_cuda_profile


ROOT = Path(__file__).resolve().parents[1]
NATIVE_REPOSITORY = "Capsize-Games/airunner-native"
CUDA_SOURCE_REPOSITORY = "https://github.com/ggml-org/llama.cpp.git"
CPU_CHECKSUMS = ROOT / ".github/native-sidecar-checksums.json"
CPU_TAG_FILE = ROOT / ".github/native-sidecar-version"
DEFAULT_CUDA_PIN = ROOT / ".github/native-cuda-profile-pin.json"
CPU_ASSET = "runtime-sidecars-linux.tar.gz"
CUDA_ASSET = "runtime-sidecars-linux-cuda-sm120a.tar.gz"
PIN_SCHEMA = "airunner-native-cuda-profile-pin-v1"
_TAG = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+\Z")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_PIN_BYTES = 1024 * 1024
_MAX_ASSET_BYTES = 8 * 1024**3


class PayloadStageError(ValueError):
    """A pinned native runtime payload could not be safely staged."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _read_cuda_pin(path: Path) -> dict:
    """Read a complete verified CUDA release pin; candidate records fail."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_PIN_BYTES:
        raise PayloadStageError(
            "verified CUDA profile pin is absent or unsafe; no CUDA profile is published yet"
        )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise PayloadStageError("CUDA profile pin is malformed") from error
    if not isinstance(record, dict):
        raise PayloadStageError("CUDA profile pin root is invalid")
    _validate_cuda_pin_fields(record)
    return record


def _validate_cuda_pin_fields(record: dict) -> None:
    """Validate release identity fields and their source/build provenance."""
    if (
        record.get("schema") != PIN_SCHEMA
        or record.get("status") != "verified"
        or record.get("release_repository") != NATIVE_REPOSITORY
        or record.get("asset") != CUDA_ASSET
    ):
        raise PayloadStageError("CUDA profile pin does not identify a verified published asset")
    if not isinstance(record.get("tag"), str) or not _TAG.fullmatch(record["tag"]):
        raise PayloadStageError("CUDA profile release tag is invalid")
    if not isinstance(record.get("archive_sha256"), str) or not _HEX64.fullmatch(record["archive_sha256"]):
        raise PayloadStageError("CUDA profile archive SHA-256 is invalid")
    if not isinstance(record.get("artifact_id"), str) or not record["artifact_id"].strip():
        raise PayloadStageError("CUDA profile artifact identity is missing")
    _validate_cuda_provenance(record.get("source"), record.get("producer"))


def _validate_cuda_provenance(source: object, producer: object) -> None:
    """Require the release source tree and producer recipe identities."""
    if not isinstance(source, dict) or not isinstance(producer, dict):
        raise PayloadStageError("CUDA profile source or producer identity is invalid")
    if (
        source.get("repository") != CUDA_SOURCE_REPOSITORY
        or not isinstance(source.get("commit"), str)
        or not _HEX40.fullmatch(source["commit"])
        or not isinstance(source.get("tree"), str)
        or not _HEX40.fullmatch(source["tree"])
        or not isinstance(producer.get("commit"), str)
        or not _HEX40.fullmatch(producer["commit"])
        or not isinstance(producer.get("recipe_sha256"), str)
        or not _HEX64.fullmatch(producer["recipe_sha256"])
    ):
        raise PayloadStageError("CUDA profile source or producer identity is invalid")


def _download(url: str, destination: Path) -> None:
    """Download one release asset into a private path with a hard size bound."""
    total = 0
    try:
        with urlopen(url, timeout=30) as response, destination.open("xb") as output:
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > _MAX_ASSET_BYTES:
                    raise PayloadStageError("native runtime release asset exceeds the size limit")
                output.write(block)
    except PayloadStageError:
        destination.unlink(missing_ok=True)
        raise
    except Exception as error:
        destination.unlink(missing_ok=True)
        raise PayloadStageError("could not fetch a pinned native runtime release asset") from error


def _asset_url(tag: str, asset: str) -> str:
    return (
        f"https://github.com/{NATIVE_REPOSITORY}/releases/download/"
        f"{quote(tag, safe='')}/{quote(asset, safe='')}"
    )


def _write_tree_checksums(root: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise PayloadStageError("staged native runtime contains a symlink")
        if path.is_file() and path.name != "SHA256SUMS":
            rows[path.relative_to(root).as_posix()] = _sha256(path)
    checksum_path = root / "SHA256SUMS"
    checksum_path.write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(rows.items())),
        encoding="utf-8",
    )
    return rows


def _replace_owned_payload(
    staged: Path, destination: Path, *, allow_drop_cuda: bool = False
) -> None:
    """Replace a previously staged tree only when it bears our marker."""
    if not destination.exists() and not destination.is_symlink():
        os.replace(staged, destination)
        return
    if destination.is_symlink() or not destination.is_dir():
        raise PayloadStageError("native runtime destination is not a real directory")
    marker = destination / ".airunner-native-owned"
    if marker.is_symlink() or not marker.is_file():
        raise PayloadStageError("refusing to replace an unowned native runtime directory")
    existing_cuda = destination / "share/airunner/native-runtimes/cuda-sm120a"
    new_cuda = staged / "share/airunner/native-runtimes/cuda-sm120a"
    if existing_cuda.exists() and not new_cuda.exists() and not allow_drop_cuda:
        raise PayloadStageError(
            "existing CUDA profile would be removed; select --sidecars-cuda with its verified pin"
        )
    backup = destination.with_name(f".{destination.name}.previous-{os.getpid()}")
    if backup.exists() or backup.is_symlink():
        raise PayloadStageError("native runtime replacement backup path already exists")
    os.replace(destination, backup)
    try:
        os.replace(staged, destination)
    except Exception:
        os.replace(backup, destination)
        raise
    shutil.rmtree(backup)


def stage_payload(
    *,
    cpu_archive: Path,
    output_dir: Path,
    cuda_profile_archive: Path | None = None,
    cuda_profile_pin: Path | None = None,
    require_cuda_profile: bool = False,
    replace_existing: bool = False,
    clean_existing: bool = False,
    checksums: Path = CPU_CHECKSUMS,
    tag_file: Path = CPU_TAG_FILE,
) -> dict:
    """Stage both payloads into one owned tree, committing only after validation."""
    if require_cuda_profile and (cuda_profile_archive is None or cuda_profile_pin is None):
        raise PayloadStageError(
            "full Linux/NVIDIA runtime requires a published verified CUDA profile archive and pin"
        )
    pin = _read_cuda_pin(cuda_profile_pin) if cuda_profile_pin is not None else None
    if (cuda_profile_archive is None) != (pin is None):
        raise PayloadStageError("CUDA profile archive and verified pin must be supplied together")

    output = Path(os.path.abspath(output_dir))
    parent = output.parent
    try:
        _require_real_directory_chain(parent)
    except SidecarArchiveError as error:
        raise PayloadStageError("native runtime output parent must be a real directory") from error
    if (output.exists() or output.is_symlink()) and not replace_existing:
        raise PayloadStageError("native runtime output already exists")

    temporary_root = Path(tempfile.mkdtemp(prefix=".native-runtime-", dir=parent))
    temp_root = temporary_root / "payload"
    try:
        cpu_digest = stage_full_bundle(
            cpu_archive,
            temp_root,
            checksums,
            tag_file,
            "linux",
        )
        cuda_digest = None
        if pin is not None and cuda_profile_archive is not None:
            stage_cuda_profile(
                cuda_profile_archive,
                temp_root,
                expected_sha256=pin["archive_sha256"],
                artifact_id=pin["artifact_id"],
                source_repository=pin["source"]["repository"],
                source_commit=pin["source"]["commit"],
                source_tree=pin["source"]["tree"],
                producer_commit=pin["producer"]["commit"],
                recipe_sha256=pin["producer"]["recipe_sha256"],
            )
            if _sha256(cuda_profile_archive) != pin["archive_sha256"]:
                raise PayloadStageError("CUDA profile archive changed after validation")
            cuda_digest = pin["archive_sha256"]
        cpu_tag, _ = _pin_record(checksums, tag_file, "linux")
        source = json.loads(checksums.read_text(encoding="utf-8"))
        receipt = {
            "schema": "airunner-native-payload-receipt-v1",
            "status": "verified",
            "cpu": {
                "tag": cpu_tag,
                "source_commit": source["source_commit"],
                "archive_sha256": cpu_digest,
                "asset": "runtime-sidecars-linux.tar.gz",
            },
            "cuda_profile": (
                {
                    "tag": pin["tag"],
                    "artifact_id": pin["artifact_id"],
                    "archive_sha256": cuda_digest,
                    "source": pin["source"],
                    "producer": pin["producer"],
                    "asset": pin["asset"],
                }
                if pin is not None
                else None
            ),
        }
        receipt_path = temp_root / "share/airunner/native-payload-receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_tree_checksums(temp_root)
        if output.exists() or output.is_symlink():
            if not replace_existing:
                raise PayloadStageError("native runtime output appeared during staging")
            _replace_owned_payload(temp_root, output, allow_drop_cuda=clean_existing)
        else:
            os.replace(temp_root, output)
        return receipt
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)


def fetch_and_stage(
    *,
    output_dir: Path,
    cuda_profile_pin: Path | None,
    require_cuda_profile: bool,
    replace_existing: bool,
    clean_existing: bool,
) -> dict:
    """Fetch only pinned public release assets, then stage their full payload."""
    pin = _read_cuda_pin(cuda_profile_pin) if cuda_profile_pin is not None else None
    if require_cuda_profile and pin is None:
        raise PayloadStageError(
            "full Linux/NVIDIA payload blocked: no reviewed CUDA profile pin is present"
        )
    if output_dir.exists() and not replace_existing:
        raise PayloadStageError("native runtime output already exists")
    parent = Path(os.path.abspath(output_dir)).parent
    try:
        _require_real_directory_chain(parent)
    except SidecarArchiveError as error:
        raise PayloadStageError("native runtime output parent must be a real directory") from error
    temp = Path(tempfile.mkdtemp(prefix=".native-runtime-fetch-", dir=parent))
    try:
        cpu_tag, _cpu_digest = _pin_record(CPU_CHECKSUMS, CPU_TAG_FILE, "linux")
        cpu_archive = temp / CPU_ASSET
        _download(_asset_url(cpu_tag, CPU_ASSET), cpu_archive)
        cuda_archive = None
        pin_path = None
        if pin is not None:
            cuda_archive = temp / CUDA_ASSET
            _download(_asset_url(pin["tag"], pin["asset"]), cuda_archive)
            pin_path = cuda_profile_pin
        staged = temp / "payload"
        receipt = stage_payload(
            cpu_archive=cpu_archive,
            output_dir=staged,
            cuda_profile_archive=cuda_archive,
            cuda_profile_pin=pin_path,
            require_cuda_profile=require_cuda_profile,
            checksums=CPU_CHECKSUMS,
            tag_file=CPU_TAG_FILE,
        )
        if output_dir.exists() or output_dir.is_symlink():
            if not replace_existing:
                raise PayloadStageError("native runtime output appeared during fetch")
            _replace_owned_payload(staged, output_dir, allow_drop_cuda=clean_existing)
        else:
            os.replace(staged, output_dir)
        return receipt
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    """Parse pinned payload inputs and report staging failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--cpu-archive", type=Path)
    parser.add_argument("--checksums", type=Path, default=CPU_CHECKSUMS)
    parser.add_argument("--tag-file", type=Path, default=CPU_TAG_FILE)
    parser.add_argument("--cuda-profile-archive", type=Path)
    parser.add_argument("--cuda-profile-pin", type=Path, default=DEFAULT_CUDA_PIN)
    parser.add_argument("--require-cuda-profile", action="store_true")
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--clean-existing", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.fetch:
            receipt = fetch_and_stage(
                output_dir=args.output_dir,
                cuda_profile_pin=(
                    args.cuda_profile_pin if args.require_cuda_profile else None
                ),
                require_cuda_profile=args.require_cuda_profile,
                replace_existing=args.replace_existing,
                clean_existing=args.clean_existing,
            )
        else:
            if args.cpu_archive is None:
                parser.error("--cpu-archive is required unless --fetch is selected")
            receipt = stage_payload(
                cpu_archive=args.cpu_archive,
                output_dir=args.output_dir,
                cuda_profile_archive=args.cuda_profile_archive,
                cuda_profile_pin=(
                    args.cuda_profile_pin if args.cuda_profile_archive else None
                ),
                require_cuda_profile=args.require_cuda_profile,
                replace_existing=args.replace_existing,
                clean_existing=args.clean_existing,
                checksums=args.checksums,
                tag_file=args.tag_file,
            )
    except (OSError, PayloadStageError, SidecarArchiveError, StageError) as error:
        parser.exit(1, f"stage-native-runtime-payload: error: {error}\n")
    print(f"stage-native-runtime-payload: staged {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
