import re
from functools import partial

from PyQt6.QtWidgets import QWidget, QGridLayout, QHBoxLayout, \
    QPushButton, QProgressBar, QFormLayout, QCheckBox, QTabWidget

from airunner.pyqt.widgets.base_widget import BaseWidget
from airunner.aihandler.settings import MAX_SEED
from airunner.aihandler.enums import MessageCode
from airunner.pyqt.widgets.controlnet_settings.controlnet_settings_widget import ControlNetSettingsWidget
from airunner.pyqt.widgets.generator_form.generator_tab_ui import Ui_generator_tab
from airunner.pyqt.widgets.slider.slider_widget import SliderWidget


class GeneratorTabWidget(BaseWidget):
    widget_class_ = Ui_generator_tab
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
        from airunner.pyqt.widgets.generator_form.generator_form_widget import GeneratorForm
        self.app.release_tab_overrides()
        self.set_tab_handlers()
        self.set_current_section_tab()
        for tab in self.ui.tab_widget_stablediffusion.findChildren(GeneratorForm):
            tab.initialize()
        for tab in self.ui.tab_widget_kandinsky.findChildren(GeneratorForm):
            tab.initialize()
        for tab in self.ui.tab_widget_shape.findChildren(GeneratorForm):
            tab.initialize()


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

    def update_image_input_thumbnail(self):
        if self.current_generator_widget.ui.input_image_widget:
            self.current_generator_widget.ui.input_image_widget.set_thumbnail()

    def update_controlnet_thumbnail(self):
        # if self.controlnet_settings_widget:
        #     self.controlnet_settings_widget.set_thumbnail()
        pass

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
        self.add_prompt_widgets()
        # self.add_controlnet_settings_widget(tab_section, tab)
        # self.add_steps_widget()
        # self.add_scale_widgets()
        # self.add_upscale_widgets()
        # self.add_samples_widgets()
        # self.add_frames_widgets()
        # self.add_generate_widgets()
        # self.release_tab_overrides()
        return widget

    def toggle_all_prompt_builder_checkboxes(self, state):
        for tab_section in self.data.keys():
            for section in self.data[tab_section].keys():
                try:
                    self.data[tab_section][section]["use_prompt_builder_checkbox"].setChecked(state)
                except KeyError:
                    pass

    def add_controlnet_settings_widget(self, tab_section, tab):
        if tab_section not in ["kandinsky", "shapegif"] and tab in ["txt2img", "img2img", "outpaint", "txt2vid"]:
            controlnet_settings_widget = ControlNetSettingsWidget(app=self.app)
            self.current_generator_widget["controlnet_settings_widget"] = controlnet_settings_widget
            self.add_widget_to_grid(controlnet_settings_widget)

    def update_available_models(self):
        self.find_widget

        for section in self.data.keys():
            for tab in self.data[section].keys():
                self.data[section][tab]["model"].clear()
                self.load_model_by_section(section, tab)

    def add_steps_widget(self):
        steps_slider = SliderWidget(
            app=self.app,
            label_text="Steps",
            slider_callback=partial(self.handle_value_change, "generator.steps"),
            current_value=int(self.settings_manager.generator.steps),
            slider_maximum=200,
            spinbox_maximum=200.0,
            display_as_float=False,
            spinbox_single_step=1,
            spinbox_page_step=1,
            spinbox_minimum=1,
            slider_minimum=1
        )
        self.current_generator_widget["steps_slider_widget"] = steps_slider
        self.add_widget_to_grid(steps_slider)

    def get_scale_slider(self, label_text="Scale"):
        return SliderWidget(
            app=self.app,
            label_text=label_text,
            slider_callback=partial(self.handle_value_change, "generator.scale"),
            current_value=int(self.settings_manager.generator.scale),
            slider_maximum=10000,
            spinbox_maximum=100.0,
            display_as_float=True,
            spinbox_single_step=0.01,
            spinbox_page_step=0.01
        )

    def add_scale_widgets(self):
        if self.tab_section == "stablediffusion" and self.tab == "upscale":
            return
        scale_slider = self.get_scale_slider()
        self.current_generator_widget["scale_slider_widget"] = scale_slider
        self.add_widget_to_grid(scale_slider)

    def update_seed(self):
        self.current_generator_widget["seed_widget"].update_seed()
        self.current_generator_widget["seed_widget_latents"].update_seed()

    def update_thumbnails(self):
        self.update_image_input_thumbnail()
        self.update_controlnet_thumbnail()

    def load_clip_skip_slider(self):
        """
        The following block will load the clip skip slider for any tab
        that is not kandinsky or shapegif (essentially just stablediffusion tab)
        """
        clip_skip_widget = SliderWidget(
            app=self.app,
            label_text="Clip Skip",
            slider_callback=partial(self.handle_value_change, "generator.clip_skip"),
            current_value=self.settings_manager.generator.clip_skip,
            slider_maximum=11,
            spinbox_maximum=12.0,
            display_as_float=False,
            spinbox_single_step=1,
            spinbox_page_step=1,
            spinbox_minimum=0,
            slider_minimum=0
        )
        self.current_generator_widget["clip_skip_slider_widget"] = clip_skip_widget
        self.add_widget_to_grid(clip_skip_widget)

    def add_samples_widgets(self):
        if self.tab == "txt2vid":
            return
        samples_widget = SliderWidget(
            app=self.app,
            label_text="Samples",
            slider_callback=partial(self.handle_value_change, "generator.n_samples"),
            current_value=self.settings_manager.generator.n_samples,
            slider_maximum=500,
            spinbox_maximum=500.0,
            display_as_float=False,
            spinbox_single_step=1,
            spinbox_page_step=1,
            spinbox_minimum=1,
            slider_minimum=1
        )
        self.current_generator_widget["samples_slider_widget"] = samples_widget

        if self.tab_section not in self.clip_skip_disabled_tabs and self.tab not in self.clip_skip_disabled_sections:
            self.load_clip_skip_slider()

        self.add_widget_to_grid(samples_widget)

        if self.tab_section == "kandinsky":
            # show a checkbox for self.app.variation
            variation_checkbox = QCheckBox("Variation")
            variation_checkbox.setObjectName("variation_checkbox")
            variation_checkbox.setChecked(self.settings_manager.generator.variation)
            variation_checkbox.toggled.connect(
                partial(self.handle_value_change, "variation", widget=variation_checkbox))
            self.add_widget_to_grid(variation_checkbox)

    def add_frames_widgets(self):
        if self.tab != "txt2vid":
            return
        samples_widget = SliderWidget(
            app=self.app,
            label_text="Frames",
            slider_callback=partial(self.handle_value_change, "generator.n_samples"),
            current_value=self.settings_manager.generator.n_samples,
            slider_maximum=200,
            spinbox_maximum=200.0,
            display_as_float=False,
            spinbox_single_step=1,
            spinbox_page_step=1,
            spinbox_minimum=1,
            slider_minimum=1
        )
        self.current_generator_widget["samples_slider_widget"] = samples_widget
        widget = QWidget()
        horizontal_layout = QHBoxLayout(widget)
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.setSpacing(10)
        horizontal_layout.addWidget(samples_widget)
        self.add_widget_to_grid(widget)

    def add_upscale_widgets(self):
        if self.tab_section != "stablediffusion" or self.tab != "upscale":
            return
        scale_slider = self.get_scale_slider(label_text="Input Image Scale")
        self.current_generator_widget.ui.input_image_widget.add_slider_to_scale_frame(scale_slider)

    def add_generate_widgets(self):
        widget_a = QWidget()
        widget_b = QWidget()
        horizontal_layout_a = QFormLayout(widget_a)
        horizontal_layout_b = QHBoxLayout(widget_b)
        horizontal_layout_a.setContentsMargins(0, 0, 0, 0)
        horizontal_layout_a.setSpacing(10)
        horizontal_layout_b.setContentsMargins(0, 0, 0, 0)
        horizontal_layout_b.setSpacing(5)

        interrupt_button = QPushButton("Interrupt")
        interrupt_button.setObjectName("interrupt_button")
        interrupt_button.clicked.connect(self.app.interrupt)
        self.interrupt_button = interrupt_button

        # horizontal_layout_a.addRow(to_canvas_radio, deterministic_radio)
        horizontal_layout_b.addWidget(interrupt_button)
        self.add_widget_to_grid(widget_a)
        self.add_widget_to_grid(widget_b)

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

    def start_progress_bar(self, tab_section, section):
        progressbar = self.find_widget("progress_bar", tab_section, section)
        if not progressbar:
            return
        progressbar.setRange(0, 0)
        self.app.message_var.emit({
            "message": {
                "step": 0,
                "total": 0,
                "action": section,
                "image": None,
                "data": None
            },
            "code": MessageCode.PROGRESS
        })

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

    def set_stylesheet(self):
        # super().set_stylesheet()
        # self.sectionTabWidget.setStyleSheet(self.app.css("section_tab_widget"))
        # self.stableDiffusionTabWidget.setStyleSheet(self.app.css("pipeline"))
        # self.kandinskyTabWidget.setStyleSheet(self.app.css("pipeline"))
        # self.shapegifTabWidget.setStyleSheet(self.app.css("pipeline"))
        pass

        # for tab_section in self.data.keys():
        #     for tab in self.data[tab_section].keys():
        #         if "controlnet_scale_slider" in self.data[tab_section][tab]:
        #             self.data[tab_section][tab]["controlnet_scale_slider"].set_stylesheet()
        #         if "steps_slider_widget" in self.data[tab_section][tab]:
        #             self.data[tab_section][tab]["steps_slider_widget"].set_stylesheet()
        #         if "scale_slider_widget" in self.data[tab_section][tab]:
        #             self.data[tab_section][tab]["scale_slider_widget"].set_stylesheet()
        #         if "samples_slider_widget" in self.data[tab_section][tab]:
        #             self.data[tab_section][tab]["samples_slider_widget"].set_stylesheet()

    def set_prompt(self, prompt):
        self.current_generator_widget.ui.prompt.setPlainText(prompt)

    def set_negative_prompt(self, prompt):
        self.current_generator_widget.ui.negative_prompt.setPlainText(prompt)
