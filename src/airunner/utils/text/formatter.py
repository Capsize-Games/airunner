import re
import os
import markdown
from PIL import Image, ImageDraw, ImageFont


class Formatter:
    """
    A generic class to format various types of content into a human-readable and visually appealing output.
    It can handle LaTeX for mathematical formulas, Markdown for rich text, and plain text.
    The output is primarily an image file, which is suitable for chatbot display.
    """

    # Constants for recognized formats
    _FORMAT_LATEX = "latex"
    _FORMAT_MARKDOWN = "markdown"
    _FORMAT_PLAINTEXT = "plaintext"

    @staticmethod
    def _is_latex(text: str) -> bool:
        r"""
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
        Heuristically checks if the given text contains Markdown syntax.
        Looks for common Markdown elements like # (headers), * (lists/emphasis), ` (code), []() (links).
        """
        # Headers
        if re.search(
            r"^(#+\s.*)|(\s\S+\n=+$)|(\s\S+\n-+$)", text, re.MULTILINE
        ):
            return True
        # Lists (unordered and ordered)
        if re.search(r"^(-|\*|\+|\d+\.)\s", text, re.MULTILINE):
            return True
        # Emphasis (bold, italics)
        if re.search(r"(\*\*|\_\_|\*|\_)[^\s]+(\*\*|\_\_|\*|\_)", text):
            return True
        # Code blocks/inline code
        if re.search(r"(`{1,3}.*`{1,3})", text, re.DOTALL):
            return True
        # Links/Images
        if re.search(r"\[.+\]\(.+\)", text):
            return True
        # Blockquotes
        if re.search(r"^>\s", text, re.MULTILINE):
            return True
        return False

    @staticmethod
    def render_markdown_to_html(markdown_string: str) -> str:
        """
        Converts a Markdown string to HTML.
        """
        return markdown.markdown(markdown_string)

    @staticmethod
    def _render_plaintext_to_image(
        text_string: str, output_path: str, font_size: int = 14
    ) -> str:
        """
        Renders plain text to a PNG image.
        Useful for displaying non-math/non-markdown text as an image for consistent output.
        """
        try:
            # Estimate image size based on text length and font size
            lines = text_string.split("\n")
            max_line_length = max(len(line) for line in lines) if lines else 1
            num_lines = len(lines) if lines else 1

            # A rough estimate for image dimensions (adjust as needed)
            # 0.6 is a rough character width to height ratio
            width_px = int(max_line_length * font_size * 0.6) + 40
            height_px = int(num_lines * font_size * 1.5) + 40

            # Ensure minimum size
            width_px = max(width_px, 300)
            height_px = max(height_px, 100)

            img = Image.new(
                "RGB", (width_px, height_px), color=(255, 255, 255)
            )
            d = ImageDraw.Draw(img)

            # Try to load a common monospaced font
            try:
                font = ImageFont.truetype("arial.ttf", font_size)  # Windows
            except IOError:
                try:
                    font = ImageFont.truetype(
                        "LiberationMono-Regular.ttf", font_size
                    )  # Linux
                except IOError:
                    font = ImageFont.load_default()  # Fallback

            d.text((20, 20), text_string, fill=(0, 0, 0), font=font)
            img.save(output_path)
            return output_path
        except Exception as e:
            print(f"Error rendering plain text to image: {e}")
            return ""

    @staticmethod
    def format_content(
        content_string: str, output_dir: str = "formatted_output"
    ) -> dict:
        """
        Analyzes the input string, determines its format, and returns a formatted representation.

        Args:
            content_string (str): The input string from the LLM.
            output_dir (str): Directory to save generated images. Will be created if it doesn't exist.

        Returns:
            dict: A dictionary containing:
                - 'type': The determined format ('latex', 'markdown', 'plaintext').
                - 'output': The formatted content (image path for latex/plaintext, HTML string for markdown).
                - 'original_content': The original input string.
        """
        os.makedirs(output_dir, exist_ok=True)
        # Only treat as LaTeX if the whole string is a LaTeX formula
        if Formatter._is_markdown(content_string):
            html_output = Formatter.render_markdown_to_html(content_string)
            return {
                "type": Formatter._FORMAT_MARKDOWN,
                "output": html_output,  # HTML string
                "original_content": content_string,
            }

        # If neither LaTeX nor Markdown, treat as plain text and return as string (do NOT render to image)
        return {
            "type": Formatter._FORMAT_PLAINTEXT,
            "output": content_string,  # Return original string
            "original_content": content_string,
        }
