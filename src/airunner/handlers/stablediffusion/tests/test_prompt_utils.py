"""
Unit tests for prompt_utils.py utility functions in stablediffusion handler.
Covers prompt formatting, preset, and negative prompt logic.
"""

import pytest
import airunner.handlers.stablediffusion.prompt_utils as prompt_utils


def test_format_prompt_basic():
    prompt = "A cat on a mat"
    formatted = prompt_utils.format_prompt(prompt)
    assert isinstance(formatted, str)
    assert "cat" in formatted


def test_apply_preset_to_prompt():
    prompt = "A dog in a park"
    preset = "high quality, detailed"
    result = prompt_utils.apply_preset_to_prompt(prompt, preset)
    assert preset in result
    assert prompt in result


def test_negative_prompt_logic():
    prompt = "A beautiful landscape"
    negative = "blurry, lowres"
    result = prompt_utils.apply_negative_prompt(prompt, negative)
    assert negative in result
    assert prompt in result


def test_empty_prompt():
    assert prompt_utils.format_prompt("") == ""
    assert prompt_utils.apply_preset_to_prompt("", "") == ""
    assert prompt_utils.apply_negative_prompt("", "") == ""
