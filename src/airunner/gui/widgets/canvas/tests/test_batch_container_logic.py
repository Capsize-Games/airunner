import pytest
import tempfile
import os
from airunner.gui.widgets.canvas.logic.batch_container_logic import (
    BatchContainerLogic,
)


class DummyPathSettings:
    def __init__(self, image_path):
        self.image_path = image_path


@pytest.fixture
def temp_image_dir(tmp_path):
    # Create a temp structure: /YYYYMMDD/batch_1/img1.png, loose.png
    date_folder = tmp_path / "20250101"
    date_folder.mkdir()
    (date_folder / "loose.png").write_text("fake")
    batch_folder = date_folder / "batch_1"
    batch_folder.mkdir()
    (batch_folder / "img1.png").write_text("fake")
    return tmp_path


@pytest.fixture
def logic(temp_image_dir):
    return BatchContainerLogic(DummyPathSettings(str(temp_image_dir)))


def test_get_date_folders(logic, temp_image_dir):
    folders = logic.get_date_folders()
    assert "20250101" in folders


def test_display_format(logic):
    assert logic.display_format("20250101") == "2025-01-01"
    assert logic.display_format("bad") == "bad"


def test_get_date_folder_path(logic):
    path = logic.get_date_folder_path("2025-01-01")
    assert path.endswith("20250101")


def test_find_loose_images(logic, temp_image_dir):
    folder = os.path.join(str(temp_image_dir), "20250101")
    images = logic.find_loose_images(folder)
    assert any("loose.png" in img for img in images)


def test_find_batches(logic, temp_image_dir):
    folder = os.path.join(str(temp_image_dir), "20250101")
    batches = logic.find_batches(folder)
    assert batches and batches[0]["batch_folder"].endswith("batch_1")
    assert any("img1.png" in img for img in batches[0]["images"])


def test_find_batch_images(logic, temp_image_dir):
    batch_folder = os.path.join(str(temp_image_dir), "20250101", "batch_1")
    images = logic.find_batch_images(batch_folder)
    assert any("img1.png" in img for img in images)


def test_get_date_folders_path_not_exist():
    logic = BatchContainerLogic(
        type("Dummy", (), {"image_path": "/tmp/does_not_exist_12345"})()
    )
    assert logic.get_date_folders() == []


def test_get_date_folder_path_invalid():
    logic = BatchContainerLogic(type("Dummy", (), {"image_path": "/tmp"})())
    # Should fallback to get_today_folder if input is not splittable
    result = logic.get_date_folder_path("not-a-date")
    assert os.path.dirname(result) == "/tmp"


def test_find_loose_images_path_not_exist():
    logic = BatchContainerLogic(type("Dummy", (), {"image_path": "/tmp"})())
    assert logic.find_loose_images("/tmp/does_not_exist_12345") == []


def test_find_batches_path_not_exist():
    logic = BatchContainerLogic(type("Dummy", (), {"image_path": "/tmp"})())
    assert logic.find_batches("/tmp/does_not_exist_12345") == []


def test_find_batch_images_path_not_exist():
    logic = BatchContainerLogic(type("Dummy", (), {"image_path": "/tmp"})())
    assert logic.find_batch_images("/tmp/does_not_exist_12345") == []
