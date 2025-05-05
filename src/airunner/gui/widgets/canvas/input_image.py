import os

from PIL import Image
from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QFileDialog, QGraphicsScene
from PIL.ImageQt import ImageQt
from PySide6.QtGui import QPixmap, QImage, QPen, QPainter

from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_VALID_IMAGE_FILES
from airunner.utils.image import (
    convert_binary_to_image,
    convert_image_to_binary,
)
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.canvas.templates.input_image_ui import Ui_input_image
from airunner.gui.widgets.canvas.input_image_scene import InputImageScene


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
        self._import_path = ""
        super().__init__(*args, **kwargs)
        self.ui.strength_slider_widget.setProperty(
            "settings_property", f"{self.settings_key}.strength"
        )
        self.ui.strength_slider_widget.setProperty(
            f"{self.settings_key}.strength", self.current_settings.strength
        )
        self._scene = None
        self.setup_scene()
        self.load_image_from_settings()

    def setup_scene(self):
        """Set up the custom scene for drawing on input images"""
        # Create our custom scene for drawing
        self._scene = InputImageScene(
            canvas_type="input_image",
            settings_key=self.settings_key,
            is_mask=self.is_mask,
        )

        # Set the drawing capabilities on the scene
        if hasattr(self._scene, "use_generated_image"):
            self._scene.use_generated_image = self.use_generated_image

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
        scene = self.ui.image_container.scene()
        if scene and scene.items():
            rect = scene.itemsBoundingRect()
            if not rect.isNull():
                scene.setSceneRect(rect)
                self.ui.image_container.fitInView(rect, Qt.KeepAspectRatio)

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
        settings_updated = False
        settings_class = None
        settings_property_name = None

        if self.settings_key == "controlnet_settings":
            self.update_controlnet_settings(key, value)
            settings_class = self.controlnet_settings.__class__
            settings_property_name = "controlnet_settings"
            settings_updated = True
        elif self.settings_key == "image_to_image_settings":
            self.update_image_to_image_settings(key, value)
            settings_class = self.image_to_image_settings.__class__
            settings_property_name = "image_to_image_settings"
            settings_updated = True
        elif self.settings_key == "outpaint_settings":
            self.update_outpaint_settings(key, value)
            settings_class = self.outpaint_settings.__class__
            settings_property_name = "outpaint_settings"
            settings_updated = True
        elif self.settings_key == "drawing_pad_settings":
            self.update_drawing_pad_settings(key, value)
            settings_class = self.drawing_pad_settings.__class__
            settings_property_name = "drawing_pad_settings"
            settings_updated = True

        # REMOVED: Cache clearing logic moved to load_image_from_grid

        self.api.art.canvas.input_image_changed(self.settings_key, key, value)

    def showEvent(self, event):
        super().showEvent(event)
        self._patch_scene_for_persistence()
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
        if self.current_settings.use_grid_image_as_input:
            self.load_image_from_grid()
            return

        self.load_image_from_settings()

    @Slot(bool)
    def enabled_toggled(self, val):
        self.update_current_settings("enabled", val)

    @Slot(bool)
    def lock_input_image(self, val):
        self.update_current_settings("lock_input_image", val)

    @Slot(bool)
    def refresh_input_image_from_grid(self):
        self.load_image_from_grid(forced=True)

    @Slot(bool)
    def use_grid_image_as_input_toggled(self, val):
        self.update_current_settings("use_grid_image_as_input", val)
        if val is True:
            self.load_image_from_grid()

    @Slot()
    def import_clicked(self):
        self.import_image()

    @Slot()
    def delete_clicked(self):
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
        image = Image.open(file_path)
        self.load_image_from_object(image)
        if image is not None:
            self.update_current_settings(
                "image", convert_image_to_binary(image)
            )

    def load_image_from_grid(self, forced=False):
        # Explicitly clear cache before reading settings to ensure lock status is fresh
        settings_property_name = None
        if self.settings_key == "image_to_image_settings":
            settings_property_name = "image_to_image_settings"
        elif self.settings_key == "controlnet_settings":
            settings_property_name = "controlnet_settings"
        elif self.settings_key == "outpaint_settings":
            settings_property_name = "outpaint_settings"
        # Add other relevant settings keys if necessary

        if settings_property_name:
            prop = getattr(type(self), settings_property_name, None)
            if (
                prop
                and hasattr(prop, "fget")
                and hasattr(prop.fget, "cache_clear")
            ):
                try:
                    prop.fget.cache_clear()
                    self.logger.debug(
                        f"Cleared cache for {settings_property_name} before check"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to clear cache for {settings_property_name}: {e}"
                    )

        # Check lock *before* updating settings
        current_settings = (
            self.current_settings
        )  # Read potentially fresh settings
        if not forced and current_settings.lock_input_image:
            self.logger.debug(
                f"Input image locked for {self.settings_key}, skipping update from grid."
            )
            return
        if not forced and not current_settings.use_grid_image_as_input:
            self.logger.debug(
                f"use_grid_image_as_input is false for {self.settings_key}, skipping update from grid."
            )
            return

        # If not locked and use_grid is true, proceed with update
        self.logger.debug(f"Updating {self.settings_key} image from grid.")
        self.update_current_settings("image", self.drawing_pad_settings.image)
        self.load_image_from_settings()

    def load_image_from_settings(self):
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
                # Clear the scene instead of setting to None which would lose drawing capability
                self._scene.clear()
            else:
                self.ui.image_container.setScene(None)

    def load_image_from_object(self, image: Image):
        if image is None:
            self.logger.warning("Image is None, unable to add to scene")
            return

        # Convert PIL image to QImage
        qimage = ImageQt(image)

        # If we have our scene, update its image
        if hasattr(self, "_scene") and self._scene:
            # Update the image in the scene
            if self._scene.image != qimage:
                # Update with the new image
                self._scene.image = qimage
                self._scene.initialize_image(
                    image
                )  # Pass the original PIL image
            # Always set scene rect to image
            if self._scene.item and hasattr(self._scene.item, "boundingRect"):
                rect = self._scene.item.boundingRect()
                self._scene.setSceneRect(rect)
            self.fit_image_to_view()
        else:
            # Legacy fallback if somehow scene isn't set up
            qpixmap = QPixmap.fromImage(QImage(qimage))
            scene = QGraphicsScene()
            scene.clear()
            scene.addPixmap(qpixmap)
            scene.setSceneRect(qpixmap.rect())
            self.ui.image_container.setScene(scene)

            # Draw a red border around the image
            pen = QPen(Qt.GlobalColor.red)
            pen.setWidth(3)
            scene.addRect(0, 0, qpixmap.width(), qpixmap.height(), pen)
            self.fit_image_to_view()

    def delete_image(self):
        if self.settings_key == "outpaint_settings" and self.is_mask:
            self.update_drawing_pad_settings("mask", None)
        else:
            self.update_current_settings("image", None)

        if self._scene:
            self._scene.clear()
        else:
            self.ui.image_container.setScene(None)

    # --- Persistence fix: save after drawing ---
    def save_current_image(self):
        # Save the current image in the scene to the correct settings/database
        if (
            hasattr(self, "_scene")
            and self._scene
            and hasattr(self._scene, "active_image")
        ):
            from PIL.ImageQt import fromqimage

            image = fromqimage(self._scene.active_image)
            base_64_image = convert_image_to_binary(image)
            if self.is_mask:
                self.update_drawing_pad_settings("mask", base_64_image)
                model = self.drawing_pad_settings.__class__.objects.first()
                model.mask = base_64_image
                model.save()
            elif (
                self.settings_key == "controlnet_settings"
                and hasattr(self, "use_generated_image")
                and self.use_generated_image
            ):
                self.update_controlnet_settings(
                    "generated_image", base_64_image
                )
                model = self.controlnet_settings.__class__.objects.first()
                model.generated_image = base_64_image
                model.save()
            elif self.settings_key == "outpaint_settings":
                self.update_outpaint_settings("image", base_64_image)
                model = self.outpaint_settings.__class__.objects.first()
                model.image = base_64_image
                model.save()
            elif self.settings_key == "image_to_image_settings":
                self.update_image_to_image_settings("image", base_64_image)
                model = self.image_to_image_settings.__class__.objects.first()
                model.image = base_64_image
                model.save()
            else:
                self.update_current_settings("image", base_64_image)
            # After saving, reload to ensure UI is in sync
            self.load_image_from_settings()

    # Patch InputImageScene to call save after drawing
    def _patch_scene_for_persistence(self):
        if self._scene:
            orig_release = self._scene._handle_left_mouse_release

            def new_release(event):
                result = orig_release(event)
                self.save_current_image()
                return result

            self._scene._handle_left_mouse_release = new_release
