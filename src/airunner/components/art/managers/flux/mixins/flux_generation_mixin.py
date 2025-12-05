"""FLUX generation preparation mixin."""

import gc
from typing import Dict, Any
import torch
from airunner.components.application.exceptions import (
    InterruptedException,
)
from airunner.utils.memory import clear_memory
from airunner.utils.settings.get_qsettings import get_qsettings


class FluxGenerationMixin:
    """Handles generation data preparation for FLUX models."""

    def _prepare_pipe_data(self) -> Dict[str, Any]:
        """Prepare pipeline initialization parameters with FLUX optimizations.

        Note: Quantization only works with from_pretrained (directory loads).
        Single-file loads (.safetensors) use bfloat16, but UNet-only checkpoints
        will have their custom transformer quantized after loading.
        """
        data = super()._prepare_pipe_data()

        data["torch_dtype"] = torch.bfloat16

        is_gguf = self.model_path and str(self.model_path).lower().endswith(
            ".gguf"
        )
        is_single_file = self.use_from_single_file

        if not is_gguf and not is_single_file:
            quantization_config = self._get_quantization_config()
            if quantization_config:
                data["quantization_config"] = quantization_config
                self.logger.info("4-bit quantization enabled for FLUX model")
        elif is_single_file:
            # For single-file loads, still pass quantization_config
            # It will be applied after loading for UNet-only checkpoints
            quantization_config = self._get_quantization_config()
            if quantization_config:
                data["quantization_config"] = quantization_config
                self.logger.info(
                    "Single-file load detected - using bfloat16 (quantization applied to custom transformer if UNet-only)"
                )
            else:
                self.logger.info("Single-file load detected - using bfloat16")
        else:
            self.logger.info(
                "GGUF model detected - skipping additional quantization"
            )

        return data

    def _load_prompt_embeds(self):
        """Load and prepare prompt embeddings for FLUX."""
        self._current_prompt = self.prompt
        self._current_negative_prompt = self.negative_prompt
        self.logger.debug("FLUX prompt handling (no pre-computed embeddings)")

    def _prepare_data(self, active_rect=None) -> Dict:
        """Prepare generation data for FLUX pipeline."""
        data = super()._prepare_data(active_rect)
        self._strip_flux_incompatible_params(data)
        self._enforce_flux_guidance(data)
        data["max_sequence_length"] = 512
        self._log_flux_generation_params(data)
        return data

    def _strip_flux_incompatible_params(self, data: Dict) -> None:
        """Remove parameters the FLUX pipeline cannot consume."""
        for key in ("clip_skip", "strength", "negative_prompt"):
            data.pop(key, None)

    def _enforce_flux_guidance(self, data: Dict) -> None:
        """Clamp guidance to the safe FLUX range."""
        guidance_scale = data.get("guidance_scale", 3.5)
        if guidance_scale <= 5.0:
            return

        self.logger.warning(
            "FLUX guidance_scale %.2f too high, clamping to 3.5. "
            "FLUX uses lower guidance than SD (recommended: 3.5 for dev, 0.0 for schnell)",
            guidance_scale,
        )
        data["guidance_scale"] = 3.5

    def _log_flux_generation_params(self, data: Dict) -> None:
        """Log core generation parameters for debugging."""
        debug_fields = {
            "prompt": data.get("prompt", "MISSING!"),
            "guidance_scale": data.get("guidance_scale", "MISSING!"),
            "steps": data.get("num_inference_steps", "MISSING!"),
            "size": f"{data.get('width')}x{data.get('height')}",
            "max_sequence_length": data.get("max_sequence_length", "MISSING!"),
        }
        self.logger.info(
            "[FLUX DEBUG] Keys: %s | Values: %s",
            list(data.keys()),
            debug_fields,
        )

    def _unload_loras(self):
        """FLUX does not support LoRA weights in the traditional sense.
        
        Override base class to prevent calling unload_lora_weights()
        which may not exist or behave differently on FLUX pipelines.
        """
        self.logger.debug("FLUX LoRA unload - clearing tracking only")
        self._loaded_lora = {}
        self._disabled_lora = []

    def _apply_torch_compile(self):
        """Apply torch.compile() to transformer for inference speedup.
        
        FLUX uses 'transformer' instead of 'unet', so we override
        the base class implementation.
        """
        settings = get_qsettings()
        settings.beginGroup("generator_settings")
        enable_torch_compile = settings.value(
            "enable_torch_compile", False, type=bool
        )
        settings.endGroup()
        
        if not enable_torch_compile:
            self.logger.debug("torch.compile disabled in settings")
            return

        if self._memory_settings_flags.get("torch_compile_applied"):
            return  # Already compiled

        if not hasattr(self._pipe, "transformer") or self._pipe.transformer is None:
            self.logger.debug("No transformer found for torch.compile")
            return

        try:
            self.logger.info(
                "Wrapping FLUX transformer with torch.compile() - compilation will happen on first generation"
            )
            self._pipe.transformer = torch.compile(
                self._pipe.transformer,
                mode="reduce-overhead",  # Best for inference
                fullgraph=False,  # Allow fallback for unsupported ops
            )
            self._memory_settings_flags["torch_compile_applied"] = True
            self.logger.info(
                "✓ FLUX transformer wrapped for compilation (first generation will take 2-3 min)"
            )
        except Exception as e:
            self.logger.warning(f"Could not compile FLUX transformer: {e}")

    def _load_deep_cache(self):
        """Deep cache not supported for FLUX."""

    def _unload_pipe(self):
        """
        FLUX-specific pipeline unload.

        CRITICAL: FLUX uses 'transformer' not 'unet', so we must explicitly
        delete it. The base class only deletes unet/vae/text_encoder.
        
        This method properly handles accelerate's CPU offload hooks to prevent
        memory leaks. When enable_model_cpu_offload() is used, components are
        cached in CPU RAM during generation. We must explicitly remove these
        hooks and their CPU memory buffers.
        """
        self.logger.info("=== FLUX _unload_pipe CALLED ===")
        self.logger.debug("Unloading FLUX pipe")
        
        if self._pipe is None:
            return
            
        try:
            # Try to use accelerate's official hook removal if available
            try:
                from accelerate.hooks import remove_hook_from_module
                has_accelerate_hooks = True
            except ImportError:
                has_accelerate_hooks = False
                self.logger.debug("accelerate.hooks not available, using manual cleanup")
            
            # CRITICAL: Remove Accelerate hooks first to prevent CPU cache retention
            if hasattr(self._pipe, "_all_hooks"):
                self.logger.debug("Removing Accelerate _all_hooks")
                for hook in list(self._pipe._all_hooks):
                    try:
                        hook.remove()
                    except Exception as e:
                        self.logger.debug(f"Error removing hook: {e}")
                self._pipe._all_hooks.clear()

            # List of all FLUX components to clean up
            component_names = [
                "transformer",
                "vae", 
                "text_encoder",
                "text_encoder_2",
                "scheduler",
                "tokenizer",
                "tokenizer_2",
            ]

            # Remove hooks from each component and delete them
            for component_name in component_names:
                component = getattr(self._pipe, component_name, None)
                if component is None:
                    continue
                    
                # Remove accelerate hooks using official API if available
                if has_accelerate_hooks and hasattr(component, "_hf_hook"):
                    try:
                        remove_hook_from_module(component, recurse=True)
                        self.logger.debug(f"Removed hooks from {component_name} via accelerate")
                    except Exception as e:
                        self.logger.debug(f"Error removing hooks from {component_name}: {e}")
                
                # Manual hook cleanup as fallback
                if hasattr(component, "_hf_hook"):
                    try:
                        if hasattr(component._hf_hook, "offload"):
                            component._hf_hook.offload(component)
                        delattr(component, "_hf_hook")
                    except Exception as e:
                        self.logger.debug(f"Error in manual hook cleanup for {component_name}: {e}")
                
                # Move component to CPU to free VRAM, then delete
                try:
                    if hasattr(component, "to"):
                        component.to("cpu")
                except Exception:
                    pass
                    
                # Clear internal state dicts and buffers
                try:
                    if hasattr(component, "_parameters"):
                        component._parameters.clear()
                    if hasattr(component, "_buffers"):
                        component._buffers.clear()
                    if hasattr(component, "_modules"):
                        component._modules.clear()
                except Exception:
                    pass
                
                # Explicitly delete the component
                try:
                    setattr(self._pipe, component_name, None)
                    del component
                except Exception as e:
                    self.logger.debug(f"Error deleting {component_name}: {e}")
                    
            # Clear any cached offload state
            if hasattr(self._pipe, "_offload_gpu_id"):
                self._pipe._offload_gpu_id = None
            if hasattr(self._pipe, "_execution_device"):
                self._pipe._execution_device = None
                    
        except Exception as e:
            self.logger.debug(f"Error removing Accelerate hooks: {e}")

        # Delete the pipeline itself
        try:
            del self._pipe
        except Exception:
            pass
        self._pipe = None

        # Aggressive memory cleanup
        gc.collect()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
        # Additional gc passes to break circular references
        gc.collect()
        gc.collect()
        
        clear_memory()

        self.logger.info("✓ FLUX pipeline unloaded and memory freed")

    def _clear_pipeline_caches(self):
        """Clear internal pipeline caches to free RAM without unloading models.
        
        With sequential CPU offload, we don't have the same caching issues
        as model CPU offload. Just do basic cleanup.
        """
        if self._pipe is None:
            return
        
        self.logger.debug("Clearing pipeline caches to free RAM")
        
        # Force garbage collection - multiple passes to break circular refs
        gc.collect()
        gc.collect()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
        gc.collect()

    def _generate(self):
        """
        Override to add aggressive cleanup after FLUX generation completes.

        CRITICAL: FLUX decode buffers (~8-10GB) stay in memory after generation.
        We must explicitly free them after all image processing is done.
        """
        try:
            # Call parent implementation
            super()._generate()
        finally:
            # CRITICAL: Clean up after ALL image processing is complete
            # This happens after images are sent to canvas and export worker
            self._clear_pipeline_caches()
            clear_memory()

            self.logger.debug("[FLUX CLEANUP] Memory freed")

    def _move_t5_to_gpu(self):
        """Placeholder - T5 stays on CPU the entire time.
        
        NOTE: For 16GB cards, we keep T5 on CPU and run encoding there,
        then just move the resulting embeddings to GPU. This is more
        memory-efficient than moving the entire model.
        """
        # T5 will be moved to GPU for encoding, then back to CPU
        pass  # Intentionally empty - actual logic in _get_results
    
    def _move_t5_to_cpu(self):
        """Move T5 back to CPU after encoding to free VRAM for diffusion."""
        # Actual logic in _get_results
        pass  # Intentionally empty - actual logic in _get_results

    def _get_results(self, data):
        """
        Run pipeline inference with cleanup between generations.

        CRITICAL: FLUX GGUF models accumulate memory without cleanup.
        After each generation, we must explicitly free VAE decode buffers.
        
        MEMORY STRATEGY for 16GB cards with BitsAndBytes quantization:
        - BitsAndBytes 4-bit models REQUIRE CUDA - they cannot run on CPU
        - During encoding: Move VAE to CPU, move T5 to GPU
        - After encoding: Move T5 to CPU, move VAE to GPU
        - This swaps ~0.3GB VAE with ~5.7GB T5 on GPU as needed
        """
        with torch.no_grad(), torch.amp.autocast(
            "cuda", dtype=torch.bfloat16, enabled=True
        ):
            total = 0
            while total < self.image_request.n_samples:
                if self.do_interrupt_image_generation:
                    raise InterruptedException()

                # STEP 1: Free GPU memory by moving VAE to CPU
                # VAE is not needed during prompt encoding
                vae = getattr(self._pipe, "vae", None)
                if vae is not None:
                    vae.to("cpu")
                    self.logger.debug("[T5 OFFLOAD] Moved VAE to CPU to make room for T5")
                
                # Clear GPU memory
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                # STEP 2: Move T5 to GPU for encoding
                # BitsAndBytes 4-bit quantized models REQUIRE CUDA
                t5_encoder = getattr(self._pipe, "text_encoder_2", None)
                if t5_encoder is not None:
                    t5_encoder.to("cuda:0")
                    self.logger.debug("[T5 OFFLOAD] Moved T5 to GPU for encoding")
                
                # STEP 3: Run encode_prompt on GPU
                self.logger.debug("[T5 OFFLOAD] Running encode_prompt (T5 and CLIP on GPU)")
                prompt_embeds, pooled_prompt_embeds, text_ids = self._pipe.encode_prompt(
                    prompt=data.get("prompt", ""),
                    prompt_2=data.get("prompt_2", data.get("prompt", "")),
                    device="cuda:0",
                    max_sequence_length=data.get("max_sequence_length", 512),
                )
                
                # STEP 4: Move T5 back to CPU to free VRAM for transformer
                if t5_encoder is not None:
                    t5_encoder.to("cpu")
                    self.logger.debug("[T5 OFFLOAD] Moved T5 back to CPU")
                
                # Clear GPU memory
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()
                
                # STEP 5: Move VAE back to GPU for decoding
                if vae is not None:
                    vae.to("cuda:0")
                    self.logger.debug("[T5 OFFLOAD] Moved VAE back to GPU for decoding")
                
                # STEP 6: Run pipeline with pre-computed embeddings (T5 not needed)
                pipe_data = {k: v for k, v in data.items() if k not in ("prompt", "prompt_2")}
                pipe_data["prompt_embeds"] = prompt_embeds
                pipe_data["pooled_prompt_embeds"] = pooled_prompt_embeds
                
                pipeline_output = self._pipe(**pipe_data)
                
                # Convert pipeline output to dict format expected by base class
                # FluxPipelineOutput has .images attribute, base expects {"images": [...]}
                results = {"images": pipeline_output.images}
                yield results
                
                # CRITICAL: Clean up after each generation to prevent RAM growth
                # The pipeline keeps intermediate tensors that must be freed
                del pipeline_output
                del results
                del prompt_embeds
                del pooled_prompt_embeds
                del text_ids
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

                if not self.image_request.generate_infinite_images:
                    total += 1
