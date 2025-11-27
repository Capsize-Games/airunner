"""FLUX pipeline loading mixin."""

import gc
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

try:
    from accelerate.hooks import remove_hook_from_module
except ImportError:
    remove_hook_from_module = None

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


def _clear_gpu_memory() -> None:
    """Aggressively clear GPU memory.
    
    Call this between loading stages to minimize peak VRAM usage.
    """
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    gc.collect()  # Second pass for released references


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

    def _materialize_offloaded_module(
        self, module: torch.nn.Module
    ) -> torch.nn.Module:
        """Materialize a module that may have offloaded hooks.
        
        When using device_map="auto" with accelerate, modules get AlignDevicesHook
        attached which lazily moves tensors. We need to remove these hooks and
        force the tensors to CPU before we can save them.
        """
        if remove_hook_from_module is None:
            return module
            
        try:
            # Remove accelerate hooks that keep tensors on meta device
            remove_hook_from_module(module, recurse=True)
            
            # Move the entire module to CPU to materialize all tensors
            module = module.to("cpu")
            
            self.logger.debug("Successfully materialized offloaded module to CPU")
            return module
        except Exception as exc:
            self.logger.debug(
                "Could not materialize module: %s", exc
            )
            return module

    def _collect_state_dict(
        self, module: torch.nn.Module
    ) -> Tuple[Dict[str, torch.Tensor], int]:
        """Return CPU state dict along with the number of meta tensors skipped.
        
        This method attempts multiple strategies to extract the state dict:
        1. Use accelerate's get_state_dict with cpu destination
        2. Remove hooks and move to CPU to materialize lazy tensors  
        3. Fall back to standard state_dict()
        """
        raw_state_dict: Optional[Dict[str, torch.Tensor]] = None
        
        # Strategy 1: Use accelerate's get_state_dict
        if _accelerate_get_state_dict is not None:
            try:
                raw_state_dict = _accelerate_get_state_dict(
                    module, destination="cpu"
                )
                # Check if we got meta tensors
                meta_in_result = sum(
                    1 for t in raw_state_dict.values() 
                    if isinstance(t, torch.Tensor) and t.device.type == "meta"
                )
                if meta_in_result > 0:
                    self.logger.debug(
                        "accelerate.get_state_dict returned %d meta tensors, "
                        "trying hook removal strategy",
                        meta_in_result,
                    )
                    raw_state_dict = None
            except Exception as exc:  # noqa: BLE001 - best effort fallback
                self.logger.debug(
                    "accelerate.get_state_dict failed (%s); trying hook removal",
                    exc,
                )

        # Strategy 2: Remove hooks and materialize on CPU
        if raw_state_dict is None:
            try:
                # Make a copy reference before modifying
                materialized = self._materialize_offloaded_module(module)
                raw_state_dict = materialized.state_dict()
            except Exception as exc:
                self.logger.debug(
                    "Hook removal strategy failed (%s); using standard state_dict",
                    exc,
                )

        # Strategy 3: Standard state_dict (may have meta tensors)
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
        """Ensure cached module has fully materialized tensors and expected count.
        
        NOTE: This validation is non-destructive - it does NOT move modules to CPU.
        We only check that the module loaded successfully and has parameters.
        """
        if module is None:
            return False

        # Simple validation: check module has parameters and they're not on meta device
        try:
            first_param = next(module.parameters(), None)
            if first_param is None:
                self.logger.warning(
                    "Cached %s has no parameters; deleting cache",
                    module_name,
                )
                self._cleanup_component_dir(component_dir)
                return False
            
            if first_param.device.type == "meta":
                self.logger.warning(
                    "Cached %s has meta tensors; deleting cache",
                    module_name,
                )
                self._cleanup_component_dir(component_dir)
                return False
                
            self.logger.debug(
                "Validated %s - has parameters on device %s",
                module_name,
                first_param.device,
            )
            return True
        except Exception as e:
            self.logger.warning(
                "Failed to validate cached %s: %s; deleting cache",
                module_name,
                e,
            )
            self._cleanup_component_dir(component_dir)
            return False

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
        """Load a UNet-only checkpoint, preferring GGUF format.
        
        Memory optimization: This method prefers GGUF format which loads
        pre-quantized weights directly without VRAM spikes. Falls back to
        BitsAndBytes if GGUF is not available.
        
        Loading priority:
        1. Try GGUF version (no VRAM spike, loads pre-quantized)
        2. Try cached quantized pipeline
        3. Fall back to BitsAndBytes (causes temporary VRAM spike)
        """
        # Priority 1: Try GGUF format (best for VRAM)
        if self._try_load_as_gguf(model_path, pipeline_class):
            return
        
        # Priority 2: Try cached quantized pipeline
        if self._try_load_quantized_pipeline(model_path, pipeline_class, data):
            return

        # Priority 3: Fall back to BitsAndBytes quantization
        self.logger.info("Using BitsAndBytes quantization (will cause brief VRAM spike)")
        self._load_with_bitsandbytes(model_path, pipeline_class, data)
    
    def _try_load_as_gguf(
        self,
        model_path: Path,
        pipeline_class: Any,
    ) -> bool:
        """Try to load or convert to GGUF format.
        
        Returns True if successfully loaded as GGUF.
        """
        # Check if we have GGUF conversion capability
        if not hasattr(self, '_should_use_gguf') or not self._should_use_gguf(str(model_path)):
            self.logger.debug("GGUF not available for this model")
            return False
        
        # Get or create GGUF file
        gguf_path = self._get_or_create_gguf(str(model_path))
        if gguf_path is None:
            self.logger.debug("GGUF conversion failed or not possible")
            return False
        
        # Load using GGUF
        try:
            self.logger.info(f"Loading GGUF model: {gguf_path}")
            self._load_gguf_model(gguf_path, pipeline_class)
            self.logger.info("✓ Loaded model via GGUF (no VRAM spike)")
            return True
        except Exception as e:
            self.logger.warning(f"GGUF loading failed: {e}. Falling back to BitsAndBytes.")
            return False
    
    def _load_with_bitsandbytes(
        self,
        model_path: Path,
        pipeline_class: Any,
        data: Dict,
    ) -> None:
        """Load using BitsAndBytes quantization (fallback method).
        
        This causes a temporary VRAM spike to ~99% during quantization.
        """
        base_model = self._base_flux_model_path()
        self._current_flux_base_model_path = base_model
        self._ensure_base_model_available(base_model)
        
        # Stage 1: Load T5 to CPU (quantization happens during load)
        text_encoder_2 = self._load_quantized_t5(base_model)
        
        # Stage 2: Load base pipeline with T5 (no transformer yet)
        self._load_base_pipeline_with_t5(
            base_model, pipeline_class, data, text_encoder_2
        )

        # Stage 3: Load and quantize transformer
        transformer = self._create_quantized_transformer(
            model_path, base_model
        )
        
        # Stage 4: Swap transformer into pipeline (frees old transformer memory)
        self._finalize_quantized_unet(transformer)

    def _try_load_quantized_pipeline(
        self,
        model_path: Path,
        pipeline_class: Any,
        data: Dict,
    ) -> bool:
        """Return True if an on-disk quantized pipeline was loaded."""
        quantized_path = self._get_quantized_model_path(str(model_path))
        self.logger.debug(
            "Checking for quantized model at %s", quantized_path
        )
        
        # First try to load a full quantized pipeline if it exists
        full_pipeline_exists = self._quantized_model_exists(str(model_path))
        component_cache_exists = self._component_cache_exists(quantized_path)
        
        self.logger.info(
            "Quantized model check: full_pipeline=%s, component_cache=%s",
            full_pipeline_exists, component_cache_exists
        )
        
        if full_pipeline_exists:
            self.logger.info(
                "Found existing full quantized pipeline at %s, loading directly...",
                quantized_path,
            )
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": "Loading pre-quantized pipeline from disk..."},
            )
            try:
                self._pipe = pipeline_class.from_pretrained(
                    str(quantized_path),
                    torch_dtype=data.get("torch_dtype", torch.bfloat16),
                    local_files_only=True,
                )
                self.logger.info("✓ Pre-quantized full pipeline loaded from disk")
                return True
            except Exception as e:
                self.logger.warning(
                    "Failed to load full pipeline from %s: %s. "
                    "Falling back to component cache...",
                    quantized_path, e
                )

        # Fall back to component cache (e.g., just transformer saved)
        if component_cache_exists:
            return self._load_pipeline_from_component_cache(
                quantized_path, pipeline_class, data
            )
        
        self.logger.info("No quantized cache found, will quantize from scratch")
        return False

    def _component_cache_exists(self, quantized_path: Path) -> bool:
        """Return True if a component-level quantized cache exists."""
        # Check for direct transformer save (new format)
        transformer_dir = quantized_path / "transformer"
        if transformer_dir.exists() and (
            list(transformer_dir.glob("*.safetensors")) or 
            list(transformer_dir.glob("*.bin"))
        ):
            # Check for model_index.json marker
            if (quantized_path / "model_index.json").exists():
                return True
        
        # Check for components subdirectory format (legacy)
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
        self.logger.info(
            "Attempting to load pipeline from component cache at %s",
            quantized_path,
        )
        
        # Check for direct transformer save first (new format)
        transformer_dir = quantized_path / "transformer"
        has_direct_format = transformer_dir.exists() and (
            list(transformer_dir.glob("*.safetensors")) or 
            list(transformer_dir.glob("*.bin"))
        )
        
        # Check for legacy manifest format
        manifest = self._read_component_manifest(quantized_path)
        has_manifest_format = manifest.get("schema") == "component-cache/v2"
        
        if not has_direct_format and not has_manifest_format:
            self.logger.info(
                "No valid component cache found at %s",
                quantized_path,
            )
            return False
        
        if has_manifest_format:
            transformer_manifest = manifest.get("transformer", {})
            if not transformer_manifest.get("saved"):
                if not has_direct_format:
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

        # Try loading T5 encoder from cache, fall back to fresh quantized load
        text_manifest = manifest.get("text_encoder_2", {}) if has_manifest_format else {}
        cached_t5 = None
        t5_dir = quantized_path / "text_encoder_2"
        t5_components_dir = quantized_path / "components" / "text_encoder_2"
        
        if t5_dir.exists() or (text_manifest.get("saved") and t5_components_dir.exists()):
            cached_t5 = self._load_cached_quantized_t5(quantized_path)
            validation_dir = t5_dir if t5_dir.exists() else t5_components_dir
            if cached_t5 and not self._validate_cached_module(
                "text_encoder_2",
                cached_t5,
                text_manifest.get("tensor_count", 0),
                validation_dir,
            ):
                cached_t5 = None
        
        # If no cached T5 available, load fresh with quantization
        if cached_t5 is None:
            self.logger.info("Loading fresh quantized T5 encoder...")
            cached_t5 = self._load_quantized_t5(base_model)

        # Skip loading the base transformer since we'll use the cached quantized one
        # This saves ~6-12GB of RAM
        self._load_base_pipeline_with_t5(
            base_model, pipeline_class, data, cached_t5, skip_transformer=True
        )

        transformer = self._load_cached_quantized_transformer(quantized_path)
        
        # Determine validation directory
        transformer_components_dir = quantized_path / "components" / "transformer"
        validation_dir = transformer_dir if transformer_dir.exists() else transformer_components_dir
        
        transformer_manifest = manifest.get("transformer", {}) if has_manifest_format else {}
        if not self._validate_cached_module(
            "transformer",
            transformer,
            transformer_manifest.get("tensor_count", 0),
            validation_dir,
        ):
            self.logger.warning(
                "Cached transformer at %s is invalid; re-quantizing",
                quantized_path,
            )
            self._cleanup_component_dir(quantized_path / "components")
            self._cleanup_component_dir(quantized_path / "transformer")
            return False

        self._finalize_quantized_unet(transformer)
        self.logger.info(
            "✓ Loaded pipeline from component cache at %s", quantized_path
        )
        return True

    def _load_cached_quantized_t5(
        self, quantized_path: Path
    ) -> Optional[T5EncoderModel]:
        """Load a cached quantized T5 encoder if present.
        
        NOTE: BitsAndBytes quantized models cannot be saved/loaded properly.
        save_pretrained() on a quantized model saves dequantized full-precision
        weights. So we skip T5 caching entirely and always load fresh.
        """
        # T5 caching doesn't work with BitsAndBytes - skip it
        # The "cached" files are actually full-precision and ~9GB
        self.logger.info(
            "Skipping T5 cache (BitsAndBytes models can't be cached properly)"
        )
        return None

    def _load_cached_quantized_transformer(
        self, quantized_path: Path
    ) -> FluxTransformer2DModel:
        """Load cached transformer from disk and quantize.
        
        NOTE: BitsAndBytes save_pretrained() saves DEQUANTIZED weights.
        This means we must re-quantize on load, causing a temporary VRAM spike.
        This is a known limitation of BitsAndBytes - the only way to avoid it
        is to use GGUF format which stores pre-quantized weights.
        
        Memory optimization: Clear GPU cache before loading.
        """
        # Clear GPU memory before loading transformer
        _clear_gpu_memory()
        self.logger.debug("Cleared GPU cache before cached transformer loading")
        
        # Check both possible locations: direct and components subdirectory
        cache_dir = quantized_path / "transformer"
        if not cache_dir.exists():
            cache_dir = quantized_path / "components" / "transformer"
        self.logger.info(
            "Loading transformer from %s (will quantize - BitsAndBytes limitation)", 
            cache_dir
        )
        
        # Must use quantization_config because BitsAndBytes saves dequantized weights
        quant_config = self._transformer_quantization_config()
        model = FluxTransformer2DModel.from_pretrained(
            str(cache_dir),
            quantization_config=quant_config,
            torch_dtype=torch.float16,
            device_map={"": 0},  # Force to GPU 0
            low_cpu_mem_usage=True,
            local_files_only=True,
        )
        self.logger.info("✓ Transformer loaded and quantized to GPU")
        return model

    def _handle_quantized_save_failure(
        self, quantized_path: Path, exc: Exception
    ) -> None:
        """Fallback to component-level cache when pipeline save fails."""
        message = str(exc).lower()
        if "meta tensor" not in message:
            return

        self.logger.debug(
            "Attempting component-level cache fallback for quantized model"
        )
        try:
            self._save_quantized_component_cache(quantized_path)
        except Exception as cache_exc:  # noqa: BLE001 - best effort
            # Component cache failure for meta tensors is expected and doesn't
            # impact model functionality - only affects subsequent load times
            if "meta tensor" in str(cache_exc).lower():
                self.logger.debug(
                    "Component cache skipped - model will re-quantize on next load"
                )
            else:
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
            # First try using save_pretrained which handles bitsandbytes models properly
            try:
                self.logger.info(
                    "Saving quantized transformer using save_pretrained..."
                )
                transformer.save_pretrained(
                    str(export_dir), 
                    safe_serialization=True
                )
                # Verify save worked by checking for essential files
                if (export_dir / "config.json").exists():
                    model_files = list(export_dir.glob("*.safetensors"))
                    if model_files:
                        self.logger.info(
                            "✓ Exported quantized transformer to %s using save_pretrained",
                            export_dir,
                        )
                        return True, len(model_files)
            except Exception as save_exc:
                self.logger.debug(
                    "save_pretrained failed (%s), trying manual state dict export",
                    save_exc,
                )
            
            # Fallback to manual state dict export
            clean_state_dict, meta_count = self._collect_state_dict(
                transformer
            )

            if meta_count > 0 and len(clean_state_dict) == 0:
                self.logger.debug(
                    "Skipping transformer cache export - all %d tensors are meta "
                    "(expected for single-file quantized loads)",
                    meta_count,
                )
                self._cleanup_component_dir(export_dir)
                return False, 0
            
            if meta_count > 0:
                self.logger.warning(
                    "Exporting partial transformer cache - %d meta tensors skipped, "
                    "%d tensors saved. Model may need re-quantization on next load.",
                    meta_count,
                    len(clean_state_dict),
                )

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
        """Export the quantized T5 encoder to disk if present.
        
        NOTE: BitsAndBytes quantized models cannot be saved properly.
        save_pretrained() saves dequantized full-precision weights (~9GB).
        We skip T5 caching entirely to avoid wasting disk space and loading
        unquantized models.
        """
        self.logger.info(
            "Skipping T5 encoder cache (BitsAndBytes models can't be saved quantized)"
        )
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
        """Instantiate the quantized T5 encoder.
        
        CRITICAL: Load T5 to CPU initially for manual offload strategy.
        T5 will be moved to GPU only during prompt encoding, then back to CPU
        to free VRAM for the transformer. This avoids accelerate hook RAM leaks.
        
        Memory optimization: Clear GPU cache before loading to ensure maximum
        available VRAM for the quantization process.
        """
        # Clear GPU memory before T5 quantization to prevent OOM during loading
        _clear_gpu_memory()
        self.logger.debug("Cleared GPU cache before T5 loading")
        
        # Load to CPU - we'll manually move to GPU during prompt encoding
        return T5EncoderModel.from_pretrained(
            base_model,
            subfolder="text_encoder_2",
            quantization_config=quant_config,
            torch_dtype=torch.float16,
            device_map={"": "cpu"},  # Start on CPU for manual offload
            low_cpu_mem_usage=True,
        )

    def _log_t5_memory(self, encoder: T5EncoderModel) -> None:
        """Log memory footprint for the quantized T5 encoder."""
        memory_gb = encoder.get_memory_footprint() / (1024**3)
        self.logger.info(
            "✓ T5 text encoder loaded to CPU (4-bit) - Memory: %.2f GB",
            memory_gb,
        )

    def _load_base_pipeline_with_t5(
        self,
        base_model: str,
        pipeline_class: Any,
        data: Dict,
        text_encoder_2: Optional[T5EncoderModel],
        skip_transformer: bool = False,
    ) -> None:
        """Load the base pipeline, optionally injecting a quantized T5 encoder.
        
        Args:
            skip_transformer: If True, don't load the transformer (we'll load
                it separately from cache). This saves significant RAM.
        
        Memory optimization: Clear GPU cache before loading to ensure maximum
        available VRAM. Also use low_cpu_mem_usage to reduce memory footprint.
        """
        # Clear GPU memory before pipeline loading
        _clear_gpu_memory()
        self.logger.debug("Cleared GPU cache before base pipeline loading")
        
        kwargs = {
            "torch_dtype": data.get("torch_dtype", torch.bfloat16),
            "local_files_only": AIRUNNER_LOCAL_FILES_ONLY,
            "low_cpu_mem_usage": True,  # Reduce memory during loading
        }
        if text_encoder_2 is not None:
            kwargs["text_encoder_2"] = text_encoder_2
        if skip_transformer:
            # Pass None to skip loading the transformer - we'll load it from cache
            kwargs["transformer"] = None
            self.logger.info("Skipping base transformer load (will use cached quantized version)")

        self._pipe = pipeline_class.from_pretrained(base_model, **kwargs)
        if skip_transformer:
            self.logger.info("✓ Base model loaded (no transformer) with quantized T5 text encoder")
        else:
            self.logger.info("✓ Base model loaded with quantized T5 text encoder")

    def _create_quantized_transformer(
        self,
        model_path: Path,
        base_model: str,
    ) -> FluxTransformer2DModel:
        """Instantiate a quantized transformer and load custom weights.
        
        Loads directly to GPU with device_map={"": 0}.
        
        Memory optimization: Clear GPU cache before loading transformer to
        ensure maximum available VRAM.
        """
        # Clear GPU memory before transformer loading to prevent OOM
        _clear_gpu_memory()
        self.logger.debug("Cleared GPU cache before transformer loading")
        
        self._announce_transformer_load(model_path)
        state_dict = self._load_transformer_state_dict(model_path)
        quant_config = self._transformer_quantization_config()
        max_memory = self._transformer_max_memory()
        config_path = os.path.join(base_model, "transformer")
        
        # Check if we need to save the quantized model
        quantized_path = self._get_quantized_model_path(str(model_path))
        need_to_save = not self._quantized_model_exists(str(model_path))
        
        if need_to_save:
            # Load with quantization, save to cache, then return directly
            transformer = self._load_and_save_for_cache(
                config_path, quant_config, state_dict, quantized_path
            )
            if transformer is not None:
                # Successfully saved - return the model directly (no need to reload)
                self._log_transformer_memory(transformer)
                return transformer
        
        # Normal path: load to GPU for inference
        transformer = self._instantiate_quantized_transformer(
            config_path,
            quant_config,
            max_memory,
        )
        self.logger.info(
            "Loading custom weights into quantized transformer..."
        )
        transformer.load_state_dict(state_dict, strict=False)
        
        # Free state_dict memory immediately after loading
        del state_dict
        gc.collect()
        
        self._log_transformer_memory(transformer)
        return transformer

    def _load_and_save_for_cache(
        self,
        config_path: str,
        quant_config: DiffusersBitsAndBytesConfig,
        state_dict: Dict[str, torch.Tensor],
        quantized_path: Path,
    ) -> Optional[FluxTransformer2DModel]:
        """Load transformer with quantization, save, then return for use.
        
        Strategy: Load WITH quantization to save the quantized weights,
        then return the model for use (avoiding a second load).
        
        Memory optimization: Clear GPU cache before loading.
        """
        try:
            # Clear GPU memory before loading
            _clear_gpu_memory()
            self.logger.debug("Cleared GPU cache before transformer caching")
            
            self.logger.info(
                "Loading transformer with quantization for caching..."
            )
            # Load with quantization directly to GPU
            transformer = FluxTransformer2DModel.from_pretrained(
                config_path,
                quantization_config=quant_config,
                torch_dtype=torch.float16,
                device_map={"": 0},  # Force to GPU 0
                low_cpu_mem_usage=True,
            )
            self.logger.info("Loading custom weights into quantized transformer...")
            transformer.load_state_dict(state_dict, strict=False)
            
            # Free the state_dict memory now that it's loaded
            del state_dict
            gc.collect()
            
            # Now save the quantized weights
            transformer_path = quantized_path / "transformer"
            transformer_path.mkdir(parents=True, exist_ok=True)
            self.logger.info("Saving quantized transformer to %s", transformer_path)
            transformer.save_pretrained(str(transformer_path), safe_serialization=True)
            
            # Create marker file
            import json
            marker_path = quantized_path / "model_index.json"
            marker_data = {
                "_class_name": "FluxPipeline",
                "_diffusers_version": "0.31.0",
                "components_cached": ["transformer"],
            }
            with marker_path.open("w") as f:
                json.dump(marker_data, f, indent=2)
            
            self.logger.info("✓ Quantized transformer cached successfully")
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": "✓ Quantized transformer cached for faster future loads"}
            )
            return transformer
            
        except Exception as e:
            self.logger.warning(
                "Failed to cache transformer (will load directly): %s", e
            )
            return None

    def _load_from_cache(
        self,
        quantized_path: Path,
        quant_config: DiffusersBitsAndBytesConfig,
        max_memory: Dict[Any, str],
    ) -> FluxTransformer2DModel:
        """Load transformer from cache and quantize.
        
        NOTE: BitsAndBytes save_pretrained() saves DEQUANTIZED weights.
        We must re-quantize on load, causing a temporary VRAM spike.
        """
        transformer_path = quantized_path / "transformer"
        self.logger.info(
            "Loading transformer from %s (will quantize)", transformer_path
        )
        
        # Clear GPU memory before loading
        _clear_gpu_memory()
        
        transformer = FluxTransformer2DModel.from_pretrained(
            str(transformer_path),
            quantization_config=quant_config,
            torch_dtype=torch.float16,
            device_map={"": 0},  # Force to GPU 0
            low_cpu_mem_usage=True,
        )
        
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
        """Load the transformer weights from a safetensors file.
        
        Memory optimization: Clear GPU cache before loading weights to ensure
        maximum available memory. Safetensors uses mmap by default which is
        already memory efficient.
        """
        # Clear GPU memory before loading large state dict
        _clear_gpu_memory()
        
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
            "Creating quantized transformer (4-bit NF4)..."
        )
        # Load directly to GPU
        return FluxTransformer2DModel.from_pretrained(
            config_path,
            quantization_config=quant_config,
            torch_dtype=torch.float16,
            device_map={"": 0},  # Force to GPU 0
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
        """Attach the quantized transformer and emit completion signal.
        
        CRITICAL: Explicitly delete the old transformer to free memory.
        Just reassigning the reference doesn't free the GPU/CPU memory.
        
        Memory optimization: Aggressively clear both GPU and CPU memory
        after swapping transformers to ensure clean state.
        """
        # Get reference to old transformer before replacing
        old_transformer = getattr(self._pipe, 'transformer', None)
        
        # Replace with new quantized transformer
        self._pipe.transformer = transformer
        
        # Explicitly delete old transformer to free memory
        if old_transformer is not None:
            self.logger.debug("Deleting old base transformer to free memory")
            # Try to move to CPU first if on GPU (helps with some memory issues)
            try:
                if hasattr(old_transformer, 'to'):
                    old_transformer.to('cpu')
            except Exception:
                pass
            del old_transformer
        
        # Aggressive memory cleanup
        _clear_gpu_memory()
        
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
