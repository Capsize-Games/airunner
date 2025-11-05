"""Utility for checking if required model files exist and triggering downloads.

This module provides functionality to verify that all required files for a
model are present on disk, and to initiate downloads for missing files.
Supports all model types: Art (SD, SDXL, FLUX), LLM, STT (Whisper), TTS (OpenVoice, SpeechT5).
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from airunner.components.data.bootstrap.unified_model_files import (
    get_required_files_for_model,
)


class ModelFileChecker:
    """Check for missing model files and coordinate downloads.

    Supports all model types:
    - art: Stable Diffusion models (SD 1.5, SDXL, FLUX)
    - llm: Language models (Llama, Qwen, etc.)
    - stt: Speech-to-text models (Whisper)
    - tts_openvoice: OpenVoice TTS models
    - tts_speecht5: SpeechT5 TTS models
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
            model_type: Type of model (art, llm, stt, tts_openvoice, tts_speecht5)
            model_id: Model identifier (repo_id or version name)
            version: Model version (for art models like "SD 1.5", "SDXL 1.0")
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

        Args:
            model_path: Path to the model directory
            model_type: Type of model (art, llm, stt, tts_openvoice, tts_speecht5)
            model_id: Model identifier (repo_id for non-art models)
            version: Model version (for art models like "SD 1.5", "SDXL 1.0")
            pipeline_action: Pipeline action (for art models like "txt2img", "inpaint")

        Returns:
            Tuple of (all_files_exist, missing_files_list)
        """
        if not model_path or not os.path.exists(model_path):
            return False, []

        # For art models, use version; for others use model_id
        if model_type == "art":
            required_files = ModelFileChecker.get_required_files(
                model_type, version, version, pipeline_action
            )
        else:
            # For non-art models, model_id is the repo ID
            if not model_id:
                model_id = model_path  # Try using path as model_id
            required_files = ModelFileChecker.get_required_files(
                model_type, model_id
            )

        if required_files is None:
            # If no required files defined, assume all files exist
            return True, []

        model_dir = Path(model_path)
        missing_files = []

        for file_path in required_files:
            full_path = model_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        all_exist = len(missing_files) == 0
        return all_exist, missing_files

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
            model_type: Type of model (art, llm, stt, tts_openvoice, tts_speecht5)
            model_id: Model identifier (repo_id for non-art models)
            version: Model version (for art models like "SD 1.5", "SDXL 1.0")
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
