"""
Tool Normalization Mixin - Handles tool argument normalization and side effects.

This mixin provides argument normalization for the Deep Research Agent:
- Tool argument normalization
- Tool side effect application
- State updates from tool results
"""

from typing import Any, Dict
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class ToolNormalizationMixin:
    """Mixin for tool argument normalization in Deep Research Agent."""

    def _normalize_document_args(
        self, tool_name: str, normalized: Dict, state: dict, topic: str
    ) -> None:
        """Normalize arguments for document creation tools."""
        if tool_name in {"create_research_document", "create_research_notes"}:
            if topic:
                normalized["topic"] = topic

    def _normalize_path_args(
        self, tool_name: str, normalized: Dict, state: dict
    ) -> None:
        """Normalize arguments for tools that need file paths."""
        notes_path = state.get("notes_path", "")
        document_path = state.get("document_path", "")

        if tool_name == "append_research_notes" and notes_path:
            normalized.setdefault("notes_path", notes_path)

        if tool_name in {
            "update_research_section",
            "add_source_citation",
            "finalize_research_document",
        }:
            if document_path:
                normalized["document_path"] = document_path

    def _normalize_search_args(
        self, tool_name: str, normalized: Dict, state: dict, topic: str
    ) -> None:
        """Normalize arguments for search tools."""
        queries = state.get("search_queries", []) or ([topic] if topic else [])

        if tool_name in {
            "search_web",
            "search_news",
            "search_knowledge_base_documents",
        }:
            desired_query = None
            if queries:
                if tool_name == "search_news" and len(queries) > 1:
                    desired_query = queries[1]
                else:
                    desired_query = queries[0]

            current_query = normalized.get("query")
            if not current_query and desired_query:
                normalized["query"] = desired_query
            elif (
                topic
                and current_query
                and topic.lower() not in current_query.lower()
            ):
                normalized["query"] = f"{topic} {current_query}".strip()

    def _normalize_content_args(
        self, tool_name: str, normalized: Dict, topic: str
    ) -> None:
        """Normalize arguments for content processing tools."""
        if (
            tool_name
            in {
                "organize_research",
                "extract_key_points",
                "compare_sources",
                "synthesize_sources",
            }
            and topic
        ):
            for key in ("findings", "text", "topic"):
                if key in normalized:
                    if topic.lower() not in str(normalized[key]).lower():
                        normalized[key] = topic
                    break

        if tool_name in {"update_research_section", "append_research_notes"}:
            if "content" in normalized and normalized["content"] is None:
                normalized["content"] = ""

    def _normalize_tool_args(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        state: dict,
    ) -> Dict[str, Any]:
        """Ensure critical tool arguments align with current research topic."""
        normalized = dict(tool_args or {})
        topic = state.get("research_topic", "").strip()

        self._normalize_document_args(tool_name, normalized, state, topic)
        self._normalize_path_args(tool_name, normalized, state)
        self._normalize_search_args(tool_name, normalized, state, topic)
        self._normalize_content_args(tool_name, normalized, topic)

        return normalized

    def _apply_tool_side_effects(
        self,
        tool_name: str,
        result: Any,
        state_updates: Dict[str, Any],
        state: dict,
    ) -> None:
        """Capture tool outputs that should update agent state."""
        if tool_name == "create_research_document" and isinstance(result, str):
            state_updates["document_path"] = result
            state["document_path"] = result

        elif tool_name == "create_research_notes" and isinstance(result, str):
            state_updates["notes_path"] = result
            state["notes_path"] = result

        elif tool_name == "search_knowledge_base_documents":
            if result and "No documents found" not in str(result):
                state_updates["rag_loaded"] = True

        elif tool_name == "append_research_notes":
            if state.get("notes_path"):
                state_updates.setdefault("notes_path", state["notes_path"])

        elif tool_name == "update_research_section" and isinstance(
            result, str
        ):
            if "Successfully updated" in result:
                sections = list(state.get("sections_written", []))
                section_name = result.replace(
                    "Successfully updated", ""
                ).strip()
                if section_name:
                    sections.append(section_name)
                    state_updates["sections_written"] = sections

        elif tool_name == "search_web" and isinstance(result, dict):
            hits = result.get("results") or []
            if hits:
                collected = list(state.get("collected_sources", []))
                collected.extend(hits)
                state_updates["collected_sources"] = collected

        elif tool_name == "search_news" and isinstance(result, dict):
            hits = result.get("results") or []
            if hits:
                collected = list(state.get("collected_sources", []))
                collected.extend(hits)
                state_updates["collected_sources"] = collected
