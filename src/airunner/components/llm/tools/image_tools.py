"""
Image generation and manipulation tools.

All tools for creating, editing, and managing images in AI Runner.
These tools adapt dynamically to the current image generator's capabilities.
"""

import json
from typing import Annotated, Any, Optional

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.llm.config.model_capabilities import ModelCapability
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _get_current_generator_capabilities(api: Any):
    """
    Get capabilities for the currently selected image generator.
    
    Args:
        api: The API object with settings access
        
    """
    from airunner.components.art.config.image_generator_capabilities import (
        get_generator_capabilities,
        ImageGeneratorCapabilities,
    )
    
    try:
        generator_name = api.application_settings.current_image_generator
        return get_generator_capabilities(generator_name), generator_name
    except Exception as e:
        logger.warning(f"Could not get generator capabilities: {e}")
        # Return default capabilities
        return ImageGeneratorCapabilities(), "unknown"


def enhance_prompt_with_specialized_model(
    prompt: str, second_prompt: str = ""
) -> tuple[str, str]:
    """
    Enhance prompts using a specialized small model.

    Uses a 2-3B parameter model optimized for prompt enhancement rather than
    the primary conversational LLM. This provides better, more detailed prompts
    for image generation while keeping the primary model focused on conversation.

    Args:
        prompt: Main prompt to enhance
        second_prompt: Secondary prompt to enhance

    """
    try:
        from airunner.components.llm.managers.llm_model_manager import (
            LLMModelManager,
        )

        manager = LLMModelManager()

        # Enhance main prompt
        enhancement_request = f"""You are an image generation prompt expert. Enhance this prompt with rich details, art styles, lighting, composition, and quality tags.

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
            second_request = f"""You are an image generation prompt expert. Enhance this background/atmosphere prompt with details about colors, mood, lighting, and environment.

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
        "The tool automatically adapts to the current image model's capabilities."
    ),
    return_direct=True,
    requires_api=True,
    defer_loading=False,  # Essential tool - always available
    keywords=["picture", "art", "draw", "create", "painting", "photo", "image", "generate"],
    input_examples=[
        {
            "prompt": "A majestic wolf standing on a mountain peak at sunset, photorealistic, detailed fur",
            "second_prompt": "golden hour lighting, dramatic clouds, warm orange and purple sky",
            "width": 1024,
            "height": 768,
        },
        {
            "prompt": "Cute anime girl with blue hair, studio ghibli style, soft lighting",
            "second_prompt": "cherry blossoms, spring garden, pastel colors",
            "width": 768,
            "height": 1024,
        },
    ],
)
def generate_image(
    prompt: Annotated[
        str,
        "Detailed description of the image subject, composition, lighting, and style. "
        "Be specific and descriptive for best results.",
    ],
    second_prompt: Annotated[
        Optional[str],
        "Optional: Description of background, colors, mood, and atmosphere. "
        "Some models (like Z-Image) don't use this - pass empty string if unsure.",
    ] = "",
    width: Annotated[
        int,
        "Width in pixels. Default: 1024. Must be multiple of 64.",
    ] = 1024,
    height: Annotated[
        int,
        "Height in pixels. Default: 1024. Must be multiple of 64.",
    ] = 1024,
    api: Any = None,
) -> str:
    """Generate an image based on prompts and current model settings."""
    # Get current generator capabilities
    caps, generator_name = _get_current_generator_capabilities(api)
    
    # Normalize dimensions to multiples of the step size
    step = caps.dimension_step
    width = (width // step) * step
    height = (height // step) * step

    # Clamp to valid range for this generator
    width = max(caps.min_width, min(caps.max_width, width))
    height = max(caps.min_height, min(caps.max_height, height))
    
    # Handle second_prompt based on model capabilities
    effective_second_prompt = ""
    if caps.supports_second_prompt and second_prompt:
        effective_second_prompt = second_prompt
    elif not caps.supports_second_prompt and second_prompt:
        # Model doesn't support second prompt - merge into main prompt
        logger.info(f"Model '{generator_name}' doesn't support second_prompt, merging into main prompt")
        prompt = f"{prompt}. {second_prompt}"

    # Enhance prompts using specialized model
    logger.info(f"Generating image with {generator_name} ({width}x{height})")
    enhanced_prompt, enhanced_second = enhance_prompt_with_specialized_model(
        prompt, effective_second_prompt
    )

    # Trigger image generation - no preset parameter needed
    api.art.llm_image_generated(
        prompt=enhanced_prompt,
        second_prompt=enhanced_second,
        section="txt2img",
        width=width,
        height=height,
    )

    return json.dumps(
        {
            "status": "generating",
            "generator": generator_name,
            "prompt": enhanced_prompt,
            "second_prompt": enhanced_second if caps.supports_second_prompt else None,
            "original_prompt": prompt,
            "width": width,
            "height": height,
            "model_capabilities": {
                "supports_negative_prompt": caps.supports_negative_prompt,
                "supports_second_prompt": caps.supports_second_prompt,
            },
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
    # Get capabilities for dimension constraints
    caps, generator_name = _get_current_generator_capabilities(api)
    
    # Normalize and clamp
    step = caps.dimension_step
    width = max(caps.min_width, min(caps.max_width, (width // step) * step))
    height = max(caps.min_height, min(caps.max_height, (height // step) * step))

    try:
        api.update_application_settings(
            working_width=width,
            working_height=height,
        )
        return f"Image dimensions set to {width}x{height} for {generator_name}"
    except AttributeError:
        # Fallback if settings API not available
        return f"Image dimensions would be set to {width}x{height}"


@tool(
    name="clear_canvas",
    category=ToolCategory.IMAGE,
    description="Clear the canvas/image workspace",
    return_direct=True,
    requires_api=True,
)
def clear_canvas(api: Any = None) -> str:
    """Clear the canvas."""
    try:
        api.art.canvas.clear()
        return "Canvas cleared"
    except Exception as e:
        logger.error(f"Error clearing canvas: {e}")
        return f"Error clearing canvas: {e}"


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

    try:
        api.art.canvas.image_from_path(path)
        return f"Opening image: {path}"
    except Exception as e:
        logger.error(f"Error opening image: {e}")
        return f"Error opening image: {e}"


@tool(
    name="get_image_model_info",
    category=ToolCategory.IMAGE,
    description="Get information about the current image generation model and its capabilities",
    return_direct=False,
    requires_api=True,
)
def get_image_model_info(api: Any = None) -> str:
    """Get current image model capabilities."""
    caps, generator_name = _get_current_generator_capabilities(api)
    
    return json.dumps({
        "generator": generator_name,
        "supports_negative_prompt": caps.supports_negative_prompt,
        "supports_second_prompt": caps.supports_second_prompt,
        "default_dimensions": f"{caps.default_width}x{caps.default_height}",
        "max_dimensions": f"{caps.max_width}x{caps.max_height}",
        "guidance": caps.prompt_guidance,
    })
