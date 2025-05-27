"""
Unit tests for InputImageContainer (business logic, minimal Qt dependencies).
"""

import pytest
from unittest.mock import MagicMock, patch
from airunner.gui.widgets.canvas.input_image_container import (
    InputImageContainer,
)


class DummyUI:
    def __init__(self):
        self.tabWidget = MagicMock()
        self.label = MagicMock()


class DummyInputImage:
    def __init__(self):
        self.on_mask_generator_worker_response_signal = MagicMock()
        self.load_image_from_grid = MagicMock()


def make_container():
    with patch.object(InputImageContainer, "__init__", lambda self: None):
        c = InputImageContainer()
        c.ui = DummyUI()
        c.input_image = DummyInputImage()
        c.mask_image = DummyInputImage()
        c.generated_image = DummyInputImage()
        c.setProperty = MagicMock()
        c.property = MagicMock(return_value="image_to_image_settings")
        return c


def test_on_mask_generator_worker_response_signal():
    c = make_container()
    c.mask_image = DummyInputImage()
    from airunner.gui.widgets.canvas.input_image_container import (
        InputImageContainer as RealInputImageContainer,
    )

    RealInputImageContainer.on_mask_generator_worker_response_signal(c, None)
    c.mask_image.on_mask_generator_worker_response_signal.assert_called_once()


def test_on_load_image_from_grid_signal():
    c = make_container()
    c.input_image = DummyInputImage()
    from airunner.gui.widgets.canvas.input_image_container import (
        InputImageContainer as RealInputImageContainer,
    )

    RealInputImageContainer.on_load_image_from_grid_signal(c)
    c.input_image.load_image_from_grid.assert_called_once()


def test_showEvent_adds_tabs(monkeypatch):
    class DummyCanvasWidget:
        drawing_pad_image_changed = MagicMock()

    dummy_canvas = DummyCanvasWidget()
    with patch.object(InputImageContainer, "__init__", lambda self, *a, **k: None):
        c = InputImageContainer(canvas_widget=dummy_canvas)
        c.ui = DummyUI()
        c.setProperty = MagicMock()
        c.property = MagicMock(return_value="image_to_image_settings")
        c.input_image = None
        c.generated_image = None
        c.mask_image = None
        monkeypatch.setattr(
            "airunner.gui.widgets.canvas.input_image_container.InputImage",
            lambda **kwargs: DummyInputImage(),
        )
        from airunner.gui.widgets.canvas.input_image_container import (
            InputImageContainer as RealInputImageContainer,
        )

        RealInputImageContainer.showEvent(c, MagicMock())
        assert c.input_image is not None
        c.property = MagicMock(return_value="controlnet_settings")
        c.generated_image = None
        RealInputImageContainer.showEvent(c, MagicMock())
        assert c.generated_image is not None
        c.property = MagicMock(return_value="outpaint_settings")
        c.mask_image = None
        RealInputImageContainer.showEvent(c, MagicMock())
        assert c.mask_image is not None


def test_set_label():
    c = make_container()
    from airunner.gui.widgets.canvas.input_image_container import (
        InputImageContainer as RealInputImageContainer,
    )

    c.property = MagicMock(return_value="outpaint_settings")
    RealInputImageContainer._set_label(c)
    c.ui.label.setText.assert_called_with("Inpaint / Outpaint")
    c.property = MagicMock(return_value="controlnet_settings")
    RealInputImageContainer._set_label(c)
    c.ui.label.setText.assert_called_with("Controlnet")
    c.property = MagicMock(return_value="image_to_image_settings")
    RealInputImageContainer._set_label(c)
    c.ui.label.setText.assert_called_with("Image-to-Image")
