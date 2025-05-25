import pytest
from unittest.mock import patch
from airunner.utils.os.open_file_path import open_file_path


def test_open_file_path_calls_qfiledialog(monkeypatch):
    called = {}

    def fake_getOpenFileName(parent, label, directory, file_type):
        called["args"] = (parent, label, directory, file_type)
        return ("/tmp/fake.png", "Image Files (*.png *.jpg *.jpeg)")

    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName", fake_getOpenFileName
    )
    result = open_file_path(
        parent="parent",
        label="lbl",
        directory="/tmp",
        file_type="Image Files (*.png *.jpg *.jpeg)",
    )
    assert result[0] == "/tmp/fake.png"
    assert called["args"][1] == "lbl"
    assert called["args"][2] == "/tmp"
    assert called["args"][3] == "Image Files (*.png *.jpg *.jpeg)"
