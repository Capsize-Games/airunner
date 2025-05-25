"""
Unit tests for image_to_image_request.py utility functions in stablediffusion handler.
Covers image-to-image request construction and validation logic.
"""

import pytest
from unittest.mock import MagicMock
import airunner.handlers.stablediffusion.image_to_image_request as image_to_image_request


def test_create_image_to_image_request_valid():
    # Simulate a valid image-to-image request
    params = {
        "input_image": MagicMock(),
        "prompt": "A cat on a mat",
        "strength": 0.8,
    }
    req = image_to_image_request.create_image_to_image_request(**params)
    assert req is not None
    assert req.prompt == params["prompt"]
    assert req.strength == 0.8


def test_create_image_to_image_request_missing_param():
    # Should raise if required params are missing
    with pytest.raises(TypeError):
        image_to_image_request.create_image_to_image_request(prompt="A dog")


def test_validate_image_to_image_request():
    # Simulate validation logic
    req = MagicMock()
    req.input_image = MagicMock()
    req.prompt = "A landscape"
    req.strength = 0.5
    assert image_to_image_request.validate_image_to_image_request(req) is True


def test_validate_image_to_image_request_invalid():
    # Simulate invalid request
    req = MagicMock()
    req.input_image = None
    req.prompt = ""
    req.strength = None
    assert image_to_image_request.validate_image_to_image_request(req) is False
