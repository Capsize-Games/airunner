"""
Unit tests for controlnet_request.py utility functions in stablediffusion handler.
Covers ControlNet request construction and validation logic.
"""

import pytest
from unittest.mock import MagicMock
import airunner.handlers.stablediffusion.controlnet_request as controlnet_request


def test_create_controlnet_request_valid():
    # Simulate a valid controlnet request
    params = {
        "model_path": "/fake/path/controlnet.pt",
        "input_image": MagicMock(),
        "conditioning": "edge",
    }
    req = controlnet_request.create_controlnet_request(**params)
    assert req is not None
    assert req.model_path == params["model_path"]
    assert req.conditioning == "edge"


def test_create_controlnet_request_missing_param():
    # Should raise if required params are missing
    with pytest.raises(TypeError):
        controlnet_request.create_controlnet_request(
            model_path="/fake/path/controlnet.pt"
        )


def test_validate_controlnet_request():
    # Simulate validation logic
    req = MagicMock()
    req.model_path = "/fake/path/controlnet.pt"
    req.input_image = MagicMock()
    req.conditioning = "depth"
    assert controlnet_request.validate_controlnet_request(req) is True


def test_validate_controlnet_request_invalid():
    # Simulate invalid request
    req = MagicMock()
    req.model_path = ""
    req.input_image = None
    req.conditioning = None
    assert controlnet_request.validate_controlnet_request(req) is False
