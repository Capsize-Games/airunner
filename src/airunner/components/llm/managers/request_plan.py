"""Typed request-plan contract for request preprocessing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass
class RequestPlan:
    """Store one normalized request-scoped plan for the workflow."""

    rewrite_needed: bool = False
    rewritten_query: str = ""
    tool_required: bool = False
    tool_categories: list[str] = field(default_factory=list)
    allowed_tool_names: list[str] = field(default_factory=list)
    primary_tool: Optional[str] = None
    planner_mode: Optional[str] = None
    planner_tool_hints: list[str] = field(default_factory=list)
    document_query_intent: Optional[str] = None
    document_summary_focus: Optional[str] = None
    document_answer_mode: Optional[str] = None
    answer_strategy: Optional[str] = None
    finalization_mode: Optional[str] = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "RequestPlan":
        """Build one request plan from a legacy preprocess mapping."""
        if not isinstance(payload, Mapping):
            return cls()

        def normalize_optional(value: Any) -> Optional[str]:
            if not isinstance(value, str):
                return None
            normalized = value.strip()
            return normalized or None

        def normalize_list(value: Any) -> list[str]:
            items = value if isinstance(value, list) else []
            normalized: list[str] = []
            for item in items:
                if not isinstance(item, str):
                    continue
                token = item.strip()
                if token and token not in normalized:
                    normalized.append(token)
            return normalized

        primary_tool = normalize_optional(payload.get("primary_tool"))
        planner_tool_hints = normalize_list(payload.get("planner_tool_hints"))
        allowed_tool_names = normalize_list(payload.get("allowed_tool_names"))
        if not allowed_tool_names and planner_tool_hints:
            allowed_tool_names = list(planner_tool_hints)
        if primary_tool and primary_tool not in allowed_tool_names:
            allowed_tool_names.insert(0, primary_tool)

        planner_mode = normalize_optional(payload.get("planner_mode"))
        if planner_mode is None and len(allowed_tool_names) > 1:
            planner_mode = "select_tools"

        return cls(
            rewrite_needed=bool(payload.get("rewrite_needed")),
            rewritten_query=str(payload.get("rewritten_query", "") or ""),
            tool_required=bool(payload.get("tool_required")),
            tool_categories=normalize_list(payload.get("tool_categories")),
            allowed_tool_names=allowed_tool_names,
            primary_tool=primary_tool,
            planner_mode=planner_mode,
            planner_tool_hints=planner_tool_hints,
            document_query_intent=normalize_optional(
                payload.get("document_query_intent")
            ),
            document_summary_focus=normalize_optional(
                payload.get("document_summary_focus")
            ),
            document_answer_mode=normalize_optional(
                payload.get("document_answer_mode")
            ),
            answer_strategy=normalize_optional(payload.get("answer_strategy")),
            finalization_mode=normalize_optional(
                payload.get("finalization_mode")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return one JSON-serializable view of the request plan."""
        return {
            "rewrite_needed": self.rewrite_needed,
            "rewritten_query": self.rewritten_query,
            "tool_required": self.tool_required,
            "tool_categories": list(self.tool_categories),
            "allowed_tool_names": list(self.allowed_tool_names),
            "primary_tool": self.primary_tool,
            "planner_mode": self.planner_mode,
            "planner_tool_hints": list(self.planner_tool_hints),
            "document_query_intent": self.document_query_intent,
            "document_summary_focus": self.document_summary_focus,
            "document_answer_mode": self.document_answer_mode,
            "answer_strategy": self.answer_strategy,
            "finalization_mode": self.finalization_mode,
        }