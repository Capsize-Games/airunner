"""
Image generation and manipulation tools.

All tools for creating, editing, and managing images in AI Runner.
"""

import json
from typing import Annotated, Any

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.enums import ImagePreset


@tool(
    name="generate_image",
    category=ToolCategory.IMAGE,
    description=(
        "Generate an image from a text description. "
        "Use this for ANY image creation request. "
        "Do NOT use search tools for image generation."
    ),
    return_direct=True,
    requires_api=True,
)
def generate_image(
    prompt: Annotated[
        str,
        "Detailed description of the image subject, composition, lighting, and style",
    ],
    second_prompt: Annotated[
        str,
        "Description of background, colors, mood, and atmosphere",
    ],
    preset: Annotated[
        str,
        f"Style preset. Options: {[p.value for p in ImagePreset]}",
    ],
    width: Annotated[
        int,
        "Width in pixels. Min: 64, max: 2048. Must be multiple of 64.",
    ],
    height: Annotated[
        int,
        "Height in pixels. Min: 64, max: 2048. Must be multiple of 64.",
    ],
    api: Any = None,
) -> str:
    """Generate an image based on prompts and settings."""
    # Normalize dimensions to multiples of 64
    width = (width // 64) * 64
    height = (height // 64) * 64

    # Clamp to valid range
    width = max(64, min(2048, width))
    height = max(64, min(2048, height))

    # Validate preset
    valid_presets = [p.value for p in ImagePreset]
    if preset not in valid_presets:
        preset = ImagePreset.ILLUSTRATION.value

    # Trigger image generation
    api.art.llm_image_generated(
        prompt=prompt,
        second_prompt=second_prompt,
        preset=preset,
        width=width,
        height=height,
    )

    return json.dumps(
        {
            "status": "generating",
            "prompt": prompt,
            "second_prompt": second_prompt,
            "preset": preset,
            "width": width,
            "height": height,
        }
    )


@tool(
    name="set_image_dimensions",
    category=ToolCategory.IMAGE,
    description="Set the working width and height for images",
    return_direct=True,
    requires_api=True,
)
def set_image_dimensions(
    width: Annotated[
        int,
        "Width in pixels. Min: 64, max: 2048. Must be multiple of 64.",
    ],
    height: Annotated[
        int,
        "Height in pixels. Min: 64, max: 2048. Must be multiple of 64.",
    ],
    api: Any = None,
) -> str:
    """Set default image dimensions."""
    # Normalize and clamp
    width = max(64, min(2048, (width // 64) * 64))
    height = max(64, min(2048, (height // 64) * 64))

    api.settings.update_application_settings(
        working_width=width,
        working_height=height,
    )

    return f"Image dimensions set to {width}x{height}"


@tool(
    name="clear_canvas",
    category=ToolCategory.IMAGE,
    description="Clear the canvas/image workspace",
    return_direct=True,
    requires_api=True,
)
def clear_canvas(api: Any = None) -> str:
    """Clear the canvas."""
    api.art.canvas.clear()
    return "Canvas cleared"


@tool(
    name="open_image",
    category=ToolCategory.IMAGE,
    description="Open an image from a file path",
    return_direct=True,
    requires_api=True,
)
def open_image(
    path: Annotated[str, "Full path to the image file"],
    api: Any = None,
) -> str:
    """Open an image from disk."""
    import os

    if not os.path.isfile(path):
        return f"Error: File not found: {path}"

    api.art.canvas.image_from_path(path)
    return f"Opening image: {path}"
