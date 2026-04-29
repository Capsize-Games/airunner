"""Tests for image export helpers."""

import importlib


export_image_module = importlib.import_module(
    "airunner.utils.image.export_image"
)


def test_get_next_image_sequence_caches_directory_scan(
    monkeypatch,
    tmp_path,
):
    """Repeated exports should not rescan the same folder every time."""
    folder = tmp_path / "20260429"
    folder.mkdir()
    scan_calls = []

    def fake_glob(pattern):
        scan_calls.append(pattern)
        return [
            str(folder / "1.png"),
            str(folder / "2.png"),
        ]

    monkeypatch.setattr(export_image_module.glob, "glob", fake_glob)
    export_image_module._NEXT_IMAGE_SEQUENCE.clear()

    first = export_image_module.get_next_image_sequence(
        str(folder),
        ".png",
    )
    second = export_image_module.get_next_image_sequence(
        str(folder),
        ".png",
    )

    assert first == 3
    assert second == 4
    assert len(scan_calls) == 1