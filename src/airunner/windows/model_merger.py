import os
from PyQt6 import uic
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QVBoxLayout

from airunner.windows.base_window import BaseWindow


class ModelMerger(BaseWindow):
    template_name = "model_merger"
    window_title = "Model Merger (experimental)"
    widgets = []
    total_models = 1
    models = []
    model_type = "txt2img / img2img"


    def initialize_window(self):
        model_types = ["txt2img / img2img", "inpaint / outpaint", "depth2img", "pix2pix", "upscale", "superresolution"]
        self.template.model_types.addItems(model_types)
        self.template.model_types.currentIndexChanged.connect(self.change_model_type)
        self.template.base_models.addItems(self.app.available_model_names_by_section("txt2img"))

        # get standard models from model_base_path
        # load the model_merger_model widget that will be used to add models
        for n in range(len(self.widgets), self.total_models):
            self.add_model(self.app.available_model_names_by_section("txt2img"), n)
        layout = QVBoxLayout()
        self.template.models.setLayout(layout)
        self.template.merge_button.clicked.connect(self.merge_models)
        self.template.addModel_button.clicked.connect(self.add_new_model)

    @property
    def section(self):
        action = self.model_type
        if self.model_type == "inpaint / outpaint":
            action = "outpaint"
        elif self.model_type == "txt2img / img2img":
            action = "txt2img"
        return action

    @property
    def output_path(self):
        output_path = None
        if self.section == "outpaint":
            output_path = self.settings_manager.settings.outpaint_model_path.get()
        elif self.section == "depth2img":
            output_path = self.settings_manager.settings.depth2img_model_path.get()
        elif self.section == "pix2pix":
            output_path = self.settings_manager.settings.pix2pix_model_path.get()
        elif self.section == "upscale":
            output_path = self.settings_manager.settings.upscale_model_path.get()
        if not output_path or output_path == "":
            output_path = self.settings_manager.settings.model_base_path.get()
        return output_path

    def change_model_type(self, index):
        self.model_type = self.template.model_types.currentText()
        self.template.base_models.clear()
        self.template.base_models.addItems(self.app.available_model_names_by_section(self.section))
    
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

    def start_progress_bar(self):
        self.template.progressBar.setRange(0, 0)
    
    def stop_progress_bar(self):
        self.template.progressBar.reset()
        self.template.progressBar.setRange(0, 100)

    def merge_models(self):
        self.start_progress_bar()
        self.template.merge_button.setEnabled(False)
        # call do_model_merge in a separate thread
        self.merge_thread = QThread()
        class ModelMergeWorker(QObject):
            version = None
            finished = pyqtSignal()
            def __init__(self, *args, **kwargs) -> None:
                self.do_model_merge = kwargs.pop("do_model_merge")
                super().__init__(*args)
            def merge(self):
                self.version = f"v{self.do_model_merge()}"
                self.finished.emit()
        self.merge_worker = ModelMergeWorker(do_model_merge=self.do_model_merge)
        self.merge_worker.moveToThread(self.merge_thread)
        self.merge_thread.started.connect(self.merge_worker.merge)
        self.merge_worker.finished.connect(self.finalize_merge)
        self.merge_thread.start()
    
    def finalize_merge(self):
        self.stop_progress_bar()
        self.merge_thread.quit()
        self.template.merge_button.setEnabled(True)
    
    def do_model_merge(self):
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
        section = self.section
        available_models_by_section = self.app.application_data.available_models_by_section(section)
        model_data = None
        for data in available_models_by_section:
            if data["name"] == model:
                model_data = data

        if model_data:
            self.app.client.sd_runner.merge_models(
                model_data["path"],
                models,
                weights,
                self.output_path,
                self.template.model_name.text(),
                self.section
            )
