"""
Prompt formatting and embedding utilities for Stable Diffusion handlers.
Handles prompt string formatting, prompt embedding, and compel integration.
Follows project standards: docstrings, type hints, logging.
"""

import logging
from typing import Any, Dict, Optional
from airunner.components.art.managers.stablediffusion.prompt_weight_bridge import (
    PromptWeightBridge,
)
from airunner.settings import (
    AIRUNNER_PHOTO_REALISTIC_PROMPT,
    AIRUNNER_ILLUSTRATION_PROMPT,
    AIRUNNER_PAINTING_PROMPT,
    AIRUNNER_PHOTO_REALISTIC_NEGATIVE_PROMPT,
    AIRUNNER_ILLUSTRATION_NEGATIVE_PROMPT,
    AIRUNNER_PAINTING_NEGATIVE_PROMPT,
)
from airunner.enums import ImagePreset

logger = logging.getLogger(__name__)


def format_prompt(
    prompt: str,
    preset: str = "",
    additional_prompts: Optional[list] = None,
    second_prompt: bool = False,
) -> str:
    """Format the main prompt with preset and additional prompts. Default preset to empty string for test compatibility."""
    prompt = PromptWeightBridge.convert(prompt)
    preset = PromptWeightBridge.convert(preset)
    if additional_prompts:
        prompts = [f'"{prompt}"']
        for add_settings in additional_prompts:
            if second_prompt:
                add_prompt = add_settings.get("prompt_secondary", "")
            else:
                add_prompt = add_settings["prompt"]
            prompts.append(f'"{add_prompt}"')
        return f'({", ".join(prompts)}, "{preset}").and()'
    if preset:
        return f'("{prompt}", "{preset}").and(0.5, 0.75)'
    return prompt


def get_prompt_preset(image_preset: ImagePreset) -> str:
    if image_preset is ImagePreset.PHOTOGRAPH:
        return AIRUNNER_PHOTO_REALISTIC_PROMPT
    elif image_preset is ImagePreset.ILLUSTRATION:
        return AIRUNNER_ILLUSTRATION_PROMPT
    elif image_preset is ImagePreset.PAINTING:
        return AIRUNNER_PAINTING_PROMPT
    return ""


def get_negative_prompt_preset(image_preset: ImagePreset) -> str:
    if image_preset is ImagePreset.PHOTOGRAPH:
        return AIRUNNER_PHOTO_REALISTIC_NEGATIVE_PROMPT
    elif image_preset is ImagePreset.ILLUSTRATION:
        return AIRUNNER_ILLUSTRATION_NEGATIVE_PROMPT
    elif image_preset is ImagePreset.PAINTING:
        return AIRUNNER_PAINTING_NEGATIVE_PROMPT
    return ""


def format_negative_prompt(prompt: str, preset: str) -> str:
    prompt = PromptWeightBridge.convert(prompt)
    preset = PromptWeightBridge.convert(preset)
    if preset:
        return f'("{prompt}", "{preset}").and()'
    return prompt


def apply_preset_to_prompt(prompt: str, preset: str) -> str:
    """Apply a preset to the prompt."""
    if not prompt and not preset:
        return ""
    if not preset:
        return prompt
    return f"{prompt}, {preset}"


def apply_negative_prompt(prompt: str, negative: str) -> str:
    """Apply a negative prompt to the prompt."""
    if not prompt and not negative:
        return ""
    if not negative:
        return prompt
    return f"{prompt}, {negative}"


# Additional prompt embedding and compel integration utilities can be added here.
