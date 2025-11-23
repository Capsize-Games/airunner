"""Writing phase mixin for DeepResearchAgent.

Handles Phase 1C and 1D: creating outline and synthesizing research document.
"""

import logging
from pathlib import Path
from typing import Optional

from airunner.components.llm.tools.research_document_tools import (
    update_research_section,
)

logger = logging.getLogger(__name__)


class WritingPhaseMixin:
    """Provides Phase 1C and 1D writing and synthesis methods."""

    def _load_notes_into_rag(self, notes_path: str) -> bool:
        """Load research notes file into RAG for querying during synthesis.

        Args:
            notes_path: Path to the research notes file

        Returns:
            True if successfully loaded, False otherwise
        """
        if not notes_path or not Path(notes_path).exists():
            logger.warning(f"[RAG] Notes file does not exist: {notes_path}")
            return False

        try:
            # API IS the RAG manager (LLMModelManager inherits from RAGMixin)
            rag_manager = self._api if self._api else None

            if not rag_manager or not hasattr(
                rag_manager, "ensure_indexed_files"
            ):
                logger.warning(
                    "[RAG] No RAG manager available, will use direct notes reading"
                )
                return False

            # Check if already loaded
            loaded_docs = getattr(rag_manager, "_loaded_doc_ids", [])
            if notes_path in loaded_docs:
                logger.info(f"[RAG] Notes already loaded: {notes_path}")
                return True

            # Load the notes file into RAG
            logger.info(f"[RAG] Loading research notes into RAG: {notes_path}")
            success = rag_manager.ensure_indexed_files([notes_path])

            if success:
                logger.info(f"[RAG] Successfully loaded notes into RAG")
                return True
            else:
                logger.warning(f"[RAG] Failed to load notes into RAG")
                return False

        except Exception as e:
            logger.error(
                f"[RAG] Error loading notes into RAG: {e}", exc_info=True
            )
            return False

    def _query_rag_for_section(
        self, section_name: str, topic: str, max_results: int = 5
    ) -> Optional[str]:
        """Query RAG for section-specific context from research notes.

        Args:
            section_name: Name of the section being written
            topic: Research topic
            max_results: Maximum number of RAG chunks to retrieve

        Returns:
            Retrieved context string or None if RAG unavailable
        """
        try:
            # API IS the RAG manager (LLMModelManager inherits from RAGMixin)
            rag_manager = self._api if self._api else None

            if not rag_manager or not hasattr(rag_manager, "search"):
                return None

            # Build section-specific query
            query = f"{topic} {section_name}"

            logger.info(
                f"[RAG] Querying for section '{section_name}': {query}"
            )

            # Use the RAG search method
            results = rag_manager.search(query, k=max_results)

            if not results:
                logger.warning(
                    f"[RAG] No results for section '{section_name}'"
                )
                return None

            # Combine results into context
            context_parts = []
            for i, doc in enumerate(results, 1):
                content = doc.page_content.strip()
                if content:
                    context_parts.append(f"[Source {i}]\n{content}\n")

            context = "\n".join(context_parts)
            logger.info(
                f"[RAG] Retrieved {len(results)} chunks ({len(context)} chars) "
                f"for section '{section_name}'"
            )

            return context

        except Exception as e:
            logger.error(
                f"[RAG] Error querying RAG for section '{section_name}': {e}"
            )
            return None

    def _phase1c_outline(self, state) -> dict:
        """Phase 1C: Generate custom outline based on collected notes using LLM."""
        topic = state.get("research_topic", "")
        notes_path = state.get("notes_path", "")

        logger.info(f"[Phase 1C] Creating LLM-generated outline for: {topic}")

        # Load notes into RAG for synthesis phase
        notes_rag_loaded = self._load_notes_into_rag(notes_path)
        if notes_rag_loaded:
            logger.info("[Phase 1C] Notes loaded into RAG for synthesis")
        else:
            logger.warning(
                "[Phase 1C] Could not load notes into RAG, will use direct reading"
            )

        # Read the collected notes
        notes_content = self._read_notes_file(notes_path)
        if not notes_content:
            logger.warning(
                "[Phase 1C] No notes available, using basic outline"
            )
            outline = self._create_fallback_outline(topic)
        else:
            outline = self._generate_outline_with_llm(topic, notes_content)

        logger.info(
            f"[Phase 1C] Created outline with {len(outline)} characters"
        )
        self._emit_progress("Phase 1C", "Created custom document outline")

        # CRITICAL: Preserve thesis_statement from state
        thesis_from_state = state.get("thesis_statement", "")
        logger.info(
            f"[Phase 1C] Preserving thesis from state: {thesis_from_state[:100] if thesis_from_state else 'EMPTY'}"
        )

        return {
            "messages": state.get("messages", []),
            "outline": outline,
            "thesis_statement": thesis_from_state,
            "notes_rag_loaded": notes_rag_loaded,  # Track RAG load status
            "current_phase": "phase1d",
        }

    def _generate_outline_with_llm(
        self, topic: str, notes_content: str
    ) -> str:
        """Use LLM to generate a custom outline based on collected notes."""
        notes_sample = self._prepare_notes_for_outline(notes_content)
        prompt = self._build_outline_prompt(topic, notes_sample)

        try:
            from langchain_core.messages import HumanMessage

            response = self._base_model.invoke([HumanMessage(content=prompt)])
            outline = response.content.strip()

            # Log and validate outline
            logger.info(
                f"[Phase 1C] LLM returned outline ({len(outline)} chars):"
            )
            logger.info(f"[Phase 1C] First 500 chars: {outline[:500]}")

            if self._is_outline_valid(outline):
                logger.info("[Phase 1C] Generated custom outline with LLM")
                return outline
            else:
                logger.warning(
                    "[Phase 1C] LLM outline missing required sections, using fallback"
                )
                return self._create_fallback_outline(topic)

        except Exception as e:
            logger.error(
                f"[Phase 1C] Failed to generate outline with LLM: {e}"
            )
            return self._create_fallback_outline(topic)

    def _prepare_notes_for_outline(self, notes_content: str) -> str:
        """Prepare notes sample for outline generation."""
        return (
            notes_content[:8000]
            if len(notes_content) > 8000
            else notes_content
        )

    def _build_outline_prompt(self, topic: str, notes_sample: str) -> str:
        """Build prompt for outline generation."""
        return f"""TASK: Generate a research paper outline for "{topic}"

CRITICAL: Your response must be ONLY an outline in markdown format. Do NOT write notes or article summaries.

Based on these research notes:
{notes_sample}

OUTPUT FORMAT (copy this structure exactly):

# {topic}

## Abstract

## Introduction

## [Custom section name from research content]

## [Custom section name from research content]

## [Custom section name from research content]

## [Custom section name from research content]

## Conclusion

## Sources

RULES:
1. Create 4-6 content sections between Introduction and Conclusion
2. Name sections based on actual themes in the research (e.g., "Sanctions Lifting Timeline", "Regional Diplomatic Relations")
3. Use ## for all section headers
4. Include ONLY section headers, NO content
5. Do NOT write article summaries or notes

Generate the outline NOW (headers only):"""

    def _is_outline_valid(self, outline: str) -> bool:
        """Check if outline has required structure."""
        if "## Abstract" not in outline or "## Introduction" not in outline:
            logger.warning(
                f"[Phase 1C] Has '## Abstract': {'## Abstract' in outline}"
            )
            logger.warning(
                f"[Phase 1C] Has '## Introduction': {'## Introduction' in outline}"
            )
            return False
        return True

    def _create_fallback_outline(self, topic: str) -> str:
        """Create a basic fallback outline if LLM generation fails.

        Args:
            topic: Research topic

        Returns:
            Basic outline structure
        """
        return f"""# {topic}

## Abstract

## Introduction

## Background

## Analysis

## Implications

## Conclusion

## Sources
"""

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
                api=self,
            )
            logger.info(f"[Phase 1D] Wrote {section_name} section")
            self._emit_progress("Phase 1D", f"Wrote {section_name}")
            return content, True
        except Exception as e:
            logger.error(f"[Phase 1D] Failed to write {section_name}: {e}")
            return None, False

    def _parse_outline_sections(self, outline: str) -> list:
        """Parse section names from outline.

        Args:
            outline: Markdown outline

        Returns:
            List of section names (excluding title and placeholder sections)
        """
        import re

        # Extract section headers (## Section Name)
        section_pattern = r"^##\s+(.+)$"
        matches = re.findall(section_pattern, outline, re.MULTILINE)

        # Filter out any empty or placeholder sections
        sections = [
            s.strip()
            for s in matches
            if s.strip() and s.strip() != "(To be written)"
        ]

        logger.info(
            f"[Phase 1D] Parsed {len(sections)} sections from outline: {sections}"
        )
        return sections

    def _phase1d_write(self, state) -> dict:
        """Phase 1D: Synthesize notes into research document using custom outline."""
        topic = state.get("research_topic", "")
        document_path = state.get("document_path", "")
        notes_path = state.get("notes_path", "")
        thesis = state.get("thesis_statement", "")
        outline = state.get("outline", "")

        self._log_write_phase_info(thesis, outline, state)

        # Validate and load content
        notes_content = self._read_notes_file(notes_path)
        if not notes_content:
            logger.error("[Phase 1D] No notes content available to synthesize")
            return self._write_skip_state(state)

        # Prepare synthesis context
        research_summary = self._get_summary_for_context(notes_path)
        parsed_notes = self._parse_research_notes(notes_content)
        section_names = self._parse_outline_sections(outline)

        # Write all sections
        sections_written = self._write_all_sections(
            section_names,
            topic,
            parsed_notes,
            thesis,
            notes_content,
            research_summary,
            document_path,
        )

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

    def _log_write_phase_info(self, thesis: str, outline: str, state: dict):
        """Log information about write phase state."""
        logger.info(f"[Phase 1D] Synthesizing research document from notes")
        logger.info(f"[Phase 1D] Thesis from state: '{thesis}'")
        logger.info(f"[Phase 1D] Outline length: {len(outline)} chars")
        logger.info(f"[Phase 1D] State keys: {list(state.keys())}")

    def _write_skip_state(self, state: dict) -> dict:
        """Return state when skipping write phase."""
        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1e",
        }

    def _write_all_sections(
        self,
        section_names: list,
        topic: str,
        parsed_notes: dict,
        thesis: str,
        notes_content: str,
        research_summary: str,
        document_path: str,
    ) -> list:
        """Write all sections from outline."""
        previous_sections = {}
        sections_written = []

        for section_name in section_names:
            synthesize_func, args = self._get_synthesis_method(
                section_name,
                topic,
                parsed_notes,
                thesis,
                previous_sections,
                notes_content,
                research_summary,
            )

            content, success = self._write_section(
                section_name, synthesize_func, document_path, *args
            )

            if success:
                if section_name.lower() != "sources":
                    previous_sections[section_name] = content
                sections_written.append(section_name)

        return sections_written

    def _get_synthesis_method(
        self,
        section_name: str,
        topic: str,
        parsed_notes: dict,
        thesis: str,
        previous_sections: dict,
        notes_content: str = "",
        research_summary: str = "",
    ):
        """Determine the synthesis method for a section."""
        section_lower = section_name.lower()

        # Map special sections to dedicated synthesis methods
        if method_info := self._get_special_section_method(
            section_lower,
            topic,
            parsed_notes,
            thesis,
            previous_sections,
            notes_content,
            research_summary,
        ):
            return method_info

        # Default to generic synthesis
        return self._synthesize_generic_section, [
            section_name,
            topic,
            parsed_notes,
            thesis,
            previous_sections,
        ]

    def _get_special_section_method(
        self,
        section_lower: str,
        topic: str,
        parsed_notes: dict,
        thesis: str,
        previous_sections: dict,
        notes_content: str,
        research_summary: str,
    ):
        """Get synthesis method for special section types."""
        if section_lower == "abstract":
            return self._synthesize_abstract, [
                topic,
                parsed_notes,
                thesis,
                previous_sections,
                notes_content,
                research_summary,
            ]
        elif section_lower == "introduction":
            return self._synthesize_introduction, [
                topic,
                parsed_notes,
                thesis,
                previous_sections,
                500,
                notes_content,
                research_summary,
            ]
        elif self._is_background_section(section_lower):
            return self._synthesize_background, [
                topic,
                parsed_notes,
                thesis,
                previous_sections,
            ]
        elif self._is_conclusion_section(section_lower):
            return self._synthesize_conclusion, [
                topic,
                parsed_notes,
                thesis,
                previous_sections,
            ]
        elif self._is_sources_section(section_lower):
            return self._synthesize_sources, [parsed_notes]
        elif self._is_implications_section(section_lower):
            return self._synthesize_implications, [
                topic,
                parsed_notes,
                thesis,
                previous_sections,
            ]
        return None

    def _is_background_section(self, section_lower: str) -> bool:
        """Check if section is a background/history/context section."""
        return (
            "background" in section_lower
            or "history" in section_lower
            or "context" in section_lower
        )

    def _is_conclusion_section(self, section_lower: str) -> bool:
        """Check if section is a conclusion/summary section."""
        return "conclusion" in section_lower or "summary" in section_lower

    def _is_sources_section(self, section_lower: str) -> bool:
        """Check if section is a sources/references section."""
        return (
            section_lower == "sources"
            or "reference" in section_lower
            or "citation" in section_lower
        )

    def _is_implications_section(self, section_lower: str) -> bool:
        """Check if section is an implications/impact section."""
        return (
            "implication" in section_lower
            or "impact" in section_lower
            or "consequence" in section_lower
        )

        return {
            "messages": state.get("messages", []),
            "sections_written": sections_written,
            "current_phase": "phase1e",
        }
