"""
Prompt formatting and embedding utilities for Stable Diffusion handlers.
Handles prompt string formatting, prompt embedding, and compel integration.
Follows project standards: docstrings, type hints, logging.
"""

from typing import Optional
from airunner.components.art.managers.stablediffusion.prompt_weight_bridge import (
    PromptWeightBridge,
)
from airunner.settings import (
    AIRUNNER_LOG_LEVEL,
)
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def format_prompt(
    prompt: str,
    additional_prompts: Optional[list] = None,
    second_prompt: bool = False,
) -> str:
    """Format the main prompt with preset and additional prompts. Default preset to empty string for test compatibility."""
    prompt = PromptWeightBridge.convert(prompt)
    if additional_prompts:
        prompts = [f'"{prompt}"']
        for add_settings in additional_prompts:
            if second_prompt:
                add_prompt = add_settings.get("prompt_secondary", "")
            else:
                add_prompt = add_settings["prompt"]
            prompts.append(f'"{add_prompt}"')
        return f'{", ".join(prompts)}'
    return prompt


def format_negative_prompt(prompt: str) -> str:
    prompt = PromptWeightBridge.convert(prompt)
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
