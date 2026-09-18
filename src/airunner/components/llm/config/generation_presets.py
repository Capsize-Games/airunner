"""Centralized generation presets for visible and hidden LLM stages.

The visible per-action table (``GenerationPreset``,
``ACTION_GENERATION_PRESETS``, ``DEFAULT_ACTION_PRESET`` and
``get_action_generation_preset``) now lives once in
``airunner_common.generation_presets``. Desktop and services both called
into independently-authored copies of it until #2225 measured (via
``scripts/compare_llm_request_for_action.py``) that 13 of the 20
``LLMActionType`` members resolved to different effective generation
kwargs depending on which side handled the request. #2225 unified the
table on the desktop/documented values; see that module's docstring for
the evidence and the decision.

Those names are re-exported here so the existing
``airunner.components.llm.config`` import surface is unchanged. Only the
desktop-only hidden *workflow-stage* presets remain local to this module
-- services has no equivalent of the document-synthesis/verification
stages, and per #2221's "contract subset, not full union" discipline they
stay out of the shared foundation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from airunner_common.generation_presets import (
    ACTION_GENERATION_PRESETS,
    DEFAULT_ACTION_PRESET,
    GenerationPreset,
    get_action_generation_preset,
)

__all__ = [
    "ACTION_GENERATION_PRESETS",
    "DEFAULT_ACTION_PRESET",
    "DEFAULT_WORKFLOW_PRESET",
    "GenerationPreset",
    "WorkflowGenerationPreset",
    "WorkflowGenerationStage",
    "get_action_generation_preset",
    "get_workflow_generation_preset",
]


class WorkflowGenerationStage(str, Enum):
    """Named hidden stages that can have dedicated generation settings."""

    DOCUMENT_SYNTHESIS = "document_synthesis"
    DOCUMENT_VERIFICATION = "document_verification"


@dataclass(frozen=True)
class WorkflowGenerationPreset:
    """Non-user-visible generation adjustments for one workflow stage."""

    min_max_new_tokens: Optional[int] = None
    reasoning_effort: Optional[str] = None
    temperature: Optional[float] = None

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
            if (
                "max_new_tokens" not in prepared
                and "max_tokens" not in prepared
            ):
                prepared["max_new_tokens"] = self.min_max_new_tokens

        if self.reasoning_effort is not None:
            prepared["reasoning_effort"] = self.reasoning_effort

        if self.temperature is not None:
            prepared["temperature"] = self.temperature

        return prepared


DEFAULT_WORKFLOW_PRESET = WorkflowGenerationPreset()


WORKFLOW_GENERATION_PRESETS = {
    WorkflowGenerationStage.DOCUMENT_SYNTHESIS: WorkflowGenerationPreset(
        min_max_new_tokens=1024,
        reasoning_effort="high",
        temperature=0.1,
    ),
    WorkflowGenerationStage.DOCUMENT_VERIFICATION: WorkflowGenerationPreset(
        min_max_new_tokens=1024,
        reasoning_effort="high",
        temperature=0.1,
    ),
}


def get_workflow_generation_preset(
    stage: WorkflowGenerationStage,
) -> WorkflowGenerationPreset:
    """Return the hidden-stage preset for one workflow stage."""
    return WORKFLOW_GENERATION_PRESETS.get(stage, DEFAULT_WORKFLOW_PRESET)
