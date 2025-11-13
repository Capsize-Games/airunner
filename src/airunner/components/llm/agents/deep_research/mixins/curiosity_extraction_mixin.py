"""Curiosity extraction mixin for DeepResearchAgent.

Handles LLM-based fact extraction for curiosity research.
"""

import logging

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class CuriosityExtractionMixin:
    """Provides LLM fact extraction methods for curiosity research."""

    def _extract_curiosity_facts_with_llm(
        self,
        raw_content: str,
        curiosity_topic: str,
        main_topic: str,
        url: str,
        title: str,
        metadata: dict = None,
    ) -> str:
        """Use LLM to extract facts about curiosity topic."""
        content_sample = (
            raw_content[:8000] if len(raw_content) > 8000 else raw_content
        )

        prompt = self._build_curiosity_prompt(
            curiosity_topic, main_topic, title, content_sample, metadata
        )

        try:
            from langchain_core.messages import HumanMessage

            response = self._base_model.invoke([HumanMessage(content=prompt)])
            extracted_facts = response.content.strip()

            return self._validate_curiosity_facts(
                extracted_facts,
                content_sample,
                main_topic,
                title,
                curiosity_topic,
            )

        except Exception as e:
            logger.error(
                f"[Phase 1A-Curiosity] LLM fact extraction failed for {url}: {e}"
            )
            return ""

    def _build_curiosity_prompt(
        self,
        curiosity_topic: str,
        main_topic: str,
        title: str,
        content_sample: str,
        metadata: dict = None,
    ) -> str:
        """Build prompt for curiosity fact extraction."""
        return f"""DEEP-DIVE CURIOSITY RESEARCH: Extract ONLY facts about "{curiosity_topic}" that relate to the main topic "{main_topic}".

SOURCE: {title}

CONTENT:
{content_sample}

TASK: Extract 2-4 SPECIFIC FACTS about "{curiosity_topic}" from this source that connect to "{main_topic}". 

CRITICAL REQUIREMENTS:
1. Extract ONLY facts directly from the provided content
2. Focus on "{curiosity_topic}" in relation to "{main_topic}"
3. Be specific and concrete (dates, names, events, decisions)
4. DO NOT make up information
5. If no relevant facts exist, respond with "NO_RELEVANT_FACTS"

Write the extracted facts (2-4 bullet points):"""

    def _validate_curiosity_facts(
        self,
        extracted_facts: str,
        content_sample: str,
        main_topic: str,
        title: str,
        curiosity_topic: str,
    ) -> str:
        """Validate extracted curiosity facts."""
        if not extracted_facts:
            return ""

        # Check for garbage responses
        if self._is_garbage_curiosity_response(extracted_facts):
            logger.warning(
                f"[Phase 1A-Curiosity] Garbage response detected, skipping {title}"
            )
            return ""

        # Check for "no facts" responses
        if "NO_RELEVANT_FACTS" in extracted_facts.upper():
            logger.info(
                f"[Phase 1A-Curiosity] No relevant facts in {title}, skipping"
            )
            return ""

        # Ensure facts mention curiosity topic
        if curiosity_topic.lower() not in extracted_facts.lower():
            logger.warning(
                f"[Phase 1A-Curiosity] Facts don't mention '{curiosity_topic}', skipping"
            )
            return ""

        return extracted_facts

    def _is_garbage_curiosity_response(self, response: str) -> bool:
        """Check if response is garbage (meta-commentary)."""
        garbage_patterns = [
            "i cannot",
            "i can't",
            "sorry",
            "as an ai",
            "i don't have",
            "i am not able",
            "no information",
            "not mentioned",
            "does not contain",
        ]
        response_lower = response.lower()
        return any(pattern in response_lower for pattern in garbage_patterns)
