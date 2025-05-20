# filename: formatter.py

import re
import os
import tempfile
import matplotlib.pyplot as plt
import markdown
from PIL import Image, ImageDraw, ImageFont

from airunner.api import API


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
    def _render_latex_to_image(
        latex_code: str, output_path: str, dpi: int = 300
    ) -> str:
        """
        Renders a LaTeX mathematical string into a PNG image.
        Uses matplotlib for rendering.

        Args:
            latex_code (str): The LaTeX mathematical string (e.g., r'\frac{1}{2}').
            output_path (str): The full path including filename where the image will be saved.
            dpi (int): Dots per inch for the output image resolution.

        Returns:
            str: The path to the generated image file.
        """
        try:
            # Clean up delimiters if present (e.g., remove $$, $ , \[ \] )
            cleaned_latex = latex_code.strip()
            if cleaned_latex.startswith("$$") and cleaned_latex.endswith("$$"):
                cleaned_latex = cleaned_latex[2:-2].strip()
            elif cleaned_latex.startswith("$") and cleaned_latex.endswith("$"):
                cleaned_latex = cleaned_latex[1:-1].strip()
            elif cleaned_latex.startswith(r"\[") and cleaned_latex.endswith(
                r"\]"
            ):
                cleaned_latex = cleaned_latex[2:-2].strip()
            elif cleaned_latex.startswith(r"\(") and cleaned_latex.endswith(
                r"\)"
            ):
                cleaned_latex = cleaned_latex[2:-2].strip()

            # Matplotlib requires raw string for LaTeX for proper escaping
            # We'll try with usetex=True first for best quality, then fallback
            plt.rcParams["text.usetex"] = True
            plt.rcParams["font.family"] = (
                "serif"  # Often looks better with LaTeX
            )

            fig = plt.figure(
                figsize=(3, 1.2), dpi=dpi
            )  # Increased size for better visibility
            ax = fig.add_axes([0, 0, 1, 1])
            ax.text(
                0.5,
                0.5,
                r"$" + cleaned_latex + r"$",
                fontsize=20,
                horizontalalignment="center",
                verticalalignment="center",
                color="black",  # Ensure text is black
            )
            ax.set_axis_off()  # Hide axes and ticks

            # Save with tight bounding box to remove extra whitespace
            plt.savefig(
                output_path, dpi=dpi, bbox_inches="tight", pad_inches=0.05
            )
            plt.close(fig)
            return output_path
        except RuntimeError as e:
            # Fallback for systems without full LaTeX installation for usetex=True
            print(
                f"Warning: LaTeX rendering with usetex=True failed ({e}). Attempting without it."
            )
            plt.rcParams["text.usetex"] = False  # Disable usetex
            fig = plt.figure(figsize=(3, 1.2), dpi=dpi)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.text(
                0.5,
                0.5,
                r"$" + cleaned_latex + r"$",
                fontsize=20,
                horizontalalignment="center",
                verticalalignment="center",
                color="black",  # Ensure text is black
            )
            ax.set_axis_off()
            plt.savefig(
                output_path, dpi=dpi, bbox_inches="tight", pad_inches=0.05
            )
            plt.close(fig)
            return output_path
        except Exception as e:
            print(f"Error rendering LaTeX: {e}")
            return ""

    @staticmethod
    def _render_markdown_to_html(markdown_string: str) -> str:
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
        temp_filename_base = os.path.join(
            output_dir,
            "formatted_content",
        )

        # Only treat as LaTeX if the whole string is a LaTeX formula
        if Formatter._is_pure_latex(content_string):
            image_path = f"{temp_filename_base}_{os.urandom(4).hex()}.png"
            rendered_path = Formatter._render_latex_to_image(
                content_string, image_path
            )
            if rendered_path:
                return {
                    "type": Formatter._FORMAT_LATEX,
                    "output": rendered_path,  # Path to the image file
                    "original_content": content_string,
                }
        elif Formatter._is_markdown(content_string):
            html_output = Formatter._render_markdown_to_html(content_string)
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
