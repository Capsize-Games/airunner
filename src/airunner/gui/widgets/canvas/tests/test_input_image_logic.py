"""
Unit tests for InputImageLogic (business logic for InputImage widget).
Covers all branches, error paths, and edge cases.
"""

import pytest
from PIL import Image
from airunner.gui.widgets.canvas.logic.input_image_logic import InputImageLogic


class DummySettings:
    def __init__(self):
        self.image = None
        self.generated_image = None
        self.lock_input_image = False
        self.use_grid_image_as_input = False
        self.mask = None
        self.enabled = True


class DummyContext:
    def __init__(self):
        self.controlnet_settings = DummySettings()
        self.image_to_image_settings = DummySettings()
        self.outpaint_settings = DummySettings()
        self.drawing_pad_settings = DummySettings()
        self._calls = []

    def update_controlnet_settings(self, key, value):
        self._calls.append(("controlnet", key, value))
        setattr(self.controlnet_settings, key, value)

    def update_image_to_image_settings(self, key, value):
        self._calls.append(("img2img", key, value))
        setattr(self.image_to_image_settings, key, value)

    def update_outpaint_settings(self, key, value):
        self._calls.append(("outpaint", key, value))
        setattr(self.outpaint_settings, key, value)

    def update_drawing_pad_settings(self, key, value):
        self._calls.append(("drawingpad", key, value))
        setattr(self.drawing_pad_settings, key, value)


@pytest.mark.parametrize(
    "settings_key",
    [
        "controlnet_settings",
        "image_to_image_settings",
        "outpaint_settings",
        "drawing_pad_settings",
    ],
)
def test_get_current_settings(settings_key):
    logic = InputImageLogic(settings_key)
    ctx = DummyContext()
    assert logic.get_current_settings(ctx) is getattr(ctx, settings_key)


def test_get_current_settings_invalid_key():
    logic = InputImageLogic("invalid_key")
    ctx = DummyContext()
    with pytest.raises(ValueError):
        logic.get_current_settings(ctx)


@pytest.mark.parametrize(
    "settings_key,update_method,attr",
    [
        (
            "controlnet_settings",
            "update_controlnet_settings",
            "controlnet_settings",
        ),
        (
            "image_to_image_settings",
            "update_image_to_image_settings",
            "image_to_image_settings",
        ),
        ("outpaint_settings", "update_outpaint_settings", "outpaint_settings"),
        (
            "drawing_pad_settings",
            "update_drawing_pad_settings",
            "drawing_pad_settings",
        ),
    ],
)
def test_update_current_settings(settings_key, update_method, attr):
    logic = InputImageLogic(settings_key)
    ctx = DummyContext()
    logic.update_current_settings(ctx, "image", "foo")
    assert getattr(getattr(ctx, attr), "image") == "foo"
    assert ctx._calls[-1][1:] == ("image", "foo")


def test_update_current_settings_invalid_key():
    logic = InputImageLogic("invalid_key")
    ctx = DummyContext()
    with pytest.raises(ValueError):
        logic.update_current_settings(ctx, "foo", "bar")


@pytest.mark.parametrize(
    "settings_key,is_mask,expected_attr",
    [
        ("outpaint_settings", True, "mask"),
        ("outpaint_settings", False, "image"),
        ("controlnet_settings", False, "image"),
    ],
)
def test_load_image_from_settings(settings_key, is_mask, expected_attr):
    logic = InputImageLogic(settings_key, is_mask=is_mask)
    ctx = DummyContext()
    setattr(
        getattr(ctx, "drawing_pad_settings" if is_mask else settings_key),
        expected_attr,
        None,
    )
    assert logic.load_image_from_settings(ctx) is None

    # Set a fake binary image
    img = Image.new("RGB", (2, 2))
    from airunner.utils.image import convert_image_to_binary

    binary = convert_image_to_binary(img)
    setattr(
        getattr(ctx, "drawing_pad_settings" if is_mask else settings_key),
        expected_attr,
        binary,
    )
    out = logic.load_image_from_settings(ctx)
    assert isinstance(out, Image.Image)
    assert out.size == (2, 2)


def test_load_image_from_settings_use_generated_image():
    logic = InputImageLogic("controlnet_settings", use_generated_image=True)
    ctx = DummyContext()
    ctx.controlnet_settings.generated_image = None
    assert logic.load_image_from_settings(ctx) is None
    # Set a fake binary image
    img = Image.new("RGB", (2, 2))
    from airunner.utils.image import convert_image_to_binary

    binary = convert_image_to_binary(img)
    ctx.controlnet_settings.generated_image = binary
    out = logic.load_image_from_settings(ctx)
    assert isinstance(out, Image.Image)
    assert out.size == (2, 2)


@pytest.mark.parametrize(
    "settings_key,is_mask,attr",
    [
        ("outpaint_settings", True, "mask"),
        ("outpaint_settings", False, "image"),
        ("controlnet_settings", False, "image"),
    ],
)
def test_delete_image(settings_key, is_mask, attr):
    logic = InputImageLogic(settings_key, is_mask=is_mask)
    ctx = DummyContext()
    setattr(
        getattr(ctx, "drawing_pad_settings" if is_mask else settings_key),
        attr,
        "foo",
    )
    logic.delete_image(ctx)
    assert (
        getattr(
            getattr(ctx, "drawing_pad_settings" if is_mask else settings_key),
            attr,
        )
        is None
    )


def test_import_image(tmp_path):
    logic = InputImageLogic("controlnet_settings")
    ctx = DummyContext()
    img = Image.new("RGB", (2, 2))
    path = tmp_path / "test.png"
    img.save(path)
    logic.import_image(ctx, str(path))
    assert isinstance(ctx.controlnet_settings.image, bytes)


def test_import_image_file_not_found():
    logic = InputImageLogic("controlnet_settings")
    ctx = DummyContext()
    with pytest.raises((FileNotFoundError, OSError)):
        logic.import_image(ctx, "/nonexistent/path/to/image.png")


@pytest.mark.parametrize(
    "lock,link,forced,should_update",
    [
        (True, True, False, False),
        (False, False, False, False),
        (False, True, False, True),
        (True, True, True, True),
        (False, False, True, True),
    ],
)
def test_should_update_from_grid(lock, link, forced, should_update):
    logic = InputImageLogic("controlnet_settings")
    ctx = DummyContext()
    ctx.controlnet_settings.lock_input_image = lock
    ctx.controlnet_settings.use_grid_image_as_input = link
    assert logic.should_update_from_grid(ctx, forced=forced) == should_update


def test_update_image_from_grid():
    logic = InputImageLogic("controlnet_settings")
    ctx = DummyContext()
    ctx.drawing_pad_settings.image = b"bar"
    logic.update_image_from_grid(ctx)
    assert ctx.controlnet_settings.image == b"bar"


def test_update_image_from_grid_all_settings_keys():
    ctx = DummyContext()
    ctx.drawing_pad_settings.image = b"baz"
    for key in [
        "controlnet_settings",
        "image_to_image_settings",
        "outpaint_settings",
        "drawing_pad_settings",
    ]:
        logic = InputImageLogic(key)
        logic.update_image_from_grid(ctx)
        assert getattr(getattr(ctx, key), "image") == b"baz"
