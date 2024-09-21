from PIL import Image
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFileDialog
from PIL.ImageQt import ImageQt
from PySide6.QtGui import QPixmap, QImage, Qt
from PySide6.QtWidgets import QGraphicsScene

from airunner.settings import VALID_IMAGE_FILES
from airunner.utils.convert_base64_to_image import convert_base64_to_image
from airunner.utils.convert_image_to_base64 import convert_image_to_base64
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas.templates.input_image_ui import Ui_input_image


class InputImage(BaseWidget):
    widget_class_ = Ui_input_image

    def showEvent(self, event):
        settings_key = self.property("settings_key")
        self.ui.label.setText(
            "Controlnet" if settings_key == "controlnet_settings" else "Image to Image"
        )
        self.ui.enable_checkbox.blockSignals(True)
        self.ui.use_grid_image_as_input_checkbox.blockSignals(True)
        self.ui.enable_checkbox.setChecked(self.settings[settings_key]["enabled"])
        self.ui.use_grid_image_as_input_checkbox.setChecked(
            self.settings[settings_key]["use_grid_image_as_input"])
        self.ui.enable_checkbox.blockSignals(False)
        self.ui.use_grid_image_as_input_checkbox.blockSignals(False)
        self.load_image_from_settings()

    @Slot(bool)
    def enabled_toggled(self, val):
        settings = self.settings
        settings[self.property("settings_key")]["enabled"] = val
        self.settings = settings

    @Slot(bool)
    def use_grid_image_as_input_toggled(self, val):
        settings = self.settings
        settings[self.property("settings_key")]["use_grid_image_as_input"] = val
        self.settings = settings

    @Slot()
    def import_clicked(self):
        self.import_image()

    @Slot()
    def delete_clicked(self):
        self.delete_image()

    def import_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.window(),  # Pass the main window as the parent
            "Open Image",
            "",
            f"Image Files ({' '.join(VALID_IMAGE_FILES)})"
        )
        if file_path == "":
            return
        self.load_image(file_path)

    def load_image(self, file_path: str):
        image = Image.open(file_path)
        self.load_image_from_object(image)

    def load_image_from_settings(self):
        settings = self.settings
        image = settings[self.property("settings_key")]["image"]
        if image is not None:
            image = convert_base64_to_image(image)
            self.load_image_from_object(image)

    def load_image_from_object(self, image: Image):
        if image is None:
            self.logger.warning("Image is None, unable to add to scene")
            return

        # Convert PIL image to QImage
        qimage = ImageQt(image)
        qpixmap = QPixmap.fromImage(QImage(qimage))

        # Create a QGraphicsScene and add the QPixmap to it
        scene = QGraphicsScene()
        scene.addPixmap(qpixmap)

        # Set the QGraphicsScene to the QGraphicsView
        self.ui.image_container.setScene(scene)

        # Fit the scene to the QGraphicsView
        self.ui.image_container.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        # Update settings with base64 image
        settings_key = self.property("settings_key")
        base64_image = convert_image_to_base64(image)
        settings = self.settings
        settings[settings_key]["image"] = base64_image
        self.settings = settings

    def delete_image(self):
        settings = self.settings
        settings[self.property("settings_key")]["image"] = None
        self.settings = settings
        self.ui.image_container.setScene(None)
