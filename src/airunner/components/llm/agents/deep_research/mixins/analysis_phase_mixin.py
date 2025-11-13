"""Analysis phase mixin for DeepResearchAgent.

Handles Phase 1B: analyzing collected notes and formulating a central thesis statement.
"""

import logging
from pathlib import Path

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class AnalysisPhaseMixin:
    """Provides Phase 1B analysis and thesis formulation methods."""

    def _phase1b_analyze(self, state) -> dict:
        """Phase 1B: Analyze collected notes and extract key information."""
        logger.info(f"[Phase 1B] Analyzing collected notes")

        notes_path = state.get("notes_path", "")

        # Just verify notes exist
        if notes_path and Path(notes_path).exists():
            notes_size = Path(notes_path).stat().st_size
            logger.info(f"[Phase 1B] Notes file size: {notes_size} bytes")
            self._emit_progress(
                "Phase 1B", f"Analyzed {notes_size} bytes of research notes"
            )
        else:
            logger.warning(f"[Phase 1B] Notes file not found: {notes_path}")

        # Phase 1B is now just a pass-through since Phase 1A does the scraping
        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1b_thesis",
        }

    def _phase1b_thesis(self, state) -> dict:
        """Phase 1B-Thesis: Formulate central thesis/argument from collected sources."""
        topic = state.get("research_topic", "")
        notes_path = state.get("notes_path", "")

        logger.info(
            f"[Phase 1B-Thesis] Formulating central thesis for: {topic}"
        )
        self._emit_progress("Phase 1B-Thesis", "Formulating central argument")

        notes_content = self._read_thesis_notes(notes_path)
        if not notes_content:
            thesis = f"This research examines {topic} through comprehensive analysis of available sources."
            return self._create_thesis_result(state, thesis)

        thesis = self._generate_thesis_from_notes(topic, notes_content)
        return self._create_thesis_result(state, thesis)

    def _read_thesis_notes(self, notes_path: str) -> str:
        """Read notes file for thesis generation."""
        if not notes_path or not Path(notes_path).exists():
            logger.warning("[Phase 1B-Thesis] No notes file available")
            return ""

        try:
            with open(notes_path, "r", encoding="utf-8") as f:
                notes_content = f.read()
            logger.info(
                f"[Phase 1B-Thesis] Read {len(notes_content)} chars from notes"
            )
            return notes_content
        except Exception as e:
            logger.error(f"[Phase 1B-Thesis] Failed to read notes: {e}")
            return ""

    def _generate_thesis_from_notes(
        self, topic: str, notes_content: str
    ) -> str:
        """Generate thesis statement using LLM based on research notes."""
        parsed_notes = self._parse_research_notes(notes_content)
        num_sources = len(parsed_notes["sources"])
        key_entities = list(parsed_notes["entities"])[:5]
        top_themes = parsed_notes.get("top_themes", [])[:5]

        excerpts_text = self._extract_source_excerpts(parsed_notes)
        entities_text = (
            ", ".join(key_entities) if key_entities else "various stakeholders"
        )
        themes_text = (
            ", ".join(top_themes) if top_themes else "multiple themes"
        )

        prompt = self._build_thesis_prompt(
            topic, num_sources, entities_text, themes_text, excerpts_text
        )

        try:
            response = self._base_model.invoke(
                [HumanMessage(content=prompt)],
                temperature=0.3,
                max_new_tokens=256,
                repetition_penalty=1.1,
            )

            if hasattr(response, "content") and response.content:
                thesis = response.content.strip().strip('"').strip("'")
                logger.info(f"[Phase 1B-Thesis] Formulated thesis: {thesis}")
                self._emit_progress(
                    "Phase 1B-Thesis", f"Thesis: {thesis[:80]}..."
                )
                return thesis
            else:
                logger.warning(
                    "[Phase 1B-Thesis] LLM returned empty, using fallback"
                )
                return self._fallback_thesis(topic, num_sources)

        except Exception as e:
            logger.error(
                f"[Phase 1B-Thesis] LLM thesis generation failed: {e}"
            )
            return self._fallback_thesis(topic, num_sources)

    def _extract_source_excerpts(self, parsed_notes: dict) -> str:
        """Extract brief excerpts from top sources."""
        source_excerpts = []
        for source in parsed_notes["sources"][:5]:
            content = source.get("content", "")
            lines = [
                l.strip() for l in content.split("\n") if len(l.strip()) > 50
            ]
            if lines:
                source_excerpts.append(lines[0][:300])

        return (
            "\n\n".join(source_excerpts)
            if source_excerpts
            else "Research findings on the topic."
        )

    def _build_thesis_prompt(
        self,
        topic: str,
        num_sources: int,
        entities_text: str,
        themes_text: str,
        excerpts_text: str,
    ) -> str:
        """Build prompt for thesis generation."""
        return f"""You are an expert academic research writer. Based on the collected research sources, formulate a CENTRAL THESIS STATEMENT for a research paper.

RESEARCH TOPIC: {topic}

RESEARCH CONTEXT:
- Sources analyzed: {num_sources}
- Key entities: {entities_text}
- Main themes: {themes_text}

SAMPLE FINDINGS FROM SOURCES (for context):
{excerpts_text}

YOUR TASK: Formulate a clear, focused THESIS STATEMENT that:
1. Presents a specific argument or central claim about {topic}
2. Can be supported by the collected sources
3. Goes beyond mere description to make an analytical point
4. Is specific enough to guide the paper's narrative
5. Is 1-2 sentences maximum
6. Uses formal academic language

A strong thesis answers "So what?" about the topic. It should present an insight, argument, or perspective that the paper will develop and support.

EXAMPLES OF STRONG THESIS STATEMENTS:
- "Recent policy shifts regarding X demonstrate a fundamental realignment of priorities that challenges traditional assumptions about Y."
- "The contradictory statements from officials reveal a strategic ambiguity designed to manage competing domestic and international pressures."
- "Analysis of Z indicates an emerging pattern that has significant implications for future developments in this domain."

Write ONLY the thesis statement (1-2 sentences, no preamble):"""

    def _fallback_thesis(self, topic: str, num_sources: int) -> str:
        """Generate fallback thesis statement."""
        return f"This research examines {topic} through analysis of {num_sources} sources, revealing key patterns and implications."

    def _create_thesis_result(self, state, thesis: str) -> dict:
        """Create result dictionary with thesis statement."""
        return {
            "messages": state.get("messages", []),
            "thesis_statement": thesis,
            "current_phase": "phase1c",
        }
