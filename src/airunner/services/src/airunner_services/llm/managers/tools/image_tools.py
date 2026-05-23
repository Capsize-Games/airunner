"""Image generation and canvas tools."""

from typing import Callable
import os

from langchain_core.tools import tool

from airunner_services.tools.base_tool import BaseTool


class ImageTools(BaseTool):
    """Mixin class providing image generation and manipulation tools."""

    def generate_image_tool(self) -> Callable:
        """Generate an image from text prompt."""

        @tool
        def generate_image(prompt: str, negative_prompt: str = "") -> str:
            """Generate an image based on a text description.

            Args:
                prompt: Description of the image to generate
                negative_prompt: Things to avoid in the image (optional)

            Returns:
                Confirmation message
            """
            try:
                if not self.dispatch_tool_action(
                    "generate_image",
                    {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                    },
                ):
                    return "Image generation is unavailable in this runtime."
                return f"Generating image: {prompt}"
            except Exception as e:
                return f"Error generating image: {str(e)}"

        return generate_image

    def clear_canvas_tool(self) -> Callable:
        """Clear the canvas."""

        @tool
        def clear_canvas() -> str:
            """Clear the image canvas.

            Returns:
                Confirmation message
            """
            try:
                if not self.dispatch_tool_action("clear_canvas"):
                    return "Canvas actions are unavailable in this runtime."
                return "Canvas cleared"
            except Exception as e:
                return f"Error clearing canvas: {str(e)}"

        return clear_canvas

    def open_image_tool(self) -> Callable:
        """Open an image from file path."""

        @tool
        def open_image(file_path: str) -> str:
            """Open an image from a file path.

            Args:
                file_path: Path to the image file

            Returns:
                Confirmation message
            """
            try:
                if not os.path.exists(file_path):
                    return f"File not found: {file_path}"

                if not self.dispatch_tool_action(
                    "load_image_from_path",
                    {"image_path": file_path},
                ):
                    return "Image loading is unavailable in this runtime."
                return f"Opened image: {file_path}"
            except Exception as e:
                return f"Error opening image: {str(e)}"

        return open_image
