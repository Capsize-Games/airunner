"""Helpers for Z-Image bundle validation and auditing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import torch
from safetensors import safe_open

from airunner.components.data.bootstrap_service import (
    get_sd_file_bootstrap_data,
)


ZIMAGE_LOAD_MODES = (
    "native_fp8_single_file",
    "single_file_checkpoint",
    "pretrained_directory",
)
ARCHIVE_DIR_NAME = "archive"
_SAFE_TENSORS_FORMATS = {"pt", "tf", "flax", "mlx"}
_SINGLE_FILE_EXTENSIONS = (".safetensors", ".ckpt", ".pt", ".bin")
_TEXT_ENCODER_CONFIG = "text_encoder/config.json"
_TEXT_ENCODER_INDEX = "text_encoder/model.safetensors.index.json"
_TEXT_ENCODER_MERGED = "text_encoder/model.safetensors"
_TRANSFORMER_CONFIG = "transformer/config.json"
_TRANSFORMER_INDEX = "transformer/diffusion_pytorch_model.safetensors.index.json"
_TRANSFORMER_MERGED = "transformer/diffusion_pytorch_model.safetensors"
_SCHEDULER_CONFIG = "scheduler/scheduler_config.json"
_TOKENIZER_FILES = (
    "tokenizer/tokenizer_config.json",
    "tokenizer/tokenizer.json",
    "tokenizer/merges.txt",
    "tokenizer/vocab.json",
)
_VAE_FILES = (
    "vae/config.json",
    "vae/diffusion_pytorch_model.safetensors",
)
_OFFICIAL_FILES = get_sd_file_bootstrap_data()["Z-Image Turbo"]["txt2img"]
_OFFICIAL_TEXT_ENCODER_SHARDS = tuple(
    file_name
    for file_name in _OFFICIAL_FILES
    if file_name.startswith("text_encoder/model-")
)
_OFFICIAL_TRANSFORMER_SHARDS = tuple(
    file_name
    for file_name in _OFFICIAL_FILES
    if file_name.startswith("transformer/diffusion_pytorch_model-")
)


def looks_like_single_file(model_path: Path) -> bool:
    """Return True when the path targets a single checkpoint file."""
    return model_path.suffix.lower() in _SINGLE_FILE_EXTENSIONS


def get_bundle_dir(model_path: Path) -> Path:
    """Return the directory that stores companion Z-Image files."""
    if looks_like_single_file(model_path):
        return model_path.parent
    return model_path


def find_checkpoint_candidates(model_path: Path) -> list[Path]:
    """Return top-level checkpoint files available for a bundle."""
    bundle_dir = get_bundle_dir(model_path)
    if not bundle_dir.is_dir():
        return []
    return sorted(
        path for path in bundle_dir.iterdir() if path.is_file() and looks_like_single_file(path)
    )


def find_active_checkpoint(model_path: Path) -> Path | None:
    """Return the checkpoint AIRunner would prefer for a bundle directory."""
    if looks_like_single_file(model_path):
        return model_path if model_path.exists() else None
    candidates = find_checkpoint_candidates(model_path)
    return next((path for path in candidates if detect_fp8_checkpoint(path)), None)


def detect_fp8_checkpoint(model_path: Path) -> bool:
    """Return True when the checkpoint looks like AIRunner's FP8 format."""
    name = model_path.name.lower()
    name_hint = "fp8" in name or "e4m3" in name or "e5m2" in name
    if model_path.suffix.lower() != ".safetensors" or not model_path.is_file():
        return name_hint
    try:
        with safe_open(model_path, framework="pt") as handle:
            return _checkpoint_uses_fp8(handle, name_hint)
    except Exception:
        return name_hint


def get_active_zimage_load_mode(model_path: Path) -> str:
    """Return the current AIRunner load mode for the given model path."""
    if not looks_like_single_file(model_path):
        return "pretrained_directory"
    if detect_fp8_checkpoint(model_path):
        return "native_fp8_single_file"
    return "single_file_checkpoint"


