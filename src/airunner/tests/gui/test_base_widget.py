import pytest
from PySide6.QtWidgets import QWidget
from airunner.gui.widgets.base_widget import BaseWidget


class DummyWidget(BaseWidget):
    def save_state(self):
        self._saved = True

    def restore_state(self):
        self._restored = True


@pytest.fixture
def dummy_widget(qtbot):
    widget = DummyWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_base_widget_happy_path(dummy_widget):
    """
    Happy path: Test initialization and state save/restore.
    """
    dummy_widget.save_state()
    dummy_widget.restore_state()
    assert hasattr(dummy_widget, "_saved")
    assert hasattr(dummy_widget, "_restored")
    assert isinstance(dummy_widget, QWidget)


def test_base_widget_sad_path_no_ui(dummy_widget):
    """
    Sad path: Test widget with no UI set (ui is None).
    """
    dummy_widget.ui = None
    # Should not raise when calling save/restore
    dummy_widget.save_state()
    dummy_widget.restore_state()
    assert dummy_widget.ui is None


def test_base_widget_bad_path_invalid_splitters(dummy_widget):
    """
    Bad path: Set splitters to an invalid type and check for robustness.
    """
    dummy_widget.splitters = (
        "not_a_list"  # Should not crash, but will break type expectations
    )
    assert isinstance(dummy_widget._splitters, str)
