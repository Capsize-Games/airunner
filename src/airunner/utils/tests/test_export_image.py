"""
Tests for airunner.utils.image.export_image and related helpers.
Covers: get_today_folder, get_next_sequence_folder, get_next_image_sequence, export_image, export_images.
"""

import os
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image, PngImagePlugin
from airunner.utils.image.export_image import (
    get_today_folder,
    get_next_sequence_folder,
    get_next_image_sequence,
    export_image,
    export_images,
)


def make_test_image(size=(8, 8), color=(123, 45, 67, 255)):
    return Image.new("RGBA", size, color)


def test_get_today_folder_creates_and_returns(tmp_path):
    folder = get_today_folder(str(tmp_path))
    assert os.path.exists(folder)
    # Should be today's date
    from datetime import datetime

    today = datetime.now().strftime("%Y%m%d")
    assert folder.endswith(today)


def test_get_next_sequence_folder(tmp_path):
    # No folders yet
    folder1 = get_next_sequence_folder(str(tmp_path), "batch_")
    assert os.path.exists(folder1)
    assert folder1.endswith("batch_1")
    # Add another
    folder2 = get_next_sequence_folder(str(tmp_path), "batch_")
    assert folder2.endswith("batch_2")
    # Add a non-numeric folder
    os.makedirs(tmp_path / "batch_foo")
    folder3 = get_next_sequence_folder(str(tmp_path), "batch_")
    assert folder3.endswith("batch_3")


def test_get_next_image_sequence(tmp_path):
    # No files
    seq = get_next_image_sequence(str(tmp_path), ".png")
    assert seq == 1
    # Add files: 1.png, 2.png, foo.png
    (tmp_path / "1.png").touch()
    (tmp_path / "2.png").touch()
    (tmp_path / "foo.png").touch()
    seq2 = get_next_image_sequence(str(tmp_path), ".png")
    assert seq2 == 3


def test_export_image_png_with_metadata(tmp_path):
    img = make_test_image()
    file_path = tmp_path / "meta.png"
    metadata = {"foo": "bar", "num": 42}
    export_image(img, str(file_path), metadata)
    assert os.path.exists(file_path)
    with Image.open(file_path) as im:
        info = im.info
        assert info.get("foo") == "bar"
        assert info.get("num") == "42"


def test_export_image_non_png_with_metadata(tmp_path):
    img = make_test_image().convert("RGB")  # JPEG does not support RGBA
    file_path = tmp_path / "meta.jpg"
    metadata = {"foo": "bar"}
    export_image(img, str(file_path), metadata)
    assert os.path.exists(file_path)
    # JPEG can't store metadata this way, so info should not have 'foo'
    with Image.open(file_path) as im:
        assert "foo" not in im.info


def test_export_images_single_and_batch(tmp_path):
    img = make_test_image()
    file_path = tmp_path / "single.png"
    export_images([img], str(file_path))
    # Should be in today's folder, named 1.png
    from datetime import datetime

    today = datetime.now().strftime("%Y%m%d")
    date_folder = tmp_path / today
    assert (date_folder / "1.png").exists()
    # Batch export
    images = [make_test_image(color=(i, 0, 0, 255)) for i in range(2)]
    batch_file = str(tmp_path / "batch.png")
    export_images(images, batch_file)
    # Should create batch_1 folder
    found = list(date_folder.glob("batch_1/1.png"))
    assert found
    found2 = list(date_folder.glob("batch_1/2.png"))
    assert found2


def test_export_images_with_metadata(tmp_path):
    images = [make_test_image(), make_test_image(color=(1, 2, 3, 255))]
    metadata = [{"a": 1}, {"b": 2}]
    file_path = tmp_path / "meta.png"
    export_images(images, str(file_path), metadata)
    from datetime import datetime

    today = datetime.now().strftime("%Y%m%d")
    date_folder = tmp_path / today
    # Should be in batch_2 (if previous batch exists)
    batch_folders = sorted(date_folder.glob("batch_*/"))
    assert batch_folders
    for i, folder in enumerate(batch_folders[-1:]):
        for idx, meta in enumerate(metadata):
            img_file = folder / f"{idx+1}.png"
            assert img_file.exists()
            with Image.open(img_file) as im:
                for k, v in meta.items():
                    assert im.info.get(k) == str(v)


def test_export_image_invalid_image(tmp_path):
    # Should raise AttributeError or TypeError if not an image
    with pytest.raises(Exception):
        export_image("notanimage", str(tmp_path / "fail.png"))


def test_export_image_unwritable_path(monkeypatch):
    img = make_test_image()
    # Patch image.save to raise OSError
    with patch.object(Image.Image, "save", side_effect=OSError("fail")):
        with pytest.raises(OSError):
            export_image(img, "/root/forbidden.png")
