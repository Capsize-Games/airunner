"""Z-Image bundle and companion-file helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from airunner_services.art.runtime_enums import SignalCode
from airunner_services.art.utils.model_file_checker import ModelFileChecker
from airunner_services.art.managers.zimage.zimage_bundle_requirements import (
    detect_fp8_checkpoint,
    get_active_zimage_load_mode,
    get_missing_files_for_mode,
)


class ZImageBundleHelper:
    """Resolve Z-Image companion files and download requirements."""

    def __init__(self, owner) -> None:
        """Store the owning loading mixin instance."""
        self._owner = owner

    def check_and_trigger_download(self) -> tuple[bool, dict]:
        """Check Z-Image files against the active runtime mode."""
        version = getattr(self._owner, "version", None)
        pipeline_action = getattr(self._owner, "pipeline_action", "txt2img")
        if version != "Z-Image Turbo":
            parent = getattr(super(type(self._owner), self._owner), "_check_and_trigger_download", None)
            return parent() if callable(parent) else (False, {})
        model_path = Path(self._owner.model_path)
        load_mode = get_active_zimage_load_mode(model_path)
        missing_files = get_missing_files_for_mode(model_path, load_mode)
        if not missing_files:
            return False, {}
        if os.environ.get("AIRUNNER_ART_SIDECAR_PROCESS") == "1":
            self._owner.logger.info(
                "Z-Image companion files missing in sidecar mode "
                "(skipping download trigger): %s",
                missing_files,
            )
            return False, {}
        repo_id = ModelFileChecker.get_repo_id_for_version(version, pipeline_action)
        if repo_id is None:
            return False, {"error": "Unable to resolve Z-Image download source"}
        download_info = self.build_zimage_download_info(repo_id, missing_files)
        self._owner.emit_signal(
            SignalCode.ART_MODEL_DOWNLOAD_REQUIRED,
            download_info,
        )
        return True, download_info

    def build_zimage_download_info(
        self,
        repo_id: str,
        missing_files: list[str],
    ) -> dict:
        """Build the Z-Image download payload for WorkerManager."""
        return {
            "repo_id": repo_id,
            "model_path": self._owner.model_path,
            "missing_files": missing_files,
            "version": self._owner.version,
            "pipeline_action": getattr(self._owner, "pipeline_action", "txt2img"),
            "image_request": getattr(self._owner, "image_request", None),
        }

    def has_complete_pretrained_structure(self, model_dir: Path) -> bool:
        """Check whether all required pretrained component folders exist."""
        required_components = [
            "transformer",
            "text_encoder",
            "vae",
            "scheduler",
            "tokenizer",
        ]
        for component in required_components:
            component_path = model_dir / component
            if not component_path.is_dir():
                self._owner.logger.debug(
                    "Missing component directory: %s",
                    component,
                )
                return False
            config_file = self._component_config_path(component_path, component)
            if not config_file.exists():
                self._owner.logger.debug("Missing config file: %s", config_file)
                return False
        model_index = model_dir / "model_index.json"
        if not model_index.exists():
            self._owner.logger.debug("Missing model_index.json")
            return False
        return True

    @staticmethod
    def _component_config_path(component_path: Path, component: str) -> Path:
        """Return the expected config file for one component directory."""
        if component == "tokenizer":
            return component_path / "tokenizer_config.json"
        if component == "scheduler":
            return component_path / "scheduler_config.json"
        return component_path / "config.json"

    @staticmethod
    def detect_fp8_checkpoint(model_path: Path) -> bool:
        """Detect whether one safetensors checkpoint stores FP8 weights."""
        return detect_fp8_checkpoint(model_path)

    def resolve_zimage_companion_dir(
        self,
        checkpoint_path: Path,
    ) -> Optional[Path]:
        """Return the canonical Z-Image Turbo companion directory when present."""
        del checkpoint_path
        from airunner_services.database.models.path_settings import PathSettings
        from airunner_services.database.session import session_scope

        try:
            with session_scope() as session:
                path_settings = session.query(PathSettings).first()
                base_path = (getattr(path_settings, "base_path", "") or "").strip()
        except Exception:
            base_path = ""
        base_path = base_path or os.path.expanduser(
            os.path.join("~", ".local", "share", "airunner")
        )
        zimage_dir = (
            Path(base_path).expanduser()
            / "art"
            / "models"
            / "Z-Image Turbo"
            / "txt2img"
        )
        if zimage_dir.is_dir():
            self._owner.logger.info(
                "Resolved Z-Image companion directory: %s",
                zimage_dir,
            )
            return zimage_dir
        return None

    def ensure_zimage_files_available(self) -> None:
        """Ensure Z-Image model files exist locally or trigger download."""
        model_path = Path(self._owner.model_path)
        load_mode = get_active_zimage_load_mode(model_path)
        if load_mode != "pretrained_directory" and not model_path.exists():
            raise RuntimeError(f"Selected Z-Image checkpoint missing: {model_path}")
        companion_dir = self.resolve_zimage_companion_dir(model_path)
        search_dir = companion_dir if companion_dir else (
            model_path.parent if model_path.is_file() else model_path
        )
        bundle_probe_path = search_dir
        if search_dir.is_dir() and model_path.is_file():
            bundle_probe_path = search_dir / model_path.name
        missing_files = get_missing_files_for_mode(bundle_probe_path, load_mode)
        if (
            bundle_probe_path != model_path
            and model_path.exists()
            and model_path.name in missing_files
        ):
            missing_files = [
                file_name
                for file_name in missing_files
                if file_name != model_path.name
            ]
        if not missing_files:
            self._owner.logger.info(
                "All Z-Image model files present for %s (checked %s)",
                load_mode,
                search_dir,
            )
            return
        if os.environ.get("AIRUNNER_ART_SIDECAR_PROCESS") == "1":
            self._owner.logger.warning(
                "Z-Image companion files missing in sidecar mode "
                "(checked %s): %s",
                search_dir,
                missing_files,
            )
            return
        repo_id = ModelFileChecker.get_repo_id_for_version(
            "Z-Image Turbo",
            "txt2img",
        )
        if repo_id is None:
            raise RuntimeError(
                "Could not resolve a download source for Z-Image Turbo"
            )
        self._owner.logger.info(
            "Missing %s Z-Image model files, triggering download from %s",
            len(missing_files),
            repo_id,
        )
        self._owner.logger.debug("Missing files: %s", missing_files)
        self._owner.emit_signal(
            SignalCode.ART_MODEL_DOWNLOAD_REQUIRED,
            {
                "repo_id": repo_id,
                "model_path": str(search_dir),
                "missing_files": missing_files,
                "version": "Z-Image Turbo",
                "pipeline_action": "txt2img",
            },
        )
        raise RuntimeError(
            f"Z-Image model files missing from {search_dir}, download triggered"
        )