"""Shared per-action generation presets for ``LLMRequest.for_action()``.

Issue Capsize-Games/airunner#2225 (part of the repo-split tracker #2185)
resolved a real behavioral fork: both the desktop app and the services
distribution implemented ``LLMRequest.for_action()``, but picked their
generation parameters from two different tables, and
``scripts/compare_llm_request_for_action.py`` measured that 13 of the 20
``LLMActionType`` members produced different effective kwargs depending
on which side handled the request.

The investigation (recorded on #2225) showed the divergence was *not*
intentional per-deployment tuning:

* The services inline ladder was a stale copy of the desktop's
  *pre-extraction* ``for_action()`` body -- identical values *and*
  identical comments (``temperature=0.7  # Qwen3 non-thinking mode
  recommended``, ``temperature=0.3  # Mostly consistent``). The desktop
  side had since extracted that ladder into a preset table
  (``35f6f12ef``) and then deliberately re-tuned it (``17b566e6d``: chat
  0.7 -> 0.2, RAG/search 0.3 -> 0.2) with regression tests asserting the
  "low-variance"/"deterministic" intent. The split commit (``42316d2db``)
  copied the *old inline ladder* into services rather than delegating to
  the new table, so the two sides silently drifted apart.
* No commit, comment or test ever documented services' ``0.7``/``0.3``
  values as intentional for that deployment, and no services-side commit
  touched them after the split. The one services-specific caller the issue
  flagged (``intelligent_crawl_tool.py``) calls ``for_action(DECISION)``
  -- an action where *both* tables already agreed -- and then overrides
  ``temperature`` itself, so it never reads the divergent value.

The unified table below therefore adopts the desktop values (the newer,
deliberately-tuned, test-codified set). Desktop behavior is unchanged;
services now gets the documented intent. Note this is a *data* table, not
the field-union case #2221 was careful about: #2221's "contract subset,
not full union" rule guards a ``hasattr``-filtered untrusted-input
surface, which has no analogue here -- #2221 itself deferred the preset
question to #2225.

``airunner_common`` is a dependency-light foundation: this module imports
only ``contract_enums`` (no ``airunner``/``airunner_services``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from airunner_common.contract_enums import LLMActionType


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
        temperature=0.2,
        repetition_penalty=1.15,
        no_repeat_ngram_size=3,
        max_new_tokens=8192,
        top_k=20,
        top_p=0.8,
        tool_categories=None,
    ),
    LLMActionType.UPDATE_MOOD: GenerationPreset(
        temperature=0.2,
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
        temperature=0.2,
        repetition_penalty=1.1,
        no_repeat_ngram_size=2,
        max_new_tokens=300,
        top_k=30,
        top_p=0.9,
        tool_categories=("RAG", "SEARCH"),
    ),
    LLMActionType.SUMMARIZE: GenerationPreset(
        temperature=0.2,
        repetition_penalty=1.1,
        no_repeat_ngram_size=2,
        max_new_tokens=300,
        top_k=30,
        top_p=0.9,
        tool_categories=("SEARCH",),
    ),
    LLMActionType.SEARCH: GenerationPreset(
        temperature=0.2,
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


__all__ = [
    "ACTION_GENERATION_PRESETS",
    "DEFAULT_ACTION_PRESET",
    "GenerationPreset",
    "get_action_generation_preset",
]
