"""Freeze and verify reviewed runtime wheels for the immutable app release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "package/linux-release-v4-artifact-sources.json"
SOURCE_LOCK = ROOT / "package/constraints-linux-nvidia-cu129-linux-release.txt"
ASSET_MANIFEST = "runtime-wheel-assets.json"
STAGING_RECEIPT = "staging-receipt.json"
_SHA_RE = re.compile(r"[0-9a-f]{40}")
_HEX_RE = re.compile(r"[0-9a-f]{64}")
_ACTION_DISTRIBUTIONS = {
    "llama-cpp-python",
    "nvidia-nvshmem-cu12",
    "torchaudio",
    "torchvision",
    "triton",
}


class RuntimeWheelAssetError(ValueError):
    """A runtime wheel handoff is incomplete or differs from its reviewed pin."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path, message: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeWheelAssetError(message) from error
    if not isinstance(value, dict):
        raise RuntimeWheelAssetError(message)
    return value


def _regular_file(path: Path, message: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise RuntimeWheelAssetError(message)


def _source_rows(
    source_manifest: Path, version: str
) -> tuple[dict[str, dict[str, Any]], str, int, str]:
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise RuntimeWheelAssetError("application release version is invalid")
    data = _read_json(source_manifest, "runtime source manifest is invalid")
    if data.get("durable_release_tag") != f"v{version}":
        raise RuntimeWheelAssetError("runtime source manifest targets a different durable release")
    rows = data.get("artifact_sources")
    selected_count = data.get("selected_count")
    if (not isinstance(rows, list) or not isinstance(selected_count, int)
            or selected_count != len(rows)):
        raise RuntimeWheelAssetError("runtime source manifest has no artifact list")
    selected = [
        row for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("source"), dict)
        and row["source"].get("kind") == "actions_artifact"
    ]
    result: dict[str, dict[str, Any]] = {}
    for row in selected:
        name = row.get("name")
        filename = row.get("filename")
        source = row["source"]
        expected_url = (
            f"https://github.com/Capsize-Games/airunner/releases/download/"
            f"v{version}/{filename}"
        )
        if (
            not isinstance(name, str)
            or name not in _ACTION_DISTRIBUTIONS
            or not isinstance(filename, str)
            or Path(filename).name != filename
            or any(character in filename for character in ("/", "\\", ":", "\0"))
            or not filename.endswith(".whl")
            or not isinstance(row.get("version"), str)
            or not isinstance(row.get("sha256"), str)
            or not _HEX_RE.fullmatch(row["sha256"])
            or not isinstance(row.get("size_bytes"), int)
            or isinstance(row.get("size_bytes"), bool)
            or row["size_bytes"] <= 0
            or row["size_bytes"] > 2_147_483_648
            or source.get("durable_release_url") != expected_url
            or source.get("repo") != "Capsize-Games/airunner"
            or not isinstance(source.get("artifact_id"), int)
            or isinstance(source.get("artifact_id"), bool)
            or source["artifact_id"] <= 0
            or not isinstance(source.get("run_id"), int)
            or isinstance(source.get("run_id"), bool)
            or source["run_id"] <= 0
            or not isinstance(source.get("artifact_name"), str)
            or not source["artifact_name"]
            or not isinstance(source.get("source_revision"), str)
            or not _SHA_RE.fullmatch(source["source_revision"])
            or not isinstance(source.get("archive_sha256"), str)
            or not _HEX_RE.fullmatch(source["archive_sha256"])
            or not isinstance(source.get("max_archive_bytes"), int)
            or isinstance(source.get("max_archive_bytes"), bool)
            or source["max_archive_bytes"] <= 0
        ):
            raise RuntimeWheelAssetError("Actions wheel source row is incomplete or malformed")
        if name in result or filename in {item["filename"] for item in result.values()}:
            raise RuntimeWheelAssetError("runtime source manifest repeats an Actions wheel")
        result[name] = row
    if set(result) != _ACTION_DISTRIBUTIONS:
        raise RuntimeWheelAssetError("runtime source manifest does not pin the complete Actions wheel set")
    lock_sha256 = data.get("selected_lock_sha256")
    if not isinstance(lock_sha256, str) or not _HEX_RE.fullmatch(lock_sha256):
        raise RuntimeWheelAssetError("runtime source manifest lock digest is invalid")
    return result, _sha256_file(source_manifest), selected_count, lock_sha256


