"""Tests for SceneManagementMixin."""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QSize
from PySide6.QtGui import QBrush, QColor

from airunner.components.art.gui.widgets.canvas.mixins.scene_management_mixin import (
    SceneManagementMixin,
)
from airunner.enums import CanvasType


class TestableSceneManagementMixin(SceneManagementMixin):
    """Testable version of SceneManagementMixin with required dependencies."""

    def __init__(self):
        self._scene = None
        self._canvas_color = "#000000"
        self.current_background_color = None
        self.canvas_type = CanvasType.IMAGE.value
        self.logger = MagicMock()
        self.grid_settings = MagicMock()
        self.grid_settings.canvas_color = "#FFFFFF"

    def viewport(self):
        """Mock viewport method."""
        mock_viewport = MagicMock()
        mock_viewport.size.return_value = QSize(800, 600)
        return mock_viewport

    def setScene(self, scene):
        """Mock setScene method."""


@pytest.fixture
def mixin(qapp):
    """Create a testable scene management mixin instance."""
    return TestableSceneManagementMixin()


@pytest.fixture
def mock_scene():
    """Create a mock scene."""
    scene = MagicMock()
    scene.parent = None
    return scene


class TestSceneProperty:
    """Test scene property getter and setter."""

    def test_scene_getter_returns_existing_scene(self, mixin, mock_scene):
        """Test that scene getter returns existing scene."""
        mixin._scene = mock_scene
        assert mixin.scene == mock_scene

    def test_scene_setter_sets_scene(self, mixin, mock_scene):
        """Test that scene setter updates _scene."""
        mixin.scene = mock_scene
        assert mixin._scene == mock_scene

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.scene_management_mixin.CustomScene"
    )
    def test_scene_creates_custom_scene_for_image_canvas(
        self, mock_custom_scene, mixin
    ):
        """Test that scene property creates CustomScene for image canvas."""
        mixin.canvas_type = CanvasType.IMAGE.value
        mixin._scene = None

        # Create mock scene instance
        scene_instance = MagicMock()
        mock_custom_scene.return_value = scene_instance

        # Access scene property
        result = mixin.scene

        # Verify CustomScene was created
        mock_custom_scene.assert_called_once_with(
            canvas_type=CanvasType.IMAGE.value
        )
        assert result == scene_instance
        assert scene_instance.parent == mixin

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.scene_management_mixin.BrushScene"
    )
    def test_scene_creates_brush_scene_for_brush_canvas(
        self, mock_brush_scene, mixin
    ):
        """Test that scene property creates BrushScene for brush canvas."""
        mixin.canvas_type = CanvasType.BRUSH.value
        mixin._scene = None

        # Create mock scene instance
        scene_instance = MagicMock()
        mock_brush_scene.return_value = scene_instance

        # Access scene property
        result = mixin.scene

        # Verify BrushScene was created
        mock_brush_scene.assert_called_once_with(
            canvas_type=CanvasType.BRUSH.value
        )
        assert result == scene_instance
        assert scene_instance.parent == mixin

    def test_scene_returns_none_for_invalid_canvas_type(self, mixin):
        """Test that scene returns None for invalid canvas type."""
        mixin.canvas_type = "invalid_type"
        mixin._scene = None

        result = mixin.scene

        assert result is None
        mixin.logger.error.assert_called_once()

    def test_scene_returns_none_when_no_canvas_type(self, mixin):
        """Test that scene returns None when canvas_type is None."""
        mixin.canvas_type = None
        mixin._scene = None

        result = mixin.scene

        assert result is None


class TestSetSceneRect:
    """Test set_scene_rect method."""

    def test_set_scene_rect_updates_scene_rect(self, mixin, mock_scene):
        """Test that set_scene_rect updates scene rect to viewport size."""
        mixin._scene = mock_scene

        mixin.set_scene_rect()

        # Verify setSceneRect was called with viewport dimensions
        mock_scene.setSceneRect.assert_called_once_with(0, 0, 800, 600)

    def test_set_scene_rect_does_nothing_when_no_scene(self, mixin):
        """Test that set_scene_rect does nothing when scene is None."""
        mixin._scene = None

        # Should not raise exception
        mixin.set_scene_rect()


class TestUpdateScene:
    """Test update_scene method."""

    def test_update_scene_calls_scene_update(self, mixin, mock_scene):
        """Test that update_scene calls scene.update()."""
        mixin._scene = mock_scene

        mixin.update_scene()

        mock_scene.update.assert_called_once()

    def test_update_scene_does_nothing_when_no_scene(self, mixin):
        """Test that update_scene does nothing when scene is None."""
        mixin._scene = None

        # Should not raise exception
        mixin.update_scene()


