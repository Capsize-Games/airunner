"""Document formatting mixin for DeepResearchAgent.

Provides document formatting and enhancement methods for research documents.
"""

import re
import logging
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class DocumentFormattingMixin:
    """Provides document formatting and enhancement methods."""

    def _generate_abstract(self, doc_content: str) -> tuple[str, list]:
        """Generate and insert abstract section if missing."""
        revisions = []

        if "## Abstract" in doc_content:
            return doc_content, revisions

        # Find insertion position
        lines = doc_content.split("\n")
        insert_pos = self._find_abstract_insertion_pos(lines)
        if insert_pos == 0:
            return doc_content, revisions

        # Extract context for abstract generation
        intro_text, conclusion_text = self._extract_abstract_context(
            doc_content
        )
        if not (intro_text and conclusion_text):
            return doc_content, revisions

        # Generate abstract with LLM
        abstract_text = self._generate_abstract_with_llm(
            intro_text, conclusion_text
        )
        if not abstract_text:
            return doc_content, revisions

        # Insert abstract
        abstract = f"\n\n---\n\n## Abstract\n\n{abstract_text}\n"
        lines.insert(insert_pos, abstract)
        doc_content = "\n".join(lines)
        revisions.append("Generated abstract")
        logger.info(
            f"[Phase 1F] Generated abstract via LLM: {len(abstract_text)} chars"
        )

        return doc_content, revisions

    def _find_abstract_insertion_pos(self, lines: list) -> int:
        """Find position to insert abstract."""
        for i, line in enumerate(lines):
            if line.startswith("**Status:**"):
                return i + 1
        return 0

    def _extract_abstract_context(
        self, doc_content: str
    ) -> tuple[str | None, str | None]:
        """Extract introduction and conclusion text for abstract."""
        intro_match = re.search(
            r"## Introduction\n\n(.+?)(?:\n##|$)", doc_content, re.DOTALL
        )
        conclusion_match = re.search(
            r"## Conclusion\n\n(.+?)(?:\n##|$)", doc_content, re.DOTALL
        )

        if not (intro_match and conclusion_match):
            return None, None

        intro_text = intro_match.group(1).strip()[:800]
        conclusion_text = conclusion_match.group(1).strip()[:600]
        return intro_text, conclusion_text

    def _generate_abstract_with_llm(
        self, intro_text: str, conclusion_text: str
    ) -> str | None:
        """Generate abstract text using LLM."""
        prompt = f"""Write a concise academic abstract (150-200 words) for this research paper.

INTRODUCTION EXCERPT:
{intro_text}

CONCLUSION EXCERPT:
{conclusion_text}

REQUIREMENTS:
1. Summarize the paper's scope, methods, and key findings
2. Use formal academic language
3. Be complete and coherent (no cut-off sentences)
4. Start directly with the content (no heading)
5. Length: 150-200 words

Write the abstract now:"""

        try:
            response = self._base_model.invoke(
                [HumanMessage(content=prompt)],
                temperature=0.2,
                max_new_tokens=512,
                repetition_penalty=1.2,
            )

            if hasattr(response, "content") and response.content:
                return response.content.strip()
        except Exception as e:
            logger.warning(
                f"[Phase 1F] Failed to generate abstract via LLM: {e}"
            )

        return None

    def _generate_table_of_contents(
        self, doc_content: str
    ) -> tuple[str, list]:
        """Generate and insert table of contents if missing.

        Args:
            doc_content: Current document content

        Returns:
            Tuple of (updated_content, revisions_applied)
        """
        revisions = []

        if "## Table of Contents" in doc_content:
            return doc_content, revisions

        section_headers = re.findall(r"^## (.+)$", doc_content, re.MULTILINE)
        sections = [
            s
            for s in section_headers
            if s not in ["Abstract", "Table of Contents"]
        ]

        if not sections:
            return doc_content, revisions

        lines = doc_content.split("\n")
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith("## Abstract"):
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("##") or lines[j].startswith("---"):
                        insert_pos = j
                        break
                break
            elif line.startswith("**Status:**") and insert_pos == 0:
                insert_pos = i + 1

        if insert_pos == 0:
            return doc_content, revisions

        toc = "\n\n---\n\n## Table of Contents\n\n"
        for idx, section in enumerate(sections, 1):
            toc += f"{idx}. {section}\n"
        toc += "\n"

        lines.insert(insert_pos, toc)
        doc_content = "\n".join(lines)
        revisions.append("Generated table of contents")
        logger.info(f"[Phase 1F] Generated table of contents")

        return doc_content, revisions

    def _normalize_section_spacing(self, doc_content: str) -> tuple[str, list]:
        """Normalize spacing between sections.

        Args:
            doc_content: Current document content

        Returns:
            Tuple of (updated_content, revisions_applied)
        """
        doc_content = re.sub(r"\n(## [A-Z])", r"\n\n\1", doc_content)
        doc_content = re.sub(r"\n{3,}", "\n\n", doc_content)
        return doc_content, ["Normalized section spacing"]

    def _add_source_count_to_title(self, doc_content: str) -> tuple[str, list]:
        """Add source count to document title if not present.

        Args:
            doc_content: Current document content

        Returns:
            Tuple of (updated_content, revisions_applied)
        """
        revisions = []
        source_count = len(re.findall(r"\*\*Source \d+\*\*", doc_content))

        if source_count == 0:
            return doc_content, revisions

        title_match = re.search(r"(# .+)", doc_content)
        if (
            title_match
            and f"({source_count} sources)" not in title_match.group(1)
        ):
            new_title = (
                title_match.group(1).rstrip()
                + f" ({source_count} sources analyzed)"
            )
            doc_content = doc_content.replace(
                title_match.group(1), new_title, 1
            )
            revisions.append(
                f"Added source count to title ({source_count} sources)"
            )
            logger.info(f"[Phase 1F] Added source count to title")

        return doc_content, revisions
