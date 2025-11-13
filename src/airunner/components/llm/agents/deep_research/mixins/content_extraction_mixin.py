"""Content extraction mixin for DeepResearchAgent.

Handles LLM-based fact extraction from web content.
"""

import logging
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class ContentExtractionMixin:
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
        author = metadata.get("author") if metadata else None
        publish_date = metadata.get("publish_date") if metadata else None

        return f"""Analyze this article about "{topic}" and create structured research notes.

SOURCE: {title}
URL: {url}
{f"Author: {author}" if author else ""}
{f"Published: {publish_date}" if publish_date else ""}

ARTICLE TEXT:
{content_sample}

CRITICAL INSTRUCTIONS - FICTION vs FACTUAL CONTENT:
1. FIRST determine if this article is FICTION (story, novel, creative writing) or FACTUAL (news, biography, documentation, reference material, profiles, portfolios)
2. Fiction markers include: "Chapter", "Prologue", "Epilogue", dialogue in quotes, narrative storytelling style, "he thought", "she whispered", fictional character names, plot-driven content
3. FACTUAL markers include: Professional profiles (GitHub, LinkedIn, personal websites), portfolios, resumes, news articles, documentation, biographies, company info
4. GitHub profiles, personal websites, and professional portfolios are ALWAYS FACTUAL - never mark them as fiction
5. If FICTION: Label as "FICTION" and explain it's a creative work
6. If FACTUAL: Label as "FACTUAL"
7. If UNCERTAIN: State "LIKELY FACTUAL" (default to factual unless clear fiction markers)

IMPORTANT - HOW TO HANDLE EACH TYPE:
- For FICTION: Include it in your notes! Fiction is valuable context (shows author's creative work). Clearly label as fiction and focus on METADATA (author, publication date, genre, themes) NOT the fictional plot as real events.
- For FACTUAL: Extract facts normally, treating content as reliable information about real events/people/topics.

Example FICTION handling:
  Content Type: FICTION - This is a science fiction short story
  Summary: "The Last War" is a science fiction story by Joe Curlee, published [date]. It explores themes of [X, Y, Z]. This is creative fiction, not factual events.
  Interesting facts: 
  - Published on [date]
  - Genre: Science fiction
  - Author: Joe Curlee

Create notes in this EXACT format (if article is irrelevant, return only "NO RELEVANT FACTS"):

#### Content Type
[FICTION or FACTUAL - state clearly which this is and why]

#### Summary
[If FICTION: Describe the work itself (title, author, publication, genre) - NOT the plot as real events]
[If FACTUAL: Write a comprehensive 4-6 sentence summary covering: 1) The main topic/event, 2) Key decisions or actions taken, 3) Important context or background, 4) Outcomes or implications mentioned in the article]

#### Interesting facts
- [Fact with date/source]
- [Another fact]

#### More research required
- [Topic needing deeper investigation]

#### How does this relate to the original query?
[2-3 sentences explaining relevance to "{topic}"]

#### My thoughts on this article
[1-2 sentences on source credibility/value]

#### Citations
- [Person/source quoted]"""

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
        ]
        return any(indicator in response for indicator in garbage_indicators)
