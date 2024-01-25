from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QDialog
from PyQt6.QtGui import QImage

from PIL import Image

from airunner.enums import SignalCode, ServiceCode
from airunner.widgets.canvas_plus.templates.standard_image_widget_ui import Ui_standard_image_widget
from airunner.utils import load_metadata_from_image, prepare_metadata
from airunner.widgets.slider.slider_widget import SliderWidget
from airunner.widgets.base_widget import BaseWidget
from airunner.service_locator import ServiceLocator


class StandardImageWidget(BaseWidget):
    widget_class_ = Ui_standard_image_widget
    _pixmap = None
    _label = None
    _layout = None
    image_path = None
    image_label = None
    image_batch = None
    meta_data = None
    _image = None

    @property
    def image(self):
        if self._image is None:
            try:
                self.image = ServiceLocator.get(ServiceCode.CURRENT_ACTIVE_IMAGE)()
            except Exception as e:
                self.logger.error(f"Error while getting image: {e}")
        return self._image
    
    @image.setter
    def image(self, image):
        self._image = image

    @property
    def canvas_widget(self):
        return self.ui.canvas_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.advanced_settings.hide()
        self.load_upscale_options()
    
    def update_image_input_thumbnail(self):
        self.ui.input_image_widget.set_thumbnail()

    def update_controlnet_settings_thumbnail(self):
        self.ui.controlnet_settings.set_thumbnail()
    
    def update_thumbnails(self):
        self.update_image_input_thumbnail()
        self.update_controlnet_settings_thumbnail()
    
    def upscale_number_changed(self, val):
        print("upscale int", val)
    
    def handle_advanced_settings_checkbox(self, val):
        if val:
            self.ui.advanced_settings.show()
        else:
            self.ui.advanced_settings.hide()
    
    def load_upscale_options(self):
        self.ui.upscale_model.blockSignals(True)
        model = self.settings["standard_image_settings"]["upscale_model"]
        index = self.ui.upscale_model.findText(model)
        if index == -1:
            index = 0
        self.ui.upscale_model.setCurrentIndex(index)
        self.ui.upscale_model.blockSignals(False)

        self.ui.face_enhance.blockSignals(True)
        self.ui.face_enhance.setChecked(self.settings["standard_image_settings"]["face_enhance"])
        self.ui.face_enhance.blockSignals(False)
    
    def upscale_model_changed(self, model):
        settings = self.settings
        settings["standard_image_settings"]["upscale_model"] = model
        self.settings = settings

    def face_enhance_toggled(self, val):
        settings = self.settings
        settings["standard_image_settings"]["face_enhance"] = val
        self.settings = settings
    
    def handle_controlnet_changed(self, val):
        settings = self.settings
        settings["standard_image_settings"]["controlnet"] = val
        self.settings = settings
    
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
    
    def similar_image_with_prompt(self):
        """
        Using the LLM, generate a description of the image
        """
        self.emit(SignalCode.DESCRIBE_IMAGE_SIGNAL, dict(
            image=self.image, 
            callback=self.handle_prompt_generated
        ))
    
    def handle_prompt_generated(self, prompt, negative_prompt):
        meta_data = load_metadata_from_image(self.image)
        meta_data["prompt"] = prompt[0]
        meta_data["negative_prompt"] = negative_prompt[0]
        meta_data = prepare_metadata({ "options": meta_data })
        if self.image_path:
            image = Image.open(self.image_path)
            image.save(self.image_path, pnginfo=meta_data)
        else:
            current_layer = ServiceLocator.get(ServiceCode.CURRENT_LAYER)()
            image = current_layer['image']
        self.image = image
        self.meta_data = load_metadata_from_image(self.image)
        self.generate_similar_image()

    def similar_image(self):
        self.generate_similar_image()
    
    def generate_similar_image(self, batch_size=1):
        meta_data = self.meta_data or {}
        
        prompt = meta_data.get("prompt", None)
        negative_prompt = meta_data.get("negative_prompt", None)
        prompt = None if prompt == "" else prompt
        negative_prompt = None if negative_prompt == "" else negative_prompt

        if prompt is None:
            #return self.similar_image_with_prompt()
            prompt = ""
        if negative_prompt is None:
            meta_data["negative_prompt"] = "verybadimagenegative_v1.3, EasyNegative"
        
        image_similarity = self.settings["standard_image_settings"]["image_similarity"]
        controlnet = self.settings["standard_image_settings"]["controlnet"]

        meta_data.pop("seed", None)
        meta_data["action"] = "txt2img"
        meta_data["width"] = self.image.width
        meta_data["height"] = self.image.height
        meta_data["enable_controlnet"] = True
        meta_data["controlnet"] = controlnet.lower()
        meta_data["controlnet_conditioning_scale"] = image_similarity / 100.0
        meta_data["strength"] = 1.1 - (image_similarity / 100.0)
        meta_data["enable_input_image"] = True
        meta_data["use_cropped_image"] = False
        meta_data["batch_size"] = batch_size

        self.emit(SignalCode.GENERATE_IMAGE_SIGNAL, dict(
            image=self.image,
            meta_data=meta_data
        ))
    
    def handle_similar_slider_change(self, value):
        self.similarity = value

    def similar_batch(self):
        self.generate_similar_image(batch_size=4)

    def upscale_2x_clicked(self):
        meta_data = self.meta_data or {}
        
        prompt = meta_data.get("prompt", None)
        negative_prompt = meta_data.get("negative_prompt", None)
        prompt = None if prompt == "" else prompt
        negative_prompt = None if negative_prompt == "" else negative_prompt

        if prompt is None:
            prompt = ""
        if negative_prompt is None:
            meta_data["negative_prompt"] = "verybadimagenegative_v1.3, EasyNegative"
        
        meta_data.pop("seed", None)
        meta_data["model_data_path"] = self.settings["standard_image_settings"]["upscale_model"]
        meta_data["face_enhance"] = self.settings["standard_image_settings"]['face_enhance']
        meta_data["denoise_strength"] = 0.5
        meta_data["action"] = "upscale"
        meta_data["width"] = self.ui.canvas_widget.current_layer.image.width
        meta_data["height"] = self.ui.canvas_widget.current_layer.image.height
        meta_data["enable_input_image"] = True
        meta_data["use_cropped_image"] = False

        self.emit(SignalCode.GENERATE_IMAGE_SIGNAL, dict(
            image=self.image,
            override_data=meta_data
        ))
    
    def showEvent(self, event):
        super().showEvent(event)
        # find all SliderWidget widgets in the template and call initialize
        for widget in self.findChildren(SliderWidget):
            try:
                current_value = getattr(
                    self.generator_settings,
                    widget.property("settings_property").split(".")[1]
                )
            except Exception as e:
                current_value = None
            if current_value is not None:
                widget.setProperty("current_value", current_value)
            widget.initialize()
        self.initialized = True