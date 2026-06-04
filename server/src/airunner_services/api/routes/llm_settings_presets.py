"""API route that exposes the LLM generation presets by action type."""

from fastapi import APIRouter
from typing import Any

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest

router = APIRouter()

_PRESET_LABELS: dict[LLMActionType, str] = {
    LLMActionType.CHAT: "Chat",
    LLMActionType.UPDATE_MOOD: "Chat",
    LLMActionType.CODE: "Code",
    LLMActionType.PERFORM_RAG_SEARCH: "RAG Search",
    LLMActionType.SUMMARIZE: "Summarize / Search",
    LLMActionType.SEARCH: "Summarize / Search",
    LLMActionType.GENERATE_IMAGE: "Generate Image",
    LLMActionType.DECISION: "Decision / Workflow",
    LLMActionType.APPLICATION_COMMAND: "Decision / Workflow",
    LLMActionType.FILE_INTERACTION: "Decision / Workflow",
    LLMActionType.WORKFLOW: "Decision / Workflow",
    LLMActionType.WORKFLOW_INTERACTION: "Decision / Workflow",
    LLMActionType.DEEP_RESEARCH: "Deep Research",
}

_PRESET_SORT_KEY: dict[str, int] = {
    "Chat": 0,
    "Code": 1,
    "RAG Search": 2,
    "Summarize / Search": 3,
    "Generate Image": 4,
    "Decision / Workflow": 5,
    "Deep Research": 6,
    "General": 7,
}


def _action_type_for_label(label: str) -> LLMActionType | None:
    """Return the first action type whose display label matches."""
    for action, lbl in _PRESET_LABELS.items():
        if lbl == label:
            return action
    return None


def _extract_preset(action: LLMActionType) -> dict[str, Any]:
    """Build a JSON-safe preset dict from one action type."""
    req = LLMRequest.for_action(action)
    return {
        "label": _PRESET_LABELS.get(action, action.value),
        "args": {
            "do_sample": req.do_sample,
            "temperature": req.temperature,
            "repetition_penalty": req.repetition_penalty,
            "ngram_size": req.no_repeat_ngram_size,
            "max_new_tokens": req.max_new_tokens,
            "top_k": req.top_k,
            "top_p": req.top_p,
            "early_stopping": req.early_stopping,
            "length_penalty": req.length_penalty,
            "min_length": req.min_length,
            "num_beams": req.num_beams,
            "sequences": req.num_return_sequences,
            "use_cache": req.use_cache,
        },
    }


def _presets() -> list[dict[str, Any]]:
    """Return a de-duplicated list of presets keyed by label."""
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for action in LLMActionType:
        label = _PRESET_LABELS.get(action)
        if label and label not in seen:
            seen.add(label)
            result.append(_extract_preset(action))
    # General fallback
    if "General" not in seen:
        result.append(_extract_preset(LLMActionType.NONE))
    result.sort(key=lambda p: _PRESET_SORT_KEY.get(p["label"], 99))
    return result


@router.get("/settings-presets")
async def list_llm_settings_presets() -> list[dict[str, Any]]:
    """Return all known LLM generation preset profiles."""
    return _presets()
