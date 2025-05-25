"""
Unit tests for airunner.utils.application.ui_loader
Covers error handling and successful widget loading for both file and string-based UI loading.
"""
import pytest
from unittest.mock import patch, MagicMock
from airunner.utils.application import ui_loader

@pytest.fixture
def fake_widget():
    widget = MagicMock()
    widget.findChildren.return_value = []
    return widget

def test_load_ui_file_success(tmp_path, fake_widget):
    ui_path = tmp_path / "test.ui"
    ui_path.write_text("<ui></ui>")
    with patch("airunner.utils.application.ui_loader.QUiLoader") as loader_cls, \
         patch("airunner.utils.application.ui_loader.QFile") as qfile_cls:
        loader = loader_cls.return_value
        qfile = qfile_cls.return_value
        qfile.open.return_value = True
        loader.load.return_value = fake_widget
        qfile.close.return_value = None
        result = ui_loader.load_ui_file(str(ui_path))
        assert result is fake_widget
        qfile.open.assert_called_once()
        loader.load.assert_called_once_with(qfile, None)
        qfile.close.assert_called_once()

def test_load_ui_file_not_found(tmp_path):
    ui_path = tmp_path / "missing.ui"
    with patch("airunner.utils.application.ui_loader.QUiLoader"), \
         patch("airunner.utils.application.ui_loader.QFile") as qfile_cls:
        qfile = qfile_cls.return_value
        qfile.open.return_value = False
        with pytest.raises(FileNotFoundError):
            ui_loader.load_ui_file(str(ui_path))

def test_load_ui_file_load_fail(tmp_path):
    ui_path = tmp_path / "fail.ui"
    ui_path.write_text("<ui></ui>")
    with patch("airunner.utils.application.ui_loader.QUiLoader") as loader_cls, \
         patch("airunner.utils.application.ui_loader.QFile") as qfile_cls:
        loader = loader_cls.return_value
        qfile = qfile_cls.return_value
        qfile.open.return_value = True
        loader.load.return_value = None
        qfile.close.return_value = None
        with pytest.raises(RuntimeError):
            ui_loader.load_ui_file(str(ui_path))

def test_load_ui_from_string_success(fake_widget):
    with patch("airunner.utils.application.ui_loader.QUiLoader") as loader_cls, \
         patch("airunner.utils.application.ui_loader.QBuffer") as buffer_cls, \
         patch("airunner.utils.application.ui_loader.QIODevice.ReadOnly", 1):
        loader = loader_cls.return_value
        buffer = buffer_cls.return_value
        buffer.open.return_value = True
        loader.load.return_value = fake_widget
        buffer.close.return_value = None
        result = ui_loader.load_ui_from_string("<ui></ui>")
        assert result is fake_widget
        buffer.setData.assert_called_once()
        buffer.open.assert_called_once()
        loader.load.assert_called_once_with(buffer, None)
        buffer.close.assert_called_once()

def test_load_ui_from_string_open_fail():
    with patch("airunner.utils.application.ui_loader.QUiLoader"), \
         patch("airunner.utils.application.ui_loader.QBuffer") as buffer_cls, \
         patch("airunner.utils.application.ui_loader.QIODevice.ReadOnly", 1):
        buffer = buffer_cls.return_value
        buffer.open.return_value = False
        with pytest.raises(RuntimeError):
            ui_loader.load_ui_from_string("<ui></ui>")

def test_load_ui_from_string_load_fail():
    with patch("airunner.utils.application.ui_loader.QUiLoader") as loader_cls, \
         patch("airunner.utils.application.ui_loader.QBuffer") as buffer_cls, \
         patch("airunner.utils.application.ui_loader.QIODevice.ReadOnly", 1):
        loader = loader_cls.return_value
        buffer = buffer_cls.return_value
        buffer.open.return_value = True
        loader.load.return_value = None
        buffer.close.return_value = None
        with pytest.raises(RuntimeError):
            ui_loader.load_ui_from_string("<ui></ui>")

def test_load_ui_from_string_signal_handler():
    # Widget with children whose objectName matches a signal handler
    child = MagicMock()
    child.objectName.return_value = "on_click"
    child.clicked = MagicMock()
    widget = MagicMock()
    widget.findChildren.return_value = [child]
    class Handler:
        def on_click(self):
            pass
    handler = Handler()
    with patch("airunner.utils.application.ui_loader.QUiLoader") as loader_cls, \
         patch("airunner.utils.application.ui_loader.QBuffer") as buffer_cls, \
         patch("airunner.utils.application.ui_loader.QIODevice.ReadOnly", 1):
        loader = loader_cls.return_value
        buffer = buffer_cls.return_value
        buffer.open.return_value = True
        loader.load.return_value = widget
        buffer.close.return_value = None
        result = ui_loader.load_ui_from_string("<ui></ui>", signal_handler=handler)
        assert result is widget
        child.clicked.connect.assert_called_once_with(getattr(handler, "on_click"))
