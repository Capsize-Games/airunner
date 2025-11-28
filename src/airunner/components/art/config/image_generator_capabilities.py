"""
Image generator model capabilities configuration.

Defines what features each image generator supports (negative prompts,
second prompts, etc.) so tools can adapt their behavior dynamically.
"""

from dataclasses import dataclass
from typing import Dict
from airunner.enums import ImageGenerator


@dataclass
class ImageGeneratorCapabilities:
    """Capabilities of an image generation model."""
    
    # Whether the model supports negative prompts
    supports_negative_prompt: bool = True
    
    # Whether the model supports a second (background/style) prompt
    supports_second_prompt: bool = True
    
    # Whether the model supports a second negative prompt
    supports_second_negative_prompt: bool = True
    
    # Default width for this model
    default_width: int = 1024
    
    # Default height for this model
    default_height: int = 1024
    
    # Maximum supported dimensions
    max_width: int = 2048
    max_height: int = 2048
    
    # Minimum supported dimensions
    min_width: int = 64
    min_height: int = 64
    
    # Dimension step (must be multiple of this)
    dimension_step: int = 64
    
    # Brief description for LLM tool prompts
    prompt_guidance: str = ""


# Capabilities for each image generator type
IMAGE_GENERATOR_CAPABILITIES: Dict[str, ImageGeneratorCapabilities] = {
    ImageGenerator.STABLEDIFFUSION.value: ImageGeneratorCapabilities(
        supports_negative_prompt=True,
        supports_second_prompt=True,
        supports_second_negative_prompt=True,
        default_width=1024,
        default_height=1024,
        prompt_guidance=(
            "SDXL supports detailed prompts with negative prompts to exclude unwanted elements. "
            "Use second_prompt for background/atmosphere details."
        ),
    ),
    ImageGenerator.FLUX.value: ImageGeneratorCapabilities(
        supports_negative_prompt=False,  # FLUX doesn't use negative prompts effectively
        supports_second_prompt=True,
        supports_second_negative_prompt=False,
        default_width=1024,
        default_height=1024,
        prompt_guidance=(
            "FLUX is a high-quality model that doesn't use negative prompts. "
            "Focus on detailed positive descriptions. Use second_prompt for style/atmosphere."
        ),
    ),
    ImageGenerator.ZIMAGE.value: ImageGeneratorCapabilities(
        supports_negative_prompt=False,  # Z-Image doesn't use negative prompts
        supports_second_prompt=False,  # Single prompt model
        supports_second_negative_prompt=False,
        default_width=1024,
        default_height=1024,
        prompt_guidance=(
            "Z-Image uses a single detailed prompt. No negative or secondary prompts. "
            "Include all details in the main prompt. Supports English and Chinese text rendering."
        ),
    ),
}


def get_generator_capabilities(generator_name: str) -> ImageGeneratorCapabilities:
    """
    Get capabilities for an image generator.
    
    Args:
        generator_name: Name of the generator (flux, stablediffusion, zimage)
        
    Returns:
        Capabilities dataclass for the generator
    """
    return IMAGE_GENERATOR_CAPABILITIES.get(
        generator_name,
        # Default to full capabilities if unknown
        ImageGeneratorCapabilities(),
    )


def get_tool_description_for_generator(generator_name: str) -> str:
    """
    Get a dynamic tool description based on the current generator.
    
    Args:
        generator_name: Name of the current image generator
        
    Returns:
        Description string for the generate_image tool
    """
    caps = get_generator_capabilities(generator_name)
    
    base_desc = "Generate an image from a text description. "
    
    if caps.supports_negative_prompt:
        base_desc += "Supports negative prompts to exclude unwanted elements. "
    else:
        base_desc += "This model does NOT use negative prompts - focus on positive descriptions. "
    
    if caps.supports_second_prompt:
        base_desc += "Use second_prompt for background, colors, and atmosphere. "
    else:
        base_desc += "This model uses a single prompt - include ALL details in the main prompt. "
    
    if caps.prompt_guidance:
        base_desc += caps.prompt_guidance
    
    return base_desc.strip()
