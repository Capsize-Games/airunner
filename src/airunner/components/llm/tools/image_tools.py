"""
Image generation and manipulation tools.

All tools for creating, editing, and managing images in AI Runner.
"""

import json
from typing import Annotated, Any

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.llm.config.model_capabilities import ModelCapability
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def enhance_prompt_with_specialized_model(
    prompt: str, second_prompt: str = ""
) -> tuple[str, str]:
    """
    Enhance prompts using a specialized small model.

    Uses a 2-3B parameter model optimized for prompt enhancement rather than
    the primary conversational LLM. This provides better, more detailed prompts
    for Stable Diffusion while keeping the primary model focused on conversation.

    Args:
        prompt: Main prompt to enhance
        second_prompt: Secondary prompt to enhance

    Returns:
        Tuple of (enhanced_prompt, enhanced_second_prompt)
    """
    try:
        from airunner.components.llm.managers.llm_model_manager import (
            LLMModelManager,
        )

        manager = LLMModelManager()

        # Enhance main prompt
        enhancement_request = f"""You are a Stable Diffusion prompt expert. Enhance this prompt with rich details, art styles, lighting, composition, and quality tags.

Original prompt: {prompt}

Enhanced prompt (detailed, specific, no explanations):"""

        enhanced_prompt = manager.use_specialized_model(
            ModelCapability.PROMPT_ENHANCEMENT,
            enhancement_request,
            max_tokens=256,
        )

        # If enhancement failed, use original
        if not enhanced_prompt:
            logger.warning("Prompt enhancement failed, using original prompt")
            return prompt, second_prompt

        enhanced_prompt = enhanced_prompt.strip()

        # Enhance second prompt if provided
        enhanced_second = second_prompt
        if second_prompt:
            second_request = f"""You are a Stable Diffusion prompt expert. Enhance this background/atmosphere prompt with details about colors, mood, lighting, and environment.

Original: {second_prompt}

Enhanced (detailed, specific, no explanations):"""

            enhanced_second = manager.use_specialized_model(
                ModelCapability.PROMPT_ENHANCEMENT,
                second_request,
                max_tokens=128,
            )
            if enhanced_second:
                enhanced_second = enhanced_second.strip()
            else:
                enhanced_second = second_prompt

        logger.info(f"Prompt enhanced: '{prompt}' -> '{enhanced_prompt}'")
        return enhanced_prompt, enhanced_second

    except Exception as e:
        logger.error(f"Error enhancing prompt: {e}", exc_info=True)
        return prompt, second_prompt


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

    # Enhance prompts using specialized model
    logger.info(f"Enhancing prompts for image generation")
    enhanced_prompt, enhanced_second = enhance_prompt_with_specialized_model(
        prompt, second_prompt
    )

    # Trigger image generation with enhanced prompts
    api.art.llm_image_generated(
        prompt=enhanced_prompt,
        second_prompt=enhanced_second,
        preset=preset,
        width=width,
        height=height,
    )

    return json.dumps(
        {
            "status": "generating",
            "prompt": enhanced_prompt,
            "second_prompt": enhanced_second,
            "original_prompt": prompt,
            "original_second_prompt": second_prompt,
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