def get_required_files_for_mode(
    model_path: Path,
    mode: str | None = None,
) -> list[str]:
    """Return AIRunner's required files for a Z-Image load mode."""
    active_mode = mode or get_active_zimage_load_mode(model_path)
    bundle_dir = get_bundle_dir(model_path)
    text_encoder = _resolve_text_encoder_weight_files(bundle_dir)
    tokenizer = list(_TOKENIZER_FILES)
    vae_files = list(_VAE_FILES)
    if active_mode == "native_fp8_single_file":
        return _dedupe([model_path.name, _TEXT_ENCODER_CONFIG] + text_encoder + tokenizer + vae_files)
    if active_mode == "single_file_checkpoint":
        return _dedupe([model_path.name, _TEXT_ENCODER_CONFIG] + text_encoder + tokenizer + vae_files)
    transformer = _resolve_transformer_weight_files(bundle_dir)
    return _dedupe([_TRANSFORMER_CONFIG] + transformer + [_TEXT_ENCODER_CONFIG] + text_encoder + tokenizer + vae_files)


def get_optional_used_files_for_mode(
    model_path: Path,
    mode: str | None = None,
) -> list[str]:
    """Return extra files the loader consults only when they exist."""
    active_mode = mode or get_active_zimage_load_mode(model_path)
    bundle_dir = get_bundle_dir(model_path)
    if active_mode == "native_fp8_single_file":
        return []
    if active_mode == "single_file_checkpoint":
        return _existing_files(bundle_dir, [_TRANSFORMER_CONFIG, _SCHEDULER_CONFIG])
    return _existing_files(bundle_dir, [_SCHEDULER_CONFIG])


def get_missing_files_for_mode(
    model_path: Path,
    mode: str | None = None,
) -> list[str]:
    """Return missing runtime files for the requested Z-Image load mode."""
    bundle_dir = get_bundle_dir(model_path)
    required = get_required_files_for_mode(model_path, mode)
    return [file_name for file_name in required if not (bundle_dir / file_name).exists()]


def get_downloadable_files_for_mode(
    model_path: Path,
    mode: str | None = None,
) -> list[str]:
    """Return repo-backed files AIRunner may download for a Z-Image mode."""
    active_mode = mode or get_active_zimage_load_mode(model_path)
    if active_mode == "pretrained_directory":
        return list(_OFFICIAL_FILES.keys())
    return _dedupe(
        [
            _TEXT_ENCODER_CONFIG,
            _TEXT_ENCODER_INDEX,
            *_OFFICIAL_TEXT_ENCODER_SHARDS,
            *_TOKENIZER_FILES,
            *_VAE_FILES,
        ]
    )


def list_bundle_files(
    model_path: Path,
    include_archived: bool = False,
) -> list[str]:
    """Return all files stored under the bundle directory."""
    bundle_dir = get_bundle_dir(model_path)
    if not bundle_dir.exists():
        return []
    return sorted(
        _relative_paths(
            bundle_dir,
            bundle_dir.rglob("*"),
            include_archived=include_archived,
        )
    )


def list_archived_files(model_path: Path) -> list[str]:
    """Return files currently stored under the bundle archive directory."""
    bundle_dir = get_bundle_dir(model_path)
    archive_dir = bundle_dir / ARCHIVE_DIR_NAME
    if not archive_dir.is_dir():
        return []
    return sorted(_relative_paths(bundle_dir, archive_dir.rglob("*"), include_archived=True))


def get_unused_files_for_mode(
    model_path: Path,
    mode: str | None = None,
) -> list[str]:
    """Return bundle files that AIRunner does not use for the mode."""
    used = set(get_required_files_for_mode(model_path, mode))
    used.update(get_optional_used_files_for_mode(model_path, mode))
    bundle_files = set(list_bundle_files(model_path))
    return sorted(bundle_files - used)


