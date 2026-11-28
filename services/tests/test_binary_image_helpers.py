"""Unit tests for the binary-to-image extraction helpers.

_normalize_binary_input, _attempt_fast_paths, and _decode_image_bytes
were extracted to keep convert_binary_to_image within the
long-function threshold. These tests pin the coercion, the fast
paths, and the decode rejection of oversized/corrupt input.
"""

import base64
import io

from PIL import Image

import importlib

cbi_module = importlib.import_module(
    "airunner_services.utils.image.convert_binary_to_image"
)
from airunner_services.utils.image.convert_binary_to_image import (
    _attempt_fast_paths,
    _decode_image_bytes,
    _normalize_binary_input,
    convert_binary_to_image,
)


def _png_bytes(width=2, height=3):
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_normalize_memoryview():
    data = memoryview(b"abc")
    assert _normalize_binary_input(data) == b"abc"


def test_normalize_str_base64_decodes():
    encoded = base64.b64encode(b"rawdata").decode()
    assert _normalize_binary_input(encoded) == b"rawdata"


def test_normalize_str_falls_back_to_utf8():
    assert _normalize_binary_input("plain text") == b"plain text"


def _raw_bytes(width=2, height=2):
    payload = b"AIRAW1" + width.to_bytes(4, "big") + height.to_bytes(4, "big")
    payload += bytes([255, 0, 0, 255] * (width * height))
    return payload


def test_attempt_fast_paths_raw_hit():
    raw = _raw_bytes()
    data, img = _attempt_fast_paths(raw)
    assert img is not None
    assert data == raw


def test_attempt_fast_paths_miss_returns_none():
    data, img = _attempt_fast_paths(b"not an image at all........")
    assert img is None


def test_convert_none_returns_none():
    assert convert_binary_to_image(None) is None


def test_convert_png_roundtrip():
    png = _png_bytes(4, 5)
    img = convert_binary_to_image(png)
    assert img is not None
    assert img.size == (4, 5)


def test_decode_rejects_garbage():
    assert _decode_image_bytes(b"") is None
    assert _decode_image_bytes(b"garbage-garbage-garbage") is None


def test_decode_rejects_oversized(monkeypatch):
    monkeypatch.setattr(cbi_module, "MAX_RAW_DIMENSION", 4)
    img = _decode_image_bytes(_png_bytes(100, 100))
    # No header dimension check fires below the cap test set above;
    # big header dimensions exceed the lowered cap and reject.
    assert img is None
