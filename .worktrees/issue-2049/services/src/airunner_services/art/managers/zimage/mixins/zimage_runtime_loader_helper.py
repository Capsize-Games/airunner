"""Runtime loader helpers for Z-Image pipeline setup."""

from __future__ import annotations

import gc
import importlib.util
import os
import time
from typing import Any

from diffusers import FlowMatchEulerDiscreteScheduler
import torch

from airunner_services.art.managers.zimage.native import (
    NativePipelineWrapper,
    ZImageNativePipeline,
)
from airunner_services.art.runtime_enums import Scheduler
from airunner_services.art.schedulers.flow_match_scheduler_factory import (
    create_flow_match_scheduler,
    is_flow_match_scheduler,
)


class ZImageRuntimeLoaderHelper:
    """Load runtime schedulers and native FP8 pipelines."""

    def __init__(self, owner) -> None:
        """Store the owning loading mixin instance."""
        self._owner = owner

    def load_zimage_scheduler(self, scheduler_path) -> Any:
        """Load a flow-match scheduler based on current user selection."""
        scheduler_name = None
        if hasattr(self._owner, "image_request") and self._owner.image_request:
            scheduler_name = getattr(self._owner.image_request, "scheduler", None)
        if not scheduler_name:
            scheduler_name = Scheduler.FLOW_MATCH_EULER.value
        self._owner.logger.info(
            "Loading scheduler: %s from %s",
            scheduler_name,
            scheduler_path,
        )
        base_config = self._load_base_scheduler_config(scheduler_path)
        if is_flow_match_scheduler(scheduler_name):
            try:
                scheduler = create_flow_match_scheduler(scheduler_name, base_config)
                self._log_scheduler_config(scheduler_name, scheduler)
                self._owner.logger.info(
                    "Loaded %s with config: %s",
                    scheduler.__class__.__name__,
                    scheduler_name,
                )
                return scheduler
            except Exception as exc:
                self._owner.logger.error(
                    "Failed to create scheduler %s: %s",
                    scheduler_name,
                    exc,
                )
                self._owner.logger.info(
                    "Falling back to default FlowMatchEulerDiscreteScheduler"
                )
        if base_config:
            return FlowMatchEulerDiscreteScheduler.from_config(base_config)
        return FlowMatchEulerDiscreteScheduler()

    def _load_base_scheduler_config(self, scheduler_path) -> Any:
        """Load and sanitize one scheduler config from disk."""
        try:
            base_scheduler = FlowMatchEulerDiscreteScheduler.from_pretrained(
                str(scheduler_path),
                local_files_only=True,
            )
            base_config = dict(base_scheduler.config)
            for flag in (
                "use_karras_sigmas",
                "stochastic_sampling",
                "use_exponential_sigmas",
                "use_beta_sigmas",
            ):
                base_config.pop(flag, None)
            return base_config
        except Exception as exc:
            self._owner.logger.warning(
                "Could not load base scheduler config: %s",
                exc,
            )
            return None

    def _log_scheduler_config(self, scheduler_name: str, scheduler: Any) -> None:
        """Log scheduler-specific runtime flags when available."""
        if not hasattr(scheduler, "config"):
            return
        karras = scheduler.config.get("use_karras_sigmas", False)
        stochastic = scheduler.config.get("stochastic_sampling", False)
        self._owner.logger.debug(
            "[ZIMAGE SCHEDULER DEBUG] %s config -> karras=%s, stochastic=%s",
            scheduler_name,
            karras,
            stochastic,
        )

    def load_native_fp8_pipeline(
        self,
        checkpoint_path: str,
        model_dir: str,
        pipeline_class: Any,
        data: dict,
    ) -> None:
        """Load Z-Image using the native FP8 implementation."""
        self._owner.logger.info(
            "Loading native FP8 pipeline from %s",
            checkpoint_path,
        )
        pipeline_started_at = time.perf_counter()
        if importlib.util.find_spec(
            "airunner_services.art.managers.zimage.native"
        ) is None:
            self._owner.logger.warning(
                "Native FP8 implementation not available - falling back "
                "to pretrained loading with 4-bit quantization"
            )
            self._owner._force_quantization_for_fp8_fallback = True
            self._owner._load_from_pretrained(model_dir, pipeline_class, data)
            return
        self._clear_cuda_memory()
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            self._owner.logger.info(
                "Pre-load VRAM state: %.2fGB allocated, %.2fGB reserved",
                allocated,
                reserved,
            )
        native_pipeline = self._create_native_pipeline(checkpoint_path, model_dir)
        self._load_native_components(native_pipeline)
        self._owner._native_pipeline = native_pipeline
        self._owner._pipe = self.create_native_pipeline_wrapper(native_pipeline)
        self._owner.logger.info(
            "Native FP8 pipeline loaded successfully in %.2fs",
            time.perf_counter() - pipeline_started_at,
        )
        self._owner.logger.info("Memory usage: %s", native_pipeline.memory_usage)

    def _clear_cuda_memory(self) -> None:
        """Clear GPU memory before heavy native loading work."""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

    def _create_native_pipeline(
        self,
        checkpoint_path: str,
        model_dir: str,
    ) -> ZImageNativePipeline:
        """Create one native Z-Image pipeline instance."""
        model_dtype = self._owner.data_type
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._owner.logger.info(
            "Native FP8 loading with dtype=%s, device=%s",
            model_dtype,
            device,
        )
        return ZImageNativePipeline(
            transformer_path=checkpoint_path,
            text_encoder_path=os.path.join(model_dir, "text_encoder"),
            vae_path=os.path.join(model_dir, "vae"),
            device=device,
            dtype=model_dtype,
            text_encoder_quantization="4bit",
        )

    def _load_native_components(self, native_pipeline: ZImageNativePipeline) -> None:
        """Load transformer, text encoder, and VAE into one native pipeline."""
        for label, metric_name, loader in (
            (
                "FP8 transformer weights (streaming)",
                "transformer",
                lambda: native_pipeline.load_transformer(stream_load=True),
            ),
            (
                "text encoder with adaptive memory strategy",
                "text encoder",
                native_pipeline.load_text_encoder,
            ),
            ("VAE", "VAE", native_pipeline.load_vae),
        ):
            self._owner.logger.info("Loading %s...", label)
            started_at = time.perf_counter()
            loader()
            self._owner.logger.info(
                "Native FP8 %s loaded in %.2fs",
                metric_name,
                time.perf_counter() - started_at,
            )

    @staticmethod
    def create_native_pipeline_wrapper(native_pipeline: Any) -> Any:
        """Create one compatibility wrapper around the native pipeline."""
        return NativePipelineWrapper(native_pipeline)