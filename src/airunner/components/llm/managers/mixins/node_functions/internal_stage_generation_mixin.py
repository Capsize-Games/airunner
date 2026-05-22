"""Internal document-stage generation helpers for node functions."""

from typing import Any, Dict, Optional

from airunner.components.llm.config.generation_presets import (
    WorkflowGenerationStage,
    get_workflow_generation_preset,
)


class InternalStageGenerationMixin:
    """Apply document-stage presets and emit debug metadata."""

    def _prepare_internal_response_generation_kwargs(
        self,
        generation_kwargs: Optional[Dict],
        *,
        tool_name: str,
        user_question: str,
        stage: WorkflowGenerationStage = (
            WorkflowGenerationStage.DOCUMENT_SYNTHESIS
        ),
    ) -> Dict:
        """Return generation kwargs tuned for one internal synthesis pass."""
        prepared = dict(generation_kwargs or {})
        if not self._is_document_result_tool(tool_name):
            return prepared
        if self._get_document_query_intent(user_question) != "summary":
            return prepared

        return get_workflow_generation_preset(stage).apply_to_generation_kwargs(
            prepared
        )

    @staticmethod
    def _collect_generation_debug_settings(
        generation_kwargs: Dict,
    ) -> Dict[str, Any]:
        """Return one compact debug view of resolved generation settings."""
        settings = {}
        for key in (
            "max_new_tokens",
            "max_tokens",
            "temperature",
            "top_p",
            "top_k",
            "num_beams",
            "repetition_penalty",
            "no_repeat_ngram_size",
            "reasoning_effort",
        ):
            value = generation_kwargs.get(key)
            if value is not None:
                settings[key] = value
        return settings

    def _build_internal_stage_debug_metadata(
        self,
        generation_kwargs: Dict,
        *,
        tool_name: str,
        user_question: str,
        stage: WorkflowGenerationStage,
    ) -> Optional[Dict[str, Any]]:
        """Return one read-only metadata payload for internal LLM stages."""
        if not self._is_document_result_tool(tool_name):
            return None
        intent = self._get_document_query_intent(user_question)
        metadata = {
            "kind": "llm_stage_settings",
            "title": stage.value.replace("_", " ").title(),
            "stage": stage.value,
            "intent": intent,
            "preset_applied": intent == "summary",
            "settings": self._collect_generation_debug_settings(
                generation_kwargs
            ),
        }
        if metadata["preset_applied"]:
            metadata["preset_id"] = stage.value
        return metadata