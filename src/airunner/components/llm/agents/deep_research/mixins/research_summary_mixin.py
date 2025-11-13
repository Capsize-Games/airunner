"""Research summary management mixin for DeepResearchAgent.

Handles maintaining a running summary of research notes that is updated
incrementally as new information is collected.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ResearchSummaryMixin:
    """Provides research summary management methods."""

    def _update_research_summary(
        self, notes_path: str, topic: str, new_notes_added: int = 0
    ) -> str:
        """Update the running research summary based on current notes.

        Args:
            notes_path: Path to notes file
            topic: Research topic
            new_notes_added: Number of new notes added since last summary

        Returns:
            Updated summary content
        """
        if not notes_path or not Path(notes_path).exists():
            logger.warning(
                "[Summary] Notes file not found, cannot update summary"
            )
            return ""

        try:
            # Read current notes
            with open(notes_path, "r", encoding="utf-8") as f:
                notes_content = f.read()

            # Extract just the notes section
            if "## Notes" in notes_content:
                notes_only = notes_content.split("## Notes", 1)[1]
            else:
                notes_only = notes_content

            # Get existing summary if any
            summary_path = (
                Path(notes_path).parent / f"{Path(notes_path).stem}.summary.md"
            )
            existing_summary = ""
            if summary_path.exists():
                with open(summary_path, "r", encoding="utf-8") as f:
                    existing_summary = f.read()

            # Generate updated summary using LLM
            summary = self._generate_summary_with_llm(
                topic, notes_only, existing_summary, new_notes_added
            )

            # Save summary
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary)

            logger.info(
                f"[Summary] Updated research summary ({len(summary)} chars)"
            )
            return summary

        except Exception as e:
            logger.error(f"[Summary] Failed to update summary: {e}")
            return existing_summary

    def _generate_summary_with_llm(
        self,
        topic: str,
        notes_content: str,
        existing_summary: str,
        new_notes_count: int,
    ) -> str:
        """Generate or update research summary using LLM."""
        notes_sample, truncated_msg = self._prepare_notes_sample(notes_content)
        prompt = self._build_summary_prompt(
            topic,
            notes_sample,
            truncated_msg,
            existing_summary,
            new_notes_count,
        )

        try:
            from langchain_core.messages import HumanMessage

            response = self._base_model.invoke([HumanMessage(content=prompt)])
            summary = response.content.strip()
            return self._format_summary_with_header(
                topic, summary, notes_content
            )

        except Exception as e:
            logger.error(f"[Summary] LLM summary generation failed: {e}")
            return self._get_fallback_summary(topic, existing_summary)

    def _prepare_notes_sample(self, notes_content: str) -> tuple[str, str]:
        """Prepare notes sample for LLM processing."""
        if len(notes_content) > 12000:
            notes_sample = notes_content[-12000:]
            truncated_msg = (
                f"[Showing most recent ~12000 characters of notes]\n\n"
            )
        else:
            notes_sample = notes_content
            truncated_msg = ""
        return notes_sample, truncated_msg

    def _build_summary_prompt(
        self,
        topic: str,
        notes_sample: str,
        truncated_msg: str,
        existing_summary: str,
        new_notes_count: int,
    ) -> str:
        """Build prompt for summary generation."""
        base_instructions = """Your summary (300-500 words) should be a COHESIVE NARRATIVE that includes:
- Main findings and key facts from the research
- Timeline of important events and decisions
- Key people, organizations, and their roles
- Emerging themes and patterns across sources
- Significant implications or outcomes

CRITICAL REQUIREMENTS:
1. Write in flowing paragraphs (3-5 paragraphs)
2. DO NOT use the note structure (no ### headers, no "Summary:", no "Interesting facts:")
3. DO NOT list individual articles or sources
4. SYNTHESIZE information across sources into a unified narrative
5. Use clear topic sentences and transitions between ideas"""

        if existing_summary:
            return f"""CRITICAL: Do NOT copy the note format. Write a COHESIVE NARRATIVE SUMMARY.

You are updating a research summary on: {topic}

EXISTING SUMMARY:
{existing_summary}

RECENT RESEARCH NOTES ({new_notes_count} new entries):
{truncated_msg}{notes_sample}

TASK: Update the summary by SYNTHESIZING the information into flowing prose. You are NOT copying or reformatting notes.

{base_instructions}

Write the updated narrative summary now:"""
        else:
            return f"""CRITICAL: Do NOT copy the note format. Write a COHESIVE NARRATIVE SUMMARY.

You are creating a research summary on: {topic}

RESEARCH NOTES:
{truncated_msg}{notes_sample}

TASK: Create a comprehensive summary by SYNTHESIZING the information into flowing prose. You are NOT copying or reformatting notes.

{base_instructions}

Write the narrative summary now:"""

    def _format_summary_with_header(
        self, topic: str, summary: str, notes_content: str
    ) -> str:
        """Format summary with metadata header."""
        from datetime import datetime

        header = f"""# Research Summary: {topic}
**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Notes Analyzed:** {len(notes_content.split('###'))} entries

---

"""
        return header + summary

    def _get_fallback_summary(self, topic: str, existing_summary: str) -> str:
        """Get fallback summary on error."""
        return (
            existing_summary
            if existing_summary
            else f"Research summary for: {topic}\n\nSummary generation in progress..."
        )

    def _get_summary_for_context(self, notes_path: str) -> str:
        """Get research summary for use in writing context.

        Args:
            notes_path: Path to notes file

        Returns:
            Summary content for system prompt
        """
        if not notes_path:
            return ""

        summary_path = (
            Path(notes_path).parent / f"{Path(notes_path).stem}.summary.md"
        )

        if not summary_path.exists():
            logger.info("[Summary] No summary available yet")
            return ""

        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"[Summary] Failed to read summary: {e}")
            return ""
