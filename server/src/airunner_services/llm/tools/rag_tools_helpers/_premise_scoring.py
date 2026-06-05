"""Compatibility facade for premise scoring helpers."""

from airunner_services.llm.tools.rag_tools_helpers._premise_evidence_builder import (
    best_early_current_setting_paragraph,
    best_neighboring_scene_paragraph,
    build_premise_evidence_documents,
    split_premise_regions,
)
from airunner_services.llm.tools.rag_tools_helpers._premise_score_rules import (
    premise_count_hits,
    premise_current_setting_score,
    premise_dialogue_penalty,
    premise_has_marker,
    premise_inciting_incident_score,
    premise_neighbor_scene_score,
    premise_opening_score,
    premise_paragraph_score,
    premise_summary_label,
)

__all__ = [
    "best_early_current_setting_paragraph",
    "best_neighboring_scene_paragraph",
    "build_premise_evidence_documents",
    "premise_count_hits",
    "premise_current_setting_score",
    "premise_dialogue_penalty",
    "premise_has_marker",
    "premise_inciting_incident_score",
    "premise_neighbor_scene_score",
    "premise_opening_score",
    "premise_paragraph_score",
    "premise_summary_label",
    "split_premise_regions",
]
