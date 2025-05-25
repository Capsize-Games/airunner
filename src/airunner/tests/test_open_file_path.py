"""
Unit tests for airunner.utils.os.open_file_path.open_file_path
"""

import pytest


def test_open_file_path(monkeypatch):
    called = {}

    def fake_getOpenFileName(parent, label, directory, file_type):
        called.update(locals())
        return ("/tmp/foo.png", "Image Files (*.png *.jpg *.jpeg)")

    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName", fake_getOpenFileName
    )
    from airunner.utils import open_file_path

    result = open_file_path(None, "Import", "/tmp", "*")
    assert result[0] == "/tmp/foo.png"
