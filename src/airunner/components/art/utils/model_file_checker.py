"""Utility for checking if required model files exist and triggering downloads.

This module provides functionality to verify that all required files for a
model are present on disk, and to initiate downloads for missing files.
Supports all model types: Art (SD, SDXL, FLUX), LLM, STT (Whisper), TTS (OpenVoice).
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from airunner.components.data.bootstrap.unified_model_files import (
    get_required_files_for_model,
)
from airunner.components.data.bootstrap.model_bootstrap_data import (
    model_bootstrap_data,
)


class ModelFileChecker:
    """Check for missing model files and coordinate downloads.

    Supports all model types:
    - art: Stable Diffusion and Flux
    - llm: Language models (Llama, Qwen, etc.)
    - stt: Speech-to-text models (Whisper)
    - tts_openvoice: OpenVoice TTS models
    """

    @staticmethod
    def get_required_files(
        model_type: str,
        model_id: str,
        version: str = None,
        pipeline_action: str = None,
    ) -> Optional[List[str]]:
        """Get list of required files for a model.

        Args:
            model_type: Type of model (art, llm, stt, tts_openvoice)
            model_id: Model identifier (repo_id or version name)
            version: Model version (for art models like "SDXL 1.0" and "Flux.1 S")
            pipeline_action: Pipeline action (for art models like "txt2img", "inpaint")

        Returns:
            List of required file paths relative to model directory,
            or None if not found
        """
        return get_required_files_for_model(
            model_type, model_id, version, pipeline_action
        )

    @staticmethod
    def check_missing_files(
        model_path: str,
        model_type: str = "art",
        model_id: str = None,
        version: str = None,
        pipeline_action: str = None,
    ) -> Tuple[bool, List[str]]:
        """Check if all required files exist for a model.

        Also checks for incomplete files by comparing actual size against expected size.

        Args:
            model_path: Path to the model directory or GGUF file
            model_type: Type of model (art, llm, stt, tts_openvoice)
            model_id: Model identifier (repo_id for non-art models)
            version: Model version (for art models like "Flux.1 S", "SDXL 1.0")
            pipeline_action: Pipeline action (for art models like "txt2img", "inpaint")

        Returns:
            Tuple of (all_files_exist, missing_files_list)
        """
        if not model_path or not os.path.exists(model_path):
            return False, []

        # For single-file models (GGUF, safetensors, etc.), check for companion files in the parent directory
        model_dir = Path(model_path)
        single_file_extensions = (
            ".gguf",
            ".safetensors",
            ".ckpt",
            ".pt",
            ".pth",
        )
        is_single_file = (
            model_path.lower().endswith(single_file_extensions)
            and model_dir.is_file()
        )
        if is_single_file:
            model_dir = model_dir.parent

        # For art models, use version; for others use model_id
        if model_type == "art":
            required_files_data = ModelFileChecker.get_required_files(
                model_type, version, version, pipeline_action
            )
        else:
            # For non-art models, model_id is the repo ID
            if not model_id:
                model_id = model_path  # Try using path as model_id
            required_files_data = ModelFileChecker.get_required_files(
                model_type, model_id
            )

        if required_files_data is None:
            # If no required files defined, assume all files exist
            return True, []

        # Handle both dict format (art models with sizes) and list format (other models)
        if isinstance(required_files_data, dict):
            # New format: {filename: expected_size}
            required_files = list(required_files_data.keys())
            file_sizes = required_files_data
        else:
            # Old format: [filename, ...]
            required_files = required_files_data
            file_sizes = {}

        # If using a single-file checkpoint, skip checking for large model weight files
        # (transformer, unet, text_encoder weights) - only check for config files
        if is_single_file and model_type == "art":
            required_files = ModelFileChecker._filter_to_config_files_only(required_files)

        missing_files = []

        for file_path in required_files:
            full_path = model_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)
            elif file_sizes.get(file_path, 0) > 0:
                # Check if file is incomplete (actual size < expected size)
                actual_size = full_path.stat().st_size
                expected_size = file_sizes[file_path]
                if actual_size < expected_size:
                    # File exists but is incomplete
                    missing_files.append(file_path)

        all_exist = len(missing_files) == 0
        return all_exist, missing_files

    @staticmethod
    def _filter_to_config_files_only(files: List[str]) -> List[str]:
        """Filter file list to skip transformer/unet weights when using single-file checkpoint.
        
        When using a single-file checkpoint (quantized safetensors), we don't need 
        to download the original transformer/unet weights since the checkpoint 
        contains those. However, we STILL need:
        - Config files for all components
        - Text encoder weights (not in single-file checkpoints)
        - VAE weights (usually not in single-file checkpoints)
        - Tokenizer files
        
        Args:
            files: List of file paths
            
        Returns:
            Filtered list excluding only transformer/unet weight files
        """
        # Only skip transformer and unet weight files - these are what the
        # single-file checkpoint replaces
        skip_patterns = (
            "transformer/diffusion_pytorch_model",
            "unet/diffusion_pytorch_model",
        )
        
        filtered = []
        for f in files:
            # Skip transformer/unet weight files (but keep their configs)
            should_skip = False
            for pattern in skip_patterns:
                if pattern in f and f.endswith((".safetensors", ".bin")):
                    should_skip = True
                    break
            
            if not should_skip:
                filtered.append(f)
        
        return filtered

    @staticmethod
    def get_model_repo_id(model_path: str) -> Optional[str]:
        """Extract HuggingFace repo ID from model path.

        Args:
            model_path: Path to model (can be HF format like "user/model")

        Returns:
            HuggingFace repo ID if it looks like one, otherwise None

        Examples:
            >>> ModelFileChecker.get_model_repo_id("stable-diffusion-v1-5/stable-diffusion-v1-5")
            "stable-diffusion-v1-5/stable-diffusion-v1-5"
            >>> ModelFileChecker.get_model_repo_id("/local/path/to/model")
            None
        """
        if not model_path:
            return None

        # If path contains "/" and doesn't start with "/" or "." it's likely a HF repo
        if "/" in model_path and not model_path.startswith(("/", ".", "~")):
            return model_path

        return None

    @staticmethod
    def get_repo_id_for_version(
        version: str, pipeline_action: str = "txt2img"
    ) -> Optional[str]:
        """Get HuggingFace repo ID for a given model version.

        Args:
            version: Model version (e.g., "SDXL 1.0", "Flux.1 S", "Safety Checker")
            pipeline_action: Pipeline action (e.g., "txt2img", "inpaint", "safety_checker")

        Returns:
            HuggingFace repo ID if found, otherwise None

        Examples:
            >>> ModelFileChecker.get_repo_id_for_version("Flux.1 S", "txt2img")
            "black-forest-labs/FLUX.1-schnell"
            >>> ModelFileChecker.get_repo_id_for_version("Safety Checker", "safety_checker")
            "CompVis/stable-diffusion-safety-checker"
        """
        # Special case for Safety Checker
        if version == "Safety Checker":
            return "CompVis/stable-diffusion-safety-checker"

        for model in model_bootstrap_data:
            if (
                model.get("version") == version
                and model.get("pipeline_action") == pipeline_action
            ):
                return model.get("path")
        return None

    @staticmethod
    def should_trigger_download(
        model_path: str,
        model_type: str = "art",
        model_id: str = None,
        version: str = None,
        pipeline_action: str = None,
    ) -> Tuple[bool, Dict]:
        """Determine if a download should be triggered for missing files.

        Args:
            model_path: Path to the model
            model_type: Type of model (art, llm, stt, tts_openvoice)
            model_id: Model identifier (repo_id for non-art models)
            version: Model version (for art models like "Flux.1 S", "SDXL 1.0")
            pipeline_action: Pipeline action (for art models like "txt2img", "inpaint")

        Returns:
            Tuple of (should_download, download_info_dict)
            download_info_dict contains:
                - repo_id: HuggingFace repo ID
                - missing_files: List of missing file paths
                - model_path: Local path to save to
                - model_type: Type of model
        """
        all_exist, missing_files = ModelFileChecker.check_missing_files(
            model_path, model_type, model_id, version, pipeline_action
        )

        if all_exist:
            return False, {}

        repo_id = ModelFileChecker.get_model_repo_id(model_path)

        # For art models with a version, try looking up the repo_id from bootstrap data
        if repo_id is None and model_type == "art" and version:
            repo_id = ModelFileChecker.get_repo_id_for_version(
                version, pipeline_action or "txt2img"
            )

        # For non-art models, try using model_id as repo_id
        if repo_id is None and model_id:
            repo_id = model_id

        if repo_id is None:
            # Can't download - it's a local path with missing files
            return False, {
                "error": "Model files missing but path is not a HuggingFace repo",
                "missing_files": missing_files,
            }

        return True, {
            "repo_id": repo_id,
            "missing_files": missing_files,
            "model_path": model_path,
            "model_type": model_type,
            "version": version,
            "pipeline_action": pipeline_action,
        }
