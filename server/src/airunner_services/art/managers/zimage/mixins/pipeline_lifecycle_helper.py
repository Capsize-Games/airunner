"""Lifecycle helpers for Z-Image pipeline loading and swapping."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from airunner_services.art.pipelines.z_image import ZImagePipeline


class ZImagePipelineLifecycleHelper:
    """Coordinate pipeline setup, verification, and swapping."""

    def __init__(self, owner) -> None:
        """Store the owning loading mixin instance."""
        self._owner = owner

    def set_pipe(self, config_path: str, data: Dict) -> None:
        """Load one Z-Image pipeline from the selected model path."""
        del config_path
        pipeline_class = self._owner._pipeline_class or ZImagePipeline
        self._owner.logger.info(
            "Loading %s from %s",
            pipeline_class.__name__,
            self._owner.model_path,
        )
        bundle_helper = self._owner._get_bundle_helper()
        bundle_helper.ensure_zimage_files_available()
        self._owner._clear_gpu_memory()
        model_path = Path(self._owner.model_path)
        is_single_file = model_path.is_file()
        companion_dir = bundle_helper.resolve_zimage_companion_dir(model_path)
        model_dir = companion_dir or (
            model_path.parent if is_single_file else model_path
        )
        has_pretrained = bundle_helper.has_complete_pretrained_structure(
            model_dir
        )
        is_fp8_checkpoint = bundle_helper.detect_fp8_checkpoint(model_path)
        self._load_pipeline_for_mode(
            model_path,
            model_dir,
            pipeline_class,
            data,
            is_single_file,
            has_pretrained,
            is_fp8_checkpoint,
        )
        self._owner.logger.debug(
            "[ZIMAGE DEBUG] After _set_pipe: self._pipe=%s, self=%s",
            self._owner._pipe,
            id(self._owner),
        )
        self._owner._clear_gpu_memory()

    def _load_pipeline_for_mode(
        self,
        model_path: Path,
        model_dir: Path,
        pipeline_class,
        data: Dict,
        is_single_file: bool,
        has_pretrained: bool,
        is_fp8_checkpoint: bool,
    ) -> None:
        """Choose the correct loading path for one Z-Image model selection."""
        if is_single_file and is_fp8_checkpoint:
            self._owner.logger.info(
                "FP8 scaled checkpoint detected (%s). Using native FP8 "
                "pipeline for memory-efficient loading.",
                model_path.name,
            )
            self._owner._get_runtime_loader_helper().load_native_fp8_pipeline(
                str(model_path),
                str(model_dir),
                pipeline_class,
                data,
            )
            return
        if is_single_file and self._owner.use_from_single_file:
            self._owner.logger.info(
                "Loading from single-file checkpoint: %s",
                model_path.name,
            )
            self._owner._load_from_single_file(
                self._owner.model_path,
                pipeline_class,
                data,
                is_fp8_checkpoint=is_fp8_checkpoint,
            )
            return
        if has_pretrained and not is_single_file:
            self._owner.logger.info(
                "Complete pretrained structure found - loading from "
                "pretrained directory"
            )
            self._owner._load_from_pretrained(
                str(model_dir), pipeline_class, data
            )
            return
        if self._owner.use_from_single_file:
            self._owner._load_from_single_file(
                self._owner.model_path,
                pipeline_class,
                data,
            )
            return
        self._owner._load_from_pretrained(
            self._owner.model_path,
            pipeline_class,
            data,
        )

    def verify_pipeline_loaded(self) -> bool:
        """Verify that required pipeline components were loaded."""
        if self._owner._pipe is None:
            return False
        for component in (
            "transformer",
            "vae",
            "text_encoder",
            "tokenizer",
            "scheduler",
        ):
            if not hasattr(self._owner._pipe, component):
                self._owner.logger.warning(
                    "Missing required component: %s",
                    component,
                )
                return False
            if getattr(self._owner._pipe, component) is None:
                self._owner.logger.warning(
                    "Missing required component: %s",
                    component,
                )
                return False
        return True

    def swap_pipeline(self) -> None:
        """Swap between txt2img and img2img pipelines without reloading."""
        pipeline_class = self._owner._pipeline_class or ZImagePipeline
        if self._owner._pipe is None:
            self._owner.logger.debug("No pipeline loaded, nothing to swap")
            return
        if self._owner._pipe.__class__ is pipeline_class:
            self._owner.logger.debug(
                "Pipeline already is %s, no swap needed",
                pipeline_class.__name__,
            )
            return
        self._owner.logger.info(
            "Swapping Z-Image pipeline from %s to %s",
            self._owner._pipe.__class__.__name__,
            pipeline_class.__name__,
        )
        try:
            components = {
                "transformer": self._owner._pipe.transformer,
                "text_encoder": self._owner._pipe.text_encoder,
                "tokenizer": self._owner._pipe.tokenizer,
                "vae": self._owner._pipe.vae,
                "scheduler": self._owner._pipe.scheduler,
            }
            self._owner._pipe = pipeline_class(**components)
            if hasattr(self._owner, "_make_memory_efficient"):
                self._owner._make_memory_efficient()
            self._owner.logger.info(
                "Successfully swapped to %s",
                pipeline_class.__name__,
            )
        except Exception as exc:
            self._owner.logger.error(
                "Failed to swap Z-Image pipeline: %s",
                exc,
                exc_info=True,
            )
            raise
