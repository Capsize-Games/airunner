"""Scene management mixin for CustomGraphicsView.

This mixin provides scene lifecycle management, including scene creation,
scene rect updates, item removal, and canvas background color management.
"""

from typing import Optional, Any
from PySide6.QtGui import QBrush, QColor

from airunner.components.art.gui.widgets.canvas.custom_scene import CustomScene
from airunner.components.art.gui.widgets.canvas.brush_scene import BrushScene
from airunner.enums import CanvasType


class SceneManagementMixin:
    """Mixin for managing graphics scene lifecycle and properties.

    This mixin handles:
    - Scene creation and initialization (CustomScene or BrushScene)
    - Scene rect updates based on viewport size
    - Scene item removal
    - Canvas background color management

    Attributes:
        _scene: The graphics scene instance
        _canvas_color: Current canvas background color (hex string)
        current_background_color: QColor for current background
    """

    @property
    def scene(self) -> Optional[CustomScene]:
        """Get or create the graphics scene for this view.

        Creates appropriate scene type (CustomScene for image canvas,
        BrushScene for brush canvas) based on canvas_type property.

        Returns:
            The graphics scene instance, or None if canvas_type is invalid.
        """
        scene = self._scene
        if not scene and self.canvas_type:
            if self.canvas_type == CanvasType.IMAGE.value:
                scene = CustomScene(canvas_type=self.canvas_type)
            elif self.canvas_type == CanvasType.BRUSH.value:
                scene = BrushScene(canvas_type=self.canvas_type)
            else:
                self.logger.error(f"Unknown canvas type: {self.canvas_type}")
                return

        if scene:
            scene.parent = self
            self._scene = scene
            self.setScene(scene)
            self.set_canvas_color(scene)
        return self._scene

    @scene.setter
    def scene(self, value: Optional[CustomScene]) -> None:
        """Set the graphics scene.

        Args:
            value: The scene instance to set.
        """
        self._scene = value

    def set_scene_rect(self) -> None:
        """Update the scene rect to match current viewport size.

        Sets scene rect to (0, 0, width, height) based on viewport dimensions.
        """
        if not self.scene:
            return
        canvas_container_size = self.viewport().size()
        self.scene.setSceneRect(
            0, 0, canvas_container_size.width(), canvas_container_size.height()
        )

    def update_scene(self) -> None:
        """Trigger a scene update to refresh the display.

        Calls scene.update() to redraw scene contents.
        """
        if not self.scene:
            return
        self.scene.update()

    def remove_scene_item(self, item: Optional[Any]) -> None:
        """Remove an item from the scene.

        Args:
            item: The graphics item to remove. Does nothing if None or not in scene.
        """
        if item is None:
            return
        if item.scene() == self.scene:
            self.scene.removeItem(item)

    def set_canvas_color(
        self,
        scene: Optional[CustomScene] = None,
        canvas_color: Optional[str] = None,
    ) -> None:
        """Set the canvas background color.

        Args:
            scene: Scene to update. Defaults to self.scene if None.
            canvas_color: Hex color string (e.g., "#000000"). Defaults to
                grid_settings.canvas_color if None.
        """
        scene = self.scene if not scene else scene
        canvas_color = canvas_color or self.grid_settings.canvas_color
        self.current_background_color = canvas_color
        color = QColor(self.current_background_color)
        brush = QBrush(color)
        scene.setBackgroundBrush(brush)
