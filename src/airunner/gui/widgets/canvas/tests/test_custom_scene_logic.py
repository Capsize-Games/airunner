import pytest
from PySide6.QtCore import QPointF
from PIL import Image, ImageFilter
from airunner.gui.widgets.canvas.logic.custom_scene_logic import (
    CustomSceneLogic,
)


class DummySettings:
    def __init__(self):
        self.current_tool = None
        self.x_pos = 10
        self.y_pos = 20


@pytest.fixture
def logic():
    settings = DummySettings()
    updates = []

    def update_application_settings(key, value):
        updates.append((key, value))
        setattr(settings, key, value)

    return (
        CustomSceneLogic(settings, update_application_settings),
        settings,
        updates,
    )


def test_add_and_clear_history(logic):
    scene_logic, _, _ = logic
    scene_logic.add_image_to_undo("img1")
    scene_logic.add_image_to_redo("img2")
    assert scene_logic.undo_history[-1]["image"] == "img1"
    assert scene_logic.redo_history[-1]["image"] == "img2"
    scene_logic.clear_history()
    assert scene_logic.undo_history == []
    assert scene_logic.redo_history == []


def test_apply_and_cancel_filter(logic):
    scene_logic, _, _ = logic
    img = Image.new("RGBA", (10, 10), (255, 0, 0, 255))
    filtered = scene_logic.apply_filter(img, ImageFilter.BLUR)
    assert filtered is not None
    restored = scene_logic.cancel_filter()
    assert restored is not None
    assert scene_logic.previewing_filter is False


def test_rotate_image(logic):
    scene_logic, _, _ = logic
    img = Image.new("RGBA", (10, 20), (255, 0, 0, 255))
    rotated = scene_logic.rotate_image(img, 90)
    assert rotated.size == (20, 10)


def test_get_pivot_point(logic):
    scene_logic, settings, _ = logic
    pt = scene_logic.get_pivot_point(settings)
    assert isinstance(pt, QPointF)
    assert pt.x() == 10 and pt.y() == 20


def test_get_current_tool(logic):
    scene_logic, settings, _ = logic
    settings.current_tool = "brush"
    assert scene_logic.get_current_tool().value == "brush"
    settings.current_tool = None
    assert scene_logic.get_current_tool() is None


def test_resize_image(logic):
    scene_logic, settings, _ = logic
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    settings.working_width = 50
    settings.working_height = 40
    resized = scene_logic.resize_image(img)
    assert resized.size[0] <= 50 and resized.size[1] <= 40


def test_cut_and_copy_image(logic):
    scene_logic, _, _ = logic
    img = Image.new("RGBA", (10, 10), (255, 0, 0, 255))
    called = {}

    def fake_copy(image):
        called["copy"] = True
        return image

    def fake_add_undo(image):
        called["undo"] = image

    def fake_delete():
        called["delete"] = True

    # cut_image should call all three
    result = scene_logic.cut_image(img, fake_copy, fake_add_undo, fake_delete)
    assert called["copy"] and called["undo"] is img and called["delete"]
    # copy_image should call only copy
    called.clear()
    result = scene_logic.copy_image(img, fake_copy)
    assert called["copy"]


def test_add_image_to_undo_and_redo(logic):
    scene_logic, _, _ = logic
    scene_logic.add_image_to_undo("img1")
    scene_logic.add_image_to_redo("img2")
    assert scene_logic.undo_history[-1]["image"] == "img1"
    assert scene_logic.redo_history[-1]["image"] == "img2"
    scene_logic.clear_history()
    assert scene_logic.undo_history == []
    assert scene_logic.redo_history == []


def test_rotate_image_and_record(logic):
    scene_logic, _, _ = logic
    img = Image.new("RGBA", (10, 20), (255, 0, 0, 255))
    called = {}

    def fake_add_undo(image):
        called["undo"] = image

    rotated = scene_logic.rotate_image_and_record(img, 90, fake_add_undo)
    assert rotated.size == (20, 10)
    assert called["undo"] is img
    # No image returns None
    assert scene_logic.rotate_image_and_record(None, 90) is None
