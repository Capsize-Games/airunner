from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.components.art.managers.stablediffusion.rect import Rect


def test_image_request_to_dict():
    r = ImageRequest(prompt="hello", steps=10, n_samples=2)
    d = r.to_dict()
    assert d["prompt"] == "hello"
    assert d["steps"] == 10
    assert d["n_samples"] == 2


def test_image_response_to_dict():
    rect = Rect(1, 2, 3, 4)
    ir = ImageResponse(
        images=None,
        data={"a": 1},
        active_rect=rect,
        is_outpaint=False,
    )
    d = ir.to_dict()
    assert d["active_rect"]["x"] == 1
