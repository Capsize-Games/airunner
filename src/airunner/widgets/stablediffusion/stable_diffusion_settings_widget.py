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

    def update_form(self):
        steps = self.generator_settings.steps
        scale = self.generator_settings.scale

        current_steps = self.get_form_element("steps_widget").property("current_value")
        current_scale = self.get_form_element("scale_widget").property("current_value")

        if steps != current_steps:
            self.get_form_element("steps_widget").setProperty("current_value", steps)

        if scale != current_scale:
            self.get_form_element("scale_widget").setProperty("current_value", scale)

        self.ui.seed_widget.setProperty("generator_section", self.application_settings.pipeline)
        self.ui.seed_widget.setProperty("generator_name", ImageGenerator.STABLEDIFFUSION.value)

        self.ui.ddim_eta_slider_widget.hide()
        self.ui.frames_slider_widget.hide()

        self.model_scanner_worker.add_to_queue("scan_for_models")

        self.ui.use_compel.setChecked(self.generator_settings.use_compel)

    def toggled_use_compel(self, val):
        self.update_generator_settings("use_compel", val)

    def handle_model_changed(self, name):
        self.update_generator_settings("model", name)
        if self.application_settings.sd_enabled:
            self.emit_signal(SignalCode.SD_LOAD_SIGNAL)

    def handle_scheduler_changed(self, name):
        self.update_generator_settings("scheduler", name)
        self.emit_signal(SignalCode.CHANGE_SCHEDULER_SIGNAL, {"scheduler": name})

    def handle_pipeline_changed(self, val):
        if val == f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}":
            val = GeneratorSection.TXT2IMG.value
        elif val == f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}":
            val = GeneratorSection.INPAINT.value
        self.update_application_settings("pipeline", val)
        self.update_generator_settings("section", val)
        self.load_versions()
        self.load_models()

    def handle_version_changed(self, val):
        self.update_application_settings("current_version_stablediffusion", val)
        self.update_generator_settings("version", val)
        self.load_models()

    def load_pipelines(self):
        self.ui.pipeline.blockSignals(True)
        self.ui.pipeline.clear()
        pipeline_names = [
            f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}",
            f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}"
        ]
        self.ui.pipeline.addItems(pipeline_names)
        current_pipeline = self.application_settings.pipeline
        if current_pipeline != "":
            if current_pipeline == GeneratorSection.TXT2IMG.value:
                current_pipeline = f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}"
            elif current_pipeline == GeneratorSection.INPAINT.value:
                current_pipeline = f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}"
            self.ui.pipeline.setCurrentText(current_pipeline)
        self.ui.pipeline.blockSignals(False)
    
    def load_versions(self):
        self.ui.version.blockSignals(True)
        self.ui.version.clear()
        pipelines = self.get_pipelines(category=ImageGenerator.STABLEDIFFUSION.value)
        version_names = set([pipeline["version"] for pipeline in pipelines])
        self.ui.version.addItems(version_names)
        current_version = self.application_settings.current_version_stablediffusion
        if current_version != "":
            self.ui.version.setCurrentText(current_version)
        self.ui.version.blockSignals(False)

    def on_models_changed_signal(self):
        try:
            self.load_pipelines()
            self.load_versions()
            self.load_models()
            self.load_schedulers()
        except RuntimeError as e:
            self.logger.error(f"Error loading models: {e}")

    def clear_models(self):
        self.ui.model.clear()

    def load_models(self):
        self.ui.model.blockSignals(True)
        self.clear_models()
        image_generator = ImageGenerator.STABLEDIFFUSION.value
        pipeline = self.application_settings.pipeline
        version = self.application_settings.current_version_stablediffusion
        models = self.ai_model_get_by_filter({
            'category': image_generator,
            'pipeline_action': pipeline,
            'version': version,
            'enabled': True
        })
        model_names = [model.name for model in models]
        self.ui.model.addItems(model_names)
        model_name = self.generator_settings.model
        if model_name != "":
            self.ui.model.setCurrentText(model_name)
        self.update_generator_settings("model", self.ui.model.currentText())

        model = None
        try:
            path = self.generator_settings.model
            model = self.ai_model_get_by_filter({"path": path})
        except Exception as e:
            name = self.generator_settings.model
            try:
                model = [model for model in self.application_settings.ai_models if model["name"] == name][0]
            except Exception as e:
                self.logger.error(f"Error finding model by name: {name}")

        self.ui.model.blockSignals(False)
        self.update_generator_settings("model", self.generator_settings.model)

    def load_schedulers(self):
        self.ui.scheduler.blockSignals(True)
        scheduler_names = [s.display_name for s in self.schedulers]
        self.ui.scheduler.clear()
        self.ui.scheduler.addItems(scheduler_names)

        current_scheduler = self.generator_settings.scheduler
        if current_scheduler != "":
            self.ui.scheduler.setCurrentText(current_scheduler)
        else:
            self.generator_settings.scheduler = self.ui.scheduler.currentText()
        self.update_generator_settings("scheduler", self.generator_settings.scheduler)
        self.ui.scheduler.blockSignals(False)
