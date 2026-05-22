"""Tests for centralized generation preset helpers."""

from airunner.components.llm.config.generation_presets import (
    ACTION_GENERATION_PRESETS,
    WorkflowGenerationStage,
    get_workflow_generation_preset,
)
from airunner.enums import LLMActionType


def test_chat_preset_uses_lower_conversational_temperature():
    """Visible chat replies should default to a low-variance temperature."""
    assert ACTION_GENERATION_PRESETS[LLMActionType.CHAT].temperature == 0.2


def test_rag_visible_presets_use_low_temperature():
    """Visible RAG/search actions should stay deterministic by default."""
    assert (
        ACTION_GENERATION_PRESETS[LLMActionType.PERFORM_RAG_SEARCH].temperature
        == 0.2
    )
    assert ACTION_GENERATION_PRESETS[LLMActionType.SUMMARIZE].temperature == 0.2
    assert ACTION_GENERATION_PRESETS[LLMActionType.SEARCH].temperature == 0.2


def test_document_synthesis_preset_sets_minimum_budget_and_reasoning_effort():
    """Document synthesis should enforce its hidden-stage floor settings."""
    preset = get_workflow_generation_preset(
        WorkflowGenerationStage.DOCUMENT_SYNTHESIS
    )

    resolved = preset.apply_to_generation_kwargs(
        {"max_new_tokens": 300, "reasoning_effort": "high"}
    )

    assert resolved["max_new_tokens"] == 1024
    assert resolved["reasoning_effort"] == "low"
    assert resolved["temperature"] == 0.1


def test_document_verification_preset_preserves_larger_existing_budget():
    """Document verification should not shrink a larger caller budget."""
    preset = get_workflow_generation_preset(
        WorkflowGenerationStage.DOCUMENT_VERIFICATION
    )

    resolved = preset.apply_to_generation_kwargs(
        {"max_new_tokens": 2048, "reasoning_effort": "medium"}
    )

    assert resolved["max_new_tokens"] == 2048
    assert resolved["reasoning_effort"] == "low"
    assert resolved["temperature"] == 0.1