def _checkpoint_uses_fp8(handle: safe_open, name_hint: bool) -> bool:
    """Return True when sampled tensors indicate an FP8 checkpoint."""
    has_scale = False
    for index, key in enumerate(handle.keys()):
        has_scale = has_scale or "scale_weight" in key
        tensor = handle.get_tensor(key)
        if tensor.dtype in _float8_types():
            return True
        if index >= 32:
            break
    return name_hint or has_scale


def _float8_types() -> tuple[torch.dtype, ...]:
    """Return the float8 dtypes available in this PyTorch build."""
    dtypes = [torch.float8_e4m3fn, torch.float8_e5m2]
    for name in ("float8_e4m3fnuz", "float8_e5m2fnuz"):
        value = getattr(torch, name, None)
        if value is not None:
            dtypes.append(value)
    return tuple(dtypes)


def _resolve_text_encoder_weight_files(model_dir: Path) -> list[str]:
    """Return the text-encoder weights AIRunner will hand to transformers."""
    merged_path = model_dir / _TEXT_ENCODER_MERGED
    index_path = model_dir / _TEXT_ENCODER_INDEX
    if merged_path.is_file() and _merged_safetensors_is_standard(merged_path):
        return [_TEXT_ENCODER_MERGED]
    sharded = _index_weight_files(index_path, "text_encoder")
    if sharded:
        return [_TEXT_ENCODER_INDEX] + sharded
    if merged_path.is_file():
        return [_TEXT_ENCODER_MERGED]
    return [_TEXT_ENCODER_INDEX] + list(_OFFICIAL_TEXT_ENCODER_SHARDS)


def _resolve_transformer_weight_files(model_dir: Path) -> list[str]:
    """Return the transformer weights AIRunner will hand to diffusers."""
    merged_path = model_dir / _TRANSFORMER_MERGED
    index_path = model_dir / _TRANSFORMER_INDEX
    if merged_path.is_file():
        return [_TRANSFORMER_MERGED]
    sharded = _index_weight_files(index_path, "transformer")
    if sharded:
        return [_TRANSFORMER_INDEX] + sharded
    return [_TRANSFORMER_INDEX] + list(_OFFICIAL_TRANSFORMER_SHARDS)


def _merged_safetensors_is_standard(merged_path: Path) -> bool:
    """Return True when a merged safetensors file advertises a standard format."""
    try:
        with safe_open(merged_path, framework="pt") as handle:
            metadata = handle.metadata() or {}
    except Exception:
        return False
    return metadata.get("format") in _SAFE_TENSORS_FORMATS


def _index_weight_files(index_path: Path, prefix: str) -> list[str]:
    """Return shard files referenced by a safetensors index."""
    if not index_path.is_file():
        return []
    try:
        data = json.loads(index_path.read_text())
    except Exception:
        return []
    weight_map = data.get("weight_map", {})
    files = sorted({f"{prefix}/{name}" for name in weight_map.values()})
    return files


def _existing_files(bundle_dir: Path, files: list[str]) -> list[str]:
    """Return files from the list that exist inside the bundle directory."""
    return [file_name for file_name in files if (bundle_dir / file_name).exists()]


def _relative_paths(
    base_dir: Path,
    paths: Iterable[Path],
    include_archived: bool = False,
) -> list[str]:
    """Return sorted relative file paths for an iterable of Path objects."""
    items = []
    for path in paths:
        if not path.is_file():
            continue
        relative_path = path.relative_to(base_dir)
        if (
            not include_archived
            and relative_path.parts
            and relative_path.parts[0] == ARCHIVE_DIR_NAME
        ):
            continue
        items.append(str(relative_path))
    return sorted(items)


def _dedupe(files: list[str]) -> list[str]:
    """Return files with stable ordering and duplicates removed."""
    return list(dict.fromkeys(files))