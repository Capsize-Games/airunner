#!/usr/bin/env python3
"""Cleanup script for LLM model storage.

This script helps manage LLM model storage by:
1. Identifying original models that have quantized versions
2. Removing original safetensors to free space
3. Migrating to GGUF format (smaller, faster)

Usage:
    # Dry run - see what would be cleaned
    python cleanup_llm_models.py --dry-run

    # Clean up duplicate originals (keep quantized)
    python cleanup_llm_models.py --clean-originals

    # Show storage usage
    python cleanup_llm_models.py --stats
"""

import argparse
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class ModelInfo:
    """Information about a model directory."""
    path: Path
    name: str
    size_bytes: int
    is_quantized: bool
    quant_type: str  # "4bit", "8bit", "gguf", "original"
    has_safetensors: bool
    has_gguf: bool

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024 ** 3)


def get_dir_size(path: Path) -> int:
    """Get total size of directory in bytes."""
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    except (PermissionError, FileNotFoundError):
        pass
    return total


def analyze_model_dir(model_dir: Path) -> ModelInfo:
    """Analyze a model directory."""
    name = model_dir.name
    size = get_dir_size(model_dir)

    # Check for quantization indicators
    is_quantized = "-4bit" in name or "-8bit" in name
    quant_type = "original"
    if "-4bit" in name:
        quant_type = "4bit"
    elif "-8bit" in name:
        quant_type = "8bit"

    # Check for file types
    has_safetensors = any(model_dir.glob("*.safetensors"))
    has_gguf = any(model_dir.glob("*.gguf"))

    if has_gguf:
        quant_type = "gguf"
        is_quantized = True

    return ModelInfo(
        path=model_dir,
        name=name,
        size_bytes=size,
        is_quantized=is_quantized,
        quant_type=quant_type,
        has_safetensors=has_safetensors,
        has_gguf=has_gguf,
    )


def find_model_pairs(models_root: Path) -> List[Tuple[ModelInfo, ModelInfo]]:
    """Find original/quantized model pairs.

    Returns list of (original, quantized) tuples.
    """
    pairs = []

    # Scan all model directories
    all_models = {}
    for model_dir in models_root.rglob("*"):
        if not model_dir.is_dir():
            continue
        # Skip hidden directories and temp files
        if model_dir.name.startswith("."):
            continue
        # Check if it looks like a model directory
        if any(model_dir.glob("*.safetensors")) or any(model_dir.glob("*.gguf")) or (model_dir / "config.json").exists():
            info = analyze_model_dir(model_dir)
            all_models[model_dir] = info

    # Find pairs
    for path, info in all_models.items():
        if info.is_quantized:
            # Look for original
            base_name = info.name.replace("-4bit", "").replace("-8bit", "")
            original_path = path.parent / base_name
            if original_path in all_models:
                original_info = all_models[original_path]
                pairs.append((original_info, info))

    return pairs


def find_redundant_originals(models_root: Path) -> List[ModelInfo]:
    """Find original models that have quantized versions."""
    pairs = find_model_pairs(models_root)
    return [original for original, quantized in pairs]


def print_stats(models_root: Path):
    """Print storage statistics."""
    print(f"\n{'='*60}")
    print(f"LLM Model Storage Analysis: {models_root}")
    print(f"{'='*60}\n")

    all_models = []
    for model_dir in models_root.rglob("*"):
        if not model_dir.is_dir():
            continue
        if model_dir.name.startswith("."):
            continue
        if any(model_dir.glob("*.safetensors")) or any(model_dir.glob("*.gguf")) or (model_dir / "config.json").exists():
            info = analyze_model_dir(model_dir)
            all_models.append(info)

    if not all_models:
        print("No models found.")
        return

    # Group by type
    originals = [m for m in all_models if not m.is_quantized]
    quantized_4bit = [m for m in all_models if m.quant_type == "4bit"]
    quantized_8bit = [m for m in all_models if m.quant_type == "8bit"]
    gguf_models = [m for m in all_models if m.quant_type == "gguf"]

    total_size = sum(m.size_bytes for m in all_models)

    print("Storage by type:")
    print(f"  Original (FP16/FP32): {len(originals)} models, {sum(m.size_gb for m in originals):.1f} GB")
    print(f"  4-bit quantized:      {len(quantized_4bit)} models, {sum(m.size_gb for m in quantized_4bit):.1f} GB")
    print(f"  8-bit quantized:      {len(quantized_8bit)} models, {sum(m.size_gb for m in quantized_8bit):.1f} GB")
    print(f"  GGUF:                 {len(gguf_models)} models, {sum(m.size_gb for m in gguf_models):.1f} GB")
    print(f"  {'─'*40}")
    print(f"  TOTAL:                {len(all_models)} models, {total_size / (1024**3):.1f} GB")

    # Find redundant originals
    pairs = find_model_pairs(models_root)
    if pairs:
        redundant_size = sum(orig.size_bytes for orig, _ in pairs)
        print(f"\n⚠️  Redundant originals (have quantized version):")
        for original, quantized in pairs:
            print(f"     {original.name} ({original.size_gb:.1f} GB) → {quantized.name} ({quantized.size_gb:.1f} GB)")
        print(f"\n💡 Potential savings: {redundant_size / (1024**3):.1f} GB")
        print(f"   Run with --clean-originals to remove redundant originals")

    print()


def clean_originals(models_root: Path, dry_run: bool = True):
    """Remove original models that have quantized versions."""
    redundant = find_redundant_originals(models_root)

    if not redundant:
        print("No redundant originals found.")
        return

    total_savings = sum(m.size_bytes for m in redundant)

    print(f"\n{'='*60}")
    print(f"{'DRY RUN - ' if dry_run else ''}Cleaning Redundant Original Models")
    print(f"{'='*60}\n")

    for model in redundant:
        print(f"{'[DRY RUN] Would remove' if dry_run else 'Removing'}: {model.name}")
        print(f"          Path: {model.path}")
        print(f"          Size: {model.size_gb:.1f} GB")

        if not dry_run:
            try:
                shutil.rmtree(model.path)
                print(f"          ✓ Removed successfully")
            except Exception as e:
                print(f"          ✗ Error: {e}")
        print()

    print(f"{'─'*60}")
    print(f"Total space {'that would be' if dry_run else ''} freed: {total_savings / (1024**3):.1f} GB")

    if dry_run:
        print(f"\n⚠️  This was a dry run. Run with --clean-originals (without --dry-run) to actually delete.")


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup LLM model storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Show storage statistics
    python cleanup_llm_models.py --stats

    # Dry run - see what would be cleaned
    python cleanup_llm_models.py --clean-originals --dry-run

    # Actually clean up redundant originals
    python cleanup_llm_models.py --clean-originals
        """
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=Path.home() / ".local/share/airunner/text/models/llm",
        help="Path to LLM models directory"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show storage statistics"
    )
    parser.add_argument(
        "--clean-originals",
        action="store_true",
        help="Remove original models that have quantized versions"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    if not args.models_dir.exists():
        print(f"Error: Models directory not found: {args.models_dir}")
        return 1

    if args.stats:
        print_stats(args.models_dir)
    elif args.clean_originals:
        clean_originals(args.models_dir, dry_run=args.dry_run)
    else:
        # Default: show stats
        print_stats(args.models_dir)

    return 0


if __name__ == "__main__":
    exit(main())
