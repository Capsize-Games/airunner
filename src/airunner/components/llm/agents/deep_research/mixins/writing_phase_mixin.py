"""Writing phase mixin for DeepResearchAgent.

Handles Phase 1C and 1D: creating outline and synthesizing research document.
"""

import logging
from pathlib import Path
from typing import TypedDict

from airunner.components.llm.tools.research_document_tools import (
    update_research_section,
)

logger = logging.getLogger(__name__)


class DeepResearchState(TypedDict):
    """Type definition for deep research state."""

    messages: list
    current_phase: str
    research_topic: str
    clean_topic: str
    search_queries: list
    document_path: str
    notes_path: str
    scraped_urls: list


class WritingPhaseMixin:
    """Provides Phase 1C and 1D writing and synthesis methods."""

    def _phase1c_outline(self, state: DeepResearchState) -> dict:
        """Phase 1C: Generate basic outline structure."""
        topic = state.get("research_topic", "")

        logger.info(f"[Phase 1C] Creating outline for: {topic}")

        # Create a basic outline structure programmatically
        outline = f"""# {topic}

## Abstract
(To be written)

## Introduction
Overview of {topic}

## Background
Historical context and current situation

## Analysis
Key findings and developments

## Implications
Consequences and future outlook

## Conclusion
Summary of findings

## Sources
(Citations to be added)
"""

        logger.info(
            f"[Phase 1C] Created outline with {len(outline)} characters"
        )
        self._emit_progress("Phase 1C", "Created document outline")

        return {
            "messages": state.get("messages", []),
            "outline": outline,
            "current_phase": "phase1d",
        }

    def _read_notes_file(self, notes_path: str) -> str:
        """Read and return notes file content."""
        if not notes_path or not Path(notes_path).exists():
            return ""
        try:
            with open(notes_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"[Phase 1D] Read {len(content)} chars from notes")
            return content
        except Exception as e:
            logger.error(f"[Phase 1D] Failed to read notes: {e}")
            return ""

    def _write_section(
        self, section_name: str, synthesize_func, document_path: str, *args
    ) -> tuple[str | None, bool]:
        """Write a single section to the document.

        Returns:
            (content, success) tuple
        """
        try:
            content = synthesize_func(*args)
            update_research_section(
                document_path=document_path,
                section_name=section_name,
                content=content,
            )
            logger.info(f"[Phase 1D] Wrote {section_name} section")
            self._emit_progress("Phase 1D", f"Wrote {section_name}")
            return content, True
        except Exception as e:
            logger.error(f"[Phase 1D] Failed to write {section_name}: {e}")
            return None, False

    def _phase1d_write(self, state: DeepResearchState) -> dict:
        """Phase 1D: Synthesize notes into a proper research document."""
        topic = state.get("research_topic", "")
        document_path = state.get("document_path", "")
        notes_path = state.get("notes_path", "")
        thesis = state.get("thesis_statement", "")

        logger.info(f"[Phase 1D] Synthesizing research document from notes")
        logger.info(f"[Phase 1D] Using thesis: {thesis}")

        notes_content = self._read_notes_file(notes_path)
        if not notes_content:
            logger.error("[Phase 1D] No notes content available to synthesize")
            return {
                "messages": state.get("messages", []),
                "current_phase": "phase1e",
            }

        parsed_notes = self._parse_research_notes(notes_content)
        previous_sections = {}
        sections_written = []

        # Write all sections
        sections = [
            (
                "Introduction",
                self._synthesize_introduction,
                [topic, parsed_notes, thesis, previous_sections],
            ),
            (
                "Background",
                self._synthesize_background,
                [topic, parsed_notes, thesis, previous_sections],
            ),
            (
                "Analysis",
                self._synthesize_analysis,
                [topic, parsed_notes, thesis, previous_sections],
            ),
            (
                "Implications",
                self._synthesize_implications,
                [topic, parsed_notes, thesis, previous_sections],
            ),
            (
                "Conclusion",
                self._synthesize_conclusion,
                [topic, parsed_notes, thesis, previous_sections],
            ),
            ("Sources", self._synthesize_sources, [parsed_notes]),
        ]

        for section_name, synthesize_func, args in sections:
            content, success = self._write_section(
                section_name, synthesize_func, document_path, *args
            )
            if success:
                if (
                    section_name != "Sources"
                ):  # Don't add Sources to previous_sections
                    previous_sections[section_name] = content
                sections_written.append(section_name)

        logger.info(
            f"[Phase 1D] Completed synthesis: {len(sections_written)} sections"
        )
        self._emit_progress(
            "Phase 1D", f"Synthesized {len(sections_written)} sections"
        )

        return {
            "messages": state.get("messages", []),
            "sections_written": sections_written,
            "current_phase": "phase1e",
        }
