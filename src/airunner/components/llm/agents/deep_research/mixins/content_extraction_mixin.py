"""Content extraction mixin for DeepResearchAgent.

Handles LLM-based fact extraction from web content.
"""

import logging
from langchain_core.messages import HumanMessage
from airunner.components.llm.agents.deep_research.mixins.content_validation_mixin import (
    ContentValidationMixin,
)

logger = logging.getLogger(__name__)


class ContentExtractionMixin(ContentValidationMixin):
    """Provides LLM-based content extraction methods."""

    def _extract_facts_with_llm(
        self,
        raw_content: str,
        topic: str,
        url: str,
        title: str,
        metadata: dict = None,
    ) -> str:
        """Use LLM to extract relevant facts from raw web content.

        Args:
            raw_content: Raw extracted web content
            topic: Research topic
            url: Source URL
            title: Page title
            metadata: Optional metadata dict with author, publish_date, description

        Returns:
            LLM-extracted facts and notes with full source attribution
        """
        # Truncate content if too long (keep first 8000 chars for context)
        content_sample = (
            raw_content[:8000] if len(raw_content) > 8000 else raw_content
        )

        # Security Check: Scan for malicious instructions/prompt injection
        if ContentValidationMixin._contains_malicious_instructions(
            content_sample
        ):
            logger.warning(
                f"[Security] Content from {url} contains malicious instructions. Skipping extraction."
            )
            return ""

        # Build source context and prompt
        source_context = self._build_source_context(url, title, metadata)
        prompt = self._build_fact_extraction_prompt(
            topic, title, url, source_context, content_sample, metadata
        )

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            extracted_facts = response.content.strip()

            # Validate extraction
            if "NO RELEVANT FACTS" in extracted_facts.upper():
                logger.info(
                    f"[LLM Extract] No relevant facts found in {url} for topic: {topic}"
                )
                return ""

            if self._is_garbage_response(extracted_facts):
                logger.warning(
                    f"[LLM Extract] LLM returned garbage/instructions for {url}, skipping"
                )
                return ""

            logger.info(
                f"[LLM Extract] Extracted {len(extracted_facts)} chars of facts from {url}"
            )
            return extracted_facts

        except Exception as e:
            logger.error(
                f"[LLM Extract] Failed to extract facts from {url}: {e}"
            )
            return ""

    def _build_source_context(
        self, url: str, title: str, metadata: dict = None
    ) -> str:
        """Build source context header with metadata.

        Args:
            url: Source URL
            title: Page title
            metadata: Optional metadata dict

        Returns:
            Formatted source context string
        """
        author = metadata.get("author") if metadata else None
        publish_date = metadata.get("publish_date") if metadata else None
        description = metadata.get("description") if metadata else None

        source_context = f"""SOURCE INFORMATION:
Title: {title}
URL: {url}"""

        if author:
            source_context += f"\nAuthor: {author}"
        if publish_date:
            source_context += f"\nPublished: {publish_date}"
        if description:
            source_context += f"\nDescription: {description}"

        return source_context

    def _build_fact_extraction_prompt(
        self,
        topic: str,
        title: str,
        url: str,
        source_context: str,
        content_sample: str,
        metadata: dict = None,
    ) -> str:
        """Build LLM prompt for fact extraction.

        Args:
            topic: Research topic
            title: Page title
            url: Source URL
            source_context: Formatted source context
            content_sample: Truncated content
            metadata: Optional metadata

        Returns:
            Formatted prompt string
        """
        return f"""Extract comprehensive, detailed facts from this source about: "{topic}"

{source_context}

Extract ALL relevant information including:
- Key facts, claims, and statements
- Statistics, data points, and numbers  
- Quotes from officials or experts (with attribution)
- Policy details, plans, and proposals
- Dates, timelines, and context
- Opposing viewpoints and criticisms
- Background information and explanations

ANTI-HALLUCINATION RULES:
- Do NOT invent names, titles, or facts
- Only use information present in the text
- If the text is irrelevant to "{topic}", return only "NO RELEVANT FACTS"

Format as detailed bullet points:
- [detailed fact 1]
- [detailed fact 2]
- [detailed fact 3]
[... continue with ALL relevant facts ...]

TEXT TO ANALYZE:
{content_sample}
"""

    def _is_garbage_response(self, response: str) -> bool:
        """Check if LLM response contains garbage/instructions.

        Args:
            response: LLM response text

        Returns:
            True if response is garbage
        """
        garbage_indicators = [
            "For events, include",
            "Cite in-text using",
            "TASK:",
            "RULES:",
            "FORMAT:",
            "OUTPUT:",
            "Example:",
            "STRUCTURE YOUR NOTES",
            "ADDITIONAL GUIDELINES",
            "writing style, and world-building",
            "Use the following structure",
            "Use the following format",
        ]
        return any(indicator in response for indicator in garbage_indicators)
