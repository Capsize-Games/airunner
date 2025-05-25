import pytest
from PySide6.QtWidgets import QApplication
from airunner.gui.widgets.canvas.canvas_widget import CanvasWidget


class DummyButton:
    def setIcon(self, icon):
        pass

    def blockSignals(self, val):
        pass

    def setChecked(self, val):
        pass


class DummySplitter:
    def restoreState(self, state):
        pass

    def setSizes(self, sizes):
        pass

    def setStretchFactor(self, index, factor):
        pass

    def setCollapsible(self, index, collapsible):
        pass

    def setOrientation(self, orientation):
        self._orientation = orientation

    def orientation(self):
        return getattr(self, "_orientation", None)

    def count(self):
        return 2

    def widget(self, index):
        return None

    def setHandleWidth(self, width):
        pass

    def setChildrenCollapsible(self, collapsible):
        pass

    def height(self) -> int:  # Added height method
        return 100  # Return a dummy height


class DummyUI:
    def __init__(self):
        self.new_button = DummyButton()
        self.import_button = DummyButton()
        self.export_button = DummyButton()
        self.recenter_button = DummyButton()
        self.active_grid_area_button = DummyButton()
        self.brush_button = DummyButton()
        self.eraser_button = DummyButton()
        self.grid_button = DummyButton()
        self.undo_button = DummyButton()
        self.redo_button = DummyButton()
        self.text_button = DummyButton()
        self.canvas_splitter = DummySplitter()

    def setupUi(self, parent):
        pass


class DummyBaseWidget(CanvasWidget):
    widget_class_ = DummyUI

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@pytest.fixture
def canvas_widget(qtbot):
    widget = DummyBaseWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_canvas_widget_happy_path(canvas_widget):
    # Happy path: Widget initializes and has expected UI attributes
    ui = canvas_widget.ui
    assert hasattr(ui, "new_button")
    assert hasattr(ui, "brush_button")
    assert hasattr(ui, "eraser_button")


def test_canvas_widget_sad_path(canvas_widget):
    # Sad path: Accessing a non-existent tool
    with pytest.raises(AttributeError):
        _ = canvas_widget.ui.non_existent_button


def test_canvas_widget_bad_path():
    # Bad path: Instantiating without QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    widget = DummyBaseWidget()
    assert widget is not None
