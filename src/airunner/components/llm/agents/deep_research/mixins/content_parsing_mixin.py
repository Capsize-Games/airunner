"""Content parsing mixin for DeepResearchAgent.

This mixin provides parsing and validation methods for research content.
"""

import re
import logging

logger = logging.getLogger(__name__)


class ContentParsingMixin:
    """Provides content parsing and validation methods."""

    # Anti-hallucination constraints for synthesis prompts
    ANTI_HALLUCINATION_RULES = """
CRITICAL CONSTRAINTS - FOLLOW THESE STRICTLY:
1. ONLY write about information that appears in the provided sources
2. DO NOT invent projects, products, games, companies, or any other details not in sources
3. DO NOT fabricate names of things (games, software, organizations, people, etc.)
4. If sources mention specific entities, use ONLY those exact names from the sources
5. DO NOT use generic examples or hypothetical scenarios not mentioned in sources
6. When in doubt, be more general rather than inventing specifics
7. If you don't have enough information, say so - don't make things up
8. STICK TO FACTS FROM SOURCES - no fabrication allowed"""

    def _parse_research_notes(self, notes_content: str) -> dict:
        """Parse research notes to extract structured information."""
        parsed = {
            "sources": [],
            "entities": set(),
            "dates": set(),
            "themes": {},
            "curiosity_topics": [],
        }

        source_sections = re.split(r"\n(?=###\s+https?://)", notes_content)

        for section in source_sections:
            if not section.strip():
                continue

            curiosity_match = re.search(
                r"\*\*CURIOSITY DEEP-DIVE: (.+?)\*\*", section
            )
            is_curiosity = curiosity_match is not None
            curiosity_topic = (
                curiosity_match.group(1) if is_curiosity else None
            )

            url_match = re.search(r"###\s+(https?://\S+)", section)
            if not url_match:
                url_match = re.search(r"URL:\s+(https?://\S+)", section)
            url = url_match.group(1) if url_match else "Unknown"

            title_match = re.search(r"Title:\s+(.+?)(?:\n|$)", section)
            title = title_match.group(1).strip() if title_match else None

            extract_match = re.search(
                r"Extract:\s+(.+?)(?:\n---|\n###|$)", section, re.DOTALL
            )
            if extract_match:
                content = extract_match.group(1).strip()
            else:
                lines = section.split("\n")
                content_start = (
                    next(
                        (
                            i
                            for i, line in enumerate(lines)
                            if line.startswith("URL:")
                        ),
                        -1,
                    )
                    + 1
                )
                content = (
                    "\n".join(lines[content_start:]).strip()
                    if content_start > 0
                    else section.strip()
                )

            source_info = {
                "url": url,
                "title": title,
                "content": content,
                "is_curiosity": is_curiosity,
                "curiosity_topic": curiosity_topic,
            }
            parsed["sources"].append(source_info)

            entities = re.findall(
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", content
            )
            parsed["entities"].update(entities)

            dates = re.findall(
                r"\b(?:January|February|March|April|May|June|July|August|September|"
                r"October|November|December)\s+\d{1,2},?\s+\d{4}\b",
                content,
            )
            dates += re.findall(r"\b\d{4}\b", content)
            parsed["dates"].update(dates)

            words = re.findall(r"\b[a-z]{4,}\b", content.lower())
            for word in words:
                if word not in [
                    "that",
                    "this",
                    "with",
                    "from",
                    "have",
                    "been",
                    "were",
                    "will",
                ]:
                    parsed["themes"][word] = parsed["themes"].get(word, 0) + 1

        for source in parsed["sources"]:
            if source["is_curiosity"] and source["curiosity_topic"]:
                parsed["curiosity_topics"].append(source["curiosity_topic"])

        top_themes = sorted(
            parsed["themes"].items(), key=lambda x: x[1], reverse=True
        )[:10]
        parsed["top_themes"] = [theme for theme, _ in top_themes]

        return parsed

    def _validate_synthesized_content(
        self, content: str, section_name: str
    ) -> tuple[bool, str]:
        """Validate synthesized section content for quality and hallucination checks."""
        if not content or len(content.strip()) < 100:
            return False, f"{section_name} content too short (< 100 chars)"

        hallucination_markers = [
            "for example",
            "such as minecraft",
            "such as fortnite",
            "like roblox",
            "popular games include",
            "well-known examples",
            "commonly used",
        ]

        content_lower = content.lower()
        found_markers = [
            m for m in hallucination_markers if m in content_lower
        ]
        if found_markers:
            logger.warning(
                f"{section_name} may contain hallucinations (markers: {found_markers})"
            )

        sentences = re.split(r"[.!?]+", content)
        if len(sentences) < 2:
            return False, f"{section_name} lacks proper sentence structure"

        return True, ""

    @staticmethod
    def _normalize_temporal_references(text: str) -> str:
        """Normalize temporal references to be more evergreen."""
        text = re.sub(r"\btoday\b", "currently", text, flags=re.IGNORECASE)
        text = re.sub(r"\bnow\b", "at present", text, flags=re.IGNORECASE)
        text = re.sub(
            r"\brecently\b", "in recent times", text, flags=re.IGNORECASE
        )
        return text

    @staticmethod
    def _get_domain_name(url: str) -> str:
        """Extract clean domain name from URL."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            domain = domain.replace("www.", "")
            domain = domain.split("/")[0]
            return domain
        except Exception:
            return "source"

    def _synthesize_sources(self, parsed_notes: dict) -> str:
        """Generate sources/references section."""
        if not parsed_notes.get("sources"):
            return "## Sources\n\nNo sources available."

        sources_list = []
        seen_urls = set()

        for source in parsed_notes["sources"]:
            url = source.get("url", "Unknown")
            if url in seen_urls or url == "Unknown":
                continue

            seen_urls.add(url)
            title = source.get("title") or self._get_domain_name(url)

            sources_list.append(f"- [{title}]({url})")

        sources_text = "\n".join(sources_list)
        return f"## Sources\n\n{sources_text}"
