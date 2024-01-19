from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QGridLayout, QProgressBar

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.generator_form.templates.generator_tab_ui import Ui_generator_tab


class GeneratorTabWidget(BaseWidget):
    widget_class_ = Ui_generator_tab
    generate_signal = pyqtSignal(dict)
    data = {}
    clip_skip_disabled_tabs = []
    clip_skip_disabled_sections = ["upscale", "superresolution", "txt2vid"]
    random_image_embed_seed = False
    row = 0
    col = 0
    layout = None

    @property
    def current_generator_widget(self):
        return self.ui.generator_form_stablediffusion

    @property
    def current_input_image_widget(self):
        return self.current_generator_widget.ui.input_image_widget

    @property
    def current_input_image(self):
        if self.app.enable_input_image:
            return self.current_input_image_widget.current_input_image
        return None

    @property
    def controlnet_settings_widget(self):
        if not self.current_generator_widget:
            return None
        return self.current_generator_widget.ui.get("controlnet_settings_widget", None)

    @property
    def input_image_widget(self):
        if not self.current_generator_widget:
            return None
        return self.current_generator_widget.ui.get("input_image_widget", None)

    @property
    def current_controlnet_input_image(self):
        if self.controlnet_settings_widget:
            return self.controlnet_settings_widget.current_image
        return None

    @property
    def controlnet_image(self):
        if self.controlnet_settings_widget:
            return self.controlnet_settings_widget.current_controlnet_image
        return None

    @property
    def use_controlnet_checkbox(self):
        if "use_controlnet_checkbox" not in self.current_generator_widget:
            return None
        return self.current_generator_widget["use_controlnet_checkbox"]

    @property
    def input_image(self):
        if "input_image" in self.current_generator_widget:
            return self.current_generator_widget["input_image"]
        return None

    @property
    def current_generator(self):
        try:
            return self.ui.generator_tabs.currentWidget().objectName().replace("tab_", "")
        except Exception as e:
            import traceback
            traceback.print_stack()
            print(e)

    def refresh_models(self):
        # iterate over all generator tabs and call load_models on the generatorform widget
        from airunner.widgets.generator_form.generator_form_widget import GeneratorForm
        for tab in self.ui.generator_form_stablediffusion.findChildren(GeneratorForm):
            tab.load_models()

    def find_generator_form(self, tab_section, tab):
        return getattr(self.ui, f"generator_form_{tab_section}", None)

    def find_widget(self, name, tab_section, tab):
        generator_form = self.find_generator_form(tab_section, tab)
        if generator_form:
            return generator_form.findChild(QProgressBar, name)

    def clear_prompts(self, tab_section, tab):
        generator_form = self.find_generator_form(tab_section, tab)
        if generator_form:
            generator_form.clear_prompts()

    def generate_form(self, tab_section, tab):
        self.tab_section = tab_section
        self.tab = tab
        self.force_tab_section(tab_section, tab)
        self.row = 0
        self.col = 0
        self.layout = None
        widget = QWidget(self)
        widget.setStyleSheet("font-size: 8pt;")
        self.layout = QGridLayout(widget)
        return widget

    def toggle_all_prompt_builder_checkboxes(self, state):
        for tab_section in self.data.keys():
            for section in self.data[tab_section].keys():
                try:
                    self.data[tab_section][section]["use_prompt_builder_checkbox"].setChecked(state)
                except KeyError:
                    pass

    def update_available_models(self):
        self.find_widget

        for section in self.data.keys():
            for tab in self.data[section].keys():
                self.data[section][tab]["model"].clear()
                self.load_model_by_section(section, tab)

    def toggle_variation(self, val):
        settings = self.app.settings
        settings["generator_settings"]["variation"] = val
        self.app.settings = settings

    def set_progress_bar_value(self, tab_section, section, value):
        progressbar = self.find_widget("progress_bar", tab_section, section)
        if not progressbar:
            return
        if progressbar.maximum() == 0:
            progressbar.setRange(0, 100)
        progressbar.setValue(value)

    def stop_progress_bar(self):
        self.generate_form.progress_bar.setRange(0, 100)
        self.generate_form.progress_bar.setValue(100)

    def add_widget_to_grid(self, widget, row=None, col=0):
        if row is None:
            row = self.row
            self.row += 1
        self.layout.addWidget(widget, row, col, 1, 1)

    def force_tab_section(self, tab_section, tab):
        self.app.override_current_generator = tab_section
        self.app.override_section = tab

    def set_prompt(self, prompt):
        self.current_generator_widget.ui.prompt.setPlainText(prompt)

    def set_negative_prompt(self, prompt):
        self.current_generator_widget.ui.negative_prompt.setPlainText(prompt)
