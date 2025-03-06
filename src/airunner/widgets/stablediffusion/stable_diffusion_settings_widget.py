from airunner.data.models import AIModels, GeneratorSettings
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

        self.ui.seed_widget.setProperty("generator_section", self.generator_settings.pipeline_action)
        self.ui.seed_widget.setProperty("generator_name", ImageGenerator.STABLEDIFFUSION.value)

        self.ui.ddim_eta_slider_widget.hide()
        self.ui.frames_slider_widget.hide()

        self.model_scanner_worker.add_to_queue("scan_for_models")

        self.ui.use_compel.setChecked(self.generator_settings.use_compel)

    def toggled_use_compel(self, val):
        self.update_generator_settings("use_compel", val)

    def handle_model_changed(self, model_name):
        index = self.ui.model.currentIndex()
        model_id = self.ui.model.itemData(index)
        self.update_generator_settings("model", model_id)
        if self.application_settings.sd_enabled:
            self.emit_signal(SignalCode.SD_LOAD_SIGNAL, {
                "do_reload": True
            })

    def handle_scheduler_changed(self, name):
        self.update_generator_settings("scheduler", name)
        self.emit_signal(SignalCode.CHANGE_SCHEDULER_SIGNAL, {"scheduler": name})

    def handle_pipeline_changed(self, val):
        if val == f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}":
            val = GeneratorSection.TXT2IMG.value
        elif val == f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}":
            val = GeneratorSection.INPAINT.value
        
        generator_settings = GeneratorSettings.objects.first()
        do_reload = False
        if val == GeneratorSection.TXT2IMG.value:
            model = AIModels.objects.filter(
                AIModels.id == generator_settings.model
            ).first()
            if model.pipeline_action == GeneratorSection.INPAINT.value:
                model = AIModels.objects.filter(
                    AIModels.version == generator_settings.version,
                    AIModels.pipeline_action == val,
                    AIModels.enabled == True,
                    AIModels.is_default == False
                ).first()
                if model is not None:
                    generator_settings.model = model.id
                else:
                    generator_settings.model = None
                do_reload = True
        generator_settings.pipeline_action = val
        generator_settings.save()
        
        self.load_versions()
        self.load_models()
        if do_reload:
            if self.application_settings.sd_enabled:
                self.emit_signal(SignalCode.SD_LOAD_SIGNAL, {
                    "do_reload": True
                })

    def handle_version_changed(self, val):
        self.update_generator_settings("version", val)
        
        generator_settings = GeneratorSettings.objects.first()
        model = AIModels.objects.filter(
            AIModels.version == val,
            AIModels.pipeline_action == generator_settings.pipeline_action,
            AIModels.enabled == True,
            AIModels.is_default == False
        ).first()
        generator_settings.version = val
        generator_settings.model = model.id
        generator_settings.save()
        
        self.load_models()
        if self.application_settings.sd_enabled:
            self.emit_signal(SignalCode.SD_LOAD_SIGNAL, {
                "do_reload": True
            })

    def _load_pipelines(self):
        self.ui.pipeline.blockSignals(True)
        self.ui.pipeline.clear()
        pipeline_names = [
            f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}",
            f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}"
        ]
        self.ui.pipeline.addItems(pipeline_names)
        current_pipeline = self.generator_settings.pipeline_action
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
        current_version = self.generator_settings.version
        if current_version != "":
            self.ui.version.setCurrentText(current_version)
        self.ui.version.blockSignals(False)

    def on_models_changed_signal(self):
        try:
            self._load_pipelines()
            self.load_versions()
            self.load_models()
            self.load_schedulers_dropdown()
        except RuntimeError as e:
            self.logger.error(f"Error loading models: {e}")

    def clear_models(self):
        self.ui.model.clear()

    def load_models(self):
        self.ui.model.blockSignals(True)
        self.clear_models()
        image_generator = ImageGenerator.STABLEDIFFUSION.value
        
        generator_settings = GeneratorSettings.objects.first()
        pipeline = generator_settings.pipeline_action
        version = generator_settings.version
        pipeline_actions = [GeneratorSection.TXT2IMG.value]
        if pipeline == GeneratorSection.INPAINT.value:
            pipeline_actions.append(GeneratorSection.INPAINT.value)
        models = AIModels.objects.filter(
            AIModels.category == image_generator,
            AIModels.pipeline_action.in_(pipeline_actions),
            AIModels.version == version,
            AIModels.enabled == True,
            AIModels.is_default == False
        ).all()
        model_id = generator_settings.model
        if model_id is None and len(models) > 0:
            current_model = models[0]
            generator_settings.model = current_model.id
            generator_settings.save()
        for model in models:
            self.ui.model.addItem(model.name, model.id)
        
        if model_id:
            index = self.ui.model.findData(model_id)
            if index != -1:
                self.ui.model.setCurrentIndex(index)
        self.ui.model.blockSignals(False)

    def load_schedulers_dropdown(self):
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
