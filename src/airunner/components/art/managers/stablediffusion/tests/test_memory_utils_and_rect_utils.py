import types
from PIL import Image

from airunner.components.art.managers.stablediffusion import (
    memory_utils,
    rect,
    utils,
)


def test_apply_last_channels_no_pipe(monkeypatch):
    class DummyPipe:
        class Unet:
            pass

    p = types.SimpleNamespace(unet=None)
    # should not raise even if attribute missing
    memory_utils.apply_last_channels(p, enabled=False)
    memory_utils.apply_last_channels(p, enabled=True)


def test_set_memory_efficient():
    assert memory_utils.set_memory_efficient(True) is True
    assert memory_utils.set_memory_efficient(False) is False


def test_rect_translate_and_props():
    r = rect.Rect(1, 2, 3, 4)
    assert r.left() == 1
    assert r.top() == 2
    r.translate(5, 6)
    assert r.x == 6 and r.y == 8


def test_resize_image_noop():
    img = Image.new("RGB", (10, 10))
    out = utils.resize_image(img, 20, 20)
    assert out is img
