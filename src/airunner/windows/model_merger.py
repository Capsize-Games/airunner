import os
from PyQt6 import uic
from PyQt6.QtWidgets import QVBoxLayout
from aihandler.settings import MODELS
from airunner.utils import load_default_models, load_models_from_path
from airunner.windows.base_window import BaseWindow


class ModelMerger(BaseWindow):
    template_name = "model_merger"
    window_title = "Model Merger"
    widgets = []
    total_models = 1
    models = []
    model_type = "txt2img / img2img"


    def initialize_window(self):
        model_types = ["txt2img / img2img", "inpaint / outpaint", "depth2img", "pix2pix"]
        self.template.model_types.addItems(model_types)
        self.template.model_types.currentIndexChanged.connect(self.change_model_type)

        self.models = self.load_models()
        path = self.settings_manager.settings.outpaint_model_path.get()
        if not path or path == "":
            path = self.settings_manager.settings.model_base_path.get()
        self.models += load_models_from_path(path)
        self.template.base_models.addItems(self.models)

        # get standard models from model_base_path
        path = self.settings_manager.settings.model_base_path.get()
        self.models = load_models_from_path(path)
        self.models.insert(0, "")
        # load the model_merger_model widget that will be used to add models
        for n in range(len(self.widgets), self.total_models):
            self.add_model(self.models, n)
        layout = QVBoxLayout()
        self.template.models.setLayout(layout)
        self.template.merge_button.clicked.connect(self.merge_models)
        self.template.addModel_button.clicked.connect(self.add_new_model)

    def load_models(self):
        if self.model_type == "txt2img / img2img":
            action = "generate"
        elif self.model_type == "inpaint / outpaint":
            action = "outpaint"
        elif self.model_type == "depth2img":
            action = "depth2img"
        elif self.model_type == "pix2pix":
            action = "pix2pix"
        return load_default_models(action)

    def change_model_type(self, index):
        self.model_type = self.template.model_types.currentText()
        self.models = []
        if self.model_type == "txt2img / img2img":
            self.models = self.load_models()
            path = self.settings_manager.settings.model_base_path.get()
            self.models += load_models_from_path(path)
        elif self.model_type == "inpaint / outpaint":
            self.models = self.load_models()
            path = self.settings_manager.settings.outpaint_model_path.get()
            if not path or path == "":
                path = self.settings_manager.settings.model_base_path.get()
            self.models += load_models_from_path(path)
        elif self.model_type == "depth2img":
            self.models = self.load_models()
            path = self.settings_manager.settings.depth2img_model_path.get()
            if not path or path == "":
                path = self.settings_manager.settings.model_base_path.get()
            self.models += self.load_models()
        elif self.model_type == "pix2pix":
            self.models = load_default_models("pix2pix")
            path = self.settings_manager.settings.pix2pix_model_path.get()
            if not path or path == "":
                path = self.settings_manager.settings.model_base_path.get()
            self.models += self.load_models()
        self.template.base_models.clear()
        self.template.base_models.addItems(self.models)
    
    def add_new_model(self):
        self.total_models += 1
        self.add_model(self.models, self.total_models-1)
    
    def add_model(self, models, index):
        widget = uic.loadUi(os.path.join(f"pyqt/model_merger_model.ui"))
        widget.models.addItems(models)
        widget.vae_weight_slider.setValue(50)
        widget.vae_weight_spinbox.setValue(0.5)
        widget.vae_weight_slider.valueChanged.connect(
            lambda value, widget=widget: widget.vae_weight_spinbox.setValue(value / 100)
        )
        widget.vae_weight_spinbox.valueChanged.connect(
            lambda value, widget=widget: widget.vae_weight_slider.setValue(int(value * 100))
        )
        widget.unet_weight_slider.setValue(50)
        widget.unet_weight_spinbox.setValue(0.5)
        widget.unet_weight_slider.valueChanged.connect(
            lambda value, widget=widget: widget.unet_weight_spinbox.setValue(value / 100)
        )
        widget.unet_weight_spinbox.valueChanged.connect(
            lambda value, widget=widget: widget.unet_weight_slider.setValue(int(value * 100))
        )
        widget.text_encoder_weight_slider.setValue(50)
        widget.text_encoder_weight_spinbox.setValue(0.5)
        widget.text_encoder_weight_slider.valueChanged.connect(
            lambda value, widget=widget: widget.text_encoder_weight_spinbox.setValue(value / 100)
        )
        widget.text_encoder_weight_spinbox.valueChanged.connect(
            lambda value, widget=widget: widget.text_encoder_weight_slider.setValue(int(value * 100))
        )
        widget.model_delete_button.clicked.connect(
            lambda _widget=widget: self.remove_model(widget)
        )
        self.widgets.append(widget)
        # self.template.models is a QTabWidget
        # add the widget as a new tab
        self.template.models.addTab(widget, f"Model {index+1}")
    
    def remove_model(self, widget):
        if len(self.widgets) > 1:
            widget.deleteLater()
            self.widgets.remove(widget)
            self.total_models -= 1

        # iterate over each tab in self.template.models and rename them
        for n in range(self.template.models.count()):
            self.template.models.setTabText(n, f"Model {n+1}")

    def merge_models(self):
        output_path = self.settings_manager.settings.outpaint_model_path.get()
        if not output_path or output_path == "":
            output_path = self.settings_manager.settings.model_base_path.get()
        models = []
        weights = []
        path = self.settings_manager.settings.model_base_path.get()

        for widget in self.widgets:
            if widget.models.currentText() != "":
                models.append(os.path.join(path, widget.models.currentText()))
                weights.append({
                    "vae": widget.vae_weight_spinbox.value(),
                    "unet": widget.unet_weight_spinbox.value(),
                    "text_encoder": widget.text_encoder_weight_spinbox.value(),
                })

        model = self.template.base_models.currentText()
        section_name = "outpaint"
        if model in MODELS[section_name]:
            model_path = MODELS[section_name][model]["path"]
        else:
            model_path = model

        self.app.client.sd_runner.merge_models(
            model_path,
            models,
            weights,
            output_path,
            self.template.model_name.text(),
        )
