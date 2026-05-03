#!/usr/bin/env python3
"""Audit Z-Image bundles for each AIRunner load mode."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import Any

from airunner.components.art.managers.zimage.zimage_bundle_requirements import (
    ARCHIVE_DIR_NAME,
    ZIMAGE_LOAD_MODES,
    detect_fp8_checkpoint,
    find_checkpoint_candidates,
    get_active_zimage_load_mode,
    get_bundle_dir,
    list_archived_files,
    get_missing_files_for_mode,
    get_optional_used_files_for_mode,
    get_required_files_for_mode,
    get_unused_files_for_mode,
    list_bundle_files,
    looks_like_single_file,
)


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the Z-Image bundle report."""
    parser = argparse.ArgumentParser(
        description="Report the files AIRunner uses for each Z-Image load mode."
    )
    parser.add_argument("model_path", type=Path, help="Z-Image checkpoint or bundle directory")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print the report as JSON",
    )
    parser.add_argument(
        "--mode",
        choices=("active", *ZIMAGE_LOAD_MODES),
        default="active",
        help="Mode to archive when using --archive-unused (default: active)",
    )
    parser.add_argument(
        "--archive-unused",
        action="store_true",
        help="Move files unused by the selected mode into the bundle archive folder",
    )
    return parser


def _candidate_checkpoints(bundle_dir: Path) -> list[Path]:
    """Return top-level checkpoint candidates inside a bundle directory."""
    return find_checkpoint_candidates(bundle_dir)


def _choose_source_for_mode(model_path: Path, mode: str) -> Path | None:
    """Return the most relevant source path for a given load mode."""
    bundle_dir = get_bundle_dir(model_path)
    checkpoints = _candidate_checkpoints(bundle_dir)
    if mode == "pretrained_directory":
        return bundle_dir
    if mode == "native_fp8_single_file":
        return next((path for path in checkpoints if detect_fp8_checkpoint(path)), None)
    return next((path for path in checkpoints if not detect_fp8_checkpoint(path)), None)


def _build_mode_report(model_path: Path, mode: str) -> dict[str, Any]:
    """Build a report for one AIRunner Z-Image load mode."""
    source = _choose_source_for_mode(model_path, mode)
    if source is None:
        return {
            "mode": mode,
            "available": False,
            "reason": "No compatible source found in bundle",
        }
    required = get_required_files_for_mode(source, mode)
    optional = get_optional_used_files_for_mode(source, mode)
    missing = get_missing_files_for_mode(source, mode)
    unused = get_unused_files_for_mode(source, mode)
    used = _dedupe(required + optional)
    bundle_dir = get_bundle_dir(source)
    return {
        "mode": mode,
        "available": True,
        "source": str(source),
        "bundle_dir": str(bundle_dir),
        "required_files": required,
        "optional_files_used_when_present": optional,
        "missing_files": missing,
        "used_files": used,
        "unused_files": unused,
        "used_size_gib": _size_gib(bundle_dir, used),
        "unused_size_gib": _size_gib(bundle_dir, unused),
    }


def _build_report(model_path: Path) -> dict[str, Any]:
    """Build the complete Z-Image bundle report."""
    source = model_path.expanduser().resolve()
    bundle_dir = get_bundle_dir(source)
    checkpoints = _candidate_checkpoints(bundle_dir)
    active_mode = get_active_zimage_load_mode(source)
    return {
        "input_path": str(source),
        "bundle_dir": str(bundle_dir),
        "bundle_files": list_bundle_files(source),
        "archived_files": list_archived_files(source),
        "bundle_size_gib": _size_gib(bundle_dir, list_bundle_files(source)),
        "archived_size_gib": _size_gib(bundle_dir, list_archived_files(source)),
        "active_mode": active_mode,
        "checkpoints": [_checkpoint_entry(path) for path in checkpoints],
        "mode_reports": [_build_mode_report(source, mode) for mode in ZIMAGE_LOAD_MODES],
    }


