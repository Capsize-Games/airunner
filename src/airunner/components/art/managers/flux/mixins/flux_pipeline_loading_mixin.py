"""FLUX pipeline loading mixin."""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import torch

try:  # Accelerate<1.8 does not expose get_state_dict
    from accelerate.utils import get_state_dict as _accelerate_get_state_dict
except ImportError:  # pragma: no cover - optional dependency path
    _accelerate_get_state_dict = None

from safetensors.torch import load_file
from transformers import (
    BitsAndBytesConfig as TransformersBitsAndBytesConfig,
    T5EncoderModel,
)
from airunner.components.art.utils.model_file_checker import (
    ModelFileChecker,
)

from diffusers import (
    FluxTransformer2DModel,
    BitsAndBytesConfig as DiffusersBitsAndBytesConfig,
)

from airunner.enums import SignalCode
from airunner.settings import (
    AIRUNNER_ADD_WATER_MARK,
    AIRUNNER_LOCAL_FILES_ONLY,
)
from airunner.components.art.utils.safetensors_inspector import (
    SafeTensorsInspector,
)


class FluxPipelineLoadingMixin:
    """Mixin for FLUX pipeline loading operations."""

    def _config_to_json_serializable(
        self, config_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert config dict to JSON-serializable format."""
        result = {}
        for key, value in config_dict.items():
            if isinstance(value, torch.dtype):
                # Convert torch dtype to string (e.g., torch.bfloat16 -> "bfloat16")
                result[key] = str(value).replace("torch.", "")
            elif isinstance(value, dict):
                result[key] = self._config_to_json_serializable(value)
            elif isinstance(value, (list, tuple)):
                result[key] = [
                    (
                        self._config_to_json_serializable({"item": item})[
                            "item"
                        ]
                        if isinstance(item, (dict, torch.dtype))
                        else item
                    )
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _collect_state_dict(
        self, module: torch.nn.Module
    ) -> Tuple[Dict[str, torch.Tensor], int]:
        """Return CPU state dict along with the number of meta tensors skipped."""
        raw_state_dict: Optional[Dict[str, torch.Tensor]] = None
        if _accelerate_get_state_dict is not None:
            try:
                raw_state_dict = _accelerate_get_state_dict(
                    module, destination="cpu"
                )
            except Exception as exc:  # noqa: BLE001 - best effort fallback
                self.logger.debug(
                    "accelerate.get_state_dict failed (%s); falling back to module.state_dict()",
                    exc,
                )

        if raw_state_dict is None:
            raw_state_dict = module.state_dict()

        clean_state_dict: Dict[str, torch.Tensor] = {}
        meta_count = 0
        for name, tensor in raw_state_dict.items():
            if not isinstance(tensor, torch.Tensor):
                continue
            if tensor.device.type == "meta":
                meta_count += 1
                continue
            clean_state_dict[name] = tensor.detach().cpu()

        return clean_state_dict, meta_count

    def _validate_cached_module(
        self,
        module_name: str,
        module: Optional[torch.nn.Module],
        expected_tensors: int,
        component_dir: Path,
    ) -> bool:
        """Ensure cached module has fully materialized tensors and expected count."""
        if module is None:
            return False

        clean_state, meta_count = self._collect_state_dict(module)
        if meta_count > 0:
            self.logger.warning(
                "Cached %s contains %d meta tensors; deleting cache",
                module_name,
                meta_count,
            )
            self._cleanup_component_dir(component_dir)
            return False

        if expected_tensors and len(clean_state) != expected_tensors:
            self.logger.warning(
                "Cached %s tensor count mismatch (expected %d, found %d); deleting cache",
                module_name,
                expected_tensors,
                len(clean_state),
            )
            self._cleanup_component_dir(component_dir)
            return False

        return True

    def _load_pipeline_from_cache(
        self,
        pipeline_class: Any,
        model_path: str,
        data: Dict[str, Any],
    ) -> bool:
        """Try loading a quantized pipeline from disk cache."""
        if not self._quantized_model_exists(model_path):
            return False

        quantized_path = self._get_quantized_model_path(model_path)
        try:
            self._pipe = pipeline_class.from_pretrained(
                str(quantized_path), **data
            )
        except Exception as exc:
            self.logger.warning(
                "Failed to load quantized model from disk: %s", exc
            )
            return False

        self.logger.info("✓ Loaded quantized model from disk")
        self._force_vae_fp32()
        return True

    def _load_pipeline_by_type(
        self,
        model_path: str,
        pipeline_class: Any,
        config_path: str,
        data: Dict[str, Any],
    ) -> None:
        """Dispatch pipeline loading based on model file layout."""
        if str(model_path).lower().endswith(".gguf"):
            self._load_gguf_model(model_path, pipeline_class)
            return

        if self.use_from_single_file:
            self._load_single_file_model(
                Path(model_path), pipeline_class, config_path, data
            )
            return

        self._load_pretrained_model(
            Path(model_path), pipeline_class, config_path, data
        )

    def _load_single_file_model(
        self,
        model_path: Path,
        pipeline_class: Any,
        config_path: Optional[str],
        data: Dict,
    ) -> None:
        """Load FLUX model from single file.

        Note: Single-file loads (.safetensors, .ckpt) do not support
        bitsandbytes quantization. Use bfloat16 for reduced memory instead.
        """
        self._announce_single_file_load(model_path)

        # Check if this is a UNet-only checkpoint
        if str(model_path).endswith(".safetensors"):
            file_type = SafeTensorsInspector.get_file_type(str(model_path))
            if file_type == "unet_only":
                self.logger.info(
                    "Detected UNet-only checkpoint - loading with base components"
                )
                self._load_unet_only_model(model_path, pipeline_class, data)
                return

        kwargs = self._single_file_kwargs(data, config_path)
        self._pipe = pipeline_class.from_single_file(str(model_path), **kwargs)
        self.logger.info("✓ Single-file model loaded (bfloat16 precision)")

    def _announce_single_file_load(self, model_path: Path) -> None:
        """Emit consistent logs when loading single-file models."""
        message = "Loading FLUX model from single file..."
        self.logger.info("%s %s", message, model_path)
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": message},
        )

    def _single_file_kwargs(
        self, data: Dict, config_path: Optional[str]
    ) -> Dict:
        """Build kwargs for single-file FLUX loading.

        Note: from_single_file does NOT support quantization_config.
        Quantization only works with from_pretrained directory loads.
        """
        # Remove quantization_config - not supported by from_single_file
        data_copy = {
            k: v for k, v in data.items() if k != "quantization_config"
        }

        kwargs = {
            "add_watermarker": AIRUNNER_ADD_WATER_MARK,
            "local_files_only": AIRUNNER_LOCAL_FILES_ONLY,
            **data_copy,
        }
        if config_path:
            kwargs["config"] = str(config_path)
        return kwargs

    def _load_unet_only_model(
        self,
        model_path: Path,
        pipeline_class: Any,
        data: Dict,
    ) -> None:
        """Load a UNet-only checkpoint and quantize components as needed."""
        if self._try_load_quantized_pipeline(model_path, pipeline_class, data):
            return

        base_model = self._base_flux_model_path()
        self._current_flux_base_model_path = base_model
        self._ensure_base_model_available(base_model)
        text_encoder_2 = self._load_quantized_t5(base_model)
        self._load_base_pipeline_with_t5(
            base_model, pipeline_class, data, text_encoder_2
        )

        transformer = self._create_quantized_transformer(
            model_path, base_model
        )
        self._finalize_quantized_unet(transformer)

    def _try_load_quantized_pipeline(
        self,
        model_path: Path,
        pipeline_class: Any,
        data: Dict,
    ) -> bool:
        """Return True if an on-disk quantized pipeline was loaded."""
        quantized_path = self._get_quantized_model_path(str(model_path))
        if self._quantized_model_exists(str(model_path)):
            self.logger.info(
                "Found existing quantized model at %s, loading directly...",
                quantized_path,
            )
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": "Loading pre-quantized model from disk..."},
            )
            self._pipe = pipeline_class.from_pretrained(
                str(quantized_path),
                torch_dtype=data.get("torch_dtype", torch.bfloat16),
                local_files_only=True,
            )
            self.logger.info("✓ Pre-quantized model loaded from disk")
            return True

        if self._component_cache_exists(quantized_path):
            return self._load_pipeline_from_component_cache(
                quantized_path, pipeline_class, data
            )

        return False

    def _component_cache_exists(self, quantized_path: Path) -> bool:
        """Return True if a component-level quantized cache exists."""
        manifest = self._read_component_manifest(
            quantized_path, suppress_errors=True
        )
        component_info = manifest.get("transformer", {})
        return (
            manifest.get("schema") == "component-cache/v2"
            and component_info.get("saved") is True
        )

    def _load_pipeline_from_component_cache(
        self,
        quantized_path: Path,
        pipeline_class: Any,
        data: Dict,
    ) -> bool:
        """Load pipeline using cached quantized components."""
        manifest = self._read_component_manifest(quantized_path)
        if manifest.get("schema") != "component-cache/v2":
            self.logger.info(
                "Component cache at %s uses deprecated schema; ignoring",
                quantized_path,
            )
            self._cleanup_component_dir(quantized_path / "components")
            return False

        transformer_manifest = manifest.get("transformer", {})
        if not transformer_manifest.get("saved"):
            self.logger.warning(
                "Component cache at %s missing transformer entry",
                quantized_path,
            )
            return False

        base_model = self._base_flux_model_path()
        self._current_flux_base_model_path = base_model
        try:
            self._ensure_base_model_available(base_model)
        except RuntimeError:
            return False

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": "Loading quantized components from cache..."},
        )

        text_manifest = manifest.get("text_encoder_2", {})
        cached_t5 = None
        if text_manifest.get("saved"):
            cached_t5 = self._load_cached_quantized_t5(quantized_path)
            if not self._validate_cached_module(
                "text_encoder_2",
                cached_t5,
                text_manifest.get("tensor_count", 0),
                quantized_path / "components" / "text_encoder_2",
            ):
                cached_t5 = None

        self._load_base_pipeline_with_t5(
            base_model, pipeline_class, data, cached_t5
        )

        transformer = self._load_cached_quantized_transformer(quantized_path)
        if not self._validate_cached_module(
            "transformer",
            transformer,
            transformer_manifest.get("tensor_count", 0),
            quantized_path / "components",
        ):
            self.logger.warning(
                "Cached transformer at %s is invalid; re-quantizing",
                quantized_path,
            )
            self._cleanup_component_dir(quantized_path / "components")
            return False

        self._finalize_quantized_unet(transformer)
        self.logger.info(
            "✓ Loaded pipeline from component cache at %s", quantized_path
        )
        return True

    def _load_cached_quantized_t5(
        self, quantized_path: Path
    ) -> Optional[T5EncoderModel]:
        """Load a cached quantized T5 encoder if present."""
        cache_dir = quantized_path / "components" / "text_encoder_2"
        if not cache_dir.exists():
            return None

        self.logger.info(
            "Loading cached quantized T5 encoder from %s", cache_dir
        )
        max_memory = self._quantized_t5_max_memory()
        return T5EncoderModel.from_pretrained(
            str(cache_dir),
            torch_dtype=torch.float16,
            device_map="auto",
            max_memory=max_memory,
            local_files_only=True,
        )

    def _load_cached_quantized_transformer(
        self, quantized_path: Path
    ) -> FluxTransformer2DModel:
        """Load cached quantized transformer from disk."""
        cache_dir = quantized_path / "components" / "transformer"
        self.logger.info(
            "Loading cached quantized transformer from %s", cache_dir
        )
        return FluxTransformer2DModel.from_pretrained(
            str(cache_dir),
            torch_dtype=torch.float16,
            device_map="auto",
            max_memory=self._transformer_max_memory(),
            low_cpu_mem_usage=True,
            local_files_only=True,
        )

    def _handle_quantized_save_failure(
        self, quantized_path: Path, exc: Exception
    ) -> None:
        """Fallback to component-level cache when pipeline save fails."""
        message = str(exc).lower()
        if "meta tensor" not in message:
            return

        self.logger.info(
            "Quantized pipeline save failed with meta tensors; caching components instead"
        )
        try:
            self._save_quantized_component_cache(quantized_path)
        except Exception as cache_exc:  # noqa: BLE001 - best effort
            self.logger.error(
                "Failed to cache quantized components at %s: %s",
                quantized_path,
                cache_exc,
            )

    def _save_quantized_component_cache(self, quantized_path: Path) -> None:
        """Persist quantized transformer/text encoder as a component cache."""
        cache_dir = quantized_path / "components"
        cache_dir.mkdir(parents=True, exist_ok=True)

        manifest: Dict[str, Any] = {
            "schema": "component-cache/v2",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "base_model": getattr(self, "_current_flux_base_model_path", None),
            "transformer": {"saved": False, "tensor_count": 0},
            "text_encoder_2": {"saved": False, "tensor_count": 0},
        }

        transformer_saved, transformer_tensors = (
            self._export_quantized_transformer(cache_dir)
        )
        manifest["transformer"]["saved"] = transformer_saved
        manifest["transformer"]["tensor_count"] = transformer_tensors

        text_saved, text_tensors = self._export_quantized_text_encoder(
            cache_dir
        )
        manifest["text_encoder_2"]["saved"] = text_saved
        manifest["text_encoder_2"]["tensor_count"] = text_tensors

        if not transformer_saved:
            self._cleanup_component_dir(cache_dir)
            raise RuntimeError(
                "Unable to persist quantized transformer weights for cache"
            )

        manifest_path = cache_dir / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)

        self._announce_quantized_save(
            f"✓ Cached quantized components to {manifest_path}"
        )

    def _cleanup_component_dir(self, path: Path) -> None:
        """Remove a component cache directory safely."""
        shutil.rmtree(path, ignore_errors=True)

    def _read_component_manifest(
        self, quantized_path: Path, suppress_errors: bool = False
    ) -> Dict[str, Any]:
        """Read component cache manifest file."""
        manifest_path = quantized_path / "components" / "manifest.json"
        try:
            with manifest_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:  # noqa: BLE001 - manifest is optional
            if not suppress_errors:
                self.logger.warning(
                    "Failed to read component cache manifest at %s: %s",
                    manifest_path,
                    exc,
                )
            return {}

    def _export_quantized_transformer(
        self, cache_dir: Path
    ) -> Tuple[bool, int]:
        """Export the quantized transformer to disk for reuse."""
        transformer = getattr(self._pipe, "transformer", None)
        if transformer is None:
            self.logger.warning("No transformer found to export for cache")
            return False, 0

        export_dir = cache_dir / "transformer"
        export_dir.mkdir(parents=True, exist_ok=True)

        try:
            clean_state_dict, meta_count = self._collect_state_dict(
                transformer
            )

            if meta_count > 0:
                self.logger.warning(
                    "Skipped %d meta tensors in transformer export - "
                    "skipping transformer cache export",
                    meta_count,
                )
                self._cleanup_component_dir(export_dir)
                return False, 0

            # Save config as JSON (transformer.config is a FrozenDict)
            config_dict = self._config_to_json_serializable(
                dict(transformer.config)
            )
            with (export_dir / "config.json").open("w") as f:
                json.dump(config_dict, f, indent=2)

            # Save the state dict
            from safetensors.torch import save_file

            save_file(
                clean_state_dict,
                str(export_dir / "diffusion_pytorch_model.safetensors"),
            )

            self.logger.info(
                "✓ Exported quantized transformer to %s (%d tensors, %d meta skipped)",
                export_dir,
                len(clean_state_dict),
                meta_count,
            )
            return True, len(clean_state_dict)
        except Exception as exc:  # noqa: BLE001 - best effort
            self.logger.error(
                "Failed to save quantized transformer for cache: %s", exc
            )
            self._cleanup_component_dir(export_dir)
            return False, 0

    def _export_quantized_text_encoder(
        self, cache_dir: Path
    ) -> Tuple[bool, int]:
        """Export the quantized T5 encoder to disk if present."""
        text_encoder = getattr(self._pipe, "text_encoder_2", None)
        if text_encoder is None:
            return False, 0

        export_dir = cache_dir / "text_encoder_2"
        export_dir.mkdir(parents=True, exist_ok=True)

        try:
            clean_state_dict, meta_count = self._collect_state_dict(
                text_encoder
            )

            if meta_count > 0:
                self.logger.warning(
                    "Skipped %d meta tensors in T5 encoder export - "
                    "skipping encoder cache export",
                    meta_count,
                )
                self._cleanup_component_dir(export_dir)
                return False, 0

            # Save config as JSON
            config_dict = self._config_to_json_serializable(
                text_encoder.config.to_dict()
            )
            with (export_dir / "config.json").open("w") as f:
                json.dump(config_dict, f, indent=2)

            # Save state dict
            from safetensors.torch import save_file

            save_file(
                clean_state_dict,
                str(export_dir / "model.safetensors"),
            )

            self.logger.info(
                "✓ Exported quantized T5 encoder to %s (%d tensors, %d meta skipped)",
                export_dir,
                len(clean_state_dict),
                meta_count,
            )
            return True, len(clean_state_dict)
        except Exception as exc:  # noqa: BLE001 - best effort
            self.logger.warning(
                "Failed to save quantized T5 encoder for cache: %s", exc
            )
            self._cleanup_component_dir(export_dir)
            return False, 0

    def _base_flux_model_path(self) -> str:
        """Return path to the base FLUX model directory."""
        return os.path.join(
            self.path_settings.base_path,
            "art/models/Flux.1 S/txt2img",
        )

    def _ensure_base_model_available(self, base_model: str) -> None:
        """Ensure base model files exist locally, otherwise trigger download."""
        should_download, download_info = (
            ModelFileChecker.should_trigger_download(
                model_path=base_model,
                model_type="art",
                version="Flux.1 S",
                pipeline_action="txt2img",
            )
        )
        if not should_download:
            return

        repo_id = download_info.get("repo_id")
        missing_files = download_info.get("missing_files", [])
        self.logger.info(
            "Missing %d base model files, triggering download from %s",
            len(missing_files),
            repo_id,
        )
        self.emit_signal(
            SignalCode.ART_MODEL_DOWNLOAD_REQUIRED,
            {
                "repo_id": repo_id,
                "model_path": base_model,
                "missing_files": missing_files,
                "version": "Flux.1 S",
                "pipeline_action": "txt2img",
            },
        )
        raise RuntimeError(
            f"Base model files missing from {base_model}, download triggered"
        )

    def _load_quantized_t5(
        self,
        base_model: str,
    ) -> Optional[T5EncoderModel]:
        """Load the T5 encoder with 4-bit quantization if possible."""
        self._announce_base_model_download(base_model)
        quant_config = self._t5_quantization_config()
        max_memory = self._quantized_t5_max_memory()

        encoder = self._attempt_quantized_t5(
            base_model, quant_config, max_memory
        )
        if encoder is None:
            return None
        self._log_t5_memory(encoder)
        return encoder

    def _attempt_quantized_t5(
        self,
        base_model: str,
        quant_config: TransformersBitsAndBytesConfig,
        max_memory: Dict[Any, str],
    ) -> Optional[T5EncoderModel]:
        """Try loading the quantized T5 encoder, returning None on failure."""
        try:
            return self._quantized_t5_from_pretrained(
                base_model, quant_config, max_memory
            )
        except Exception as exc:
            self.logger.warning(
                "Failed to quantize T5 encoder, loading in bfloat16: %s",
                exc,
            )
            return None

    def _announce_base_model_download(self, base_model: str) -> None:
        """Log and emit status for initial base-model download."""
        message = (
            f"Downloading base model from {base_model} (one-time download)..."
        )
        self.logger.info("Loading T5 text encoder with 4-bit quantization...")
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": message},
        )

    @staticmethod
    def _t5_quantization_config() -> TransformersBitsAndBytesConfig:
        """Return the BitsAndBytes config used for T5 quantization."""
        return TransformersBitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            llm_int8_enable_fp32_cpu_offload=True,
        )

    @staticmethod
    def _quantized_t5_max_memory() -> Dict[Any, str]:
        """Return conservative memory limits for the quantized T5 encoder."""
        return {0: "5GiB", "cpu": "30GiB"}

    def _quantized_t5_from_pretrained(
        self,
        base_model: str,
        quant_config: TransformersBitsAndBytesConfig,
        max_memory: Dict[Any, str],
    ) -> T5EncoderModel:
        """Instantiate the quantized T5 encoder."""
        return T5EncoderModel.from_pretrained(
            base_model,
            subfolder="text_encoder_2",
            quantization_config=quant_config,
            torch_dtype=torch.float16,
            device_map="auto",
            max_memory=max_memory,
        )

    def _log_t5_memory(self, encoder: T5EncoderModel) -> None:
        """Log memory footprint for the quantized T5 encoder."""
        memory_gb = encoder.get_memory_footprint() / (1024**3)
        self.logger.info(
            "✓ T5 text encoder loaded (4-bit) - Memory: %.2f GB",
            memory_gb,
        )

    def _load_base_pipeline_with_t5(
        self,
        base_model: str,
        pipeline_class: Any,
        data: Dict,
        text_encoder_2: Optional[T5EncoderModel],
    ) -> None:
        """Load the base pipeline, optionally injecting a quantized T5 encoder."""
        kwargs = {
            "torch_dtype": data.get("torch_dtype", torch.bfloat16),
            "local_files_only": AIRUNNER_LOCAL_FILES_ONLY,
        }
        if text_encoder_2 is not None:
            kwargs["text_encoder_2"] = text_encoder_2

        self._pipe = pipeline_class.from_pretrained(base_model, **kwargs)
        self.logger.info("✓ Base model loaded with quantized T5 text encoder")

    def _create_quantized_transformer(
        self,
        model_path: Path,
        base_model: str,
    ) -> FluxTransformer2DModel:
        """Instantiate a quantized transformer and load custom weights."""
        self._announce_transformer_load(model_path)
        state_dict = self._load_transformer_state_dict(model_path)
        quant_config = self._transformer_quantization_config()
        max_memory = self._transformer_max_memory()

        transformer = self._instantiate_quantized_transformer(
            os.path.join(base_model, "transformer"),
            quant_config,
            max_memory,
        )
        self.logger.info(
            "Loading custom weights into quantized transformer..."
        )
        transformer.load_state_dict(state_dict, strict=False)
        self._log_transformer_memory(transformer)
        return transformer

    def _announce_transformer_load(self, model_path: Path) -> None:
        """Log the start of transformer quantized loading."""
        self.logger.info(
            "Loading custom transformer from %s with 4-bit quantization...",
            model_path.name,
        )

    def _load_transformer_state_dict(
        self, model_path: Path
    ) -> Dict[str, torch.Tensor]:
        """Load the transformer weights from a safetensors file."""
        self.logger.info("Loading weights from safetensors file...")
        return load_file(str(model_path))

    @staticmethod
    def _transformer_quantization_config() -> DiffusersBitsAndBytesConfig:
        """Return quantization config for the Flux transformer."""
        return DiffusersBitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            llm_int8_enable_fp32_cpu_offload=True,
        )

    @staticmethod
    def _transformer_max_memory() -> Dict[Any, str]:
        """Return conservative memory limits for the Flux transformer."""
        return {0: "6GiB", "cpu": "30GiB"}

    def _instantiate_quantized_transformer(
        self,
        config_path: str,
        quant_config: DiffusersBitsAndBytesConfig,
        max_memory: Dict[Any, str],
    ) -> FluxTransformer2DModel:
        """Create a quantized transformer instance."""
        self.logger.info(
            "Creating quantized transformer (4-bit NF4) with CPU offload..."
        )
        return FluxTransformer2DModel.from_pretrained(
            config_path,
            quantization_config=quant_config,
            torch_dtype=torch.float16,
            device_map="auto",
            max_memory=max_memory,
            low_cpu_mem_usage=True,
        )

    def _log_transformer_memory(
        self, transformer: FluxTransformer2DModel
    ) -> None:
        """Log memory usage for the quantized transformer."""
        memory_gb = transformer.get_memory_footprint() / (1024**3)
        self.logger.info(
            "✓ Quantized transformer loaded - Memory footprint: %.2f GB",
            memory_gb,
        )

    def _finalize_quantized_unet(
        self,
        transformer: FluxTransformer2DModel,
    ) -> None:
        """Attach the quantized transformer and emit completion signal."""
        self._pipe.transformer = transformer
        self.logger.info("✓ Custom transformer loaded and swapped")
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": "✓ UNet-only model loaded: Transformer (4-bit) + T5 encoder (4-bit) with aggressive CPU offload"
            },
        )

    def _load_pretrained_model(
        self,
        model_path: Path,
        pipeline_class: Any,
        config_path: Optional[str],
        data: Dict,
    ) -> None:
        """Load FLUX model from pretrained directory."""
        kwargs = {**data}
        if config_path:
            kwargs["config"] = str(config_path)

        file_directory = (
            os.path.dirname(model_path)
            if os.path.isfile(model_path)
            else model_path
        )
        self._pipe = pipeline_class.from_pretrained(
            str(file_directory), **kwargs
        )

    def _set_pipe(self, config_path: str, data: Dict):
        """Load FLUX pipeline with automatic quantization."""
        pipeline_class = self._pipeline_class
        model_path = self.model_path

        if self._load_pipeline_from_cache(pipeline_class, model_path, data):
            return

        try:
            self._load_pipeline_by_type(
                model_path, pipeline_class, config_path, data
            )
        except Exception as exc:
            self.logger.error("Failed to load FLUX model: %s", exc)
            raise

        self._force_vae_fp32()

        if not str(model_path).lower().endswith(".gguf"):
            self._save_quantized_model(model_path)
