"""
Tests for airunner.utils.image utility functions.
Covers: convert_binary_to_image, convert_image_to_binary, pil_to_qimage, convert_pil_to_qpixmap, delete_image, export_image, export_images, load_metadata_from_image.
"""

import io
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from PySide6.QtGui import QImage, QPixmap

from airunner.utils.image import (
    convert_binary_to_image,
    convert_image_to_binary,
    pil_to_qimage,
    convert_pil_to_qpixmap,
    delete_image,
    export_image,
    export_images,
    load_metadata_from_image,
)


def make_test_image(size=(10, 10), color=(255, 0, 0, 255)):
    img = Image.new("RGBA", size, color)
    return img


def test_convert_image_to_binary_and_back():
    img = make_test_image()
    binary = convert_image_to_binary(img)
    assert isinstance(binary, bytes)
    img2 = convert_binary_to_image(binary)
    assert isinstance(img2, Image.Image)
    assert img2.size == img.size


@pytest.mark.parametrize("bad_input", [b"notanimage", 123])
def test_convert_binary_to_image_bad_input(bad_input, capfd):
    img = convert_binary_to_image(bad_input)
    assert img is None
    out, err = capfd.readouterr()
    assert "Something went wrong" in out or "Something went wrong" in err


def test_convert_binary_to_image_none():
    img = convert_binary_to_image(None)
    assert img is None


def test_convert_image_to_binary_none():
    with pytest.raises(ValueError):
        convert_image_to_binary(None)


def test_convert_image_to_binary_attribute_error(capfd):
    class BadImage:
        def save(self, *a, **k):
            raise AttributeError("fail")

    result = convert_image_to_binary(BadImage())
    assert result is None
    out, err = capfd.readouterr()
    assert "Something went wrong" in out or "Something went wrong" in err


def test_pil_to_qimage_and_qpixmap(qapp):
    img = make_test_image()
    qimg = pil_to_qimage(img)
    assert isinstance(qimg, QImage)
    pixmap = convert_pil_to_qpixmap(img)
    assert isinstance(pixmap, QPixmap)


@pytest.mark.parametrize("mode", ["RGBA", "RGB", "L"])
def test_pil_to_qimage_all_modes(mode, qapp):
    # Create images in different modes
    if mode == "RGBA":
        img = Image.new("RGBA", (5, 5), (10, 20, 30, 40))
    elif mode == "RGB":
        img = Image.new("RGB", (5, 5), (10, 20, 30))
    elif mode == "L":
        img = Image.new("L", (5, 5), 128)
    else:
        pytest.skip("Unsupported mode")
    from airunner.utils.image.convert_pil_to_qimage import pil_to_qimage

    qimg = pil_to_qimage(img)
    assert isinstance(qimg, QImage)
    assert qimg.width() == 5 and qimg.height() == 5


def test_delete_image(tmp_path):
    file_path = tmp_path / "test.png"
    img = make_test_image()
    img.save(file_path)
    assert os.path.exists(file_path)
    delete_image(str(file_path))
    assert not os.path.exists(file_path)


def test_delete_image_missing(tmp_path, capfd):
    file_path = tmp_path / "missing.png"
    delete_image(str(file_path))  # Should not raise
    out, err = capfd.readouterr()
    # No error expected, but should not crash


def test_export_image_and_images(tmp_path):
    img = make_test_image()
    file_path = tmp_path / "out.png"
    export_image(img, str(file_path))
    assert os.path.exists(file_path)
    # export_images with batch
    images = [make_test_image(color=(i, 0, 0, 255)) for i in range(3)]
    batch_file = str(tmp_path / "batch.png")
    from datetime import datetime

    today = datetime.now().strftime("%Y%m%d")
    date_folder = tmp_path / today
    export_images(images, batch_file)
    # Should create a batch folder with images inside the date folder
    found = list(date_folder.glob("batch_*/"))
    assert found


def test_load_metadata_from_image(tmp_path):
    img = make_test_image()
    # Save and reload as Image object
    file_path = tmp_path / "meta.png"
    img.save(file_path)
    with Image.open(file_path) as im:
        meta = load_metadata_from_image(im)
    assert isinstance(meta, (dict, type(None)))


def test_load_metadata_from_image_missing(tmp_path):
    # Pass None to simulate missing image
    meta = load_metadata_from_image(None)
    assert meta == {} or meta is None
