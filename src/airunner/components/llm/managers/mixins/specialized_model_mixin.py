"""Specialized model swapping functionality for LLM models.

This mixin handles:
- Loading specialized models for specific tasks/capabilities
- Restoring primary model after specialized task
- Convenience method for single-use specialized generation
"""

from typing import Optional, Any, TYPE_CHECKING

from langchain_core.messages import AIMessage

if TYPE_CHECKING:
    from airunner.components.llm.config.model_capabilities import (
        ModelCapability,
    )


class SpecializedModelMixin:
    """Mixin for specialized model swapping functionality."""

    def load_specialized_model(
        self,
        capability: "ModelCapability",
        return_to_primary: bool = True,
    ) -> Optional[Any]:
        """Load a specialized model for a specific task.

        This method is used by tools to load specialized models (e.g., prompt
        enhancer, code generator) for specific tasks. It handles model
        swapping through the resource manager and can optionally return to
        the primary model after the task completes.

        Args:
            capability: The capability needed (from ModelCapability enum)
            return_to_primary: Whether to swap back to primary model after use

        Returns:
            The loaded chat model, or None if loading failed

        Example:
            # In a tool:
            from airunner.components.llm.config.model_capabilities import (
                ModelCapability
            )

            manager = LLMModelManager()
            model = manager.load_specialized_model(
                ModelCapability.PROMPT_ENHANCEMENT
            )
            if model:
                enhanced = model.invoke("Enhance this: " + prompt)
                # Model auto-swaps back to primary after this method returns
        """
        from airunner.components.llm.config.model_capabilities import (
            get_model_for_capability,
        )

        # Get the model spec for this capability
        model_spec = get_model_for_capability(capability)
        if not model_spec:
            self.logger.warning(
                f"No model registered for capability: {capability}"
            )
            return None

        # Store the current primary model info
        if return_to_primary:
            primary_model_path = self._current_model_path or self.model_path

        # Check if we're already using the right model
        current_path = self._current_model_path or self.model_path
        if current_path == model_spec.model_path:
            self.logger.info(
                f"Already using {model_spec.model_path} for {capability}"
            )
            return self._chat_model

        # Use resource manager to swap models
        self.logger.info(
            f"Loading specialized model {model_spec.model_path} for "
            f"{capability}"
        )

        # Unload current model
        self.unload()

        # Temporarily override model path
        original_model_path = self.llm_generator_settings.model_path
        self.llm_generator_settings.model_path = model_spec.model_path

        try:
            # Load the specialized model
            self.load()

            if return_to_primary:
                # Store function to restore primary model
                self._restore_primary_model = lambda: self._do_restore_primary(
                    primary_model_path, original_model_path
                )

            return self._chat_model

        except Exception as e:
            self.logger.error(
                f"Failed to load specialized model: {e}", exc_info=True
            )
            # Restore original settings
            self.llm_generator_settings.model_path = original_model_path
            return None

    def _do_restore_primary(
        self, primary_model_path: str, original_setting: str
    ) -> None:
        """Restore primary model after specialized model use.

        Args:
            primary_model_path: Path to the primary model
            original_setting: Original model path setting value
        """
        self.logger.info(f"Restoring primary model: {primary_model_path}")
        self.unload()
        self.llm_generator_settings.model_path = original_setting
        self.load()
        self._restore_primary_model = None

    def use_specialized_model(
        self,
        capability: "ModelCapability",
        prompt: str,
        max_tokens: int = 512,
    ) -> Optional[str]:
        """Use a specialized model for a single generation.

        This loads the specialized model, generates a response, and
        automatically swaps back to the primary model.

        Args:
            capability: The capability needed
            prompt: The prompt to send to the specialized model
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text, or None if generation failed

        Example:
            # In a tool:
            manager = LLMModelManager()
            enhanced_prompt = manager.use_specialized_model(
                ModelCapability.PROMPT_ENHANCEMENT,
                "Enhance this Stable Diffusion prompt: a cat"
            )
        """
        model = self.load_specialized_model(capability, return_to_primary=True)
        if not model:
            return None

        try:
            # Generate with the specialized model
            response = model.invoke(prompt)

            # Extract text from response
            if isinstance(response, AIMessage):
                result = response.content
            elif isinstance(response, str):
                result = response
            else:
                result = str(response)

            # Restore primary model if needed
            if (
                hasattr(self, "_restore_primary_model")
                and self._restore_primary_model
            ):
                self._restore_primary_model()

            return result

        except Exception as e:
            self.logger.error(
                f"Failed to generate with specialized model: {e}",
                exc_info=True,
            )
            # Try to restore primary model even on error
            if (
                hasattr(self, "_restore_primary_model")
                and self._restore_primary_model
            ):
                try:
                    self._restore_primary_model()
                except Exception as restore_error:
                    self.logger.error(
                        f"Failed to restore primary model: {restore_error}"
                    )
            return None
