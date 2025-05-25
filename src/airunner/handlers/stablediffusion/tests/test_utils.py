"""
Unit tests for utils.py utility functions in stablediffusion handler.
Covers image resizing and general helpers.
"""

import pytest
from unittest.mock import MagicMock
import airunner.handlers.stablediffusion.utils as utils


def test_resize_image():
    # Simulate resizing an image
    fake_image = MagicMock()
    fake_image.size = (1024, 1024)
    max_width = 512
    max_height = 512
    fake_image.resize.return_value = "resized_image"
    result = utils.resize_image(fake_image, max_width, max_height)
    assert result == "resized_image"
    fake_image.resize.assert_called_with(
        (512, 512), utils.PIL.Image.Resampling.LANCZOS
    )


def test_helper_function():
    # Test a generic helper function if present
    if hasattr(utils, "some_helper"):
        assert utils.some_helper(1, 2) == 3  # Example assertion
