import pytest
from PIL import Image
from airunner.gui.widgets.canvas.logic.brush_scene_logic import BrushSceneLogic


class DummyAppSettings:
    working_width = 8
    working_height = 4


class DummyBrushSettings:
    primary_color = "red"


class DummyPadSettings:
    mask_layer_enabled = False
    mask = None


def test_create_mask_image():
    logic = BrushSceneLogic(
        DummyAppSettings(), DummyBrushSettings(), DummyPadSettings()
    )
    mask = logic.create_mask_image()
    assert mask.size == (8, 4)
    assert mask.mode == "RGBA"


def test_adjust_mask_alpha():
    logic = BrushSceneLogic(
        DummyAppSettings(), DummyBrushSettings(), DummyPadSettings()
    )
    # Create a 2x2 mask: black, white, gray, red
    img = Image.new("RGBA", (2, 2), (0, 0, 0, 255))
    img.putpixel((1, 0), (255, 255, 255, 255))
    img.putpixel((0, 1), (128, 128, 128, 255))
    img.putpixel((1, 1), (255, 0, 0, 255))
    out = logic.adjust_mask_alpha(img)
    # Black pixel alpha should be 0, white 128, others unchanged
    assert out.getpixel((0, 0))[3] == 0
    assert out.getpixel((1, 0))[3] == 128
    assert out.getpixel((0, 1))[3] == 255
    assert out.getpixel((1, 1))[3] == 255


def test_display_color_and_eraser_color():
    logic = BrushSceneLogic(
        DummyAppSettings(), DummyBrushSettings(), DummyPadSettings()
    )
    assert logic.display_color(True) == "white"
    assert logic.display_color(False, "blue") == "blue"
    assert logic.eraser_color(True) == "black"
    assert logic.eraser_color(False) == "transparent"