def _receipt_matches(
    receipt: dict[str, Any], rows: dict[str, dict[str, Any]], *,
    source_manifest_sha256: str, lock_sha256: str, selected_count: int,
) -> None:
    if (
        receipt.get("schema_version") != 1
        or receipt.get("status") != "verified wheel inputs; not installed or imported"
        or receipt.get("manifest_sha256") != source_manifest_sha256
        or receipt.get("selected_lock_sha256") != lock_sha256
        or receipt.get("requirements_sha256") != lock_sha256
        or receipt.get("selected_count") != selected_count
    ):
        raise RuntimeWheelAssetError("staging receipt is not bound to the selected source manifest and lock")
    wheel_entries = receipt.get("wheels")
    route_entries = receipt.get("source_routes")
    if not isinstance(wheel_entries, list) or not isinstance(route_entries, list):
        raise RuntimeWheelAssetError("staging receipt does not include wheel routes")
    if len(wheel_entries) != selected_count or len(route_entries) != selected_count:
        raise RuntimeWheelAssetError("staging receipt does not cover the full selected runtime graph")
    wheel_by_name = {item.get("filename"): item for item in wheel_entries if isinstance(item, dict)}
    route_by_name = {item.get("filename"): item for item in route_entries if isinstance(item, dict)}
    if len(wheel_by_name) != len(wheel_entries) or len(route_by_name) != len(route_entries):
        raise RuntimeWheelAssetError("staging receipt repeats or malforms wheel entries")
    for row in rows.values():
        filename = row["filename"]
        wheel = wheel_by_name.get(filename)
        route = route_by_name.get(filename)
        source = row["source"]
        expected_origin = {
            key: source[key]
            for key in (
                "repo", "artifact_id", "run_id", "artifact_name", "source_revision",
                "archive_sha256", "max_archive_bytes",
            )
            if key in source
        }
        if (
            not isinstance(wheel, dict)
            or wheel.get("sha256") != row["sha256"]
            or wheel.get("size_bytes") != row["size_bytes"]
            or wheel.get("source_kind") not in {"actions_artifact", "durable_release"}
            or wheel.get("artifact_id") != source["artifact_id"]
            or not isinstance(route, dict)
            or route.get("durable_release_url") != source["durable_release_url"]
            or route.get("original_actions_source") != expected_origin
            or route.get("selected_route") != wheel.get("source_kind")
        ):
            raise RuntimeWheelAssetError("staging receipt does not preserve an exact Actions wheel provenance")


def _expected_manifest(
    rows: dict[str, dict[str, Any]], *, version: str, source_sha: str,
    source_manifest_sha256: str, lock_sha256: str, receipt_sha256: str,
) -> dict[str, Any]:
    wheels = []
    for name in sorted(rows):
        row = rows[name]
        source = row["source"]
        wheels.append({
            "name": name,
            "version": row["version"],
            "filename": row["filename"],
            "sha256": row["sha256"],
            "size_bytes": row["size_bytes"],
            "durable_release_url": source["durable_release_url"],
            "actions_source": {
                key: source[key]
                for key in (
                    "repo", "artifact_id", "run_id", "artifact_name", "source_revision",
                    "archive_sha256", "max_archive_bytes",
                )
            },
        })
    return {
        "schema_version": 1,
        "status": "verified release wheel assets; source Actions provenance retained",
        "application_version": version,
        "source_commit": source_sha,
        "source_manifest_sha256": source_manifest_sha256,
        "selected_lock_sha256": lock_sha256,
        "staging_receipt_sha256": receipt_sha256,
        "wheels": wheels,
    }


def verify_assets(
    asset_dir: Path, *, source_manifest: Path, selected_lock: Path,
    application_version: str, source_sha: str,
) -> dict[str, Any]:
    if asset_dir.is_symlink() or not asset_dir.is_dir():
        raise RuntimeWheelAssetError("runtime wheel asset directory is missing or unsafe")
    if not _SHA_RE.fullmatch(source_sha):
        raise RuntimeWheelAssetError("source commit is invalid")
    rows, source_manifest_sha256, selected_count, manifest_lock_sha256 = _source_rows(
        source_manifest, application_version
    )
    _regular_file(selected_lock, "selected runtime lock is not a regular file")
    lock_sha256 = _sha256_file(selected_lock)
    if lock_sha256 != manifest_lock_sha256:
        raise RuntimeWheelAssetError("selected runtime lock differs from the source manifest")
    receipt_path = asset_dir / STAGING_RECEIPT
    manifest_path = asset_dir / ASSET_MANIFEST
    _regular_file(receipt_path, "staging receipt is missing or unsafe")
    _regular_file(manifest_path, "runtime wheel asset manifest is missing or unsafe")
    receipt = _read_json(receipt_path, "staging receipt is invalid")
    _receipt_matches(
        receipt, rows,
        source_manifest_sha256=source_manifest_sha256,
        lock_sha256=lock_sha256,
        selected_count=selected_count,
    )
    receipt_sha256 = _sha256_file(receipt_path)
    expected_manifest = _expected_manifest(
        rows,
        version=application_version,
        source_sha=source_sha,
        source_manifest_sha256=source_manifest_sha256,
        lock_sha256=lock_sha256,
        receipt_sha256=receipt_sha256,
    )
    if _read_json(manifest_path, "runtime wheel asset manifest is invalid") != expected_manifest:
        raise RuntimeWheelAssetError("runtime wheel asset manifest differs from exact source provenance")
    expected_files = {
        ASSET_MANIFEST, STAGING_RECEIPT,
        *(row["filename"] for row in rows.values()),
    }
    actual_files = {path.name for path in asset_dir.iterdir()}
    if actual_files != expected_files:
        raise RuntimeWheelAssetError("runtime wheel asset directory has missing or unexpected files")
    for row in rows.values():
        wheel_path = asset_dir / row["filename"]
        _regular_file(wheel_path, "runtime wheel asset is missing or unsafe")
        if wheel_path.stat().st_size != row["size_bytes"] or _sha256_file(wheel_path) != row["sha256"]:
            raise RuntimeWheelAssetError("runtime wheel asset size or digest differs from its reviewed pin")
    return expected_manifest


