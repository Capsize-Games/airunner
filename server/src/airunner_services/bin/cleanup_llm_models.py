#!/usr/bin/env python3
"""Manage AIRunner LLM model storage outside the GUI package."""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_MODELS_DIR = Path.home() / ".local/share/airunner/text/models/llm"


@dataclass(frozen=True)
class ModelInfo:
    """Describe one discovered model directory."""

    path: Path
    name: str
    size_bytes: int
    is_quantized: bool
    quant_type: str
    has_safetensors: bool
    has_gguf: bool

    @property
    def size_gb(self) -> float:
        """Return the model size in GiB."""
        return self.size_bytes / (1024**3)


def _iter_model_dirs(models_root: Path) -> Iterable[Path]:
    """Yield directories that look like stored models."""
    for model_dir in models_root.rglob("*"):
        if model_dir.is_dir() and not model_dir.name.startswith("."):
            if _looks_like_model_dir(model_dir):
                yield model_dir


def _looks_like_model_dir(model_dir: Path) -> bool:
    """Return True when the directory contains model artifacts."""
    if any(model_dir.glob("*.safetensors")):
        return True
    if any(model_dir.glob("*.gguf")):
        return True
    return (model_dir / "config.json").exists()


def _get_dir_size(path: Path) -> int:
    """Return the total directory size in bytes."""
    total = 0
    try:
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total += file_path.stat().st_size
    except (FileNotFoundError, PermissionError):
        return total
    return total


def _get_quant_type(name: str, has_gguf: bool) -> tuple[bool, str]:
    """Infer whether a model is quantized and how."""
    if has_gguf:
        return True, "gguf"
    if "-4bit" in name:
        return True, "4bit"
    if "-8bit" in name:
        return True, "8bit"
    return False, "original"


def analyze_model_dir(model_dir: Path) -> ModelInfo:
    """Return metadata about one model directory."""
    has_safetensors = any(model_dir.glob("*.safetensors"))
    has_gguf = any(model_dir.glob("*.gguf"))
    is_quantized, quant_type = _get_quant_type(model_dir.name, has_gguf)
    return ModelInfo(
        path=model_dir,
        name=model_dir.name,
        size_bytes=_get_dir_size(model_dir),
        is_quantized=is_quantized,
        quant_type=quant_type,
        has_safetensors=has_safetensors,
        has_gguf=has_gguf,
    )


def _collect_models(models_root: Path) -> dict[Path, ModelInfo]:
    """Collect model metadata keyed by model directory path."""
    return {
        model_dir: analyze_model_dir(model_dir)
        for model_dir in _iter_model_dirs(models_root)
    }


def find_model_pairs(models_root: Path) -> list[tuple[ModelInfo, ModelInfo]]:
    """Find original models that already have a quantized sibling."""
    pairs: list[tuple[ModelInfo, ModelInfo]] = []
    all_models = _collect_models(models_root)
    for path, model in all_models.items():
        if not model.is_quantized:
            continue
        base_name = model.name.replace("-4bit", "").replace("-8bit", "")
        original_path = path.parent / base_name
        if original_path in all_models:
            pairs.append((all_models[original_path], model))
    return pairs


def find_redundant_originals(models_root: Path) -> list[ModelInfo]:
    """Return original models that can be reclaimed."""
    return [original for original, _quantized in find_model_pairs(models_root)]


