import re

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QGridLayout, QProgressBar, QTabWidget

from airunner.widgets.base_widget import BaseWidget
from airunner.aihandler.settings import MAX_SEED
from airunner.widgets.generator_form.templates.generator_tab_ui import Ui_generator_tab


class GeneratorTabWidget(BaseWidget):
    widget_class_ = Ui_generator_tab
    generate_signal = pyqtSignal(dict)
    data = {}
    clip_skip_disabled_tabs = ["kandinsky", "shapegif"]
    clip_skip_disabled_sections = ["upscale", "superresolution", "txt2vid"]
    random_image_embed_seed = False
    row = 0
    col = 0
    layout = None

    @property
    def current_generator_widget(self):
        #return self.data[self.tab_section][self.tab]
        try:
            obj = getattr(self.ui, f"tab_{self.current_generator}_{self.current_section}")
            return obj.findChild(QWidget, f"generator_form_{self.current_generator}_{self.current_section}")
        except Exception as e:
            print(e)
            return None

    @property
    def current_input_image_widget(self):
        return self.current_generator_widget.ui.input_image_widget

    @property
    def current_input_image(self):
        if self.settings_manager.settings.enable_input_image:
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

    @property
    def current_section(self):
        try:
            tab_widget_name = f"tab_widget_{self.current_generator}"
            tab_widget = self.ui.generator_tabs.findChild(QWidget, tab_widget_name)
            return tab_widget.currentWidget().objectName().replace(f"tab_{self.current_generator}_", "")
        except Exception as e:
            import traceback
            traceback.print_stack()
            print(e)

    def initialize(self):
        from airunner.widgets.generator_form.generator_form_widget import GeneratorForm
        self.app.release_tab_overrides()
        self.set_tab_handlers()
        self.set_current_section_tab()
        for tab in self.ui.tab_widget_stablediffusion.findChildren(GeneratorForm):
            tab.initialize()
        for tab in self.ui.tab_widget_kandinsky.findChildren(GeneratorForm):
            tab.initialize()
        for tab in self.ui.tab_widget_shape.findChildren(GeneratorForm):
            tab.initialize()

    def refresh_models(self):
        # iterate over all generator tabs and call load_models on the generatorform widget
        from airunner.widgets.generator_form.generator_form_widget import GeneratorForm
        for tab in self.ui.tab_widget_stablediffusion.findChildren(GeneratorForm):
            tab.load_models()

    def find_generator_form(self, tab_section, tab):
        obj = getattr(self.ui, f"tab_{tab_section}_{tab}")
        return obj.findChild(QWidget, f"generator_form_{tab_section}_{tab}")

    def find_widget(self, name, tab_section, tab):
        generator_form = self.find_generator_form(tab_section, tab)
        if generator_form:
            return generator_form.findChild(QProgressBar, name)

    def clear_prompts(self, tab_section, tab):
        generator_form = self.find_generator_form(tab_section, tab)
        if generator_form:
            generator_form.clear_prompts()

    def handle_generator_tab_changed(self):
        """
        This method is called when the generator tab is changed.
        Generator tabs are stablediffusion, kandinsky etc.
        :return: 
        """
        self.settings_manager.set_value("current_tab", self.current_generator)
        self.set_current_section_tab()
        self.app.handle_generator_tab_changed()

    def handle_tab_section_changed(self):
        """
        This method is called when the tab section is changed.
        Tab sections are txt2img, depth2img etc.
        :return:
        """
        self.settings_manager.set_value(f"current_section_{self.current_generator}", self.current_section)
        self.app.handle_tab_section_changed()

    def set_tab_handlers(self):
        self.ui.generator_tabs.currentChanged.connect(self.handle_generator_tab_changed)
        self.ui.tab_widget_stablediffusion.currentChanged.connect(self.handle_tab_section_changed)

    def set_current_section_tab(self):
        current_tab = self.settings_manager.current_tab
        current_section = getattr(self.settings_manager, f"current_section_{current_tab}")

        tab_object = self.ui.generator_tabs.findChild(QWidget, f"tab_{current_tab}")
        tab_index = self.ui.generator_tabs.indexOf(tab_object)
        self.ui.generator_tabs.setCurrentIndex(tab_index)

        tab_widget = tab_object.findChild(QTabWidget, f"tab_widget_{current_tab}")
        tab_index = tab_widget.indexOf(tab_widget.findChild(QWidget, f"tab_{current_tab}_{current_section}"))
        tab_widget.setCurrentIndex(tab_index)

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

    def update_thumbnails(self):
        self.current_generator_widget.update_image_input_thumbnail()
        self.current_generator_widget.update_controlnet_settings_thumbnail()

    def toggle_variation(self, val):
        self.settings_manager.set_value("generator.variation", val)

    def set_progress_bar_value(self, tab_section, section, value):
        progressbar = self.find_widget("progress_bar", tab_section, section)
        if not progressbar:
            return
        if progressbar.maximum() == 0:
            progressbar.setRange(0, 100)
        progressbar.setValue(value)

    def stop_progress_bar(self, tab_section, section):
        progressbar = self.find_widget("progress_bar", tab_section, section)
        if not progressbar:
            return
        progressbar.setRange(0, 100)
        progressbar.setValue(100)

    def add_widget_to_grid(self, widget, row=None, col=0):
        if row is None:
            row = self.row
            self.row += 1
        self.layout.addWidget(widget, row, col, 1, 1)

    def force_tab_section(self, tab_section, tab):
        self.app.override_current_generator = tab_section
        self.app.override_section = tab

    def handle_value_change(self, attr_name, value=None, widget=None, val=None):
        if attr_name in ["prompt", "negative_prompt"]:
            self.app.prompt_builder.process_prompt()

        if attr_name == "random_seed":
            value = not value
        elif attr_name == "seed":
            value = re.sub("[^0-9]", "", value)
            try:
                value = int(value)
            except ValueError:
                value = 0
            if value > MAX_SEED:
                value = MAX_SEED
            if widget:
                widget.setText(str(value))
        elif attr_name == "controlnet":
            value = value.lower()

        if widget:
            try:
                value = widget.toPlainText()
            except AttributeError:
                try:
                    value = widget.currentText()
                except AttributeError:
                    try:
                        value = widget.value()
                    except AttributeError:
                        print(f"something went wrong while setting the value for {attr_name}", widget)

        self.settings_manager.set_value(attr_name, value)

    def set_prompt(self, prompt):
        self.current_generator_widget.ui.prompt.setPlainText(prompt)

    def set_negative_prompt(self, prompt):
        self.current_generator_widget.ui.negative_prompt.setPlainText(prompt)

    def update_prompt(self, prompt):
        self.current_generator_widget.ui.prompt.setPlainText(prompt)

    def update_negative_prompt(self, prompt):
        self.current_generator_widget.ui.negative_prompt.setPlainText(prompt)