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

        original_length = len(content)

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

        # Remove meta-commentary at the end
        content = re.sub(
            r"\n+(?:Note|Disclaimer|Warning):.*?$",
            "",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove paragraph-level duplication (more than 2 consecutive identical paragraphs)
        content = OutputCleaningMixin._remove_duplicate_paragraphs(content)

        # Clean up whitespace
        content = content.strip()

        # Log if significant cleaning occurred
        cleaned_length = len(content)
        if original_length - cleaned_length > 100:
            logger.info(
                f"[Cleaning] Removed {original_length - cleaned_length} chars of artifacts "
                f"from {section_name or 'output'}"
            )

        return content

    @staticmethod
    def _remove_duplicate_paragraphs(content: str) -> str:
        """Remove consecutive duplicate paragraphs.

        Args:
            content: Text content with potential duplicates

        Returns:
            Content with duplicates removed
        """
        # Split into paragraphs
        paragraphs = re.split(r"\n\n+", content)

        if len(paragraphs) <= 2:
            return content

        # Track consecutive duplicates
        cleaned_paragraphs = []
        prev_para = None
        consecutive_count = 0

        for para in paragraphs:
            para_normalized = para.strip()

            if not para_normalized:
                continue

            # Check if this is a duplicate of the previous paragraph
            if para_normalized == prev_para:
                consecutive_count += 1
                # Keep first two occurrences, remove rest
                if consecutive_count <= 1:
                    cleaned_paragraphs.append(para)
            else:
                # New paragraph
                cleaned_paragraphs.append(para)
                prev_para = para_normalized
                consecutive_count = 0

        # Rejoin with double newlines
        cleaned = "\n\n".join(cleaned_paragraphs)

        # Log if significant deduplication occurred
        original_paras = len(paragraphs)
        cleaned_paras = len(cleaned_paragraphs)
        if original_paras - cleaned_paras > 2:
            logger.warning(
                f"[Cleaning] Removed {original_paras - cleaned_paras} duplicate paragraphs "
                f"({original_paras} → {cleaned_paras})"
            )

        return cleaned

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
