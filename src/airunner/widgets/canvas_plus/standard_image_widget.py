from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QDialog
from PyQt6.QtGui import QImage

from PIL import Image
from PIL.ImageQt import ImageQt
from PIL.PngImagePlugin import PngInfo

from airunner.utils import get_session
from airunner.data.models import AIModel
from airunner.widgets.canvas_plus.standard_base_widget import StandardBaseWidget
from airunner.widgets.canvas_plus.templates.standard_image_widget_ui import Ui_standard_image_widget
from airunner.utils import delete_image, load_metadata_from_image, prepare_metadata


class StandardImageWidget(StandardBaseWidget):
    widget_class_ = Ui_standard_image_widget
    _pixmap = None
    _label = None
    _layout = None
    image_path = None
    image_label = None
    image_batch = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.batch_container.hide()
        self.ui.tableWidget.hide()
        self.ui.similar_groupbox.hide()
    
    def handle_image_data(self, data):
        images = data["images"]
        if len(images) == 1:
            self.load_image_from_path(data["path"])
        else:
            self.load_batch_images(images)
    
    def clear_batch_images(self):
        for widget in self.ui.batch_container.findChildren(QLabel):
            widget.deleteLater()

    def load_batch_images(self, images):
        self.ui.batch_container.show()
        self.clear_batch_images()
        images = images[:4]
        for image in images:
            # resize the image to 128x128
            image = image.resize((128, 128))
            qimage = ImageQt(image)
            pixmap = QPixmap.fromImage(qimage)
            label = QLabel()
            label.setPixmap(pixmap)
            self.ui.batch_container.layout().addWidget(label)
    
    def load_image_from_path(self, image_path):
        image = Image.open(image_path)
        self.load_image_from_object(image=image, image_path=image_path)
    
    def load_image_from_object(self, image, image_path=NotImplemented):
        if self.app.image_editor_tab_name == "Standard":
            self.set_pixmap(image=image, image_path=image_path)
    
    def set_pixmap(self, image_path=None, image=None):
        self.image_path = image_path
        self.image = image
        meta_data = image.info
        self.meta_data = meta_data if meta_data is not None else load_metadata_from_image(image)
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
        self.ui.image_frame.show()
        self.ui.similar_groupbox.show()
    
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
    
    def similar_image_with_prompt(self):
        """
        Using the LLM, generate a description of the image
        """
        self.app.describe_image(image=self.image, callback=self.handle_prompt_generated)
    
    def handle_prompt_generated(self, prompt):
        meta_data = load_metadata_from_image(self.image)
        meta_data["prompt"] = prompt[0]
        meta_data = prepare_metadata({ "options": meta_data })
        image = Image.open(self.image_path)
        image.save(self.image_path, pnginfo=meta_data)
        self.image = image
        self.meta_data = load_metadata_from_image(self.image)
        self.generate_similar_image()

    def similar_image(self):
        self.generate_similar_image()
    
    def generate_similar_image(self, batch_size=1):
        meta_data = self.meta_data
        
        prompt = meta_data.get("prompt", None)
        negative_prompt = meta_data.get("negative_prompt", None)
        prompt = None if prompt == "" else prompt
        negative_prompt = None if negative_prompt == "" else negative_prompt

        if prompt is None:
            return self.similar_image_with_prompt()
        if negative_prompt is None:
            meta_data["negative_prompt"] = "verybadimagenegative_v1.3, EasyNegative"
        
        meta_data.pop("seed", None)
        meta_data.pop("latents_seed", None)
        meta_data["action"] = "txt2img"
        meta_data["width"] = self.image.width
        meta_data["height"] = self.image.height
        meta_data["enable_controlnet"] = True
        meta_data["controlnet"] = "canny"
        meta_data["controlnet_conditioning_scale"] = self.settings_manager.image_similarity / 100.0
        #meta_data["image_guidance_scale"] = 100 * (100 - self.settings_manager.image_similarity) / 100.0
        meta_data["strength"] = 1.1 - (self.settings_manager.image_similarity / 100.0)
        print(meta_data["controlnet_conditioning_scale"], meta_data["strength"])
        meta_data["enable_input_image"] = True
        meta_data["use_cropped_image"] = False
        meta_data["batch_size"] = batch_size

        self.app.generator_tab_widget.current_generator_widget.call_generate(
            image=self.image,
            override_data=meta_data
        )
    
    def handle_similar_slider_change(self, value):
        self.similarity = value

    def similar_batch(self):
        self.generate_similar_image(batch_size=4)

    def upscale_2x_clicked(self):
        meta_data = self.meta_data
        
        prompt = meta_data.get("prompt", None)
        negative_prompt = meta_data.get("negative_prompt", None)
        prompt = None if prompt == "" else prompt
        negative_prompt = None if negative_prompt == "" else negative_prompt

        if prompt is None:
            return self.similar_image_with_prompt()
        if negative_prompt is None:
            meta_data["negative_prompt"] = "verybadimagenegative_v1.3, EasyNegative"
        
        meta_data.pop("seed", None)
        meta_data.pop("latents_seed", None)

        meta_data["model_data_name"] = "sd-x2-latent-upscaler"
        meta_data["model_data_path"] = "stabilityai/sd-x2-latent-upscaler"
        meta_data["steps"] = "40"
        meta_data["action"] = "upscale"
        meta_data["width"] = self.image.width
        meta_data["height"] = self.image.height
        meta_data["enable_controlnet"] = True
        meta_data["controlnet"] = "canny"
        meta_data["controlnet_conditioning_scale"] = self.settings_manager.image_similarity
        meta_data["image_guidance_scale"] = 100 * (1000 - self.settings_manager.image_similarity) / 100.0
        meta_data["strength"] = 1.0
        meta_data["enable_input_image"] = True
        meta_data["use_cropped_image"] = False
        meta_data["batch_size"] = 1

        self.app.generator_tab_widget.current_generator_widget.call_generate(
            image=self.image,
            override_data=meta_data
        )