def create_assets(
    wheelhouse: Path, output_dir: Path, *, source_manifest: Path,
    selected_lock: Path, application_version: str, source_sha: str,
) -> dict[str, Any]:
    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        raise RuntimeWheelAssetError("staged runtime wheelhouse is missing or unsafe")
    if output_dir.exists() or output_dir.is_symlink():
        raise RuntimeWheelAssetError("runtime wheel asset output already exists")
    rows, source_manifest_sha256, selected_count, manifest_lock_sha256 = _source_rows(
        source_manifest, application_version
    )
    _regular_file(selected_lock, "selected runtime lock is not a regular file")
    lock_sha256 = _sha256_file(selected_lock)
    if lock_sha256 != manifest_lock_sha256:
        raise RuntimeWheelAssetError("selected runtime lock differs from the source manifest")
    receipt_path = wheelhouse / STAGING_RECEIPT
    _regular_file(receipt_path, "runtime stager receipt is missing or unsafe")
    receipt = _read_json(receipt_path, "runtime stager receipt is invalid")
    _receipt_matches(
        receipt, rows,
        source_manifest_sha256=source_manifest_sha256,
        lock_sha256=lock_sha256,
        selected_count=selected_count,
    )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".runtime-wheel-assets-", dir=output_dir.parent))
    try:
        for row in rows.values():
            source = wheelhouse / row["filename"]
            _regular_file(source, "staged runtime wheel is missing or unsafe")
            if source.stat().st_size != row["size_bytes"] or _sha256_file(source) != row["sha256"]:
                raise RuntimeWheelAssetError("staged runtime wheel differs from its exact reviewed pin")
            shutil.copyfile(source, temporary / row["filename"])
        shutil.copyfile(receipt_path, temporary / STAGING_RECEIPT)
        receipt_sha256 = _sha256_file(temporary / STAGING_RECEIPT)
        asset_manifest = _expected_manifest(
            rows,
            version=application_version,
            source_sha=source_sha,
            source_manifest_sha256=source_manifest_sha256,
            lock_sha256=lock_sha256,
            receipt_sha256=receipt_sha256,
        )
        (temporary / ASSET_MANIFEST).write_text(
            json.dumps(asset_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.rename(temporary, output_dir)
        temporary = Path()
    finally:
        if temporary != Path():
            shutil.rmtree(temporary, ignore_errors=True)
    return verify_assets(
        output_dir,
        source_manifest=source_manifest,
        selected_lock=selected_lock,
        application_version=application_version,
        source_sha=source_sha,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("create", "verify"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--source-manifest", type=Path, default=SOURCE_MANIFEST)
        sub.add_argument("--selected-lock", type=Path, default=SOURCE_LOCK)
        sub.add_argument("--application-version", required=True)
        sub.add_argument("--source-sha", required=True)
        if command == "create":
            sub.add_argument("--wheelhouse", type=Path, required=True)
            sub.add_argument("--output-dir", type=Path, required=True)
        else:
            sub.add_argument("--asset-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "create":
            result = create_assets(
                args.wheelhouse,
                args.output_dir,
                source_manifest=args.source_manifest,
                selected_lock=args.selected_lock,
                application_version=args.application_version,
                source_sha=args.source_sha,
            )
        else:
            result = verify_assets(
                args.asset_dir,
                source_manifest=args.source_manifest,
                selected_lock=args.selected_lock,
                application_version=args.application_version,
                source_sha=args.source_sha,
            )
    except (OSError, RuntimeWheelAssetError) as error:
        print(f"Runtime wheel asset validation failed: {error}", file=sys.stderr)
        return 1
    print(f"Verified {len(result['wheels'])} durable runtime wheel assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