def _archive_unused_files(model_path: Path, mode: str) -> dict[str, Any]:
    """Move files unused by the selected mode into an archive folder."""
    source = model_path.expanduser().resolve()
    active_mode = get_active_zimage_load_mode(source) if mode == "active" else mode
    unused_files = get_unused_files_for_mode(source, active_mode)
    bundle_dir = get_bundle_dir(source)
    archive_root = bundle_dir / ARCHIVE_DIR_NAME
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = archive_root / active_mode / timestamp
    moved_files = []

    for relative_name in unused_files:
        src = bundle_dir / relative_name
        if not src.exists():
            continue
        dest = archive_dir / relative_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        moved_files.append(relative_name)

    manifest = {
        "input_path": str(source),
        "bundle_dir": str(bundle_dir),
        "mode": active_mode,
        "archive_dir": str(archive_dir),
        "moved_files": moved_files,
        "timestamp": timestamp,
    }
    if moved_files:
        manifest_path = archive_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        manifest["manifest_path"] = str(manifest_path)
    return manifest


def _checkpoint_entry(checkpoint: Path) -> dict[str, Any]:
    """Return a small summary for a checkpoint candidate."""
    return {
        "path": str(checkpoint),
        "fp8": detect_fp8_checkpoint(checkpoint),
        "size_gib": round(checkpoint.stat().st_size / (1024 ** 3), 2),
    }


def _size_gib(bundle_dir: Path, files: list[str]) -> float:
    """Return the summed size of files that exist in the bundle directory."""
    total = sum((bundle_dir / file_name).stat().st_size for file_name in files if (bundle_dir / file_name).exists())
    return round(total / (1024 ** 3), 2)


def _dedupe(items: list[str]) -> list[str]:
    """Return a list with duplicates removed while preserving order."""
    return list(dict.fromkeys(items))


def _print_text_report(report: dict[str, Any]) -> None:
    """Print the report in a human-readable format."""
    print(f"Input path: {report['input_path']}")
    print(f"Bundle dir: {report['bundle_dir']}")
    print(f"Bundle size: {report['bundle_size_gib']:.2f} GiB")
    print(f"Archived size: {report['archived_size_gib']:.2f} GiB")
    print(f"Active mode: {report['active_mode']}")
    print("Checkpoints:")
    for checkpoint in report["checkpoints"]:
        print(f"  - {checkpoint['path']} | fp8={checkpoint['fp8']} | {checkpoint['size_gib']:.2f} GiB")
    print("Modes:")
    for mode_report in report["mode_reports"]:
        _print_mode_report(mode_report)


def _print_archive_result(result: dict[str, Any]) -> None:
    """Print a compact archive summary."""
    print(f"Archive mode: {result['mode']}")
    print(f"Archive dir: {result['archive_dir']}")
    print(f"Moved files: {len(result['moved_files'])}")
    manifest_path = result.get("manifest_path")
    if manifest_path:
        print(f"Manifest: {manifest_path}")
    for item in result["moved_files"]:
        print(f"  - {item}")


def _print_mode_report(mode_report: dict[str, Any]) -> None:
    """Print one mode report in a readable block."""
    print(f"  {mode_report['mode']}:")
    if not mode_report["available"]:
        print(f"    unavailable: {mode_report['reason']}")
        return
    print(f"    source: {mode_report['source']}")
    print(f"    used size: {mode_report['used_size_gib']:.2f} GiB")
    print(f"    unused size: {mode_report['unused_size_gib']:.2f} GiB")
    _print_list("required", mode_report["required_files"])
    _print_list("optional when present", mode_report["optional_files_used_when_present"])
    _print_list("missing", mode_report["missing_files"])
    _print_list("unused", mode_report["unused_files"])


def _print_list(label: str, items: list[str]) -> None:
    """Print a labeled list with a compact empty-state message."""
    if not items:
        print(f"    {label}: none")
        return
    print(f"    {label}:")
    for item in items:
        print(f"      - {item}")


def main() -> int:
    """Run the Z-Image bundle report CLI."""
    args = _build_parser().parse_args()
    if args.archive_unused:
        archive_result = _archive_unused_files(args.model_path, args.mode)
        if args.as_json:
            print(json.dumps(archive_result, indent=2, sort_keys=True))
            return 0
        _print_archive_result(archive_result)
        return 0
    report = _build_report(args.model_path)
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    _print_text_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())