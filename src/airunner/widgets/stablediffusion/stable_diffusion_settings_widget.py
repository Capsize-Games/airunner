from airunner.enums import SignalCode, ServiceCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.stablediffusion.templates.stable_diffusion_settings_ui import Ui_stable_diffusion_settings_widget


class StableDiffusionSettingsWidget(BaseWidget):
    widget_class_ = Ui_stable_diffusion_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(SignalCode.APPLICATION_MODELS_CHANGED_SIGNAL, self.on_models_changed_signal)

    def showEvent(self, event):
        super().showEvent(event)
        steps = target_val = self.settings["generator_settings"]["steps"]
        scale = target_val = self.settings["generator_settings"]["scale"]

        current_steps = self.get_form_element("steps_widget").property("current_value")
        current_scale = self.get_form_element("scale_widget").property("current_value")

        if steps != current_steps:
            self.get_form_element("steps_widget").setProperty("current_value", target_val)

        if scale != current_scale:
            self.get_form_element("scale_widget").setProperty("current_value", target_val)
        
        self.ui.seed_widget.setProperty("generator_section", self.settings["pipeline"])
        self.ui.seed_widget.setProperty("generator_name", "stablediffusion")

        self.ui.ddim_eta_slider_widget.hide()
        self.ui.frames_slider_widget.hide()

        self.load_pipelines()
        self.load_versions()
        self.load_models()
        self.load_schedulers()

    def handle_model_changed(self, name):
        settings = self.settings
        settings["generator_settings"]["model"] = name
        self.settings = settings

    def handle_scheduler_changed(self, name):
        settings = self.settings
        settings["generator_settings"]["scheduler"] = name
        self.settings = settings
    
    def handle_pipeline_changed(self, val):
        if val == "txt2img / img2img":
            val = "txt2img"
        elif val == "inpaint / outpaint":
            val = "outpaint"
        settings = self.settings
        settings["pipeline"] = val
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
        self.logger.info("load_pipelines")
        self.ui.pipeline.blockSignals(True)
        self.ui.pipeline.clear()
        pipeline_names = ["txt2img / img2img", "inpaint / outpaint", "depth2img", "pix2pix", "upscale", "superresolution", "txt2vid"]
        self.ui.pipeline.addItems(pipeline_names)
        current_pipeline = self.settings["pipeline"]
        if current_pipeline != "":
            if current_pipeline == "txt2img":
                current_pipeline = "txt2img / img2img"
            elif current_pipeline == "outpaint":
                current_pipeline = "inpaint / outpaint"
            self.ui.pipeline.setCurrentText(current_pipeline)
        self.ui.pipeline.blockSignals(False)
    
    def load_versions(self):
        self.logger.info("load_versions")
        self.ui.version.blockSignals(True)
        self.ui.version.clear()
        pipelines = self.get_service(ServiceCode.GET_PIPELINES)(category="stablediffusion")
        version_names = set([pipeline["version"] for pipeline in pipelines])
        self.ui.version.addItems(version_names)
        current_version = self.settings["current_version_stablediffusion"]
        if current_version != "":
            self.ui.version.setCurrentText(current_version)
        self.ui.version.blockSignals(False)

    def on_models_changed_signal(self, _ignore):
        self.load_pipelines()
        self.load_versions()
        self.load_models()
        self.load_schedulers()

    def clear_models(self):
        self.ui.model.clear()

    def load_models(self):
        self.logger.info("load_models")
        self.ui.model.blockSignals(True)
        self.clear_models()

        image_generator = "stablediffusion"
        pipeline = self.settings["pipeline"]
        version = self.settings["current_version_stablediffusion"]

        models = self.get_service("ai_model_get_by_filter")({
            'category': image_generator,
            'pipeline_action': pipeline,
            'version': version,
            'enabled': True
        })
        model_names = [model["name"] for model in models]
        self.ui.model.addItems(model_names)
        settings = self.settings
        current_model = settings["generator_settings"]["model"]
        if current_model != "":
            self.ui.model.setCurrentText(current_model)
        settings["generator_settings"]["model"] = self.ui.model.currentText()
        self.ui.model.blockSignals(False)
        self.settings = settings

    def load_schedulers(self):
        self.logger.info("load_schedulers")
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