"""
Unit tests for image_generation.py utility functions in stablediffusion handler.
Covers NSFW checking and image export logic.
"""

import pytest
from unittest.mock import patch, MagicMock
import airunner.handlers.stablediffusion.image_generation as image_generation


def test_nsfw_check_safe():
    # Simulate a safe image
    with patch("airunner.handlers.stablediffusion.image_generation.NSFWChecker") as mock_checker:
        instance = mock_checker.return_value
        instance.is_nsfw.return_value = False
        result = image_generation.is_nsfw(MagicMock())
        assert result is False


def test_nsfw_check_unsafe():
    # Simulate an unsafe image
    with patch("airunner.handlers.stablediffusion.image_generation.NSFWChecker") as mock_checker:
        instance = mock_checker.return_value
        instance.is_nsfw.return_value = True
        result = image_generation.is_nsfw(MagicMock())
        assert result is True


def test_export_image_success(tmp_path):
    # Simulate exporting an image
    fake_image = MagicMock()
    fake_path = tmp_path / "output.png"
    with patch("airunner.handlers.stablediffusion.image_generation.save_image") as mock_save:
        mock_save.return_value = str(fake_path)
        result = image_generation.export_image(fake_image, str(fake_path))
        assert result == str(fake_path)


def test_export_image_failure(tmp_path):
    # Simulate a failure in exporting
    fake_image = MagicMock()
    fake_path = tmp_path / "fail.png"
    with patch("airunner.handlers.stablediffusion.image_generation.save_image", side_effect=IOError("fail")):
        with pytest.raises(IOError):
            image_generation.export_image(fake_image, str(fake_path))
