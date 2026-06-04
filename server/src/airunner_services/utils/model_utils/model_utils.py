"""
Model utility functions for AI Runner.

This module provides utilities for determining the correct model storage path for Stable Diffusion and related models.

Functions:
    get_stable_diffusion_model_storage_path(filename: str) -> str
        Returns the absolute path where a model file should be stored in the AI Runner folder.

"""

import os


def get_stable_diffusion_model_storage_path(
    version: str, pipeline_action: str, filename: str
) -> str:
    """Return the absolute path for storing a Stable Diffusion model file in the AI Runner folder.

    Args:
        version (str): Model version (e.g., 'SDXL 1.0').
        pipeline_action (str): Pipeline action (e.g., 'txt2img').
        filename (str): The name of the model file (e.g., 'model.safetensors').

    Returns:
        str: The absolute path where the model should be stored.
    """
    base_dir = os.path.expanduser(
        os.path.join(
            "~",
            ".local",
            "share",
            "airunner",
            "art",
            "models",
            version,
            pipeline_action,
        )
    )
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, filename)
