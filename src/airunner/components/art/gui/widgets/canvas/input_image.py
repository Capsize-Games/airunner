import os
from typing import Optional, Union

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QFileDialog, QGraphicsScene
from PySide6.QtGui import QPixmap, QImage, QPen, QPainter

from airunner.settings import AIRUNNER_VALID_IMAGE_FILES
from airunner.utils.image import (
    convert_binary_to_image,
    convert_image_to_binary,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.canvas.templates.input_image_ui import (
    Ui_input_image,
)
from airunner.components.art.gui.widgets.canvas.input_image_scene import (
    InputImageScene,
)
from airunner.components.art.gui.widgets.canvas.simple_image_scene import (
    SimpleImageScene,
)


class InputImage(BaseWidget):
    widget_class_ = Ui_input_image
    icons = [
        ("link", "link_to_grid_image_button"),
        ("lock", "lock_input_image_button"),
        ("refresh-ccw", "refresh_button"),
        ("folder", "import_button"),
        ("trash-2", "delete_button"),
    ]

    def __init__(self, *args, **kwargs):
        self.settings_key = kwargs.pop("settings_key")
        self.use_generated_image = kwargs.pop("use_generated_image", False)
        self.is_mask = kwargs.pop("is_mask", False)
        # Use simple scene by default for preview-only widgets
        # Complex scene is only needed for mask drawing (is_mask=True)
        self._use_simple_scene = kwargs.pop("use_simple_scene", not self.is_mask)
        self._import_path = ""
        super().__init__(*args, **kwargs)
        self.ui.strength_slider_widget.setProperty(
            "settings_property", f"{self.settings_key}.strength"
        )
        self.ui.strength_slider_widget.setProperty(
            f"{self.settings_key}.strength", self.current_settings.strength
        )
        self._scene: Optional[Union[InputImageScene, SimpleImageScene]] = None
        self.setup_scene()
        self.load_image_from_settings()

    def setup_scene(self):
        """Set up the scene for displaying input images.
        
        Uses SimpleImageScene for preview-only widgets (most cases).
        Uses InputImageScene only for mask drawing (is_mask=True).
        """
        if self._use_simple_scene:
            # Simple, reliable scene for preview-only widgets
            self._scene = SimpleImageScene()
        else:
            # Complex scene with drawing capabilities for mask editing
            self._scene = InputImageScene(
                canvas_type="input_image",
                settings_key=self.settings_key,
                is_mask=self.is_mask,
            )

            if hasattr(self._scene, "use_generated_image"):
                allow_generated = self.use_generated_image and not getattr(
                    self.current_settings, "lock_input_image", False
                )
                self._scene.use_generated_image = allow_generated

        # Connect the scene to the graphics view
        self.ui.image_container.setScene(self._scene)

        # Set up the graphics view for proper interaction
        self.ui.image_container.setRenderHints(
            QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.Antialiasing
        )

        # Enable mouse tracking and clickable interaction
        self.ui.image_container.setMouseTracking(True)
        self.ui.image_container.setInteractive(True)

        # Set anchors for scaling
        self.ui.image_container.setResizeAnchor(
            self.ui.image_container.ViewportAnchor.AnchorViewCenter
        )
        self.ui.image_container.setTransformationAnchor(
            self.ui.image_container.ViewportAnchor.AnchorViewCenter
        )
        # Connect resize event to fitInView
        self.ui.image_container.resizeEvent = self._fit_image_on_resize

        self.ui.image_container.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.ui.image_container.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

    def _fit_image_on_resize(self, event):
        # Call the default resizeEvent
        QGraphicsView = type(self.ui.image_container)
        QGraphicsView.resizeEvent(self.ui.image_container, event)
        self.fit_image_to_view()

    def fit_image_to_view(self):
        """Fit the current image to the view bounds."""
        scene = self._scene
        if not scene:
            return
        
        # Get the scene rect (already set correctly by SimpleImageScene.set_image)
        rect = scene.sceneRect()
        if rect.isNull() or rect.isEmpty():
            return
        
        self.ui.image_container.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    @property
    def current_settings(self):
        settings = None
        if self.settings_key == "controlnet_settings":
            settings = self.controlnet_settings
        elif self.settings_key == "image_to_image_settings":
            settings = self.image_to_image_settings
        elif self.settings_key == "outpaint_settings":
            settings = self.outpaint_settings
        elif self.settings_key == "drawing_pad_settings":
            settings = self.drawing_pad_settings

        if not settings:
            raise ValueError(
                f"Settings not found for key: {self.settings_key}"
            )

        return settings

    def on_mask_generator_worker_response_signal(self):
        if self.settings_key == "outpaint_settings":
            self.load_image_from_settings()

    def update_current_settings(self, key, value):
        if self.settings_key == "controlnet_settings":
            self.update_controlnet_settings(**{key: value})
        elif self.settings_key == "image_to_image_settings":
            self.update_image_to_image_settings(**{key: value})
        elif self.settings_key == "outpaint_settings":
            self.update_outpaint_settings(**{key: value})
        elif self.settings_key == "drawing_pad_settings":
            self.update_drawing_pad_settings(**{key: value})

        self.api.art.canvas.input_image_changed(self.settings_key, key, value)
        # If lock_input_image changed programmatically, ensure the scene honors it
        if key == "lock_input_image":
            try:
                if self._scene and hasattr(self._scene, "use_generated_image"):
                    self._scene.use_generated_image = (
                        self.use_generated_image and not bool(value)
                    )
            except Exception:
                # Defensive: don't let UI updates raise
                pass

    def showEvent(self, event):
        super().showEvent(event)
        if self.settings_key == "controlnet_settings":
            self.ui.strength_slider_widget.hide()
            self.ui.controlnet_settings.show()
        else:
            self.ui.strength_slider_widget.show()
            self.ui.controlnet_settings.hide()

        if self.settings_key == "outpaint_settings":
            self.ui.strength_slider_widget.setProperty(
                "settings_property", "outpaint_settings.strength"
            )
            self.ui.mask_blur_slider_widget.show()
        else:
            self.ui.mask_blur_slider_widget.hide()

        self.ui.EnableSwitch.toggled.connect(self.enabled_toggled)

        if self.settings_key == "outpaint_settings":
            if self.is_mask:
                self.ui.import_button.hide()

        self.ui.EnableSwitch.blockSignals(True)
        self.ui.EnableSwitch.checked = self.current_settings.enabled
        self.ui.EnableSwitch.setChecked(self.current_settings.enabled)
        self.ui.EnableSwitch.dPtr.animate(self.current_settings.enabled)
        self.ui.EnableSwitch.blockSignals(False)

        self.ui.link_to_grid_image_button.blockSignals(True)
        self.ui.lock_input_image_button.blockSignals(True)
        self.ui.link_to_grid_image_button.setChecked(
            self.current_settings.use_grid_image_as_input
        )
        self.ui.lock_input_image_button.setChecked(
            self.current_settings.lock_input_image or False
        )
        self.ui.link_to_grid_image_button.blockSignals(False)
        self.ui.lock_input_image_button.blockSignals(False)

        # Ensure the scene reflects the current lock state when the widget is shown.
        try:
            if self._scene and hasattr(self._scene, "use_generated_image"):
                self._scene.use_generated_image = (
                    self.use_generated_image
                    and not getattr(
                        self.current_settings, "lock_input_image", False
                    )
                )
        except Exception:
            pass
        if self.current_settings.use_grid_image_as_input:
            self.load_image_from_grid()
            return

        self.load_image_from_settings()

    @Slot(bool)
    def enabled_toggled(self, val):
        self.update_current_settings("enabled", val)

    @Slot(bool)
    def on_lock_input_image_button_toggled(self, val: bool):
        self.update_current_settings("lock_input_image", val)
        # Immediately update the scene so generated images are ignored when locked.
        try:
            if self._scene and hasattr(self._scene, "use_generated_image"):
                self._scene.use_generated_image = (
                    self.use_generated_image and not val
                )
        except Exception:
            pass

    @Slot()
    def on_refresh_button_clicked(self):
        self.load_image_from_grid(forced=True)

    @Slot(bool)
    def on_link_to_grid_image_button_toggled(self, val: bool):
        self.update_current_settings("use_grid_image_as_input", val)
        if val is True:
            self.load_image_from_grid()

    @Slot()
    def on_import_button_clicked(self):
        self.import_image()

    @Slot()
    def on_delete_button_clicked(self):
        self.delete_image()

    def import_image(self):
        self._import_path, _ = QFileDialog.getOpenFileName(
            self.window(),
            "Open Image",
            self._import_path,
            f"Image Files ({' '.join(AIRUNNER_VALID_IMAGE_FILES)})",
        )
        if self._import_path == "":
            return
        self.load_image(os.path.abspath(self._import_path))

    def load_image(self, file_path: str):
        # Use the facehuggershield user override if available to allow this explicit user action.
        try:
            from airunner.vendor.facehuggershield.darklock.restrict_os_access import (
                RestrictOSAccess,
            )

            ros = RestrictOSAccess()
            # Allow only the selected file for this thread while importing
            with ros.user_override(paths=[file_path]):
                image = Image.open(file_path)
        except Exception as e:
            # Fallback to normal operation if darklock is not available or fails
            try:
                # Try to log the exception if possible
                print(
                    f"Darklock user_override failed, falling back to normal operation: {e}"
                )
            except Exception:
                pass
            image = Image.open(file_path)

        self.load_image_from_object(image)
        if image is not None:
            self.update_current_settings(
                "image", convert_image_to_binary(image)
            )

    def load_image_from_grid(self, forced: bool = False):
        """Load the current grid image into this input image panel.
        
        Args:
            forced: If True, load regardless of lock/link settings.
        """
        # Clear settings cache to ensure fresh data
        settings_property_name = None
        if self.settings_key == "image_to_image_settings":
            settings_property_name = "image_to_image_settings"
        elif self.settings_key == "controlnet_settings":
            settings_property_name = "controlnet_settings"
        elif self.settings_key == "outpaint_settings":
            settings_property_name = "outpaint_settings"

        if settings_property_name:
            prop = getattr(type(self), settings_property_name, None)
            if (
                prop
                and hasattr(prop, "fget")
                and hasattr(prop.fget, "cache_clear")
            ):
                try:
                    prop.fget.cache_clear()
                except Exception:
                    pass

        # Check lock and link flags
        current_settings = self.current_settings
        if not forced and current_settings.lock_input_image:
            return
        if not forced and not current_settings.use_grid_image_as_input:
            return

        # Avoid redundant updates if content is identical
        grid_image = self.drawing_pad_settings.image
        if (
            not forced
            and getattr(self.current_settings, "image", None) is not None
            and grid_image == getattr(self.current_settings, "image", None)
        ):
            return

        self.update_current_settings("image", grid_image)
        if grid_image:
            image = convert_binary_to_image(grid_image)
            self.load_image_from_object(image)

    def load_image_from_settings(self):
        """Load image from current settings into the scene."""
        # Check if image is locked and scene already has content
        is_locked = getattr(self.current_settings, "lock_input_image", False)
        has_content = False
        if self._scene:
            if self._use_simple_scene:
                has_content = self._scene.has_image()
            else:
                has_content = getattr(self._scene, "item", None) is not None
        
        if is_locked and has_content:
            # User has locked the input image and there's already content
            return

        if self.settings_key == "outpaint_settings":
            if self.is_mask:
                image = self.drawing_pad_settings.mask
            else:
                image = self.outpaint_settings.image
        else:
            if self.use_generated_image:
                image = self.current_settings.generated_image
            else:
                image = self.current_settings.image

        if image is not None:
            image = convert_binary_to_image(image)

        if image is not None:
            self.load_image_from_object(image)
        else:
            if self._scene:
                if self._use_simple_scene:
                    self._scene.clear_image()
                else:
                    self._scene.clear()
            else:
                self.ui.image_container.setScene(None)

    def load_image_from_object(self, image: Image.Image):
        """Load a PIL image into the scene.
        
        Args:
            image: PIL Image to display.
        """
        if image is None:
            self.logger.warning("Image is None, unable to add to scene")
            return

        if not self._scene:
            self.logger.warning("Scene is None, cannot load image")
            return

        if self._use_simple_scene:
            # Simple path: just set the image directly
            self._scene.set_image(image)
        else:
            # Complex path for InputImageScene (mask drawing support)
            try:
                self._scene._add_image_to_scene(
                    image=image, is_outpaint=False, generated=False
                )
            except Exception:
                qimage = ImageQt(image)
                self._scene.image = qimage
                self._scene.initialize_image(image)

            # For input image scenes, ensure item is at origin
            if self._scene.item is not None:
                self._scene.item.setPos(0, 0)

            # Adjust scene rect to the item bounds if present
            if self._scene.item and hasattr(self._scene.item, "boundingRect"):
                rect = self._scene.item.sceneBoundingRect()
                self._scene.setSceneRect(rect)

        # Force view updates
        self._scene.update()
        for view in self._scene.views():
            view.viewport().update()
            view.update()

        self.fit_image_to_view()
        self.update()

    def delete_image(self):
        if self.settings_key == "outpaint_settings" and self.is_mask:
            self.update_drawing_pad_settings(mask=None)
        else:
            self.update_current_settings("image", None)

        if self._scene:
            if self._use_simple_scene:
                self._scene.clear_image()
            else:
                self._scene.clear()
        else:
            self.ui.image_container.setScene(None)
