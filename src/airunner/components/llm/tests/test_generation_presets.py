"""Tests for centralized generation preset helpers."""

from airunner.components.llm.config.generation_presets import (
    WorkflowGenerationStage,
    get_workflow_generation_preset,
)


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