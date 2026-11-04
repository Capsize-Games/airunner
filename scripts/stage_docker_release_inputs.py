"""Prepare the reviewed, offline Docker build contexts outside the checkout."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGER_PATH = ROOT / "scripts/stage_linux_release_artifacts.py"
INPUTS = {
    "runtime": (
        "package/linux-release-v4-artifact-sources.json",
        "package/constraints-linux-nvidia-cu129-linux-release.txt",
    ),
    "builder": (
        "package/linux-builder-tools-artifact-sources.json",
        "package/constraints-linux-builder-tools.txt",
    ),
    "bootstrap": (
        "package/linux-docker-bootstrap-artifact-sources.json",
        "package/constraints-linux-docker-bootstrap.txt",
    ),
}
RELEASE_SOURCE_FILES = (
    "packaging/linux/services-bundle-spec.toml",
    "scripts/dependency_notices.py",
    "scripts/source_notice_supplements.py",
    "scripts/vendor_notice_supplements.py",
    "scripts/collect_runtime_dependency_notices.py",
)


class PreparationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_stager():
    spec = importlib.util.spec_from_file_location("linux_release_stager", STAGER_PATH)
    if spec is None or spec.loader is None:
        raise PreparationError("could not load the reviewed release input stager")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _validate_output(output: Path) -> tuple[Path, bool]:
    if not output.is_absolute():
        raise PreparationError("--output-dir must be an absolute path")
    if output.is_symlink():
        raise PreparationError("--output-dir must not be a symlink")
    parent = output.parent.resolve(strict=True)
    target = parent / output.name
    if target == ROOT or ROOT in target.parents or target == Path("/"):
        raise PreparationError("--output-dir must be outside the repository")
    existed = output.exists()
    if existed and (not output.is_dir() or any(output.iterdir())):
        raise PreparationError("--output-dir must not exist or must be an empty directory")
    return target, existed


def _copy_file(relative: str, destination: Path, inventory: dict[str, str]) -> None:
    source = ROOT / relative
    if source.is_symlink() or not source.is_file():
        raise PreparationError(f"allowlisted release source is missing or unsafe: {relative}")
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    inventory[relative] = _sha256(target)


def _copy_release_source(destination: Path) -> dict[str, str]:
    source_root = destination / "release-source"
    inventory: dict[str, str] = {}
    for relative in RELEASE_SOURCE_FILES:
        _copy_file(relative, source_root, inventory)
    lock_relative = INPUTS["runtime"][1]
    _copy_file(lock_relative, source_root, inventory)

    licenses_source = ROOT / "packaging/licenses"
    licenses_target = source_root / "packaging/licenses"
    if licenses_source.is_symlink() or not licenses_source.is_dir():
        raise PreparationError("reviewed license collection is missing or unsafe")
    for source in sorted(licenses_source.rglob("*")):
        if source.is_symlink():
            raise PreparationError("reviewed license collection contains a symlink")
        if source.is_file():
            relative = source.relative_to(ROOT).as_posix()
            target = licenses_target / source.relative_to(licenses_source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            inventory[relative] = _sha256(target)
    return inventory


def _stage_existing_wheelhouse(name: str, source_dir: Path, destination: Path,
                              stager_module) -> dict[str, str]:
    manifest_relative, lock_relative = INPUTS[name]
    manifest_path = ROOT / manifest_relative
    lock_path = ROOT / lock_relative
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stager_module.validate_lock(manifest, lock_path)
    source_receipt_path = source_dir / "staging-receipt.json"
    requirements_path = source_dir / "requirements.txt"
    if (source_dir.is_symlink() or not source_dir.is_dir()
            or source_receipt_path.is_symlink() or requirements_path.is_symlink()
            or not source_receipt_path.is_file() or not requirements_path.is_file()):
        raise PreparationError(f"cached {name} wheelhouse is missing or unsafe")
    source_receipt = json.loads(source_receipt_path.read_text(encoding="utf-8"))
    if (source_receipt.get("manifest_sha256") != _sha256(manifest_path)
            or source_receipt.get("selected_lock_sha256") != _sha256(lock_path)
            or source_receipt.get("requirements_sha256") != _sha256(requirements_path)
            or source_receipt.get("selected_count") != manifest.get("selected_count")):
        raise PreparationError(f"cached {name} wheelhouse receipt does not match current reviewed inputs")
    expected = {
        row["filename"]: {key: row[key] for key in ("filename", "sha256", "size_bytes")}
        for row in manifest["artifact_sources"]
    }
    received = {
        row.get("filename"): {key: row.get(key) for key in ("filename", "sha256", "size_bytes")}
        for row in source_receipt.get("wheels", [])
    }
    if len(source_receipt.get("wheels", [])) != len(expected) or received != expected:
        raise PreparationError(f"cached {name} wheelhouse receipt has a different selected artifact set")
    expected_files = set(expected) | {"requirements.txt", "staging-receipt.json"}
    if {item.name for item in source_dir.iterdir()} != expected_files:
        raise PreparationError(f"cached {name} wheelhouse contains unexpected files")
    destination.mkdir(parents=True)
    copied = {}
    for filename, spec in sorted(expected.items()):
        source = source_dir / filename
        target = destination / filename
        stager_module.copy_checked(source, target, spec)
        copied[filename] = spec["sha256"]
    shutil.copyfile(requirements_path, destination / "requirements.txt")
    shutil.copyfile(source_receipt_path, destination / "staging-receipt.json")
    shutil.copyfile(manifest_path, destination / "artifact-sources.json")
    shutil.copyfile(lock_path, destination / "selected-lock.txt")
    return {
        "source_receipt_sha256": _sha256(source_receipt_path),
        "selected_count": len(expected),
        "wheel_sha256": copied,
    }


def _write_preparation_receipt(temp: Path, wheelhouse_proofs: dict[str, dict],
                               source_hashes: dict[str, str]) -> dict:
    receipt = {
        "schema_version": 1,
        "status": "reviewed offline Docker build inputs staged; not installed or imported",
        "inputs": {
            name: {
                "manifest": manifest,
                "manifest_sha256": _sha256(ROOT / manifest),
                "selected_lock": lockfile,
                "selected_lock_sha256": _sha256(ROOT / lockfile),
                "cached_wheelhouse_revalidation": wheelhouse_proofs.get(name),
            }
            for name, (manifest, lockfile) in INPUTS.items()
        },
        "release_source_sha256": dict(sorted(source_hashes.items())),
    }
    (temp / "preparation-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def prepare(output_dir: Path, stage_fn=None) -> dict:
    target, existed = _validate_output(output_dir)
    stage_fn = stage_fn or _load_stager().stage
    temp = Path(tempfile.mkdtemp(prefix=f".{target.name}.prepared-", dir=target.parent))
    try:
        for name, (manifest, lockfile) in INPUTS.items():
            stage_fn(ROOT / manifest, ROOT / lockfile, temp / name)
            shutil.copyfile(ROOT / manifest, temp / name / "artifact-sources.json")
            shutil.copyfile(ROOT / lockfile, temp / name / "selected-lock.txt")
        source_hashes = _copy_release_source(temp)
        receipt = _write_preparation_receipt(temp, {}, source_hashes)
        if existed:
            output_dir.rmdir()
        os.replace(temp, target)
        return receipt
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise


def prepare_from_wheelhouses(output_dir: Path, wheelhouses: dict[str, Path]) -> dict:
    if set(wheelhouses) != set(INPUTS):
        raise PreparationError("cached staging requires runtime, builder, and bootstrap wheelhouses")
    target, existed = _validate_output(output_dir)
    stager_module = _load_stager()
    temp = Path(tempfile.mkdtemp(prefix=f".{target.name}.prepared-", dir=target.parent))
    try:
        proofs = {
            name: _stage_existing_wheelhouse(name, wheelhouses[name], temp / name, stager_module)
            for name in INPUTS
        }
        source_hashes = _copy_release_source(temp)
        receipt = _write_preparation_receipt(temp, proofs, source_hashes)
        if existed:
            target.rmdir()
        os.replace(temp, target)
        return receipt
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runtime-wheelhouse", type=Path)
    parser.add_argument("--builder-wheelhouse", type=Path)
    parser.add_argument("--bootstrap-wheelhouse", type=Path)
    args = parser.parse_args()
    try:
        cached = (args.runtime_wheelhouse, args.builder_wheelhouse, args.bootstrap_wheelhouse)
        if any(cached) and not all(cached):
            raise PreparationError("all three cached wheelhouse paths must be supplied together")
        if all(cached):
            prepare_from_wheelhouses(args.output_dir, {
                "runtime": args.runtime_wheelhouse,
                "builder": args.builder_wheelhouse,
                "bootstrap": args.bootstrap_wheelhouse,
            })
        else:
            prepare(args.output_dir)
    except Exception as error:
        print(f"Docker input staging failed: {error}", file=sys.stderr)
        return 1
    print(f"Prepared reviewed Docker inputs at {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
