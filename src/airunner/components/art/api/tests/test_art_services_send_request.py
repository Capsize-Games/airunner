import pytest

from airunner.components.art.api.art_services import ARTAPIService
from airunner.components.art.managers.stablediffusion.image_request import ImageRequest
from airunner.enums import SignalCode, GeneratorSection


def test_send_request_defaults_to_canvas_image_request(monkeypatch):
    api = ARTAPIService()

    emitted = []

    def fake_emit_signal(code, data=None):
        emitted.append((code, data))

    sentinel_request = ImageRequest(
        prompt="p1",
        strength=0.12,
        generator_section=GeneratorSection.IMG2IMG,
    )

    monkeypatch.setattr(api, "emit_signal", fake_emit_signal)
    monkeypatch.setattr(api.canvas, "create_image_request", lambda **_: sentinel_request)

    api.send_request()

    assert emitted, "Expected a DO_GENERATE_SIGNAL emission"
    code, data = emitted[-1]
    assert code == SignalCode.DO_GENERATE_SIGNAL
    assert data["image_request"] is sentinel_request


def test_send_request_prefers_explicit_image_request(monkeypatch):
    api = ARTAPIService()

    emitted = []

    def fake_emit_signal(code, data=None):
        emitted.append((code, data))

    monkeypatch.setattr(api, "emit_signal", fake_emit_signal)

    called = {"canvas": 0}

    def fake_create_image_request(**_kwargs):
        called["canvas"] += 1
        return ImageRequest(prompt="from_canvas")

    monkeypatch.setattr(api.canvas, "create_image_request", fake_create_image_request)

    explicit = ImageRequest(prompt="explicit", generator_section=GeneratorSection.IMG2IMG)
    api.send_request(image_request=explicit)

    assert called["canvas"] == 0
    assert emitted[-1][0] == SignalCode.DO_GENERATE_SIGNAL
    assert emitted[-1][1]["image_request"] is explicit


def test_send_request_prefers_data_image_request(monkeypatch):
    api = ARTAPIService()

    emitted = []

    def fake_emit_signal(code, data=None):
        emitted.append((code, data))

    monkeypatch.setattr(api, "emit_signal", fake_emit_signal)

    called = {"canvas": 0}

    def fake_create_image_request(**_kwargs):
        called["canvas"] += 1
        return ImageRequest(prompt="from_canvas")

    monkeypatch.setattr(api.canvas, "create_image_request", fake_create_image_request)

    in_data = ImageRequest(prompt="in_data", generator_section=GeneratorSection.OUTPAINT)
    api.send_request(data={"image_request": in_data})

    assert called["canvas"] == 0
    assert emitted[-1][0] == SignalCode.DO_GENERATE_SIGNAL
    assert emitted[-1][1]["image_request"] is in_data
