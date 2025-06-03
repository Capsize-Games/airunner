import re
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
import pygments
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
import logging

# Suppress noisy markdown extension debug logs
logging.getLogger("MARKDOWN").setLevel(logging.WARNING)
logging.getLogger("markdown").setLevel(logging.WARNING)


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
        Accepts both single and double backslashes for robustness.
        """
        # Common inline math delimiters
        if re.search(r"\$[^\$]+\$", text):
            return True
        # Common display math delimiters
        if re.search(r"\$\$[^$]+\$\$", text):
            return True
        # Accept both single and double backslash for \[...\] and \(...\)
        if re.search(r"(\\\\|\\)\[.*(\\\\|\\)\]", text):
            return True
        if re.search(r"(\\\\|\\)\(.*(\\\\|\\)\)", text):
            return True
        # Check for common LaTeX math commands
        if re.search(r"\\frac|\\sqrt|\\sum|\\int|\\alpha|\\beta|\\cos|\\sin", text):
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
        For code blocks with language 'markdown', always use the TextLexer to preserve newlines and formatting.
        """
        num_triple_backticks = markdown_string.count("```")
        if num_triple_backticks % 2 == 1:
            markdown_string += "\n```"

        def process_code_blocks(text):
            pattern = r"```\s*(\w+)?\s*\n(.*?)\n\s*```"

            def replace_code_block(match):
                language = match.group(1) or "text"
                code = match.group(2)
                if language.lower() == "markdown":
                    from pygments.lexers.special import TextLexer

                    lexer = TextLexer(stripall=True)
                else:
                    try:
                        lexer = get_lexer_by_name(language, stripall=True)
                    except pygments.util.ClassNotFound:
                        try:
                            lexer = guess_lexer(code, stripall=True)
                        except pygments.util.ClassNotFound:
                            from pygments.lexers.special import TextLexer

                            lexer = TextLexer(stripall=True)
                formatter = HtmlFormatter(
                    cssclass=f"codehilite lang-{language}",
                    linenos=True,
                    linenostart=1,
                    linenospecial=0,
                    lineseparator="\n",  # Force newline between lines
                    hl_lines=[],
                )
                highlighted_code = highlight(code, lexer, formatter)
                # Patch: If language is 'markdown', forcibly replace <span> line separators with <br> to preserve newlines
                if language.lower() == "markdown":
                    import re

                    # Replace any span-based line separators with <br> if present
                    highlighted_code = re.sub(
                        r'(</span>)(<span class="[^\"]+">)',
                        r"\1<br>\2",
                        highlighted_code,
                    )
                return highlighted_code

            return re.sub(pattern, replace_code_block, text, flags=re.DOTALL)

        processed_markdown = process_code_blocks(markdown_string)

        extensions = [
            FencedCodeExtension(),
            CodeHiliteExtension(
                linenums=False, css_class="codehilite", noclasses=False
            ),
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
        ]
        pygments_css = HtmlFormatter(style="monokai").get_style_defs(".codehilite")
        # Ensure pre/code blocks preserve newlines
        extra_css = ".codehilite pre { white-space: pre-wrap !important; }"
        html_content = markdown.markdown(processed_markdown, extensions=extensions)
        html_with_css = f"""
        <style>
        {pygments_css}
        {extra_css}
        .codehilite {{
            background: #272822;
            padding: 0;
            border-radius: 5px;
            margin: 10px 0;
            overflow-x: auto;
            border: 1px solid #3c3c3c;
        }}
        .linenodiv {{
            background-color: #262626;
            border-right: 1px solid #444;
            padding: 3px 5px 3px 3px;
            color: #777;
            text-align: right;
            user-select: none;
            margin-right: 5px;
        }}
        .codehilite pre {{
            margin: 0;
            padding: 10px 5px 10px 5px;
            background-color: transparent;
            border: none;
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
        # Always treat triple-backtick code blocks as markdown, even if mixed
        if re.search(r"```.*```", content_string, re.DOTALL):
            html_content = FormatterExtended._render_markdown_to_html(content_string)
            return {
                "type": FormatterExtended.FORMAT_MARKDOWN,
                "content": html_content,
                "original_content": content_string,
                "parts": [{"type": "markdown", "content": html_content}],
            }
        # For mixed content with LaTeX formulas
        if re.search(
            r"\$\$.*?\$\$", content_string, re.DOTALL
        ) and not FormatterExtended._is_pure_latex(content_string):
            parts = []
            # Split by LaTeX delimiters
            segments = re.split(r"(\$\$.*?\$\$)", content_string, flags=re.DOTALL)
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
            html_content = FormatterExtended._render_markdown_to_html(content_string)
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

    @staticmethod
    def strip_nonlinguistic(text: str) -> str:
        r"""
        Remove LaTeX, code blocks, and inline code from the text to improve language detection.
        - Removes LaTeX ($...$, $$...$$, \\[...\\], \\(...\\))
        - Removes fenced code blocks (```...```)
        - Removes inline code (`...`)
        """
        # Remove LaTeX math environments
        text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.DOTALL)  # $$...$$
        text = re.sub(r"\$[^$]+\$", " ", text)  # $...$
        text = re.sub(r"\\\[.*?\\\]", " ", text, flags=re.DOTALL)  # \[...\]
        text = re.sub(r"\\\(.*?\\\)", " ", text, flags=re.DOTALL)  # \(...\)
        # Remove fenced code blocks (```...```)
        text = re.sub(r"```[\w\W]*?```", " ", text)
        # Remove inline code (`...`)
        text = re.sub(r"`[^`]+`", " ", text)
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def to_speakable_text(text: str) -> str:
        """
        Converts input text to a version suitable for text-to-speech:
        - Replaces code blocks and inline code with a placeholder (e.g., "[code block omitted]").
        - Replaces LaTeX math with a speakable version (removes delimiters, optionally replaces common LaTeX commands with words),
          and inserts a 1 second pause after the word 'formula'.
        - Leaves natural language text untouched.
        """
        # Replace code blocks (```...```)
        text = re.sub(r"```[\w\W]*?```", "[code block omitted]", text)
        # Replace inline code (`...`)
        text = re.sub(r"`[^`]+`", "[inline code omitted]", text)

        # Replace LaTeX math environments with a speakable version
        def latex_to_speakable(match):
            latex = match.group(0)
            # Remove delimiters
            if latex.startswith("$$") and latex.endswith("$$"):
                latex = latex[2:-2]
            elif latex.startswith("$") and latex.endswith("$"):
                latex = latex[1:-1]
            elif latex.startswith(r"\\[") and latex.endswith(r"\\]"):
                latex = latex[2:-2]
            elif latex.startswith(r"\\(") and latex.endswith(r"\\)"):
                latex = latex[2:-2]
            # Optionally, replace some common LaTeX commands with words
            replacements = [
                (r"\\frac\s*{([^}]*)}\s*{([^}]*)}", r"fraction \1 over \2"),
                (r"\\sqrt\s*{([^}]*)}", r"square root of \1"),
                (r"\\sum", "sum"),
                (r"\\int", "integral"),
                (r"\\alpha", "alpha"),
                (r"\\beta", "beta"),
                (r"\\cos", "cosine"),
                (r"\\sin", "sine"),
                (r"\\theta", "theta"),
                (r"\\pi", "pi"),
            ]
            for pattern, repl in replacements:
                latex = re.sub(pattern, repl, latex)
            # Remove remaining backslashes (for simple symbols)
            latex = re.sub(r"\\([a-zA-Z]+)", r"\1", latex)
            # Collapse whitespace
            latex = re.sub(r"\s+", " ", latex)
            # Just return a speakable formula, no pause markup
            return f"[formula: {latex.strip()}]"

        # Replace $$...$$
        text = re.sub(r"\$\$.*?\$\$", latex_to_speakable, text, flags=re.DOTALL)
        # Replace $...$
        text = re.sub(r"\$[^$]+\$", latex_to_speakable, text)
        # Replace \[...\]
        text = re.sub(r"\\\[.*?\\\]", latex_to_speakable, text, flags=re.DOTALL)
        # Replace \(...\)
        text = re.sub(r"\\\(.*?\\\)", latex_to_speakable, text, flags=re.DOTALL)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()
