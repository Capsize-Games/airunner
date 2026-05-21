"""Centralized generation presets for visible and hidden LLM stages."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from airunner.enums import LLMActionType


@dataclass(frozen=True)
class GenerationPreset:
    """Resolved generation settings for one request stage or action."""

    do_sample: bool = True
    early_stopping: bool = True
    eta_cutoff: int = 200
    length_penalty: float = 1.0
    max_new_tokens: int = 8192
    min_length: int = 1
    no_repeat_ngram_size: int = 3
    num_beams: int = 1
    num_return_sequences: int = 1
    repetition_penalty: float = 1.15
    temperature: float = 0.7
    top_k: int = 20
    top_p: float = 0.8
    use_cache: bool = True
    tool_categories: Optional[tuple[str, ...]] = None
    reasoning_effort: Optional[str] = None

    def to_request_kwargs(self) -> dict:
        """Return kwargs compatible with LLMRequest construction."""
        data = self.__dict__.copy()
        categories = data["tool_categories"]
        data["tool_categories"] = list(categories) if categories else None
        return data


DEFAULT_ACTION_PRESET = GenerationPreset(
    temperature=0.8,
    max_new_tokens=500,
    top_k=50,
    top_p=0.9,
)


ACTION_GENERATION_PRESETS = {
    LLMActionType.CHAT: GenerationPreset(
        temperature=0.7,
        repetition_penalty=1.15,
        no_repeat_ngram_size=3,
        max_new_tokens=8192,
        top_k=20,
        top_p=0.8,
        tool_categories=None,
    ),
    LLMActionType.UPDATE_MOOD: GenerationPreset(
        temperature=0.7,
        repetition_penalty=1.15,
        no_repeat_ngram_size=3,
        max_new_tokens=8192,
        top_k=20,
        top_p=0.8,
        tool_categories=None,
    ),
    LLMActionType.CODE: GenerationPreset(
        temperature=0.6,
        repetition_penalty=1.1,
        no_repeat_ngram_size=2,
        max_new_tokens=8192,
        top_k=20,
        top_p=0.8,
        tool_categories=None,
    ),
    LLMActionType.PERFORM_RAG_SEARCH: GenerationPreset(
        temperature=0.3,
        repetition_penalty=1.1,
        no_repeat_ngram_size=2,
        max_new_tokens=300,
        top_k=30,
        top_p=0.9,
        tool_categories=("RAG", "SEARCH"),
    ),
    LLMActionType.SUMMARIZE: GenerationPreset(
        temperature=0.3,
        repetition_penalty=1.1,
        no_repeat_ngram_size=2,
        max_new_tokens=300,
        top_k=30,
        top_p=0.9,
        tool_categories=("SEARCH",),
    ),
    LLMActionType.SEARCH: GenerationPreset(
        temperature=0.3,
        repetition_penalty=1.1,
        no_repeat_ngram_size=2,
        max_new_tokens=300,
        top_k=30,
        top_p=0.9,
        tool_categories=("SEARCH",),
    ),
    LLMActionType.GENERATE_IMAGE: GenerationPreset(
        temperature=0.9,
        repetition_penalty=1.15,
        no_repeat_ngram_size=3,
        max_new_tokens=200,
        top_k=50,
        top_p=0.9,
    ),
    LLMActionType.DECISION: GenerationPreset(
        temperature=0.6,
        repetition_penalty=1.0,
        no_repeat_ngram_size=0,
        max_new_tokens=32768,
        top_k=20,
        top_p=0.95,
        tool_categories=None,
    ),
    LLMActionType.APPLICATION_COMMAND: GenerationPreset(
        temperature=0.6,
        repetition_penalty=1.0,
        no_repeat_ngram_size=0,
        max_new_tokens=32768,
        top_k=20,
        top_p=0.95,
        tool_categories=None,
    ),
    LLMActionType.FILE_INTERACTION: GenerationPreset(
        temperature=0.6,
        repetition_penalty=1.0,
        no_repeat_ngram_size=0,
        max_new_tokens=32768,
        top_k=20,
        top_p=0.95,
        tool_categories=None,
    ),
    LLMActionType.WORKFLOW: GenerationPreset(
        temperature=0.6,
        repetition_penalty=1.0,
        no_repeat_ngram_size=0,
        max_new_tokens=32768,
        top_k=20,
        top_p=0.95,
        tool_categories=None,
    ),
    LLMActionType.WORKFLOW_INTERACTION: GenerationPreset(
        temperature=0.6,
        repetition_penalty=1.0,
        no_repeat_ngram_size=0,
        max_new_tokens=32768,
        top_k=20,
        top_p=0.95,
        tool_categories=None,
    ),
    LLMActionType.DEEP_RESEARCH: GenerationPreset(
        temperature=0.6,
        repetition_penalty=1.15,
        no_repeat_ngram_size=3,
        max_new_tokens=32768,
        top_k=20,
        top_p=0.95,
        tool_categories=("RESEARCH", "SEARCH"),
    ),
}


def get_action_generation_preset(action: LLMActionType) -> GenerationPreset:
    """Return the visible-response preset for one action."""
    return ACTION_GENERATION_PRESETS.get(action, DEFAULT_ACTION_PRESET)


class WorkflowGenerationStage(str, Enum):
    """Named hidden stages that can have dedicated generation settings."""

    DOCUMENT_SYNTHESIS = "document_synthesis"
    DOCUMENT_VERIFICATION = "document_verification"


@dataclass(frozen=True)
class WorkflowGenerationPreset:
    """Non-user-visible generation adjustments for one workflow stage."""

    min_max_new_tokens: Optional[int] = None
    reasoning_effort: Optional[str] = None

    def apply_to_generation_kwargs(
        self,
        generation_kwargs: Optional[dict],
    ) -> dict:
        """Return generation kwargs with stage-specific adjustments applied."""
        prepared = dict(generation_kwargs or {})

        if self.min_max_new_tokens is not None:
            for key in ("max_new_tokens", "max_tokens"):
                value = prepared.get(key)
                if isinstance(value, int):
                    prepared[key] = max(value, self.min_max_new_tokens)
            if "max_new_tokens" not in prepared and "max_tokens" not in prepared:
                prepared["max_new_tokens"] = self.min_max_new_tokens

        if self.reasoning_effort is not None:
            prepared["reasoning_effort"] = self.reasoning_effort

        return prepared


DEFAULT_WORKFLOW_PRESET = WorkflowGenerationPreset()


WORKFLOW_GENERATION_PRESETS = {
    WorkflowGenerationStage.DOCUMENT_SYNTHESIS: WorkflowGenerationPreset(
        min_max_new_tokens=1024,
        reasoning_effort="low",
    ),
    WorkflowGenerationStage.DOCUMENT_VERIFICATION: WorkflowGenerationPreset(
        min_max_new_tokens=1024,
        reasoning_effort="low",
    ),
}


def get_workflow_generation_preset(
    stage: WorkflowGenerationStage,
) -> WorkflowGenerationPreset:
    """Return the hidden-stage preset for one workflow stage."""
    return WORKFLOW_GENERATION_PRESETS.get(stage, DEFAULT_WORKFLOW_PRESET)