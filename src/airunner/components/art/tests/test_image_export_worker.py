"""Tests for image export worker behavior."""

from types import SimpleNamespace

from airunner.components.art.workers.image_export_worker import (
    ImageExportWorker,
)


def test_export_images_skips_when_request_disables_auto_export(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "airunner.components.art.workers.image_export_worker."
        "image_generation.export_images_with_metadata",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    worker = SimpleNamespace(emit_signal=lambda *args, **kwargs: None)

    ImageExportWorker._export_images(
        worker,
        [object()],
        {
            "image_request": SimpleNamespace(skip_auto_export=True),
            "application_settings": SimpleNamespace(
                auto_export_images=True,
                image_export_type="png",
            ),
            "path_settings": SimpleNamespace(image_path="/tmp"),
        },
    )

    assert calls == []