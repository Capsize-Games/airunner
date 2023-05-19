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


    def initialize_window(self):
        self.models = load_default_models("outpaint")
        path = self.settings_manager.settings.outpaint_model_path.get()
        if not path or path == "":
            path = self.settings_manager.settings.model_base_path.get()
        self.models += load_models_from_path(path)
        self.template.inpaint_models.addItems(self.models)

        # get standard models from model_base_path
        path = self.settings_manager.settings.model_base_path.get()
        self.models = load_models_from_path(path)
        self.models.insert(0, "")

        # load the model_merger_model widget that will be used to add models
        for n in range(self.total_models):
            self.add_model(self.models, n)
        layout = QVBoxLayout()
        self.template.models.setLayout(layout)
        for widget in self.widgets:
            self.template.models.layout().addWidget(widget)
        self.template.merge_button.clicked.connect(self.merge_models)
        self.template.addModel_button.clicked.connect(self.add_new_model)
    
    def add_new_model(self):
        self.total_models += 1
        self.add_model(self.models, self.total_models-1)
        self.template.models.layout().addWidget(self.widgets[-1])
    
    def add_model(self, models, index):
        widget = uic.loadUi(os.path.join(f"pyqt/model_merger_model.ui"))
        widget.model_label.setText(f"Model {index+1}")
        widget.models.addItems(models)
        widget.model_weight_slider.setValue(50)
        widget.model_weight_spinbox.setValue(0.5)
        widget.model_weight_slider.valueChanged.connect(
            lambda value, widget=widget: widget.model_weight_spinbox.setValue(value / 100)
        )
        widget.model_weight_spinbox.valueChanged.connect(
            lambda value, widget=widget: widget.model_weight_slider.setValue(int(value * 100))
        )
        widget.model_delete_button.clicked.connect(
            lambda _widget=widget: self.remove_model(widget)
        )
        self.widgets.append(widget)
    
    def remove_model(self, widget):
        if len(self.widgets) > 1:
            widget.deleteLater()
            self.widgets.remove(widget)
            self.total_models -= 1

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
                weights.append(widget.model_weight_spinbox.value())

        model = self.template.inpaint_models.currentText()
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