def _print_storage_breakdown(models: list[ModelInfo]) -> None:
    """Print aggregate size statistics by model type."""
    originals = [model for model in models if not model.is_quantized]
    quantized_4bit = [model for model in models if model.quant_type == "4bit"]
    quantized_8bit = [model for model in models if model.quant_type == "8bit"]
    gguf_models = [model for model in models if model.quant_type == "gguf"]
    total_size = sum(model.size_bytes for model in models)
    print("Storage by type:")
    print(
        "  Original (FP16/FP32): "
        f"{len(originals)} models, {sum(m.size_gb for m in originals):.1f} GB"
    )
    print(
        "  4-bit quantized:      "
        f"{len(quantized_4bit)} models, "
        f"{sum(m.size_gb for m in quantized_4bit):.1f} GB"
    )
    print(
        "  8-bit quantized:      "
        f"{len(quantized_8bit)} models, "
        f"{sum(m.size_gb for m in quantized_8bit):.1f} GB"
    )
    print(
        "  GGUF:                 "
        f"{len(gguf_models)} models, {sum(m.size_gb for m in gguf_models):.1f} GB"
    )
    print(f"  {'-' * 40}")
    print(
        "  TOTAL:                "
        f"{len(models)} models, {total_size / (1024**3):.1f} GB"
    )


def _print_redundant_pairs(pairs: list[tuple[ModelInfo, ModelInfo]]) -> None:
    """Print removable original models and potential reclaimed space."""
    if not pairs:
        return
    redundant_size = sum(original.size_bytes for original, _ in pairs)
    print("\nRedundant originals (have quantized version):")
    for original, quantized in pairs:
        print(
            f"  {original.name} ({original.size_gb:.1f} GB)"
            f" -> {quantized.name} ({quantized.size_gb:.1f} GB)"
        )
    print(f"\nPotential savings: {redundant_size / (1024**3):.1f} GB")
    print("Run with --clean-originals to remove redundant originals")


def print_stats(models_root: Path) -> None:
    """Print storage statistics for the given model directory."""
    print(f"\n{'=' * 60}")
    print(f"LLM Model Storage Analysis: {models_root}")
    print(f"{'=' * 60}\n")
    all_models = list(_collect_models(models_root).values())
    if not all_models:
        print("No models found.")
        return
    _print_storage_breakdown(all_models)
    _print_redundant_pairs(find_model_pairs(models_root))
    print()


def clean_originals(models_root: Path, dry_run: bool = True) -> None:
    """Remove original models that already have quantized variants."""
    redundant = find_redundant_originals(models_root)
    if not redundant:
        print("No redundant originals found.")
        return
    total_savings = sum(model.size_bytes for model in redundant)
    print(f"\n{'=' * 60}")
    title = "Cleaning Redundant Original Models"
    if dry_run:
        title = f"DRY RUN - {title}"
    print(title)
    print(f"{'=' * 60}\n")
    for model in redundant:
        _print_cleanup_action(model, dry_run)
        if not dry_run:
            _remove_model_dir(model.path)
        print()
    print(f"{'-' * 60}")
    action = "that would be " if dry_run else ""
    print(f"Total space {action}freed: {total_savings / (1024**3):.1f} GB")
    if dry_run:
        print("\nThis was a dry run. Run without --dry-run to delete.")


def _print_cleanup_action(model: ModelInfo, dry_run: bool) -> None:
    """Print one cleanup action."""
    action = "[DRY RUN] Would remove" if dry_run else "Removing"
    print(f"{action}: {model.name}")
    print(f"          Path: {model.path}")
    print(f"          Size: {model.size_gb:.1f} GB")


def _remove_model_dir(model_path: Path) -> None:
    """Delete one model directory and report failures."""
    try:
        shutil.rmtree(model_path)
        print("          Removed successfully")
    except Exception as exc:  # pragma: no cover - surface filesystem issues
        print(f"          Error: {exc}")


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(description="Cleanup LLM model storage")
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=DEFAULT_MODELS_DIR,
        help="Path to the LLM models directory.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show storage statistics.",
    )
    parser.add_argument(
        "--clean-originals",
        action="store_true",
        help="Remove original models that have quantized versions.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without deleting anything.",
    )
    return parser


def main() -> int:
    """Run the CLI."""
    args = _build_parser().parse_args()
    if not args.models_dir.exists():
        print(f"Error: Models directory not found: {args.models_dir}")
        return 1
    if args.clean_originals:
        clean_originals(args.models_dir, dry_run=args.dry_run)
        return 0
    print_stats(args.models_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
