"""Bootstrap file requirements for BRIA RMBG background removal models.

These lists are used by the custom HuggingFace downloader to determine which
files must exist on disk before attempting to load a model.

We intentionally keep this minimal to avoid downloading large optional assets
(e.g. ONNX exports) when using the PyTorch/Transformers path.
"""

RMBG_FILES: dict[str, list[str]] = {
    # BRIA Background Removal v2.0 (BiRefNet remote code)
    "briaai/RMBG-2.0": [
        "config.json",
        "model.safetensors",
        "preprocessor_config.json",
        "BiRefNet_config.py",
        "birefnet.py",
    ],
}
