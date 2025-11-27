"""Output cleaning mixin for DeepResearchAgent.

Provides comprehensive cleaning of LLM outputs to remove artifacts, instructions, and duplication.
"""

import re
import logging

logger = logging.getLogger(__name__)


class OutputCleaningMixin:
    """Provides output cleaning methods for LLM-generated content."""

    @staticmethod
    def _clean_llm_output(content: str, section_name: str = "") -> str:
        """Clean LLM output by removing artifacts, instructions, and duplication.

        Args:
            content: Raw LLM output
            section_name: Name of the section (for logging)

        Returns:
            Cleaned content
        """
        if not content:
            return content

        len(content)

        # Remove markdown code fences
        content = re.sub(r"^```(?:markdown)?\n", "", content)
        content = re.sub(r"\n```$", "", content)

        # Remove conversational preambles
        conversational_patterns = [
            r"^.*?here is the (?:revised|rewritten|corrected|section|content).*?:\s*\n+",
            r"^.*?here's the (?:revised|rewritten|corrected|section|content).*?:\s*\n+",
            r"^.*?below is the (?:revised|rewritten|corrected|section|content).*?:\s*\n+",
            r"^.*?(?:revised|rewritten|corrected) (?:section|content) below.*?:\s*\n+",
            r"^.*?please correct the issues.*?(?:revised|corrected) text.*?:\s*\n+",
            r"^please correct the issues.*?\n+",
        ]
        for pattern in conversational_patterns:
            content = re.sub(
                pattern, "", content, flags=re.IGNORECASE | re.DOTALL
            )

        # Remove "Tool call:" instructions (critical for deep research)
        content = re.sub(
            r"Tool call:.*?(?:\n|$)", "", content, flags=re.IGNORECASE
        )

        # Remove "Call the relevant tools" placeholders
        content = re.sub(
            r"Call the relevant tools.*?(?:\n|$)",
            "",
            content,
            flags=re.IGNORECASE,
        )

        # Remove inline tool-call snippets such as `tool_call("...")` or `text-extract(...)`
        content = re.sub(
            r"^`?(?:tool_call|text-[\w-]+)\([^`]*\)`?(?:assistant)?$",
            "",
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        # Remove instruction-style text
        instruction_patterns = [
            r"^.*?(?:write|generate|create) (?:a|the) section.*?:\s*\n+",
            r"^.*?(?:write|generate|create) (?:only|just) the.*?:\s*\n+",
            r"^.*?no labels.*?headers.*?\n+",
        ]
        for pattern in instruction_patterns:
            content = re.sub(
                pattern, "", content, flags=re.IGNORECASE | re.DOTALL
            )

        # Remove one-line meta instructions that sometimes slip through prompts
        meta_line_patterns = [
            r"^(?:next|previous|following) section.*$",
            r"^here is the requested section.*$",
            r"^here is the section.*$",
            r"^timeline is unclear.*$",
            r"^highlights? the significance of the findings.*$",
            r"^unclear,? use phrases? like.*$",
            r"^background:? unclear.*$",
            r"^literature review:? unclear.*$",
            r"^methodology:? unclear.*$",
            r"^his previous term.*to refer to.*$",
        ]
        for pattern in meta_line_patterns:
            content = re.sub(
                pattern,
                "",
                content,
                flags=re.IGNORECASE | re.MULTILINE,
            )

        # Remove emoji markers (🔍, etc.) and their following instruction lines
        content = re.sub(
            r"[🔍✅❌⚠️🚨]\s*(?:CRITICAL:?)?\s*[A-Z][^\n]*",
            "",
            content,
        )

        # Remove standalone instruction phrases that appear as content
        content = re.sub(
            r"^\s*(?:SOURCES|AVOID ASSUMPTIONS|VERIFY|TIMELINE ACCURACY)\s*$",
            "",
            content,
            flags=re.MULTILINE,
        )

        # Remove single-line reminders that explicitly instruct on citing evidence
        instructional_line_phrases = [
            "paraphrased statement should be supported",
            "avoid making claims that",  # e.g., "avoid making claims that aren't supported..."
            "reference the evidence;",
            "cite the evidence rather than",
        ]
        for phrase in instructional_line_phrases:
            content = re.sub(
                rf"^.*{re.escape(phrase)}.*$",
                "",
                content,
                flags=re.IGNORECASE | re.MULTILINE,
            )

        content = OutputCleaningMixin._remove_duplicate_headers(content)

        # Remove single instructional bullet points
        content = re.sub(
            r"(?:^|\n)\s*-\s*(?:Use|Ensure|Avoid|Do not|Keep|Maintain|Write|Include|Focus)\b[^\n]*\n",
            "\n",
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        # Remove blocks of instructional bullet points (e.g., "- Use the ..." guidelines)
        # Expanded to catch 2+ bullets and more keywords
        content = re.sub(
            r"(?:^|\n)(?:[A-Z][^\n]*?:)?\s*(?:-\s*(?:Use|Ensure|Avoid|Do not|Keep|Maintain|Write|Include|Focus)[^\n]*\n){2,}",
            "\n",
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        # Remove isolated instruction lines like "objective, and informative."
        content = re.sub(
            r"^\s*(?:objective|informative|professional|comprehensive)(?:, (?:objective|informative|professional|comprehensive))*\.\s*$",
            "",
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        # Remove sections that are effectively empty (just punctuation or very short)
        # We do this by finding headers and checking the content until the next header
        content = OutputCleaningMixin._remove_empty_sections(content)

        return content.strip()

    @staticmethod
    def _remove_empty_sections(content: str) -> str:
        """Remove sections that have no meaningful content."""

        # Split by headers
        # We use a capture group to keep the delimiter
        parts = re.split(r"(^## .+?$)", content, flags=re.MULTILINE)

        if len(parts) < 2:
            return content

        new_content = [parts[0]]  # Keep preamble

        i = 1
        while i < len(parts):
            header = parts[i]
            if i + 1 < len(parts):
                section_body = parts[i + 1]
                # Check if body is empty or just whitespace/punctuation
                clean_body = re.sub(r"[\s\.\-\*]+", "", section_body)
                if len(clean_body) < 10:  # Threshold for "empty"
                    # Skip this section (header and body)
                    logger.warning(f"Removing empty section: {header.strip()}")
                    i += 2
                    continue

                new_content.append(header)
                new_content.append(section_body)
                i += 2
            else:
                # Last header without body?
                new_content.append(header)
                i += 1

        return "".join(new_content)

    @staticmethod
    def _remove_duplicate_headers(content: str) -> str:
        """Collapse patterns like '## Title' followed by a setext version of the same title."""

        if not content:
            return content

        pattern = re.compile(
            r"(##\s+([^\n]+))\n+(?:\s*\n)*\s*\2\s*\n[=-]{3,}",
            re.IGNORECASE,
        )

        def _replace(match: re.Match) -> str:
            return match.group(1)

        return re.sub(pattern, _replace, content)

    @staticmethod
    def _detect_incomplete_generation(content: str) -> bool:
        """Detect if content is incomplete (truncated mid-sentence).

        Args:
            content: Generated content

        Returns:
            True if content appears incomplete
        """
        if not content:
            return True

        # Check if ends mid-sentence (no proper punctuation)
        last_100 = content[-100:].strip()

        # Should end with sentence-ending punctuation
        if not re.search(r"[.!?\"']$", last_100):
            logger.warning(
                "[Validation] Content appears incomplete (no ending punctuation)"
            )
            return True

        # Check for common truncation patterns
        truncation_patterns = [
            r"it remains to be seen$",
            r"will have$",
            r"is likely to$",
            r"may lead to$",
        ]

        for pattern in truncation_patterns:
            if re.search(pattern, last_100, re.IGNORECASE):
                logger.warning(
                    f"[Validation] Content appears truncated (pattern: {pattern})"
                )
                return True

        return False
