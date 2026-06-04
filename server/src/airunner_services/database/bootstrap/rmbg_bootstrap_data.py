"""Shared bootstrap file requirements for BRIA RMBG."""

from __future__ import annotations


RMBG_FILES: dict[str, list[str]] = {
    "briaai/RMBG-2.0": [
        "config.json",
        "model.safetensors",
        "preprocessor_config.json",
        "BiRefNet_config.py",
        "birefnet.py",
    ],
}


__all__ = ["RMBG_FILES"]