from functools import partial

from PyQt6.QtCore import pyqtSignal

from airunner.data.models import ActionScheduler
from airunner.utils import get_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.generator_form.templates.generatorform_ui import Ui_generator_form
from airunner.widgets.slider.slider_widget import SliderWidget


class GeneratorForm(BaseWidget):
    widget_class_ = Ui_generator_form
    changed_signal = pyqtSignal(str, object)

    @property
    def generator_section(self):
        try:
            return self.property("generator_section")
        except Exception as e:
            print(e)
            return None

    @property
    def generator_name(self):
        try:
            return self.property("generator_name")
        except Exception as e:
            print(e)
            return None

    @property
    def generator_settings(self):
        return self.settings_manager.find_generator(
            self.generator_section,
            self.generator_name
        )

    """
    Slot functions

    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """
    def handle_prompt_changed(self):
        self.handle_textbox_change("generator.prompt", "prompt")

    def handle_negative_prompt_changed(self):
        self.handle_textbox_change("generator.negative_prompt", "negative_prompt")

    def toggle_prompt_builder_checkbox(self, toggled):
        pass

    def handle_model_changed(self, name):
        if not self.initialized:
            return
        self.settings_manager.set_value("generator.model", name)
        self.changed_signal.emit("generator.model", name)

    def handle_scheduler_changed(self, name):
        if not self.initialized:
            return
        self.settings_manager.set_value("generator.scheduler", name)
        self.changed_signal.emit("generator.scheduler", name)

    def toggle_variation(self, toggled):
        pass

    def handle_generate_button_clicked(self):
        pass

    def handle_interrupt_button_clicked(self):
        pass
    """
    End Slot functions
    """

    def save_db_session(self):
        from airunner.utils import save_session
        save_session()

    def handle_checkbox_change(self, key, widget_name):
        widget = getattr(self.ui, widget_name)
        value = widget.isChecked()
        setattr(self.generator_settings, key, value)
        self.save_db_session()
        self.changed_signal.emit(key, value)

    def handle_textbox_change(self, key, widget_name):
        widget = getattr(self.ui, widget_name)
        value = widget.toPlainText()
        setattr(self.settings_manager, key, value)
        self.save_db_session()
        self.changed_signal.emit(key, value)

    initialized = False
    def initialize(self):
        self.settings_manager.generator_section = self.generator_section
        self.settings_manager.generator_name = self.generator_name
        self.clear_prompts()
        self.load_models()
        self.load_schedulers()
        self.set_form_values()
        self.initialize_handlers()
        self.set_controlnet_settings_properties()
        self.set_input_image_widget_properties()

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

        self.ui.seed_widget.setProperty("generator_section", self.generator_section)
        self.ui.seed_widget.setProperty("generator_name", self.generator_name)
        self.ui.seed_widget.initialize(
            self.generator_section,
            self.generator_name
        )

        self.ui.seed_widget_latents.setProperty("generator_section", self.generator_section)
        self.ui.seed_widget_latents.setProperty("generator_name", self.generator_name)
        self.ui.seed_widget_latents.initialize(
            self.generator_section,
            self.generator_name
        )
        self.initialized = True

    def set_controlnet_settings_properties(self):
        self.ui.controlnet_settings.initialize(
            self.generator_name,
            self.generator_section
        )

    def set_input_image_widget_properties(self):
        self.ui.input_image_widget.initialize(
            self.generator_name,
            self.generator_section
        )
        self.ui.controlnet_settings.initialize(
            self.generator_name,
            self.generator_section
        )

    def clear_prompts(self):
        self.ui.prompt.clear()
        self.ui.negative_prompt.clear()
        # self.ui.prompt.setPlainText("")
        # self.ui.negative_prompt.setPlainText("")

    def load_models(self):
        self.clear_models()
        requested_section = "txt2img" if self.generator_section == "txt2vid" \
            else self.generator_section
        models = self.settings_manager.available_model_names(
            pipeline_action=requested_section,
            category=self.generator_name)
        self.ui.model.addItems(models)

    def load_schedulers(self):
        session = get_session()
        schedulers = session.query(ActionScheduler).filter(
            ActionScheduler.section == self.generator_section,
            ActionScheduler.generator_name == self.generator_name
        ).all()
        scheduler_names = [s.scheduler.display_name for s in schedulers]
        self.ui.scheduler.addItems(scheduler_names)

    def set_form_values(self):
        self.ui.prompt.setPlainText(
            self.generator_settings.prompt
        )
        self.ui.negative_prompt.setPlainText(
            self.generator_settings.negative_prompt
        )
        self.ui.use_prompt_builder_checkbox.setChecked(
            self.settings_manager.use_prompt_builder_checkbox
        )

    def initialize_handlers(self):
        self.ui.use_prompt_builder_checkbox.stateChanged.connect(partial(
            self.handle_checkbox_change,
            "use_prompt_builder_checkbox",
            "use_prompt_builder_checkbox",
        ))
        self.ui.prompt_builder_settings_button.clicked.connect(partial(
            self.app.show_section,
            "prompt_builder"
        ))
        self.ui.generate_button.clicked.connect(partial(
            self.app.generate,
            self.ui.progress_bar
        ))
        # self.app.image_generated.connect(
        #     self.ui.controlnet_settings.handle_image_generated
        # )
        # self.app.controlnet_image_generated.connect(
        #     self.ui.controlnet_settings.handle_controlnet_image_generated
        # )

    def clear_models(self):
        self.ui.model.clear()
