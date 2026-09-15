"""Typed result for request-time tool routing decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ToolSelectionPlan:
    """Canonical tool-selection result for one LLM request."""

    selected_categories: Optional[list[str]]
    effective_categories: Optional[list[str]]
    filtered_tools: Optional[list[Any]]
    force_tool: Optional[str] = None
    tool_choice: Any = None
    rebuild_workflow: bool = False
    keep_existing_tools: bool = False