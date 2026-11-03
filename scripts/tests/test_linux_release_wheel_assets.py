"""Exact provenance checks for durable Linux runtime wheel release assets."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import linux_release_wheel_assets as assets


_DISTRIBUTIONS = (
    "llama-cpp-python", "nvidia-nvshmem-cu12", "torchaudio",
    "torchvision", "triton",
)


def _fixture(tmp_path: Path):
    version = "6.1.9"
    source_sha = "a" * 40
    package = tmp_path / "package"
    package.mkdir()
    source_rows = []
    lock_lines = []
    payloads = {}
    for index, name in enumerate(_DISTRIBUTIONS, 1):
        package_version = "1.0.0"
        filename = f"{name.replace('-', '_')}-{package_version}-py3-none-any.whl"
        payload = f"wheel-bytes:{name}".encode()
        digest = hashlib.sha256(payload).hexdigest()
        source = {
            "kind": "actions_artifact",
            "repo": "Capsize-Games/airunner",
            "artifact_id": 100 + index,
            "run_id": 200 + index,
            "artifact_name": f"runtime-wheel-artifact-{index}",
            "source_revision": "b" * 40,
            "archive_sha256": "c" * 64,
            "max_archive_bytes": 4096,
            "durable_release_url": (
                f"https://github.com/Capsize-Games/airunner/releases/download/"
                f"v{version}/{filename}"
            ),
        }
        source_rows.append({
            "name": name,
            "version": package_version,
            "filename": filename,
            "sha256": digest,
            "size_bytes": len(payload),
            "source": source,
        })
        lock_lines.append(f"{name}=={package_version} --hash=sha256:{digest}")
        payloads[filename] = payload
    lock_text = "\n".join(lock_lines) + "\n"
    lock = package / "constraints.txt"
    lock.write_text(lock_text, encoding="utf-8")
    manifest = package / "sources.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "durable_release_tag": f"v{version}",
        "selected_count": len(source_rows),
        "selected_lock_sha256": hashlib.sha256(lock_text.encode()).hexdigest(),
        "artifact_sources": source_rows,
    }, indent=2) + "\n", encoding="utf-8")

    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    for filename, payload in payloads.items():
        (wheelhouse / filename).write_bytes(payload)
    manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    lock_sha = hashlib.sha256(lock.read_bytes()).hexdigest()
    receipt = {
        "schema_version": 1,
        "status": "verified wheel inputs; not installed or imported",
        "manifest_sha256": manifest_sha,
        "selected_lock_sha256": lock_sha,
        "requirements_sha256": lock_sha,
        "selected_count": len(source_rows),
        "source_routes": [
            {
                "filename": row["filename"],
                "selected_route": "actions_artifact",
                "durable_release_url": row["source"]["durable_release_url"],
                "original_actions_source": {
                    key: row["source"][key]
                    for key in (
                        "repo", "artifact_id", "run_id", "artifact_name",
                        "source_revision", "archive_sha256", "max_archive_bytes",
                    )
                },
            }
            for row in source_rows
        ],
        "wheels": [
            {
                "filename": row["filename"],
                "sha256": row["sha256"],
                "size_bytes": row["size_bytes"],
                "source_kind": "actions_artifact",
                "artifact_id": row["source"]["artifact_id"],
            }
            for row in source_rows
        ],
    }
    (wheelhouse / assets.STAGING_RECEIPT).write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return version, source_sha, manifest, lock, wheelhouse, payloads, source_rows


def test_create_and_verify_exact_runtime_wheel_handoff(tmp_path: Path) -> None:
    version, source_sha, manifest, lock, wheelhouse, payloads, _rows = _fixture(tmp_path)
    output = tmp_path / "runtime-wheels"

    result = assets.create_assets(
        wheelhouse,
        output,
        source_manifest=manifest,
        selected_lock=lock,
        application_version=version,
        source_sha=source_sha,
    )
    verified = assets.verify_assets(
        output,
        source_manifest=manifest,
        selected_lock=lock,
        application_version=version,
        source_sha=source_sha,
    )

    assert len(result["wheels"]) == 5
    assert verified == result
    for filename, payload in payloads.items():
        assert (output / filename).read_bytes() == payload
    assert (output / assets.STAGING_RECEIPT).is_file()
    assert (output / assets.ASSET_MANIFEST).is_file()


def test_asset_bytes_or_manifest_provenance_mismatch_fails(tmp_path: Path) -> None:
    version, source_sha, manifest, lock, wheelhouse, _payloads, rows = _fixture(tmp_path)
    output = tmp_path / "runtime-wheels"
    assets.create_assets(
        wheelhouse,
        output,
        source_manifest=manifest,
        selected_lock=lock,
        application_version=version,
        source_sha=source_sha,
    )
    wheel_path = output / rows[0]["filename"]
    wheel_path.write_bytes(b"tampered")

    with pytest.raises(assets.RuntimeWheelAssetError, match="digest"):
        assets.verify_assets(
            output,
            source_manifest=manifest,
            selected_lock=lock,
            application_version=version,
            source_sha=source_sha,
        )


def test_asset_manifest_cannot_retarget_release_or_action_source(tmp_path: Path) -> None:
    version, source_sha, manifest, lock, wheelhouse, _payloads, _rows = _fixture(tmp_path)
    output = tmp_path / "runtime-wheels"
    assets.create_assets(
        wheelhouse,
        output,
        source_manifest=manifest,
        selected_lock=lock,
        application_version=version,
        source_sha=source_sha,
    )
    asset_manifest_path = output / assets.ASSET_MANIFEST
    asset_manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
    asset_manifest["wheels"][0]["actions_source"]["artifact_id"] += 1
    asset_manifest_path.write_text(json.dumps(asset_manifest), encoding="utf-8")

    with pytest.raises(assets.RuntimeWheelAssetError, match="manifest differs"):
        assets.verify_assets(
            output,
            source_manifest=manifest,
            selected_lock=lock,
            application_version=version,
            source_sha=source_sha,
        )
