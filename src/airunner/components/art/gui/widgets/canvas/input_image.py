import os
from typing import Optional, Union

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QFileDialog
from PySide6.QtGui import QPainter

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
        ("pin", "pin_image"),
        ("grid-3x3", "grid_image"),
        ("folder", "import_button"),
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

    def _apply_current_settings_value(self, key, value) -> None:
        if self.settings_key == "controlnet_settings":
            self.update_controlnet_settings(**{key: value})
        elif self.settings_key == "image_to_image_settings":
            self.update_image_to_image_settings(**{key: value})
        elif self.settings_key == "outpaint_settings":
            self.update_outpaint_settings(**{key: value})
        elif self.settings_key == "drawing_pad_settings":
            self.update_drawing_pad_settings(**{key: value})

    def update_current_settings(self, key, value):
        self._apply_current_settings_value(key, value)

        self.api.art.canvas.input_image_changed(self.settings_key, key, value)
        if key == "lock_input_image":
            self._update_scene_lock_state(bool(value))

    def _update_scene_lock_state(self, locked: bool) -> None:
        try:
            if self._scene and hasattr(self._scene, "use_generated_image"):
                self._scene.use_generated_image = (
                    self.use_generated_image and not locked
                )
        except Exception:
            pass

    def _sync_pin_button_state(self) -> None:
        self.ui.pin_image.blockSignals(True)
        self.ui.pin_image.setChecked(
            bool(getattr(self.current_settings, "lock_input_image", False))
        )
        self.ui.pin_image.blockSignals(False)

    def should_follow_grid_updates(self) -> bool:
        """Return whether the widget should mirror the live grid image."""
        return not bool(
            getattr(self.current_settings, "lock_input_image", False)
        )

    def _link_to_grid_image(
        self,
        force_load: bool = False,
        sync_settings: bool = True,
    ) -> None:
        self.load_image_from_grid(
            forced=force_load,
            sync_settings=sync_settings,
        )

    def _sync_input_source(
        self,
        force_grid_load: bool = False,
        sync_settings: bool = True,
    ) -> None:
        is_locked = not self.should_follow_grid_updates()
        self._sync_pin_button_state()
        self._update_scene_lock_state(is_locked)
        if is_locked:
            self.load_image_from_settings()
            return
        self._link_to_grid_image(
            force_load=force_grid_load,
            sync_settings=sync_settings,
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.ui.grid_image.setVisible(
            self.settings_key == "image_to_image_settings"
        )
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

        if self.settings_key == "outpaint_settings":
            if self.is_mask:
                self.ui.import_button.hide()

        self._sync_input_source(sync_settings=False)

    @Slot(bool)
    def on_pin_image_toggled(self, val: bool):
        if val:
            self._capture_current_input_image()
            self.update_current_settings("lock_input_image", True)
            self._update_scene_lock_state(True)
            return

        self.update_current_settings("lock_input_image", False)
        self._update_scene_lock_state(False)
        self._link_to_grid_image(force_load=True)

    @Slot()
    def on_grid_image_clicked(self):
        if self.settings_key != "image_to_image_settings":
            return

        self.load_image_from_grid(forced=True)

    def _capture_current_input_image(self) -> None:
        """Persist the current visible source image before locking it."""
        if self.is_mask:
            return

        displayed_image = self._get_displayed_image()
        image = displayed_image or self._get_lock_source_image()
        if image is None:
            return

        if displayed_image is None:
            self.load_image_from_object(image)
        self._apply_current_settings_value(
            "image",
            convert_image_to_binary(image),
        )

    def _get_displayed_image(self) -> Optional[Image.Image]:
        """Return the currently displayed preview image when available."""
        if self._scene is None:
            return None

        if self._use_simple_scene and hasattr(self._scene, "get_image"):
            return self._scene.get_image()

        try:
            return self._scene.current_active_image
        except Exception:
            return None

    def _get_lock_source_image(self) -> Optional[Image.Image]:
        """Return the image that should be frozen by the lock button."""
        if self.settings_key == "image_to_image_settings":
            return self.img2img_image or self.drawing_pad_image
        if self.settings_key == "controlnet_settings":
            return self.controlnet_image or self.drawing_pad_image
        if self.settings_key == "outpaint_settings":
            return self.outpaint_image or self.drawing_pad_image
        return self.drawing_pad_image

    @Slot()
    def on_import_button_clicked(self):
        self.import_image()

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
        # Allow this explicit user action even when darklock is active.
        try:
            from airunner_services.vendor.facehuggershield.darklock.restrict_os_access import (
                RestrictOSAccess,
            )

            ros = RestrictOSAccess()
            with ros.user_override(paths=[file_path]):
                image = Image.open(file_path)
        except Exception as e:
            try:
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

    def load_image_from_grid(
        self,
        forced: bool = False,
        sync_settings: bool = True,
    ) -> None:
        """Load the current grid image into this input image panel.

        Args:
            forced: If True, load regardless of lock/link settings.
            sync_settings: When False, refresh only the preview scene.
        """
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

        current_settings = self.current_settings
        if not forced and current_settings.lock_input_image:
            return
        if not forced and not self.should_follow_grid_updates():
            return

        grid_image = self.drawing_pad_settings.image
        if (
            sync_settings
            and not forced
            and getattr(self.current_settings, "image", None) is not None
            and grid_image == getattr(self.current_settings, "image", None)
        ):
            return

        if sync_settings:
            self.update_current_settings("image", grid_image)
        if grid_image:
            image = convert_binary_to_image(grid_image)
            self.load_image_from_object(image)
            return

        self._clear_scene_image()

    def _clear_scene_image(self) -> None:
        """Clear the displayed preview image from the scene."""
        if self._scene:
            if self._use_simple_scene:
                self._scene.clear_image()
            else:
                self._scene.clear()
            return

        self.ui.image_container.setScene(None)

    def load_image_from_settings(self):
        """Load image from current settings into the scene."""
        is_locked = getattr(self.current_settings, "lock_input_image", False)
        has_content = False
        if self._scene:
            if self._use_simple_scene:
                has_content = self._scene.has_image()
            else:
                has_content = getattr(self._scene, "item", None) is not None

        if is_locked and has_content:
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
            self._clear_scene_image()

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
            self._scene.set_image(image)
        else:
            try:
                self._scene._add_image_to_scene(
                    image=image, is_outpaint=False, generated=False
                )
            except Exception:
                qimage = ImageQt(image)
                self._scene.image = qimage
                self._scene.initialize_image(image)

            if self._scene.item is not None:
                self._scene.item.setPos(0, 0)

            if self._scene.item and hasattr(self._scene.item, "boundingRect"):
                rect = self._scene.item.sceneBoundingRect()
                self._scene.setSceneRect(rect)

        self._scene.update()
        for view in self._scene.views():
            view.viewport().update()
            view.update()

        self.fit_image_to_view()
        self.update()
