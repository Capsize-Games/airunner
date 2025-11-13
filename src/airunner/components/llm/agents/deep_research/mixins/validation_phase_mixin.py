"""Validation phase mixin for DeepResearchAgent.

This phase validates collected notes to filter out irrelevant content
before analysis and synthesis.
"""

import logging
import re
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class ValidationPhaseMixin:
    """Provides validation phase methods for filtering collected notes."""

    def _phase1a_validate(self, state) -> dict:
        """Validate collected notes to filter out irrelevant content.

        This phase examines each note entry and uses LLM validation to determine
        if it's truly about the research subject. Filters out:
        - Different people with similar names
        - Obituaries of unrelated people
        - Age/timeline mismatches
        - Occupation/context mismatches

        Args:
            state: Current research state with notes

        Returns:
            Updated state with filtered notes
        """
        logger.info("[Phase 1A-Validate] Starting note validation")

        topic = state.get("topic", "")
        notes_content = state.get("notes_content", "")

        if not notes_content or not topic:
            logger.warning("No notes or topic to validate")
            return state

        # Parse individual note entries
        note_sections = self._parse_note_sections(notes_content)

        if not note_sections:
            logger.warning("Could not parse note sections")
            return state

        logger.info(f"Found {len(note_sections)} note sections to validate")

        # Validate each section
        validated_sections = []
        rejected_count = 0

        for i, section in enumerate(note_sections):
            logger.info(f"Validating section {i+1}/{len(note_sections)}")

            if self._validate_note_section(section, topic):
                validated_sections.append(section)
            else:
                rejected_count += 1
                logger.info(f"Rejected section {i+1} as irrelevant")

        # Reconstruct notes with only validated sections
        if validated_sections:
            header = f"# {topic}\n**Date: {state.get('timestamp', '')}**\n\n## Notes\n\n"
            validated_notes = header + "\n\n---\n\n".join(validated_sections)

            logger.info(
                f"[Phase 1A-Validate] Kept {len(validated_sections)} sections, "
                f"rejected {rejected_count} irrelevant sections"
            )

            return {
                **state,
                "notes_content": validated_notes,
                "validation_stats": {
                    "total": len(note_sections),
                    "kept": len(validated_sections),
                    "rejected": rejected_count,
                },
            }
        else:
            logger.warning("All sections rejected - keeping original notes")
            return state

    def _parse_note_sections(self, notes_content: str) -> list:
        """Parse notes content into individual sections.

        Args:
            notes_content: Full notes content

        Returns:
            List of note section strings
        """
        # Split on ### headers (individual articles/sources)
        # Pattern: ### Title [domain](url)
        sections = re.split(r"\n### ", notes_content)

        # First section is header metadata, skip it
        if len(sections) > 1:
            # Re-add ### to each section (except metadata header)
            sections = [f"### {s}" for s in sections[1:]]
            return sections

        return []

    def _validate_note_section(self, section: str, topic: str) -> bool:
        """Validate a single note section using LLM.

        Args:
            section: Note section text
            topic: Research topic

        Returns:
            True if section is relevant, False to reject
        """
        # Extract title and URL for context
        title_match = re.search(r"### (.+?) \[", section)
        url_match = re.search(r"\[.+?\]\((.+?)\)", section)

        title = title_match.group(1) if title_match else "Unknown"
        url = url_match.group(1) if url_match else "Unknown"

        # Truncate section for LLM (first 2500 chars)
        section_sample = section[:2500] if len(section) > 2500 else section

        prompt = f"""You are validating if a research note is about: "{topic}"

NOTE TITLE: {title}
SOURCE URL: {url}

NOTE CONTENT:
{section_sample}

CRITICAL TASK: Is this note about the EXACT SAME person/entity as "{topic}"?

STRICT VALIDATION RULES:

1. NAME MATCHING:
   - First name must match EXACTLY (not just similar)
   - Different first names = DIFFERENT PEOPLE (reject)
   - Last name alone is NOT enough

2. CONTEXT CONSISTENCY CHECK:
   - Does the profession/occupation match other research?
   - Does the timeline/dates align with other research?
   - Does the location match other research?
   - Are there contradictions with other known facts?

3. CONTRADICTION DETECTION:
   - If OTHER research shows software engineer and THIS shows farmer → REJECT
   - If OTHER research shows active in 2025 and THIS shows died in 2023 → REJECT
   - If OTHER research shows age 30s and THIS shows age 60s → REJECT
   - ANY major contradiction → REJECT

4. OBITUARIES:
   - Only relevant if person is confirmed dead
   - If other research shows person ALIVE/ACTIVE → obituary is WRONG PERSON → REJECT

ANSWER FORMAT:
First line: RELEVANT or REJECT
Second line: Why (one sentence)

Your answer:"""

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            decision = response.content.strip()

            # Parse response
            lines = decision.split("\n")
            verdict = lines[0].strip().upper()
            reasoning = lines[1].strip() if len(lines) > 1 else "No reasoning"

            is_relevant = "RELEVANT" in verdict

            if is_relevant:
                logger.debug(f"Validation PASS: '{title}' ({url})")
            else:
                logger.info(
                    f"Validation FAIL: '{title}' ({url}) - Reasoning: {reasoning}"
                )

            return is_relevant

        except Exception as e:
            logger.warning(
                f"Validation failed for '{title}': {e}, keeping note"
            )
            return True  # Default to keeping if validation fails
