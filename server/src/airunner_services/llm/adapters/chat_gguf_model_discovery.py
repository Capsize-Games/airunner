"""GGUF model-file discovery helpers."""

from pathlib import Path
from typing import Optional


def find_gguf_file(
    model_dir: str,
    preferred_filename: Optional[str] = None,
) -> Optional[str]:
    """Find a GGUF file in a model directory."""
    model_path = Path(model_dir)
    if not model_path.exists():
        return None

    gguf_files = sorted(
        model_path.glob("*.gguf"),
        key=lambda path: path.name.lower(),
    )
    if not gguf_files:
        return None
    matched_preferred = _match_preferred_gguf(gguf_files, preferred_filename)
    if matched_preferred is not None:
        return matched_preferred
    for gguf_file in gguf_files:
        if "Q4_K_M" in gguf_file.name or "q4_k_m" in gguf_file.name:
            return str(gguf_file)
    return str(gguf_files[0])


def _match_preferred_gguf(
    gguf_files: list[Path],
    preferred_filename: Optional[str],
) -> Optional[str]:
    """Return the preferred GGUF file when the filename is known."""
    if not preferred_filename:
        return None
    preferred_name = str(preferred_filename).strip()
    for gguf_file in gguf_files:
        if gguf_file.name == preferred_name:
            return str(gguf_file)
    preferred_name = preferred_name.lower()
    for gguf_file in gguf_files:
        if gguf_file.name.lower() == preferred_name:
            return str(gguf_file)
    return None


def is_gguf_model(model_path: str) -> bool:
    """Check if a model path contains a GGUF model."""
    path = Path(model_path)
    if path.suffix == ".gguf":
        return path.exists()
    if path.is_dir():
        return find_gguf_file(str(path)) is not None
    return False
