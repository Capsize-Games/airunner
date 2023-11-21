import os


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QDialog
from PyQt6.QtGui import QImage

from PIL import Image
from PIL import PngImagePlugin

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas_plus.templates.standard_image_widget_ui import Ui_standard_image_widget
from airunner.utils import delete_image, load_metadata_from_image, prepare_metadata


class StandardImageWidget(BaseWidget):
    widget_class_ = Ui_standard_image_widget
    _pixmap = None
    _label = None
    _layout = None
    image = None
    image_path = None
    image_label = None
    image_batch = None
    image_backup = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.image_data.connect(self.handle_image_data)
        self.app.load_image.connect(self.load_image_from_path)
        self.ui.controls_container.hide()
        self.ui.batch_container.hide()
        self.ui.delete_confirmation.hide()
        self.ui.tableWidget.hide()
    
    def handle_image_data(self, data):
        print(data)
        self.image_path = data["path"]
        images = data["images"]
        if len(images) == 1:
            self.image = images[0]
            self.load_image_from_object(self.image, self.image_path)
        else:
            self.load_batch_images(images)
    
    def clear_batch_images(self):
        for widget in self.ui.batch_container.layout().children():
            widget.deleteLater()

    def load_batch_images(self, images):
        self.clear_batch_images()
        images = images[:4]
        for image in images:
            raw_data = image.tobytes("raw", "RGBA")
            qimage = QImage(
                raw_data, 
                image.size[0], 
                image.size[1], 
                QImage.Format.Format_RGBA8888
            )
            pixmap = QPixmap.fromImage(qimage)
            label = QLabel()
            label.setPixmap(pixmap)
            self.ui.batch_container.layout().addWidget(label)
    
    def load_image_from_path(self, image_path):
        self.image_path = image_path
        image = Image.open(image_path)
        self.load_image_from_object(image=image, image_path=image_path)
    
    def load_image_from_object(self, image, image_path):
        if self.app.image_editor_tab_name == "Standard":
            self.set_pixmap(image=image, image_path=image_path)
    
    def set_pixmap(self, image_path=None, image=None):
        self.image_path = image_path
        self.image = image
        self.meta_data = load_metadata_from_image(image)
        size = self.ui.image_frame.width() - 20

        pixmap = self._pixmap
        if not pixmap:
            pixmap = QPixmap()
            self._pixmap = pixmap

        if image_path:
            pixmap.load(image_path)
        else:
            raw_data = image.tobytes("raw", "RGBA")
            qimage = QImage(
                raw_data, 
                image.size[0], 
                image.size[1], 
                QImage.Format.Format_RGBA8888
            )
            pixmap = QPixmap.fromImage(qimage)
        
        width = pixmap.width()
        height = pixmap.height()
        
        label = self._label
        if not label:
            label = QLabel(self.ui.image_frame)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._label = label

        pixmap = pixmap.scaled(
            size, 
            size, 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        label.setPixmap(pixmap)
        label.setFixedWidth(size)
        label.setFixedHeight(size)

        # on label click:
        label.mousePressEvent = self.handle_label_clicked
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = self._layout
        if not layout:
            layout = QVBoxLayout(self.ui.image_frame)
            layout.addWidget(label)        
            self._layout = layout
        
        # get the metadata from this image, load it as a png first
        # then load the metadata from the png
        self.clear_table_data()
        if image_path:
            image = Image.open(image_path)
            meta_data = image.info

            meta_data["width"] = width
            meta_data["height"] = height

            self.set_table_data(meta_data)
        
        self.ui.controls_container.show()
    
    def handle_label_clicked(self, event):
        # create a popup window and show the full size image in it
        self.dialog = QDialog()
        self.dialog.setWindowTitle("Image preview")
        layout = QVBoxLayout(self.dialog)
        self.dialog.setLayout(layout)

        if self.image_path:
            self.image = Image.open(self.image_path)

        if self.image:
            raw_data = self.image.tobytes("raw", "RGBA")
            qimage = QImage(
                raw_data, 
                self.image.size[0], 
                self.image.size[1], 
                QImage.Format.Format_RGBA8888
            )
            pixmap = QPixmap.fromImage(qimage)
        label = QLabel()
        label.setPixmap(pixmap)
        layout.addWidget(label)
        
        self.dialog.show()
    
    def set_table_data(self, data):
        if "options" in data:
            data = data["options"]

        for k, v in data.items():
            self.ui.tableWidget.insertRow(self.ui.tableWidget.rowCount())
            self.ui.tableWidget.setItem(self.ui.tableWidget.rowCount()-1, 0, QTableWidgetItem(str(k)))
            self.ui.tableWidget.setItem(self.ui.tableWidget.rowCount()-1, 1, QTableWidgetItem(str(v)))
        self.ui.tableWidget.resizeColumnsToContents()
        self.ui.tableWidget.resizeRowsToContents()
        self.ui.tableWidget.update()
        QApplication.processEvents()

    def clear_table_data(self):
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)
    
    def image_to_canvas(self):
        self.app.load_image.emit(self.image_path)

    def delete_image(self):
        self.ui.delete_confirmation.show()

    def confirm_delete(self):
        self._label.setPixmap(QPixmap())
        delete_image(self.image_path)
        self.ui.delete_confirmation.hide()

    def cancel_delete(self):
        self.ui.delete_confirmation.hide()

    def similar_image_with_prompt(self):
        """
        Using the LLM, generate a description of the image
        """
        self.app.describe_image(image=self.image, callback=self.handle_prompt_generated)
    
    def handle_prompt_generated(self, prompt):
        print("handle_prompt_generated", prompt)
        meta_data = load_metadata_from_image(self.image)
        meta_data["prompt"] = prompt[0]
        meta_data = prepare_metadata({ "options": meta_data })
        image = Image.open(self.image_path)
        image.save(self.image_path, pnginfo=meta_data)
        self.image = image
        print("saving meta_data", meta_data)
        self.meta_data = load_metadata_from_image(self.image)
        self.generate_similar_image()

    def similar_image(self):
        self.generate_similar_image()
    
    def generate_similar_image(self, batch_size=1):
        meta_data = self.meta_data
        print("meta_data", meta_data)
        if "prompt" not in meta_data or meta_data["prompt"] == "" or meta_data["prompt"] is None:
            return self.similar_image_with_prompt()
        if "negative_prompt" not in meta_data or meta_data["negative_prompt"] == "" or meta_data["negative_prompt"] is None:
            meta_data["negative_prompt"] = "verybadimagenegative_v1.3, EasyNegative"

        meta_data["action"] = "txt2img"
        meta_data["width"] = self.image.width
        meta_data["height"] = self.image.height
        meta_data["enable_controlnet"] = True
        meta_data["controlnet"] = "canny"
        meta_data["controlnet_conditioning_scale"] = self.settings_manager.image_similarity
        meta_data["image_guidance_scale"] = 100 * (1000 - self.settings_manager.image_similarity) / 100.0
        meta_data["strength"] = 1.0
        meta_data["enable_input_image"] = True
        meta_data["use_cropped_image"] = False
        meta_data["batch_size"] = batch_size

        meta_data.pop("seed", None)
        meta_data.pop("latents_seed", None)

        self.app.generator_tab_widget.current_generator_widget.call_generate(
            image=self.image,
            override_data=meta_data
        )
    
    def handle_similar_slider_change(self, value):
        self.similarity = value

    def similar_batch(self):
        self.generate_similar_image(batch_size=4)

    def export_image(self):
        pass

    def filter_with_filter(self, filter):
        return type(filter).__name__ in [
            "SaturationFilter", 
            "ColorBalanceFilter", 
            "RGBNoiseFilter", 
            "PixelFilter", 
            "HalftoneFilter", 
            "RegistrationErrorFilter"]

    def preview_filter(self, filter):
        image = self.current_image
        if not image:
            return
        self.image_backup = image.copy()
        if self.filter_with_filter:
            filtered_image = filter.filter(image)
        else:
            filtered_image = image.filter(filter)
        self.load_image_from_object(filtered_image)
    
    def cancel_filter(self):
        print("CANCEL")
        if self.image_backup:
            self.load_image_from_object(self.image_backup)
            self.image_backup = None
    
    def apply_filter(self, filter):
        pass