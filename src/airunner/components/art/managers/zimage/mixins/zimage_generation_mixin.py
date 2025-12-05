"""Z-Image generation mixin for preparing and running generation."""

import gc
from typing import Dict, Any
import torch
from airunner.components.application.exceptions import InterruptedException
from airunner.utils.memory import clear_memory
from airunner.utils.settings.get_qsettings import get_qsettings


class ZImageGenerationMixin:
    """Handles generation data preparation for Z-Image models."""

    def _prepare_pipe_data(self) -> Dict[str, Any]:
        """Prepare pipeline initialization parameters with Z-Image optimizations.

        Z-Image uses a single text encoder (Qwen2.5-VL or similar LLM) instead
        of dual CLIP/T5 encoders like FLUX.
        """
        data = super()._prepare_pipe_data()

        # Z-Image uses bfloat16 for optimal performance
        data["torch_dtype"] = torch.bfloat16

        return data

    def _load_prompt_embeds(self):
        """Load and prepare prompt embeddings for Z-Image."""
        self._current_prompt = self.prompt
        self._current_negative_prompt = self.negative_prompt
        self.logger.debug("Z-Image prompt handling (no pre-computed embeddings)")

    def _prepare_data(self, active_rect=None) -> Dict:
        """Prepare generation data for Z-Image pipeline."""
        data = super()._prepare_data(active_rect)
        self._strip_zimage_incompatible_params(data)
        self._enforce_zimage_guidance(data)
        data["max_sequence_length"] = 512
        self._log_zimage_generation_params(data)
        return data

    def _strip_zimage_incompatible_params(self, data: Dict) -> None:
        """Remove parameters the Z-Image pipeline cannot consume."""
        # Z-Image Turbo does not use negative prompts or CFG in the traditional sense
        # It uses cfg_normalization and cfg_truncation instead
        # The ZImagePipeline.__call__ doesn't accept negative_prompt
        for key in ("clip_skip", "strength", "negative_prompt"):
            data.pop(key, None)

    def _enforce_zimage_guidance(self, data: Dict) -> None:
        """Log guidance and steps for Z-Image (uses DB settings).
        
        Z-Image Turbo works best with guidance_scale=0.0 and 8-9 steps,
        but we respect whatever the user has configured.
        """
        pass

    def _log_zimage_generation_params(self, data: Dict) -> None:
        """Log core generation parameters for debugging."""
        debug_fields = {
            "prompt": data.get("prompt", "MISSING!")[:50] + "...",
            "guidance_scale": data.get("guidance_scale", "MISSING!"),
            "steps": data.get("num_inference_steps", "MISSING!"),
            "size": f"{data.get('width')}x{data.get('height')}",
            "max_sequence_length": data.get("max_sequence_length", "MISSING!"),
        }
        self.logger.info(
            "[Z-IMAGE DEBUG] Keys: %s | Values: %s",
            list(data.keys()),
            debug_fields,
        )

    def _unload_loras(self):
        """Unload Z-Image LoRA weights if any are loaded.
        
        Z-Image supports LoRA weights through ZImageLoraLoaderMixin.
        """
        if hasattr(self._pipe, 'unload_lora_weights'):
            try:
                self._pipe.unload_lora_weights()
                self.logger.debug("Unloaded Z-Image LoRA weights")
            except Exception as e:
                self.logger.debug(f"No LoRA weights to unload: {e}")
        self._loaded_lora = {}
        self._disabled_lora = []

    def _load_scheduler(self, scheduler_name=None):
        """Load a flow-match scheduler for Z-Image.
        
        Overrides base class to use flow-match scheduler factory.
        
        Args:
            scheduler_name: Display name of the scheduler to load.
        """
        from airunner.components.art.schedulers.flow_match_scheduler_factory import (
            is_flow_match_scheduler,
            create_flow_match_scheduler,
        )
        from airunner.enums import Scheduler, ModelType, ModelStatus
        
        # Get scheduler name
        requested_name = (
            scheduler_name
            or (self.image_request.scheduler if self.image_request else None)
            or getattr(self, '_scheduler_name', None)
            or Scheduler.FLOW_MATCH_EULER.value
        )
        
        # Only handle flow-match schedulers
        if not is_flow_match_scheduler(requested_name):
            self.logger.warning(
                f"Scheduler {requested_name} is not a flow-match scheduler. "
                f"Z-Image requires flow-match schedulers."
            )
            requested_name = Scheduler.FLOW_MATCH_EULER.value
        
        self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADING)
        
        try:
            # Use base config from current scheduler for structural params, but
            # strip behavioral flags so the factory sets them explicitly.
            base_config = None
            if self._pipe and hasattr(self._pipe, "scheduler"):
                base_config = dict(self._pipe.scheduler.config)
                for flag in (
                    "use_karras_sigmas",
                    "stochastic_sampling",
                    "use_exponential_sigmas",
                    "use_beta_sigmas",
                ):
                    base_config.pop(flag, None)
            
            # Create the new scheduler
            scheduler = create_flow_match_scheduler(requested_name, base_config)
            
            # Apply to pipeline
            if self._pipe is not None:
                self._pipe.scheduler = scheduler
            
            self._scheduler = scheduler
            self._scheduler_name = requested_name
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADED)
            self.logger.info(f"Loaded Z-Image scheduler: {requested_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to load scheduler {requested_name}: {e}")
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.FAILED)

    def _apply_torch_compile(self):
        """Apply torch.compile() to transformer for inference speedup.
        
        Z-Image uses 'transformer' instead of 'unet', so we override
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
                "Wrapping Z-Image transformer with torch.compile() - compilation will happen on first generation"
            )
            self._pipe.transformer = torch.compile(
                self._pipe.transformer,
                mode="reduce-overhead",  # Best for inference
                fullgraph=False,  # Allow fallback for unsupported ops
            )
            self._memory_settings_flags["torch_compile_applied"] = True
            self.logger.info(
                "✓ Z-Image transformer wrapped for compilation (first generation will take 2-3 min)"
            )
        except Exception as e:
            self.logger.warning(f"Could not compile Z-Image transformer: {e}")

    def _load_deep_cache(self):
        """Deep cache not supported for Z-Image."""

    def _unload_pipe(self):
        """Z-Image-specific pipeline unload.

        Similar to FLUX, Z-Image uses 'transformer' not 'unet', so we must
        explicitly delete it along with the text encoder.
        """
        self.logger.info("=== Z-IMAGE _unload_pipe CALLED ===")
        self.logger.debug("Unloading Z-Image pipe")
        
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
            
            # CRITICAL: Remove Accelerate hooks first
            if hasattr(self._pipe, "_all_hooks"):
                self.logger.debug("Removing Accelerate _all_hooks")
                for hook in list(self._pipe._all_hooks):
                    try:
                        hook.remove()
                    except Exception as e:
                        self.logger.debug(f"Error removing hook: {e}")
                self._pipe._all_hooks.clear()

            # List of all Z-Image components to clean up
            component_names = [
                "transformer",
                "vae", 
                "text_encoder",
                "scheduler",
                "tokenizer",
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
                    
                # Explicitly delete the component
                try:
                    setattr(self._pipe, component_name, None)
                    del component
                except Exception as e:
                    self.logger.debug(f"Error deleting {component_name}: {e}")
                    
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
            
        gc.collect()
        gc.collect()
        
        clear_memory()

        self.logger.info("✓ Z-Image pipeline unloaded and memory freed")

    def _clear_pipeline_caches(self):
        """Clear internal pipeline caches to free RAM."""
        if self._pipe is None:
            return
        
        self.logger.debug("Clearing pipeline caches to free RAM")
        
        gc.collect()
        gc.collect()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
        gc.collect()

    def _generate(self):
        """Override to add cleanup after Z-Image generation."""
        # Log the active scheduler flags at generation time for debugging
        try:
            if self._pipe and hasattr(self._pipe, "scheduler") and hasattr(self._pipe.scheduler, "config"):
                karras = self._pipe.scheduler.config.get("use_karras_sigmas", False)
                stochastic = self._pipe.scheduler.config.get("stochastic_sampling", False)
                self.logger.info(
                    "[ZIMAGE SCHEDULER DEBUG] generate() using %s (karras=%s, stochastic=%s)",
                    self._pipe.scheduler.__class__.__name__,
                    karras,
                    stochastic,
                )
        except Exception:
            self.logger.debug("Could not log scheduler flags during generation", exc_info=True)
        try:
            super()._generate()
        finally:
            self._clear_pipeline_caches()
            clear_memory()
            self.logger.debug("[Z-IMAGE CLEANUP] Memory freed")

    def _get_results(self, data):
        """Run pipeline inference with cleanup between generations.
        
        Z-Image uses a single text encoder (Qwen-based), so memory management
        is simpler than FLUX which has dual encoders.
        """
        with torch.no_grad(), torch.amp.autocast(
            "cuda", dtype=torch.bfloat16, enabled=True
        ):
            total = 0
            while total < self.image_request.n_samples:
                if self.do_interrupt_image_generation:
                    raise InterruptedException()

                # Run pipeline
                pipeline_output = self._pipe(**data)
                
                # Convert pipeline output to dict format expected by base class
                results = {"images": pipeline_output.images}
                yield results
                
                # Cleanup after each generation
                del pipeline_output
                del results
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

                if not self.image_request.generate_infinite_images:
                    total += 1
