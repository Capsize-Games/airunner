"""Document formatting mixin for DeepResearchAgent.

Provides document formatting and enhancement methods for research documents.
"""

import re
import logging
from langchain_core.messages import HumanMessage, SystemMessage

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
            messages = [HumanMessage(content=prompt)]
            system_prompt = (
                self._get_synthesis_system_prompt()
                if hasattr(self, "_get_synthesis_system_prompt")
                else getattr(self, "_synthesis_system_prompt", None)
            )
            if not system_prompt:
                system_prompt = getattr(self, "_system_prompt", None)
            if system_prompt:
                messages.insert(0, SystemMessage(content=system_prompt))
            response = self._base_model.invoke(
                messages,
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

        # Filter out duplicates while preserving order
        seen_sections = set()
        sections = []
        for s in section_headers:
            # Skip Abstract, TOC
            if s in ["Abstract", "Table of Contents"]:
                continue

            # If we see "Sources" more than once, only include it once in TOC
            if s == "Sources" and "Sources" in seen_sections:
                continue

            if s not in seen_sections:
                sections.append(s)
                seen_sections.add(s)

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

    def _deduplicate_sections(self, doc_content: str) -> tuple[str, list]:
        """Remove duplicate sections from document.

        Args:
            doc_content: Current document content

        Returns:
            Tuple of (updated_content, revisions_applied)
        """
        revisions = []

        # Find all section headers
        section_headers = list(
            re.finditer(r"^## (.+)$", doc_content, re.MULTILINE)
        )

        if not section_headers:
            return doc_content, revisions

        seen_sections = set()
        sections_to_remove = []

        # Identify duplicates (keep the LAST occurrence as it's likely the most updated/corrected one)
        # We iterate in reverse to easily identify which ones to keep
        for match in reversed(section_headers):
            section_name = match.group(1).strip()

            if section_name in seen_sections:
                # This is a duplicate (and since we're reversing, it's an earlier one)
                # We should remove it
                sections_to_remove.append(match)
            else:
                seen_sections.add(section_name)

        if not sections_to_remove:
            return doc_content, revisions

        # Remove duplicates
        # We need to be careful about ranges. Since we're modifying the string,
        # it's safer to split by sections and rebuild, or use string replacement carefully.
        # Given the structure, splitting by "## " might be safer.

        parts = re.split(r"(^## .+)", doc_content, flags=re.MULTILINE)
        # parts[0] is preamble (title etc)
        # parts[1] is header 1, parts[2] is content 1
        # parts[3] is header 2, parts[4] is content 2

        new_parts = [parts[0]]
        seen_headers = set()

        # Process sections in reverse order to keep the last one
        # But we need to reconstruct in forward order

        # Let's collect all sections first
        sections = []
        for i in range(1, len(parts), 2):
            header = parts[i]
            content = parts[i + 1] if i + 1 < len(parts) else ""
            sections.append((header, content))

        # Filter duplicates (keeping last)
        unique_sections = []
        seen_headers_set = set()

        for header, content in reversed(sections):
            header_clean = header.replace("## ", "").strip()
            if header_clean not in seen_headers_set:
                unique_sections.insert(0, (header, content))
                seen_headers_set.add(header_clean)
            else:
                revisions.append(f"Removed duplicate section: {header_clean}")

        # Reconstruct document
        new_content = new_parts[0]
        for header, content in unique_sections:
            new_content += header + content

        if revisions:
            logger.info(
                f"[Phase 1F] Removed {len(revisions)} duplicate sections"
            )

        return new_content, revisions
