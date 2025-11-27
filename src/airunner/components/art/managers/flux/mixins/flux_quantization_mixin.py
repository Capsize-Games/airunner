"""FLUX quantization management mixin."""

from pathlib import Path
from typing import Any, Optional
import torch
from transformers import BitsAndBytesConfig

from airunner.enums import SignalCode


class FluxQuantizationMixin:
    """Handles all quantization-related operations for FLUX models."""

    def _get_quantization_config(self) -> Optional[BitsAndBytesConfig]:
        """Get 4-bit quantization configuration for FLUX models."""
        try:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            return quantization_config
        except Exception as e:
            self.logger.warning(f"Could not create quantization config: {e}")
            self.logger.warning(
                "Install bitsandbytes for 4-bit quantization: pip install bitsandbytes"
            )
            return None

    def _get_quantized_model_path(self, model_path: str) -> Path:
        """Get path where quantized model should be saved."""
        base_path = Path(model_path)
        parent = base_path.parent
        name = base_path.name
        quantized_path = parent / f"{name}_4bit_quantized"
        return quantized_path

    def _quantized_model_exists(self, model_path: str) -> bool:
        """Check if a FULL quantized pipeline exists on disk.
        
        This only returns True for full pipeline saves that can be loaded
        directly with pipeline_class.from_pretrained(). For component-only
        caches (e.g., just transformer), use _component_cache_exists() instead.
        """
        quantized_path = self._get_quantized_model_path(model_path)
        if not quantized_path.exists():
            return False

        # Check for model_index.json (required for full pipeline)
        if not (quantized_path / "model_index.json").exists():
            return False
            
        # A FULL pipeline save has multiple component directories beyond just transformer
        # Required components for a loadable Flux pipeline:
        transformer_dir = quantized_path / "transformer"
        scheduler_dir = quantized_path / "scheduler"
        
        has_transformer = transformer_dir.exists() and (
            list(transformer_dir.glob("*.safetensors")) or 
            list(transformer_dir.glob("*.bin"))
        )
        
        # The key distinction: a full pipeline has scheduler config, tokenizer, etc.
        # A component-only cache just has transformer
        has_scheduler = scheduler_dir.exists() and (scheduler_dir / "scheduler_config.json").exists()
        
        if has_transformer and has_scheduler:
            self.logger.info(f"Found existing FULL quantized pipeline at {quantized_path}")
            return True
        elif has_transformer:
            # This is a component-only cache, not a full pipeline
            self.logger.debug(f"Found component cache (not full pipeline) at {quantized_path}")
            return False
        
        # Legacy check: config.json at root with model files
        if (quantized_path / "config.json").exists():
            model_files = list(quantized_path.glob("*.safetensors")) + list(
                quantized_path.glob("*.bin")
            )
            if model_files:
                self.logger.info(f"Found existing quantized model at {quantized_path}")
                return True

        return False

    def _save_quantized_model(self, model_path: str) -> None:
        """Persist the quantized pipeline for faster future loads."""
        if self._should_skip_quantized_save(model_path):
            return
        self._persist_quantized_pipeline(
            self._get_quantized_model_path(model_path)
        )

    def _save_component_with_meta_handling(
        self, 
        component: Any, 
        save_path: Path, 
        component_name: str
    ) -> bool:
        """Save a model component, handling meta tensors gracefully.
        
        Uses multiple strategies to save the component:
        1. Try save_pretrained directly (works if no meta tensors)
        2. Try getting state dict via accelerate utilities
        3. Try extracting only non-meta tensors directly
        
        Returns True if save was successful.
        """
        import json
        import torch
        from safetensors.torch import save_file
        
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Strategy 1: Try save_pretrained directly
        try:
            component.save_pretrained(str(save_path), safe_serialization=True)
            self.logger.info("✓ %s saved via save_pretrained to %s", component_name, save_path)
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "meta" not in error_msg:
                self.logger.warning("save_pretrained failed for %s: %s", component_name, e)
            else:
                self.logger.debug("save_pretrained has meta tensors, trying alternatives")
        
        # Strategy 2: Try to gather weights using accelerate's disk offload utilities
        try:
            from accelerate import infer_auto_device_map, dispatch_model
            from accelerate.utils import get_balanced_memory, offload_state_dict
            
            # Try offloading state dict to disk first, then saving
            temp_dir = save_path / "_temp_offload"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                offload_state_dict(str(temp_dir), component.state_dict())
                
                # Now load it back and save properly
                from safetensors.torch import load_file as load_safetensors
                
                state_files = list(temp_dir.glob("*.safetensors"))
                if state_files:
                    combined_state = {}
                    for sf in state_files:
                        combined_state.update(load_safetensors(str(sf)))
                    
                    self._save_component_config(component, save_path)
                    save_file(combined_state, str(save_path / "model.safetensors"))
                    self.logger.info("✓ %s saved via offload strategy to %s", 
                                   component_name, save_path)
                    
                    # Cleanup temp
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return True
            finally:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except ImportError:
            self.logger.debug("accelerate offload utilities not available")
        except Exception as e:
            self.logger.debug("Offload strategy failed: %s", e)
            
        # Strategy 3: Try using accelerate's get_state_dict with offload_to_cpu
        try:
            from accelerate.utils import get_state_dict as accelerate_get_state_dict
            
            # Try with full offload
            state_dict = accelerate_get_state_dict(component, destination="cpu")
            
            # Check for meta tensors in result
            meta_count = sum(1 for t in state_dict.values() 
                           if hasattr(t, 'device') and t.device.type == "meta")
            
            if meta_count == 0 and len(state_dict) > 0:
                # Save config
                self._save_component_config(component, save_path)
                
                # Save state dict
                save_file(state_dict, str(save_path / "model.safetensors"))
                self.logger.info("✓ %s saved via accelerate to %s (%d tensors)", 
                               component_name, save_path, len(state_dict))
                return True
            else:
                self.logger.debug("accelerate.get_state_dict returned %d meta tensors out of %d", 
                                meta_count, len(state_dict))
        except ImportError:
            self.logger.debug("accelerate.utils.get_state_dict not available")
        except Exception as e:
            self.logger.debug("accelerate strategy failed: %s", e)
        
        # Strategy 4: Extract non-meta tensors directly from state_dict
        # This creates a partial save which may still be useful
        try:
            state_dict = component.state_dict()
            
            # Filter to only non-meta tensors on real devices
            clean_dict = {}
            meta_count = 0
            for name, tensor in state_dict.items():
                if not isinstance(tensor, torch.Tensor):
                    continue
                if tensor.device.type == "meta":
                    meta_count += 1
                    continue
                # Detach and move to CPU
                clean_dict[name] = tensor.detach().cpu()
            
            total = len(state_dict)
            saved = len(clean_dict)
            
            if saved > 0:
                self.logger.info(
                    "Extracted %d/%d tensors from %s (%d meta tensors skipped)",
                    saved, total, component_name, meta_count
                )
                
                # Save config
                self._save_component_config(component, save_path)
                
                # Save state dict
                save_file(clean_dict, str(save_path / "model.safetensors"))
                
                # Mark as partial if not all tensors saved
                if meta_count > 0:
                    partial_marker = save_path / "partial_save.json"
                    with partial_marker.open("w") as f:
                        json.dump({
                            "total_tensors": total,
                            "saved_tensors": saved,
                            "meta_tensors_skipped": meta_count,
                            "note": "This is a partial save - some tensors were on meta device"
                        }, f, indent=2)
                    self.logger.warning(
                        "⚠ %s partially saved (%d/%d tensors) - may need re-quantization",
                        component_name, saved, total
                    )
                else:
                    self.logger.info("✓ %s saved via direct extraction to %s", 
                                   component_name, save_path)
                return saved > 0
                
        except Exception as e:
            self.logger.debug("Direct extraction failed: %s", e)
        
        self.logger.warning("All save strategies failed for %s", component_name)
        return False
    
    def _save_component_config(self, component: Any, save_path: Path) -> None:
        """Save the component's config to JSON."""
        import json
        
        if not hasattr(component, 'config'):
            return
            
        config = component.config
        if hasattr(config, 'to_dict'):
            config_dict = config.to_dict()
        elif hasattr(config, '__dict__'):
            config_dict = dict(config.__dict__)
        else:
            try:
                config_dict = dict(config)
            except Exception:
                return
        
        # Convert torch dtypes to strings
        def convert_types(obj):
            import torch
            if isinstance(obj, torch.dtype):
                return str(obj).replace("torch.", "")
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_types(v) for v in obj]
            return obj
        
        config_dict = convert_types(config_dict)
        
        with (save_path / "config.json").open("w") as f:
            json.dump(config_dict, f, indent=2)

    def _persist_quantized_pipeline(self, quantized_path: Path) -> None:
        """Save the pipeline and surface status updates."""
        import json
        
        try:
            self._announce_quantized_save(
                f"Saving quantized FLUX model to {quantized_path}"
            )
            quantized_path.mkdir(parents=True, exist_ok=True)
            
            # Save each component individually to handle meta tensors better
            components_saved = []
            
            # Try saving transformer first (most important)
            if hasattr(self._pipe, "transformer") and self._pipe.transformer is not None:
                transformer_path = quantized_path / "transformer"
                if self._save_component_with_meta_handling(
                    self._pipe.transformer, transformer_path, "transformer"
                ):
                    components_saved.append("transformer")
            
            # Try saving text_encoder_2 (T5)
            if hasattr(self._pipe, "text_encoder_2") and self._pipe.text_encoder_2 is not None:
                t5_path = quantized_path / "text_encoder_2"
                if self._save_component_with_meta_handling(
                    self._pipe.text_encoder_2, t5_path, "text_encoder_2"
                ):
                    components_saved.append("text_encoder_2")
            
            if components_saved:
                self._announce_quantized_save(
                    f"✓ Quantized components ({', '.join(components_saved)}) saved to {quantized_path}"
                )
                # Save a marker file to indicate this is a valid cache
                marker_path = quantized_path / "model_index.json"
                marker_data = {
                    "_class_name": "FluxPipeline",
                    "_diffusers_version": "0.31.0",
                    "components_cached": components_saved,
                }
                with marker_path.open("w") as f:
                    json.dump(marker_data, f, indent=2)
            else:
                self._announce_quantized_save(
                    "⚠ Could not save quantized model (meta tensors) - will re-quantize on next load"
                )
                    
        except Exception as exc:  # noqa: BLE001 - saving is optional
            self.logger.error(
                "Failed to save quantized model at %s: %s",
                quantized_path,
                exc,
            )
            self._announce_quantized_save(
                f"⚠ Failed to save quantized model: {exc}"
            )

    def _should_skip_quantized_save(self, model_path: str) -> bool:
        """Return True if saving a quantized model is unnecessary."""
        if str(model_path).lower().endswith(".gguf"):
            self.logger.info(
                "Skipping save for GGUF model (already quantized)"
            )
            return True

        # Skip if quantized cache already exists (either full pipeline or component cache)
        quantized_path = self._get_quantized_model_path(model_path)
        if self._quantized_model_exists(model_path):
            self.logger.info(
                "Skipping save - full quantized pipeline already exists at %s",
                quantized_path
            )
            return True
        
        # Check for component cache (transformer directory with model files)
        transformer_dir = quantized_path / "transformer"
        if transformer_dir.exists() and (
            list(transformer_dir.glob("*.safetensors")) or 
            list(transformer_dir.glob("*.bin"))
        ):
            self.logger.info(
                "Skipping save - component cache already exists at %s",
                quantized_path
            )
            return True

        if self._pipe is not None:
            return False

        self.logger.error("Cannot save quantized model: pipeline is None")
        return True

    def _announce_quantized_save(self, message: str) -> None:
        """Log and emit a status message for quantized saves."""
        self.logger.info(message)
        self.emit_signal(SignalCode.UPDATE_DOWNLOAD_LOG, {"message": message})

    def _load_or_quantize_text_encoder(
        self,
        model_class: Any,
        source_dir: Path,
        cache_dir: Path,
        quantization_config: BitsAndBytesConfig,
    ) -> Any:
        """Load cached quantized text encoder or quantize and cache it."""
        cached_model = self._load_cached_encoder(
            model_class, cache_dir, quantization_config
        )
        if cached_model is not None:
            return cached_model

        model = self._quantize_encoder(
            model_class, source_dir, quantization_config
        )
        self._cache_quantized_encoder(model, cache_dir)
        return model

    def _load_cached_encoder(
        self,
        model_class: Any,
        cache_dir: Path,
        quantization_config: BitsAndBytesConfig,
    ) -> Optional[Any]:
        """Load a previously cached quantized encoder if available."""
        if not self._has_cached_encoder(cache_dir):
            return None

        try:
            return self._load_cached_encoder_from_disk(
                model_class, cache_dir, quantization_config
            )
        except Exception as exc:  # noqa: BLE001 - informational
            self._log_cached_encoder_failure(cache_dir, exc)
            return None

    @staticmethod
    def _has_cached_encoder(cache_dir: Path) -> bool:
        """Return True when a cached encoder with config exists."""
        return cache_dir.exists() and (cache_dir / "config.json").exists()

    def _load_cached_encoder_from_disk(
        self,
        model_class: Any,
        cache_dir: Path,
        quantization_config: BitsAndBytesConfig,
    ) -> Any:
        """Return cached encoder from disk."""
        self.logger.info("Loading cached quantized model from %s", cache_dir)
        return model_class.from_pretrained(
            str(cache_dir),
            quantization_config=quantization_config,
            device_map="auto",
            local_files_only=True,
        )

    def _log_cached_encoder_failure(
        self, cache_dir: Path, exc: Exception
    ) -> None:
        """Log cache load failure while keeping refactor readable."""
        self.logger.warning(
            "Failed to load cached model from %s: %s. Quantizing from source instead.",
            cache_dir,
            exc,
        )

    def _quantize_encoder(
        self,
        model_class: Any,
        source_dir: Path,
        quantization_config: BitsAndBytesConfig,
    ) -> Any:
        """Quantize an encoder from its source directory."""
        self.logger.info("Quantizing model from %s", source_dir)
        return model_class.from_pretrained(
            str(source_dir),
            quantization_config=quantization_config,
            device_map="auto",
            local_files_only=True,
        )

    def _cache_quantized_encoder(self, model: Any, cache_dir: Path) -> None:
        """Persist a quantized encoder for faster future loads."""
        try:
            cache_dir.parent.mkdir(parents=True, exist_ok=True)
            self.logger.info("Saving quantized model to %s", cache_dir)
            model.save_pretrained(str(cache_dir))
            self.logger.info(
                "✓ Quantized model cached for faster future loads"
            )
        except Exception as exc:  # noqa: BLE001 - cache failures are non-fatal
            self.logger.warning(
                "Failed to cache quantized model at %s: %s", cache_dir, exc
            )
