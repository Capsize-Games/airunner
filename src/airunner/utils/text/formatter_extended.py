# filename: formatter_extended.py

import re
import os
import tempfile
import matplotlib.pyplot as plt
import markdown
from PIL import Image, ImageDraw, ImageFont
import html


class FormatterExtended:
    """
    An extended formatter that provides detailed content structure information.
    Based on the original Formatter but returning richer content details.
    """

    # Constants for recognized formats
    FORMAT_LATEX = "latex"
    FORMAT_MARKDOWN = "markdown"
    FORMAT_PLAINTEXT = "plaintext"
    FORMAT_MIXED = "mixed"

    @staticmethod
    def _is_latex(text: str) -> bool:
        """
        Heuristically checks if the given text contains LaTeX mathematical expressions.
        Looks for common math delimiters like $...$, $$...$$, \[...\], etc.
        """
        # Common inline math delimiters
        if re.search(r"\$[^\$]+\$", text):
            return True
        # Common display math delimiters
        if re.search(r"\$\$[^$]+\$\$", text):
            return True
        if re.search(r"\\\[.*\\\]", text):
            return True
        if re.search(r"\\\(.*\\\)", text):
            return True
        # Check for common LaTeX math commands
        if re.search(
            r"\\frac|\\sqrt|\\sum|\\int|\\alpha|\\beta|\\cos|\\sin", text
        ):
            return True
        return False

    @staticmethod
    def _is_pure_latex(text: str) -> bool:
        r"""
        Checks if the entire string is a LaTeX formula (not mixed with plain text).
        Accepts only if the string starts and ends with LaTeX math delimiters.
        """
        text = text.strip()
        # $$...$$
        if text.startswith("$$") and text.endswith("$$"):
            return True
        # $...$
        if text.startswith("$") and text.endswith("$"):
            return True
        # \[...\]
        if text.startswith(r"\[") and text.endswith(r"\]"):
            return True
        # \(...\)
        if text.startswith(r"\(") and text.endswith(r"\)"):
            return True
        return False

    @staticmethod
    def _is_markdown(text: str) -> bool:
        """
        Heuristically checks if the given text contains Markdown formatting.
        """
        # Headers (# Title, ## Subtitle, etc.)
        if re.search(r"^#+\s+.+$", text, re.MULTILINE):
            return True
        # Lists (- item, * item, 1. item)
        if re.search(r"^[\-\*\+]\s+.+$", text, re.MULTILINE):
            return True
        if re.search(r"^\d+\.\s+.+$", text, re.MULTILINE):
            return True
        # Emphasis (*text*, _text_, **text**, __text__)
        if re.search(
            r"\*[^\s\*][^\*]*\*|\*\*[^\s\*][^\*]*\*\*|_[^\s_][^_]*_|__[^\s_][^_]*__",
            text,
        ):
            return True
        # Code blocks (```...```)
        if re.search(r"```.*```", text, re.DOTALL):
            return True
        # Inline code (`code`)
        if re.search(r"`[^`]+`", text):
            return True
        # Links/Images
        if re.search(r"\[.+\]\(.+\)", text):
            return True
        # Blockquotes
        if re.search(r"^>\s", text, re.MULTILINE):
            return True
        return False

    @staticmethod
    def _render_markdown_to_html(markdown_string: str) -> str:
        """
        Converts a Markdown string to HTML.
        """
        return markdown.markdown(markdown_string)

    @staticmethod
    def format_content(content_string: str) -> dict:
        """
        Analyzes the input string, determines its format, and returns a detailed content structure.

        Args:
            content_string (str): The input string to analyze.

        Returns:
            dict: A dictionary containing:
                - 'type': The determined format type
                - 'content': Processed content depending on the type
                - 'original_content': The original input string
                - 'parts': For mixed content, a list of content parts with their types
        """
        # For mixed content with LaTeX formulas
        if re.search(
            r"\$\$.*?\$\$", content_string, re.DOTALL
        ) and not FormatterExtended._is_pure_latex(content_string):
            parts = []
            # Split by LaTeX delimiters
            segments = re.split(
                r"(\$\$.*?\$\$)", content_string, flags=re.DOTALL
            )
            for segment in segments:
                if segment.startswith("$$") and segment.endswith("$$"):
                    parts.append({"type": "latex", "content": segment})
                elif segment.strip():  # Skip empty text segments
                    parts.append({"type": "text", "content": segment})

            return {
                "type": FormatterExtended.FORMAT_MIXED,
                "content": parts,
                "original_content": content_string,
                "parts": parts,
            }
        # Pure LaTeX content
        elif FormatterExtended._is_pure_latex(content_string):
            return {
                "type": FormatterExtended.FORMAT_LATEX,
                "content": content_string,
                "original_content": content_string,
                "parts": [{"type": "latex", "content": content_string}],
            }
        # Markdown content
        elif FormatterExtended._is_markdown(content_string):
            html_content = FormatterExtended._render_markdown_to_html(
                content_string
            )
            return {
                "type": FormatterExtended.FORMAT_MARKDOWN,
                "content": html_content,
                "original_content": content_string,
                "parts": [{"type": "markdown", "content": html_content}],
            }
        # Plain text (default)
        else:
            return {
                "type": FormatterExtended.FORMAT_PLAINTEXT,
                "content": content_string,
                "original_content": content_string,
                "parts": [{"type": "text", "content": content_string}],
            }
