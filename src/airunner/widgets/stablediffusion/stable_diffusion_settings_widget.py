from airunner.enums import SignalCode, GeneratorSection, ImageGenerator
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.stablediffusion.templates.stable_diffusion_settings_ui import Ui_stable_diffusion_settings_widget
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.utils.create_worker import create_worker
from airunner.workers.model_scanner_worker import ModelScannerWorker


class StableDiffusionSettingsWidget(
    BaseWidget,
    PipelineMixin
):
    widget_class_ = Ui_stable_diffusion_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PipelineMixin.__init__(self)
        self.model_scanner_worker = create_worker(ModelScannerWorker)
        self.register(SignalCode.AI_MODELS_CREATE_SIGNAL, self.on_models_changed_signal)
        self.register(SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL, self.update_form)

    def showEvent(self, event):
        super().showEvent(event)
        self.update_form()

    def update_form(self, _data: dict = None):
        steps = self.settings["generator_settings"]["steps"]
        scale = self.settings["generator_settings"]["scale"]

        current_steps = self.get_form_element("steps_widget").property("current_value")
        current_scale = self.get_form_element("scale_widget").property("current_value")

        if steps != current_steps:
            self.get_form_element("steps_widget").setProperty("current_value", steps)

        if scale != current_scale:
            self.get_form_element("scale_widget").setProperty("current_value", scale)
        
        self.ui.seed_widget.setProperty("generator_section", self.settings["pipeline"])
        self.ui.seed_widget.setProperty("generator_name", ImageGenerator.STABLEDIFFUSION.value)

        self.ui.ddim_eta_slider_widget.hide()
        self.ui.frames_slider_widget.hide()

        self.model_scanner_worker.add_to_queue("scan_for_models")

        self.ui.use_compel.setChecked(self.settings["generator_settings"]["use_compel"])

    def toggled_use_compel(self, val):
        settings = self.settings
        settings["generator_settings"]["use_compel"] = val
        self.settings = settings

    def handle_model_changed(self, name):
        settings = self.settings
        settings["generator_settings"]["model"] = name
        self.settings = settings
        self.emit_signal(SignalCode.SD_LOAD_SIGNAL)

    def handle_scheduler_changed(self, name):
        settings = self.settings
        settings["generator_settings"]["scheduler"] = name
        self.settings = settings
        self.emit_signal(SignalCode.CHANGE_SCHEDULER_SIGNAL, {"scheduler": name})
    
    def handle_pipeline_changed(self, val):
        if val == f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}":
            val = GeneratorSection.TXT2IMG.value
        elif val == f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}":
            val = GeneratorSection.OUTPAINT.value
        settings = self.settings
        settings["pipeline"] = val
        settings["generator_settings"]["section"] = val
        self.settings = settings
        self.load_versions()
        self.load_models()

    def handle_version_changed(self, val):
        settings = self.settings
        settings["current_version_stablediffusion"] = val
        settings["generator_settings"]["version"] = val
        self.settings = settings
        self.load_models()

    def load_pipelines(self):
        self.logger.debug("load_pipelines")
        self.ui.pipeline.blockSignals(True)
        self.ui.pipeline.clear()
        pipeline_names = [
            f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}",
            f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}",
            GeneratorSection.DEPTH2IMG.value,
            GeneratorSection.PIX2PIX.value,
            GeneratorSection.UPSCALE.value,
        ]
        self.ui.pipeline.addItems(pipeline_names)
        current_pipeline = self.settings["pipeline"]
        if current_pipeline != "":
            if current_pipeline == GeneratorSection.TXT2IMG.value:
                current_pipeline = f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}"
            elif current_pipeline == GeneratorSection.OUTPAINT.value:
                current_pipeline = f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}"
            self.ui.pipeline.setCurrentText(current_pipeline)
        self.ui.pipeline.blockSignals(False)
    
    def load_versions(self):
        self.logger.debug("load_versions")
        self.ui.version.blockSignals(True)
        self.ui.version.clear()
        pipelines = self.get_pipelines(category=ImageGenerator.STABLEDIFFUSION.value)
        version_names = set([pipeline["version"] for pipeline in pipelines])
        self.ui.version.addItems(version_names)
        current_version = self.settings["current_version_stablediffusion"]
        if current_version != "":
            self.ui.version.setCurrentText(current_version)
        self.ui.version.blockSignals(False)

    def on_models_changed_signal(self, data: dict):
        try:
            self.load_pipelines()
            self.load_versions()
            self.load_models(data["models"])
            self.load_schedulers()
        except RuntimeError as e:
            self.logger.error(f"Error loading models: {e}")

    def clear_models(self):
        self.ui.model.clear()

    def load_models(self, models=None):
        models = models or self.settings["ai_models"]
        self.logger.debug("load_models")
        self.ui.model.blockSignals(True)
        self.clear_models()
        image_generator = ImageGenerator.STABLEDIFFUSION.value
        pipeline = self.settings["pipeline"]
        version = self.settings["current_version_stablediffusion"]
        models = self.ai_model_get_by_filter(models, {
            'category': image_generator,
            'pipeline_action': pipeline,
            'version': version,
            'enabled': True
        })
        model_names = [model["name"] for model in models]
        self.ui.model.addItems(model_names)
        settings = self.settings
        model_name = settings["generator_settings"]["model"]
        if model_name != "":
            self.ui.model.setCurrentText(model_name)
        settings["generator_settings"]["model"] = self.ui.model.currentText()

        model = None
        try:
            path = self.settings["generator_settings"]["model"]
            model = [model for model in self.settings["ai_models"] if model["path"] == path][0]
        except Exception as e:
            name = self.settings["generator_settings"]["model"]
            try:
                model = [model for model in self.settings["ai_models"] if model["name"] == name][0]
            except Exception as e:
                self.logger.error(f"Error finding model by name: {name}")

        if model:
            settings["generator_settings"]["model"] = model["name"]
        self.ui.model.blockSignals(False)
        self.settings = settings

    def ai_model_get_by_filter(self, models, filter_dict):
        return [item for item in models if all(item.get(k) == v for k, v in filter_dict.items())]

    def load_schedulers(self):
        self.logger.debug("load_schedulers")
        self.ui.scheduler.blockSignals(True)
        scheduler_names = [s["display_name"] for s in self.settings["schedulers"]]
        self.ui.scheduler.clear()
        self.ui.scheduler.addItems(scheduler_names)

        settings = self.settings
        current_scheduler = settings["generator_settings"]["scheduler"]
        if current_scheduler != "":
            self.ui.scheduler.setCurrentText(current_scheduler)
        else:
            settings["generator_settings"]["scheduler"] = self.ui.scheduler.currentText() 
        self.settings = settings
        self.ui.scheduler.blockSignals(False)
