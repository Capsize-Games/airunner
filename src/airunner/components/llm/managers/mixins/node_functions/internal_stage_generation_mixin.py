"""Internal document-stage generation helpers for node functions."""

from typing import Any, Dict, Optional

from airunner.components.llm.config.generation_presets import (
    WorkflowGenerationStage,
    get_workflow_generation_preset,
)


class InternalStageGenerationMixin:
    """Apply document-stage presets and emit debug metadata."""

    def _should_increase_document_stage_reasoning(
        self,
        *,
        all_tool_content: str,
        tool_name: str,
        user_question: str,
        stage: WorkflowGenerationStage,
    ) -> bool:
        """Return whether one internal stage needs extra reasoning."""
        if stage != WorkflowGenerationStage.DOCUMENT_VERIFICATION:
            return False
        if not self._is_document_result_tool(tool_name):
            return False
        if self._get_document_query_intent(user_question) != "summary":
            return False

        should_disable = getattr(
            self,
            "_should_disable_document_stage_thinking",
            None,
        )
        if not callable(should_disable):
            return False
        return not should_disable(all_tool_content, tool_name)

    def _prepare_internal_response_generation_kwargs(
        self,
        generation_kwargs: Optional[Dict],
        *,
        all_tool_content: str = "",
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

        prepared = get_workflow_generation_preset(stage).apply_to_generation_kwargs(
            prepared
        )
        if self._should_increase_document_stage_reasoning(
            all_tool_content=all_tool_content,
            tool_name=tool_name,
            user_question=user_question,
            stage=stage,
        ):
            prepared["reasoning_effort"] = "high"
        return prepared

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