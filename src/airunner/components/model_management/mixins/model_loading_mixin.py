"""Model loading and swapping mixin for ModelResourceManager."""

from typing import List, Dict, Any, Optional


class ModelLoadingMixin:
    """Mixin for model loading, swapping, and resource preparation.

    This mixin handles:
    - Preparing resources before model loading
    - Automatic model swapping when out of memory
    - Determining which models to unload
    - Managing model priority for swapping decisions

    Dependencies (from parent):
        registry: ModelRegistry instance
        hardware_profiler: HardwareProfiler instance
        quantization_strategy: QuantizationStrategy instance
        memory_allocator: MemoryAllocator instance
        signal_mediator: SignalMediator instance
        logger: Logger instance
        set_model_state: Method from ModelStateMixin
        get_active_models: Method from ModelStateMixin
        _model_states: Dict from ModelStateMixin
        _model_types: Dict from ModelStateMixin
    """

    def prepare_model_loading(
        self,
        model_id: str,
        model_type: str = "llm",
        preferred_quantization: Optional[Any] = None,
        auto_swap: bool = True,
    ) -> dict:
        """Prepare resources for model loading.

        Args:
            model_id: Identifier for the model
            model_type: Type of model (llm, text_to_image, tts, stt)
            preferred_quantization: Preferred quantization level
            auto_swap: Whether to automatically unload conflicting models

        Returns:
            Dict with keys:
            - can_load: bool
            - reason: str (if can_load is False)
            - metadata: ModelMetadata (if available)
            - quantization: QuantizationConfig (if applicable)
            - allocation: MemoryAllocation (if successful)
            - swapped_models: List[str] (models that were unloaded)
        """
        # Import ModelState from the parent module at runtime to avoid circular imports
        from airunner.components.model_management.model_resource_manager import (
            ModelState,
        )

        # Set loading state
        self.set_model_state(model_id, ModelState.LOADING, model_type)

        metadata = self.registry.get_model(model_id)
        if not metadata:
            self.logger.warning(
                f"Model {model_id} not in registry - checking for conflicts anyway"
            )
            # Even if not in registry, check if there are conflicting models loaded
            # and attempt to swap if auto_swap is enabled
            if auto_swap:
                # Check if any models are currently loaded
                active_models = self.get_active_models()
                if active_models:
                    self.logger.info(
                        f"Found {len(active_models)} active models while loading unregistered model"
                    )
                    self.logger.debug(
                        f"Active models: {[(m.model_type, m.state) for m in active_models]}"
                    )
                    # Attempt to swap to make room
                    swap_result = self.request_model_swap(model_id, model_type)
                    self.logger.info(
                        f"Swap result: success={swap_result['success']}, "
                        f"unloaded={swap_result['unloaded_models']}, "
                        f"reason={swap_result.get('reason', 'N/A')}"
                    )
                    if (
                        swap_result["success"]
                        and swap_result["unloaded_models"]
                    ):
                        self.logger.info(
                            f"Auto-swapped {len(swap_result['unloaded_models'])} models for unregistered model"
                        )
                        return {
                            "can_load": True,
                            "reason": "Model not in registry but made room via auto-swap",
                            "swapped_models": swap_result["unloaded_models"],
                        }
                    else:
                        self.logger.warning(
                            f"Auto-swap did not unload any models. Proceeding anyway but OOM likely."
                        )

            # Allow load but warn
            return {
                "can_load": True,
                "reason": "Model not in registry - no validation performed",
                "swapped_models": [],
            }

        hardware = self.hardware_profiler.get_profile()
        quantization = self.quantization_strategy.select_quantization(
            metadata.size_gb, hardware, preferred_quantization
        )

        # Try to allocate memory
        allocation = self.memory_allocator.allocate(model_id, quantization)

        # If allocation fails and auto_swap is enabled, try swapping models
        if not allocation and auto_swap:
            self.logger.info(
                f"Insufficient memory for {model_id}, attempting auto-swap"
            )
            swap_result = self.request_model_swap(model_id, model_type)

            if swap_result["success"]:
                self.logger.info(
                    f"Auto-swap successful: unloaded {len(swap_result['unloaded_models'])} models"
                )
                # Try allocation again after swap
                allocation = self.memory_allocator.allocate(
                    model_id, quantization
                )

                if allocation:
                    self.logger.info(
                        f"Prepared {metadata.name} after auto-swap: {quantization.description}"
                    )
                    return {
                        "can_load": True,
                        "metadata": metadata,
                        "quantization": quantization,
                        "allocation": allocation,
                        "swapped_models": swap_result["unloaded_models"],
                    }

        if not allocation:
            from airunner.components.model_management.model_resource_manager import (
                ModelState,
            )

            self.set_model_state(model_id, ModelState.UNLOADED)
            return {
                "can_load": False,
                "reason": "Insufficient memory even after attempting model swap",
                "metadata": metadata,
                "quantization": quantization,
                "swapped_models": [],
            }

        self.logger.info(
            f"Prepared {metadata.name}: {quantization.description}"
        )
        return {
            "can_load": True,
            "metadata": metadata,
            "quantization": quantization,
            "allocation": allocation,
            "swapped_models": [],
        }

    def request_model_swap(
        self, target_model_id: str, target_model_type: str
    ) -> Dict[str, Any]:
        """Request automatic model swapping to make room for target model.

        Args:
            target_model_id: Model we want to load
            target_model_type: Type of model to load

        Returns:
            Dict with keys:
            - success: bool - whether swap was successful
            - unloaded_models: List[str] - models that were unloaded
            - reason: str - explanation if swap failed
        """
        # Get models that need to be unloaded
        models_to_unload = self._determine_models_to_unload(
            target_model_id, target_model_type
        )

        if not models_to_unload:
            return {
                "success": True,
                "unloaded_models": [],
                "reason": "No models need to be unloaded",
            }

        # Track which models were successfully unloaded
        unloaded = []

        for model_id in models_to_unload:
            model_type = self._model_types.get(model_id, "unknown")
            self.logger.info(
                f"Auto-swapping: Unloading {model_type} model {model_id}"
            )

            try:
                # CRITICAL: Use synchronous API calls instead of async signals
                # This ensures models are ACTUALLY unloaded before we try to load the new one
                # Async signals were causing race conditions where SD would try to load
                # before LLM was fully unloaded, leading to VRAM exhaustion

                if model_type == "llm":
                    # Import here to avoid circular dependency
                    from airunner.components.llm.managers.llm_model_manager import (
                        LLMModelManager,
                    )

                    manager = LLMModelManager()
                    manager.unload()
                    self.logger.info(
                        "LLM unloaded synchronously for auto-swap"
                    )

                elif model_type == "text_to_image":
                    # SD unload via API
                    from airunner.components.application.api.api import API

                    api = API()
                    api.art.unload()
                    self.logger.info("SD unloaded synchronously for auto-swap")

                elif model_type == "tts":
                    from airunner.enums import SignalCode

                    self._emit_signal(SignalCode.TTS_DISABLE_SIGNAL, {})

                elif model_type == "stt":
                    from airunner.enums import SignalCode

                    self._emit_signal(SignalCode.STT_DISABLE_SIGNAL, {})

                unloaded.append(model_id)

            except Exception as e:
                self.logger.error(
                    f"Failed to unload {model_id}: {e}", exc_info=True
                )
                return {
                    "success": False,
                    "unloaded_models": unloaded,
                    "reason": f"Failed to unload {model_id}: {str(e)}",
                }

        return {
            "success": True,
            "unloaded_models": unloaded,
            "reason": f"Successfully unloaded {len(unloaded)} models",
        }

    def _determine_models_to_unload(
        self, target_model_id: str, target_model_type: str
    ) -> List[str]:
        """Determine which models should be unloaded for target model.

        Strategy:
        1. Never unload models in LOADING or BUSY state
        2. Prioritize unloading models based on type hierarchy:
           - SD has highest priority (art generation)
           - LLM has medium priority (chat)
           - TTS/STT have lowest priority (auxiliary)
        3. Unload lowest priority models first
        4. Stop when sufficient memory is available

        Args:
            target_model_id: Model we want to load
            target_model_type: Type of model to load

        Returns:
            List of model IDs to unload
        """
        # Import ModelState from the parent module
        from airunner.components.model_management.model_resource_manager import (
            ModelState,
        )

        # Define model priority (higher = more important, keep loaded)
        priority_map = {
            "text_to_image": 3,  # Highest priority - keep SD loaded if possible
            "llm": 2,  # Medium priority
            "tts": 1,  # Low priority
            "stt": 1,  # Low priority
        }

        target_priority = priority_map.get(target_model_type, 2)

        # Get all loaded models that can be unloaded
        candidates = []
        self.logger.debug(
            f"Determining models to unload for {target_model_type} (priority {target_priority})"
        )
        self.logger.debug(
            f"Current model states: {list(self._model_states.items())}"
        )

        for model_id, state in self._model_states.items():
            if state not in (ModelState.LOADED, ModelState.UNLOADED):
                # Skip models that are loading or busy
                self.logger.debug(
                    f"Skipping {model_id} - state {state} not eligible for unload"
                )
                continue

            if state == ModelState.UNLOADED:
                self.logger.debug(f"Skipping {model_id} - already unloaded")
                continue

            model_type = self._model_types.get(model_id, "unknown")
            model_priority = priority_map.get(model_type, 2)

            self.logger.debug(
                f"Checking {model_id}: type={model_type}, priority={model_priority}, "
                f"target_priority={target_priority}"
            )

            # Only unload models with lower or equal priority
            if model_priority <= target_priority:
                allocation = self.memory_allocator._allocations.get(model_id)
                if allocation:
                    candidates.append(
                        (
                            model_id,
                            model_type,
                            model_priority,
                            allocation.vram_allocated_gb,
                        )
                    )
                    self.logger.debug(
                        f"Added {model_id} as unload candidate "
                        f"(VRAM: {allocation.vram_allocated_gb:.1f}GB)"
                    )
                else:
                    self.logger.debug(
                        f"Skipping {model_id} - no allocation record found"
                    )
            else:
                self.logger.debug(
                    f"Skipping {model_id} - priority {model_priority} > target {target_priority}"
                )

        # Sort by priority (lowest first), then by VRAM usage (largest first)
        candidates.sort(key=lambda x: (x[2], -x[3]))

        # Determine how much memory we need
        # For now, we'll unload all conflicting lower-priority models
        # In the future, we could be smarter and only unload what's needed

        models_to_unload = [model_id for model_id, _, _, _ in candidates]

        if models_to_unload:
            self.logger.info(
                f"Selected {len(models_to_unload)} models for unloading: {models_to_unload}"
            )
        else:
            self.logger.warning(
                f"No models selected for unloading despite {len(self._model_states)} tracked models"
            )

        return models_to_unload

    def _emit_signal(self, signal_code, data):
        """Emit signal via SignalMediator."""
        self.signal_mediator.emit(signal_code, data)