class TestRemoveSceneItem:
    """Test remove_scene_item method."""

    def test_remove_scene_item_removes_item_from_scene(
        self, mixin, mock_scene
    ):
        """Test that remove_scene_item removes item from scene."""
        mixin._scene = mock_scene
        mock_item = MagicMock()
        mock_item.scene.return_value = mock_scene

        mixin.remove_scene_item(mock_item)

        mock_scene.removeItem.assert_called_once_with(mock_item)

    def test_remove_scene_item_does_nothing_for_none_item(
        self, mixin, mock_scene
    ):
        """Test that remove_scene_item does nothing for None item."""
        mixin._scene = mock_scene

        mixin.remove_scene_item(None)

        mock_scene.removeItem.assert_not_called()

    def test_remove_scene_item_does_nothing_if_item_not_in_scene(
        self, mixin, mock_scene
    ):
        """Test that remove_scene_item does nothing if item not in this scene."""
        mixin._scene = mock_scene
        mock_item = MagicMock()
        other_scene = MagicMock()
        mock_item.scene.return_value = other_scene

        mixin.remove_scene_item(mock_item)

        mock_scene.removeItem.assert_not_called()


class TestSetCanvasColor:
    """Test set_canvas_color method."""

    def test_set_canvas_color_sets_background_brush(self, mixin, mock_scene):
        """Test that set_canvas_color sets scene background brush."""
        mixin._scene = mock_scene

        mixin.set_canvas_color(scene=mock_scene, canvas_color="#FF0000")

        # Verify background brush was set
        mock_scene.setBackgroundBrush.assert_called_once()
        call_args = mock_scene.setBackgroundBrush.call_args[0][0]
        assert isinstance(call_args, QBrush)
        assert mixin.current_background_color == "#FF0000"

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.scene_management_mixin.CustomScene"
    )
    def test_set_canvas_color_uses_default_scene(
        self, mock_custom_scene, mixin
    ):
        """Test that set_canvas_color uses self.scene when scene is None."""
        # Create a mock scene instance
        scene_instance = MagicMock()
        mock_custom_scene.return_value = scene_instance
        mixin.canvas_type = CanvasType.IMAGE.value
        mixin._scene = None
        mixin.setScene = MagicMock()

        # When scene=None, set_canvas_color should get self.scene
        # This will trigger scene creation
        mixin.set_canvas_color(canvas_color="#00FF00")

        # Scene should have been created and setBackgroundBrush called
        # (once during scene creation, once during set_canvas_color call)
        assert scene_instance.setBackgroundBrush.call_count >= 1
        assert mixin.current_background_color == "#00FF00"

    def test_set_canvas_color_uses_grid_settings_color(
        self, mixin, mock_scene
    ):
        """Test that set_canvas_color uses grid_settings.canvas_color when None."""
        mixin._scene = mock_scene
        mixin.grid_settings.canvas_color = "#0000FF"

        mixin.set_canvas_color(scene=mock_scene)

        mock_scene.setBackgroundBrush.assert_called_once()
        assert mixin.current_background_color == "#0000FF"

    def test_set_canvas_color_creates_correct_qcolor(self, mixin, mock_scene):
        """Test that set_canvas_color creates QColor correctly."""
        mixin._scene = mock_scene

        mixin.set_canvas_color(scene=mock_scene, canvas_color="#ABCDEF")

        # Verify the color in the brush
        call_args = mock_scene.setBackgroundBrush.call_args[0][0]
        assert isinstance(call_args, QBrush)
        color = call_args.color()
        assert isinstance(color, QColor)
        # QColor should match the input color
        test_color = QColor("#ABCDEF")
        assert color.name() == test_color.name()


class TestSceneIntegration:
    """Test integration scenarios with scene management."""

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.scene_management_mixin.CustomScene"
    )
    def test_scene_creation_sets_parent_and_calls_setscene(
        self, mock_custom_scene, mixin
    ):
        """Test that scene creation properly initializes scene."""
        scene_instance = MagicMock()
        mock_custom_scene.return_value = scene_instance
        mixin.canvas_type = CanvasType.IMAGE.value
        mixin._scene = None
        mixin.setScene = MagicMock()

        result = mixin.scene

        # Verify all setup steps
        assert scene_instance.parent == mixin
        mixin.setScene.assert_called_once_with(scene_instance)
        assert result == scene_instance

    def test_multiple_scene_accesses_return_same_instance(self, mixin):
        """Test that multiple scene property accesses return cached instance."""
        mock_scene = MagicMock()
        mixin._scene = mock_scene

        scene1 = mixin.scene
        scene2 = mixin.scene

        assert scene1 is scene2
        assert scene1 is mock_scene
