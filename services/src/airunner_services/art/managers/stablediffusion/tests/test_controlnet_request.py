from PIL import Image

from airunner.components.art.managers.stablediffusion.controlnet_request import (
    ControlnetRequest,
    create_controlnet_request,
    validate_controlnet_request,
)


def test_create_controlnet_request():
    img = Image.new("RGB", (10, 10))
    req = create_controlnet_request("/path/to/model", img, conditioning="edge")
    assert isinstance(req, ControlnetRequest)
    assert req.model_path == "/path/to/model"
    assert req.input_image is img
    assert req.conditioning == "edge"


def test_validate_controlnet_request_missing_fields():
    req = ControlnetRequest(model_path="", input_image=None)
    assert not validate_controlnet_request(req)


def test_validate_controlnet_request_ok():
    img = Image.new("RGB", (5, 5))
    req = ControlnetRequest(model_path="m", input_image=img)
    assert validate_controlnet_request(req)
