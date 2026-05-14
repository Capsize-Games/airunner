"""Bootstrap file requirements for BRIA RMBG background removal."""

RMBG_FILES: dict[str, list[str]] = {
    "briaai/RMBG-2.0": [
        "config.json",
        "model.safetensors",
        "preprocessor_config.json",
        "BiRefNet_config.py",
        "birefnet.py",
    ],
}