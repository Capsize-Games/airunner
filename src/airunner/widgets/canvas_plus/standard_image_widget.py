from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QDialog
from PyQt6.QtGui import QImage

from PIL import Image

from airunner.data.models import AIModel
from airunner.widgets.canvas_plus.standard_base_widget import StandardBaseWidget
from airunner.widgets.canvas_plus.templates.standard_image_widget_ui import Ui_standard_image_widget
from airunner.utils import load_metadata_from_image, prepare_metadata
from airunner.widgets.slider.slider_widget import SliderWidget
from airunner.data.models import ActionScheduler, Pipeline
from airunner.data.session_scope import session_scope


class StandardImageWidget(StandardBaseWidget):
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
            self.image = self.app.canvas_widget.current_layer.image
        return self._image
    
    @image.setter
    def image(self, image):
        self._image = image

    @property
    def canvas_widget(self):
        return self.ui.canvas_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.settings_tab_widget.tabBar().hide()        
        self.ui.advanced_settings.hide()
        self.load_upscale_options()
        self.set_controlnet_settings_properties()
        self.set_input_image_widget_properties()
        self.ui.ddim_eta_slider_widget.hide()
        self.ui.frames_slider_widget.hide()
    
    def set_controlnet_settings_properties(self):
        self.ui.controlnet_settings.initialize()

    def set_input_image_widget_properties(self):
        self.ui.input_image_widget.initialize()
        self.ui.controlnet_settings.initialize()
    
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
        model = self.app.settings_manager.standard_image_settings.upscale_model
        index = self.ui.upscale_model.findText(model)
        if index == -1:
            index = 0
        self.ui.upscale_model.setCurrentIndex(index)
        self.ui.upscale_model.blockSignals(False)

        self.ui.face_enhance.blockSignals(True)
        self.ui.face_enhance.setChecked(self.app.settings_manager.standard_image_settings.face_enhance)
        self.ui.face_enhance.blockSignals(False)
    
    def upscale_model_changed(self, model):
        self.app.settings_manager.set_value("standard_image_settings.upscale_model", model)

    def face_enhance_toggled(self, val):
        self.app.settings_manager.set_value("standard_image_settings.face_enhance", val)
    
    def handle_controlnet_changed(self, val):
        self.app.settings_manager.set_value("standard_image_settings.controlnet", val)

    def handle_image_data(self, data):
        images = data["images"]
        if len(images) == 1:
            self.load_image_from_path(data["path"])
    
    def load_image_from_path(self, image_path):
        image = Image.open(image_path)
        self.load_image_from_object(image=image, image_path=image_path)
        self.app.ui.image_browser.add_image(image_path)
    
    def load_image_from_object(self, image, image_path=NotImplemented):
        self.set_pixmap(image=image, image_path=image_path)

    def set_pixmap(self, image_path=None, image=None):
        self.image_path = image_path
        self.image = image
        meta_data = image.info
        self.meta_data = meta_data if meta_data is not None else load_metadata_from_image(image)
        return
        #size = self.ui.image_frame.width() - 20

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
        if image_path:
            image = Image.open(image_path)
            meta_data = image.info

            meta_data["width"] = width
            meta_data["height"] = height

            #self.set_table_data(meta_data)
    
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
        self.app.describe_image(image=self.image, callback=self.handle_prompt_generated)
        # prompt = self.app.generator_tab_widget.ui.prompt.toPlainText()
        # negative_prompt = self.app.generator_tab_widget.ui.negative_prompt.toPlainText()
        # self.handle_prompt_generated([prompt], [negative_prompt])
    
    def handle_prompt_generated(self, prompt, negative_prompt):
        meta_data = load_metadata_from_image(self.image)
        meta_data["prompt"] = prompt[0]
        meta_data["negative_prompt"] = negative_prompt[0]
        meta_data = prepare_metadata({ "options": meta_data })
        if self.image_path:
            image = Image.open(self.image_path)
            image.save(self.image_path, pnginfo=meta_data)
        else:
            image = self.app.canvas_widget.current_layer.image
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
        
        meta_data.pop("seed", None)
        meta_data.pop("latents_seed", None)
        meta_data["action"] = "txt2img"
        meta_data["width"] = self.image.width
        meta_data["height"] = self.image.height
        meta_data["enable_controlnet"] = True
        meta_data["controlnet"] = self.app.settings_manager.standard_image_widget_settings.controlnet.lower()
        meta_data["controlnet_conditioning_scale"] = self.app.settings_manager.standard_image_widget_settings.image_similarity / 100.0
        #meta_data["image_guidance_scale"] = 100 * (100 - self.app.settings_manager.image_similarity) / 100.0
        meta_data["strength"] = 1.1 - (self.app.settings_manager.standard_image_widget_settings.image_similarity / 100.0)
        print(meta_data["controlnet_conditioning_scale"], meta_data["strength"])
        meta_data["enable_input_image"] = True
        meta_data["use_cropped_image"] = False
        meta_data["batch_size"] = batch_size

        self.app.generator_tab_widget.call_generate(
            image=self.image,
            override_data=meta_data
        )
    
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
        meta_data.pop("latents_seed", None)
        meta_data["model_data_path"] = self.app.settings_manager.standard_image_widget_settings.upscale_model
        meta_data["face_enhance"] = self.app.settings_manager.standard_image_widget_settings.face_enhance
        meta_data["denoise_strength"] = 0.5
        meta_data["action"] = "upscale"
        meta_data["width"] = self.ui.canvas_widget.current_layer.image.width
        meta_data["height"] = self.ui.canvas_widget.current_layer.image.height
        meta_data["enable_input_image"] = True
        meta_data["use_cropped_image"] = False

        self.app.generator_tab_widget.call_generate(
            image=self.ui.canvas_widget.current_layer.image,
            override_data=meta_data
        )
    
    def set_form_values(self):
        self.set_form_property("steps_widget", "current_value", "generator.steps")
        self.set_form_property("scale_widget", "current_value", "generator.scale")
    
    def load_pipelines(self):
        self.ui.pipeline.blockSignals(True)
        self.ui.pipeline.clear()
        pipeline_names = ["txt2img / img2img", "inpaint / outpaint", "depth2img", "pix2pix", "upscale", "superresolution", "txt2vid"]
        self.ui.pipeline.addItems(pipeline_names)
        current_pipeline = self.app.settings_manager.settings.current_section_stablediffusion
        if current_pipeline != "":
            if current_pipeline == "txt2img":
                current_pipeline = "txt2img / img2img"
            elif current_pipeline == "outpaint":
                current_pipeline = "inpaint / outpaint"
            self.ui.pipeline.setCurrentText(current_pipeline)
        self.ui.pipeline.blockSignals(False)
    
    def load_versions(self):
        with session_scope() as session:
            self.ui.version.blockSignals(True)
            self.ui.version.clear()
            pipelines = session.query(Pipeline).filter(Pipeline.category == "stablediffusion").all()
            version_names = set([pipeline.version for pipeline in pipelines])
            self.ui.version.addItems(version_names)
            current_version = self.app.settings_manager.settings.current_version_stablediffusion
            if current_version != "":
                self.ui.version.setCurrentText(current_version)
            self.ui.version.blockSignals(False)

    def load_models(self):
        with session_scope() as session:
            self.ui.model.blockSignals(True)
            self.clear_models()

            image_generator = "stablediffusion"
            pipeline = self.app.settings_manager.settings.current_section_stablediffusion
            version = self.app.settings_manager.settings.current_version_stablediffusion

            models = session.query(AIModel).filter(
                AIModel.category == image_generator,
                AIModel.pipeline_action == pipeline,
                AIModel.version == version,
                AIModel.enabled == True
            ).all()
            model_names = [model.name for model in models]
            self.ui.model.addItems(model_names)
            current_model = self.app.settings_manager.generator.model
            if current_model != "":
                self.ui.model.setCurrentText(current_model)
            self.app.settings_manager.generator.model = self.ui.model.currentText()
            self.ui.model.blockSignals(False)

    def load_schedulers(self):
        with session_scope() as session:
            self.ui.scheduler.blockSignals(True)
            schedulers = session.query(ActionScheduler).filter(
                ActionScheduler.section == self.app.settings_manager.settings.current_section_stablediffusion,
                ActionScheduler.generator_name == "stablediffusion"
            ).all()
            scheduler_names = [s.scheduler.display_name for s in schedulers]
            self.ui.scheduler.clear()
            self.ui.scheduler.addItems(scheduler_names)

            current_scheduler = self.app.settings_manager.generator.scheduler
            if current_scheduler != "":
                self.ui.scheduler.setCurrentText(current_scheduler)
            else:
                self.app.settings_manager.set_value("generator.scheduler", self.ui.scheduler.currentText())
            self.ui.scheduler.blockSignals(False)
    
    def clear_models(self):
        self.ui.model.clear()
    
    def initialize_generator_form(self, override_id=None):
        if override_id:
            self.ui.steps_widget.set_slider_and_spinbox_values(self.app.settings_manager.generator.steps)
            self.ui.scale_widget.set_slider_and_spinbox_values(self.app.settings_manager.generator.scale * 100)
            self.ui.clip_skip_slider_widget.set_slider_and_spinbox_values(self.app.settings_manager.generator.clip_skip)
            
            self.ui.pipeline.blockSignals(True)
            self.ui.version.blockSignals(True)
            self.ui.model.blockSignals(True)
            self.ui.scheduler.blockSignals(True)
            
            self.ui.pipeline.setCurrentText(self.app.settings_manager.generator.section)
            self.ui.version.setCurrentText(self.app.settings_manager.generator.version)
            self.ui.model.setCurrentText(self.app.settings_manager.generator.model)
            self.ui.scheduler.setCurrentText(self.app.settings_manager.generator.scheduler)

            self.ui.pipeline.blockSignals(False)
            self.ui.version.blockSignals(False)
            self.ui.model.blockSignals(False)
            self.ui.scheduler.blockSignals(False)
        else:
            self.set_form_values()
            self.load_pipelines()
            self.load_versions()
            self.load_models()
            self.load_schedulers()
    
    def handle_changed_signal(self, key, val):
        print("standard_image_widget handle_settings_manager_changed handle_settings_manager_changed handle_settings_manager_changed handle_settings_manager_changed handle_settings_manager_changed")
        if key == "settings.generator_settings_override_id":
            self.initialize_generator_form(val)
        elif key == "settings.ai_mode":
            print("HANDLE SETTINGS MANAGER CHANGED")
            self.ui.settings_tab_widget.setCurrentIndex(1 if self.app.settings_manager.settings.ai_mode else 0)
        
    def initialize(self):
        self.set_form_values()
        self.load_pipelines()
        self.load_versions()
        self.load_models()
        self.load_schedulers()
        self.app.settings_manager.changed_signal.connect(self.handle_changed_signal)

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

        self.ui.seed_widget.setProperty("generator_section", self.app.settings_manager.settings.current_section_stablediffusion)
        self.ui.seed_widget.setProperty("generator_name", "stablediffusion")
        # self.ui.seed_widget.initialize(
        #     self.generator_section,
        #     self.generator_name
        # )

        self.ui.seed_widget_latents.setProperty("generator_section", self.app.settings_manager.settings.current_section_stablediffusion)
        self.ui.seed_widget_latents.setProperty("generator_name", "stablediffusion")
        # self.ui.seed_widget_latents.initialize(
        #     self.generator_section,
        #     self.generator_name
        # )
        self.initialized = True
    
    def handle_model_changed(self, name):
        if not self.initialized:
            return
        self.app.settings_manager.set_value("generator.model", name)

    def handle_scheduler_changed(self, name):
        if not self.initialized:
            return
        self.app.settings_manager.set_value("generator.scheduler", name)
    
    def handle_pipeline_changed(self, val):
        if val == "txt2img / img2img":
            val = "txt2img"
        elif val == "inpaint / outpaint":
            val = "outpaint"
        self.app.settings_manager.set_value("settings.current_section_stablediffusion", val)
        self.load_versions()
        self.load_models()

    def handle_version_changed(self, val):
        print("VERSION CHANGED", val)
        self.app.settings_manager.set_value(f"settings.current_version_stablediffusion", val)
        self.load_models()