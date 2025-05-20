# filename: formatter_extended.py

import re
import os
import tempfile
import matplotlib.pyplot as plt
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from PIL import Image, ImageDraw, ImageFont
import html
import pygments
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter


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
        Looks for common math delimiters like $...$, $$...$$, \\[...\\], etc.
        """
        # Common inline math delimiters
        if re.search(r"\$[^\$]+\$", text):
            return True
        # Common display math delimiters
        if re.search(r"\$\$[^$]+\$\$", text):
            return True
        if re.search(r"\\\\[.*\\\\]", text):
            return True
        if re.search(r"\\\\(.*\\\\)", text):
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
        Converts a Markdown string to HTML with syntax highlighting for code blocks.
        """

        # Process custom code blocks with language specification
        def process_code_blocks(text):
            # Process fenced code blocks with language specification (```python, etc.)
            # Improved pattern to handle language specifiers more accurately and support optional spaces
            pattern = r"```\s*(\w+)?\s*\n(.*?)\n\s*```"

            def replace_code_block(match):
                language = match.group(1) or "text"
                code = match.group(2)

                # Try to get lexer for the specified language
                try:
                    lexer = get_lexer_by_name(language, stripall=True)
                except pygments.util.ClassNotFound:
                    # If language is not recognized, try guessing based on content
                    try:
                        lexer = guess_lexer(code, stripall=True)
                    except pygments.util.ClassNotFound:
                        # Fallback to text if language can't be recognized or guessed
                        lexer = get_lexer_by_name("text", stripall=True)

                # Create formatter with line numbers and style class
                formatter = HtmlFormatter(
                    cssclass=f"codehilite lang-{language}",
                    linenos=True,
                    linenostart=1,
                )
                highlighted_code = highlight(code, lexer, formatter)
                return highlighted_code

            return re.sub(pattern, replace_code_block, text, flags=re.DOTALL)

        # First pass: handle code blocks with explicit language
        processed_markdown = process_code_blocks(markdown_string)

        # Second pass: use markdown's built-in processor for everything else
        extensions = [
            FencedCodeExtension(),
            CodeHiliteExtension(
                linenums=False, css_class="codehilite", noclasses=False
            ),
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
        ]

        # Get pygments CSS - use the monokai style for better dark theme compatibility
        pygments_css = HtmlFormatter(style="monokai").get_style_defs(
            ".codehilite"
        )

        # Process the markdown content
        html_content = markdown.markdown(
            processed_markdown, extensions=extensions
        )

        # Add the CSS to the HTML
        html_with_css = f"""
        <style>
        {pygments_css}
        .codehilite {{
            background: #272822;
            padding: 0;
            border-radius: 5px;
            margin: 10px 0;
            overflow-x: auto;
            border: 1px solid #3c3c3c;
        }}
        </style>
        {html_content}
        """

        return html_with_css

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
