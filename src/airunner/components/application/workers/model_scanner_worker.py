"""Model scanner worker for discovering art models in the filesystem.

This worker scans the model directory structure to find and register AI models
for image generation (FLUX, Z-Image, Stable Diffusion, etc.).

Directory structure expected:
    {base_path}/art/models/{version}/{pipeline_action}/{model_file_or_folder}

Example:
    ~/.local/share/airunner/art/models/Z-Image Turbo/txt2img/model.safetensors
    ~/.local/share/airunner/art/models/FLUX.1-dev/txt2img/flux-dev/
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from airunner.components.art.data.ai_models import AIModels
from airunner.enums import SignalCode, ImageGenerator, StableDiffusionVersion
from airunner.components.application.gui.windows.main.pipeline_mixin import (
    PipelineMixin,
)
from airunner.components.application.workers.worker import Worker


# Mapping from version names to ImageGenerator categories
VERSION_TO_CATEGORY: dict[str, str] = {
    StableDiffusionVersion.FLUX_DEV.value: ImageGenerator.FLUX.value,
    StableDiffusionVersion.FLUX_SCHNELL.value: ImageGenerator.FLUX.value,
    StableDiffusionVersion.Z_IMAGE_TURBO.value: ImageGenerator.ZIMAGE.value,
    StableDiffusionVersion.Z_IMAGE_BASE.value: ImageGenerator.ZIMAGE.value,
    StableDiffusionVersion.SDXL1_0.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.SDXL_TURBO.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.SDXL_LIGHTNING.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.SDXL_HYPER.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.X4_UPSCALER.value: ImageGenerator.STABLEDIFFUSION.value,
}

# Valid model file extensions
MODEL_EXTENSIONS = (".ckpt", ".safetensors", ".gguf")

# Folders that indicate a diffusers model directory
DIFFUSERS_REQUIRED_FOLDERS = ("scheduler", "text_encoder", "tokenizer", "unet", "vae")

# Folders to skip during scanning
SKIP_FOLDERS = ("controlnet_processors",)


def get_category_for_version(version: str) -> str:
    """Get the ImageGenerator category for a given version name.

    Args:
        version: The version folder name (e.g., 'Z-Image Turbo', 'FLUX.1-dev')

    Returns:
        The category string (e.g., 'zimage', 'flux', 'stablediffusion').
        Defaults to 'flux' for unknown versions.
    """
    return VERSION_TO_CATEGORY.get(version, ImageGenerator.FLUX.value)


@dataclass
class ScannedModel:
    """Represents a model found during scanning."""

    name: str
    path: str
    version: str
    category: str
    pipeline_action: str


class ModelScannerWorker(Worker, PipelineMixin):
    """Worker that scans the filesystem for AI models.

    Scans the configured model directory for art models and registers them
    in the database. Handles both single-file models (.safetensors, .gguf, .ckpt)
    and diffusers-format model directories.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PipelineMixin.__init__(self)

    def handle_message(self, _message) -> None:
        """Process a scan request message."""
        self.scan_for_models()
        self.remove_missing_models()

    @property
    def model_base_path(self) -> Path:
        """Get the base path for art models."""
        return Path(self.path_settings.base_path).expanduser() / "art" / "models"

    def scan_for_models(self) -> None:
        """Scan the model directory and register found models."""
        self.logger.debug("Starting model scan")
        model_path = self.model_base_path

        if not model_path.exists():
            self.logger.debug(f"Creating model path: {model_path}")
            model_path.mkdir(parents=True, exist_ok=True)

        models = self._scan_model_directory(model_path)
        self.logger.debug(f"Total models found: {len(models)}")

        # Convert to AIModels and emit signal
        ai_models = [self._create_ai_model(m) for m in models]
        self.emit_signal(
            SignalCode.AI_MODELS_SAVE_OR_UPDATE_SIGNAL, {"models": ai_models}
        )

    def _scan_model_directory(self, base_path: Path) -> List[ScannedModel]:
        """Scan the model directory structure.

        Args:
            base_path: The base path to scan (e.g., ~/.local/share/airunner/art/models)

        Returns:
            List of ScannedModel objects found during scanning.
        """
        models: List[ScannedModel] = []

        if not base_path.exists():
            return models

        # Iterate through version folders (e.g., "Z-Image Turbo", "FLUX.1-dev")
        for version_dir in self._iter_directories(base_path):
            version_name = version_dir.name
            self.logger.debug(f"Scanning version: {version_name}")

            # Iterate through pipeline action folders (e.g., "txt2img", "inpaint")
            for action_dir in self._iter_directories(version_dir):
                action_name = action_dir.name

                if action_name in SKIP_FOLDERS:
                    continue

                # Scan for models in this action folder
                found_models = self._scan_action_directory(
                    action_dir, version_name, action_name
                )
                models.extend(found_models)

        return models

    def _scan_action_directory(
        self, action_dir: Path, version: str, action: str
    ) -> List[ScannedModel]:
        """Scan a pipeline action directory for models.

        Args:
            action_dir: Path to the action directory (e.g., .../Z-Image Turbo/txt2img)
            version: The version name
            action: The pipeline action name

        Returns:
            List of ScannedModel objects found.
        """
        models: List[ScannedModel] = []

        for item in action_dir.iterdir():
            model = self._identify_model(item, version, action)
            if model:
                self.logger.debug(f"Found model: {model.name} at {model.path}")
                models.append(model)

        return models

    def _identify_model(
        self, path: Path, version: str, action: str
    ) -> Optional[ScannedModel]:
        """Identify if a path is a valid model file or directory.

        Args:
            path: Path to check
            version: The version name
            action: The pipeline action name

        Returns:
            ScannedModel if valid, None otherwise.
        """
        category = get_category_for_version(version)

        if path.is_file():
            return self._identify_model_file(path, version, category, action)
        elif path.is_dir():
            return self._identify_model_directory(path, version, category, action)

        return None

    def _identify_model_file(
        self, path: Path, version: str, category: str, action: str
    ) -> Optional[ScannedModel]:
        """Check if a file is a valid model file.

        Args:
            path: Path to the file
            version: The version name
            category: The model category
            action: The pipeline action name

        Returns:
            ScannedModel if valid model file, None otherwise.
        """
        if not path.suffix.lower() in MODEL_EXTENSIONS:
            return None

        # Remove extension to get model name
        name = path.stem

        return ScannedModel(
            name=name,
            path=str(path),
            version=version,
            category=category,
            pipeline_action=action,
        )

    def _identify_model_directory(
        self, path: Path, version: str, category: str, action: str
    ) -> Optional[ScannedModel]:
        """Check if a directory is a valid diffusers model directory.

        Args:
            path: Path to the directory
            version: The version name
            category: The model category
            action: The pipeline action name

        Returns:
            ScannedModel if valid diffusers directory, None otherwise.
        """
        # Check if all required diffusers folders exist
        is_diffusers = all(
            (path / folder).exists() for folder in DIFFUSERS_REQUIRED_FOLDERS
        )

        if not is_diffusers:
            return None

        return ScannedModel(
            name=path.name,
            path=str(path),
            version=version,
            category=category,
            pipeline_action=action,
        )

    def _iter_directories(self, path: Path):
        """Iterate over directories in a path, skipping files.

        Args:
            path: Path to iterate

        Yields:
            Path objects for each directory.
        """
        try:
            for item in path.iterdir():
                if item.is_dir():
                    yield item
        except PermissionError:
            self.logger.warning(f"Permission denied accessing: {path}")
        except OSError as e:
            self.logger.error(f"Error scanning {path}: {e}")

    def _create_ai_model(self, scanned: ScannedModel) -> AIModels:
        """Create an AIModels instance from a ScannedModel.

        Args:
            scanned: The scanned model data

        Returns:
            AIModels instance ready for database insertion.
        """
        model = AIModels()
        model.name = scanned.name
        model.path = scanned.path
        model.branch = "main"
        model.version = scanned.version
        model.category = scanned.category
        model.pipeline_action = scanned.pipeline_action
        model.enabled = True
        model.model_type = "art"
        model.is_default = False
        return model

    def remove_missing_models(self) -> None:
        """Remove database entries for models that no longer exist on disk."""
        existing_models = AIModels.objects.all()

        for model in existing_models:
            if not Path(model.path).exists():
                self.logger.debug(f"Removing missing model: {model.name} (id={model.id})")
                AIModels.objects.delete(model.id)
