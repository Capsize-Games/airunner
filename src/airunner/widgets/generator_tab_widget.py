import os
import re
from functools import partial

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QGridLayout, QPlainTextEdit, QLabel, QHBoxLayout, \
    QPushButton, QProgressBar, QFormLayout, QCheckBox

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.controlnet_settings_widget import ControlNetSettingsWidget
from airunner.widgets.input_image_settings_widget import InputImageSettingsWidget
from airunner.widgets.seed_widget import SeedWidget, LatentsSeedWidget
from airunner.widgets.slider_widget import SliderWidget
from airunner.aihandler.settings import MAX_SEED, AVAILABLE_SCHEDULERS_BY_ACTION
from airunner.aihandler.enums import MessageCode


class GeneratorTabWidget(BaseWidget):
    name = "generator_tab"
    data = {}
    clip_skip_disabled_tabs = ["kandinsky", "shapegif"]
    clip_skip_disabled_sections = ["upscale", "superresolution", "txt2vid"]
    _random_image_embed_seed = False

    @property
    def random_image_embed_seed(self):
        return self._random_image_embed_seed

    @random_image_embed_seed.setter
    def random_image_embed_seed(self, value):
        self._random_image_embed_seed = value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self):
        self.row = 0
        self.col = 0
        self.layout = None
        self.app.settings_manager.disable_save()
        self.app.settings_manager.settings.model_base_path.my_signal.connect(self.refresh_model_list)
        # add all tabs
        # get the current tab name and pass it as section
        for tab_section in self.app._tabs.keys():
            self.force_tab_section(tab_section, None)
            self.data[tab_section] = {}
            for tab in self.app.tabs.keys():
                self.add_tab(section=tab_section, tab=tab)
        self.release_tab_section()
        self.set_tabs()
        self.sectionTabWidget.currentChanged.connect(partial(
            self.handle_generator_tab_changed
        ))
        self.app.settings_manager.enable_save()

    def clear_prompts(self, tab_section, tab):
        self.data[tab_section][tab]["prompt_widget"].setPlainText("")
        if "negative_prompt_widget" in self.data[tab_section][tab]:
            self.data[tab_section][tab]["negative_prompt_widget"].setPlainText("")

    def add_tab(self, section, tab):
        self.app.override_section = tab
        self.data[section][tab] = {}
        tab_section = getattr(
            self,
            f"{'stableDiffusion' if section == 'stablediffusion' else section}TabWidget"
        )
        tab_name = tab
        if tab_name == "outpaint":
            tab_name = "inpaint / outpaint"
        elif tab_name == "txt2img":
            tab_name = "txt2img / img2img"
        tab_section.addTab(
            self.generate_form(section, tab),
            tab_name
        )
        # on tab change
        tab_section.currentChanged.connect(partial(
            self.handle_tab_section_changed
        ))

    def handle_tab_section_changed(self):
        self.app.update()
        self.app.enable_embeddings()
        self.app.current_section_by_tab = self.app.current_section

    def handle_generator_tab_changed(self):
        self.app.update()
        self.app.enable_embeddings()
        self.app.settings_manager.settings.current_tab.set(self.app.currentTabSection)
        self.set_current_section_tab()

    def set_tabs(self):
        # get the tab section index
        tab_section_index = None
        current_tab = self.app.settings_manager.settings.current_tab.get()
        tabs = self.app._tabs.keys()
        if current_tab in list(tabs):
            tab_section_index = list(tabs).index(current_tab)
        if tab_section_index:
            self.sectionTabWidget.setCurrentIndex(tab_section_index)

        self.set_current_section_tab()

    def set_current_section_tab(self):
        current_tab = self.app.settings_manager.settings.current_tab.get()
        # get the section index
        section_index = None
        current_section = self.app.current_section_by_tab
        sections = self.app._tabs[current_tab].keys()
        if current_section in list(sections):
            section_index = list(sections).index(current_section)

        if section_index:
            if current_tab == "stablediffusion":
                tab_section = self.stableDiffusionTabWidget
            elif current_tab == "kandinsky":
                tab_section = self.kandinskyTabWidget
            elif current_tab == "shapegif":
                tab_section = self.shapegifTabWidget
            else:
                tab_section = None
            if tab_section:
                tab_section.setCurrentIndex(section_index)

    @property
    def current_input_image_widget(self):
        return self.current_section_data["input_image_widget"]

    @property
    def current_input_image(self):
        if self.app.enable_input_image:
            return self.current_input_image_widget.current_input_image
        return None

    @property
    def controlnet_settings_widget(self):
        return self.current_section_data.get("controlnet_settings_widget", None)

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

    def update_controlnet_thumbnail(self):
        if self.controlnet_settings_widget:
            self.controlnet_settings_widget.set_thumbnail()

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
        self.add_optional_tool_checkbox_widgets()
        self.add_input_image_widgets()
        self.add_controlnet_settings_widget(tab_section, tab)
        self.add_model_scheduler_widgets()
        self.add_seed_widgets()
        self.add_steps_widget()
        self.add_scale_widgets()
        self.add_upscale_widgets()
        self.add_samples_widgets()
        self.add_frames_widgets()
        self.add_generate_widgets()
        self.release_tab_section()
        return widget

    def add_prompt_widgets(self):
        prompt_label_container = QWidget(self)
        horizontal_layout = QHBoxLayout(prompt_label_container)
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        prompt_label = QLabel(self)
        prompt_label.setObjectName("prompt_label")
        prompt_label.setText("Prompt")

        prompt_widget = QPlainTextEdit(self)
        prompt_widget.setObjectName("prompt")
        prompt_widget.setPlainText(self.app.prompt)
        prompt_widget.textChanged.connect(
            partial(self.handle_value_change, "prompt", widget=prompt_widget))
        horizontal_layout.addWidget(prompt_label)
        self.data[self.tab_section][self.tab]["prompt_widget"] = prompt_widget
        self.add_widget_to_grid(prompt_label_container)
        self.add_widget_to_grid(prompt_widget)

        if self.app.currentTabSection != "shapegif":
            negative_label = QLabel(self)
            negative_label.setObjectName("negative_prompt_label")
            negative_label.setText("Negative Prompt")
            negative_prompt_widget = QPlainTextEdit(self)
            negative_prompt_widget.setObjectName("negative_prompt")
            negative_prompt_widget.setPlainText(self.app.negative_prompt)
            negative_prompt_widget.textChanged.connect(
                partial(self.handle_value_change, "negative_prompt", widget=negative_prompt_widget))
            self.data[self.tab_section][self.tab]["negative_prompt_widget"] = negative_prompt_widget
            self.add_widget_to_grid(negative_label)
            self.add_widget_to_grid(negative_prompt_widget)

    def add_optional_tool_checkbox_widgets(self):
        if self.app.currentTabSection in ["shapegif"]:
            return

        stylesheet = "font-size: 8pt;"

        # checkbox horizontal layout
        checkbox_widget = QWidget(self)
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        checkbox_layout.setSpacing(5)
        checkbox_widget.setLayout(checkbox_layout)

        # use prompt builder checkbox
        use_prompt_builder_checkbox = QCheckBox()
        use_prompt_builder_checkbox.setStyleSheet(stylesheet)
        use_prompt_builder_checkbox.setObjectName("use_prompt_builder_checkbox")
        use_prompt_builder_checkbox.setText("Prompt Builder")
        use_prompt_builder_checkbox.setChecked(self.app.use_prompt_builder_checkbox)
        use_prompt_builder_checkbox.stateChanged.connect(
            partial(self.handle_value_change, "use_prompt_builder_checkbox", widget=use_prompt_builder_checkbox))
        self.data[self.tab_section][self.tab]["use_prompt_builder_checkbox"] = use_prompt_builder_checkbox
        self.add_widget_to_grid(use_prompt_builder_checkbox)
        checkbox_layout.addWidget(use_prompt_builder_checkbox)

        # add the checkbox layout to the grid
        self.add_widget_to_grid(checkbox_widget)

    @property
    def use_controlnet_checkbox(self):
        if "use_controlnet_checkbox" not in self.current_section_data:
            return None
        return self.current_section_data["use_controlnet_checkbox"]

    def add_input_image_widgets(self):
        if self.app.current_section in ["txt2vid"]:
            return
        input_image_widget = InputImageSettingsWidget(app=self.app)
        self.data[self.tab_section][self.tab]["input_image_widget"] = input_image_widget
        self.add_widget_to_grid(input_image_widget)

        self.data[self.tab_section][self.tab]["is_using_grid_input_image"] = True

    @property
    def is_using_grid_input_image(self):
        return self.data[self.tab_section][self.tab]["is_using_grid_input_image"]

    @property
    def input_image(self):
        if "input_image" in self.data[self.tab_section][self.tab]:
            return self.data[self.tab_section][self.tab]["input_image"]
        return None

    def toggle_all_prompt_builder_checkboxes(self, state):
        for tab_section in self.data.keys():
            for section in self.data[tab_section].keys():
                try:
                    self.data[tab_section][section]["use_prompt_builder_checkbox"].setChecked(state)
                except KeyError:
                    pass

    def refresh_model_list(self):
        for i, section in enumerate(self.app._tabs[self.app.currentTabSection].keys()):
            self.data[self.app.currentTabSection][section]["model_dropdown_widget"].clear()
            self.load_model_by_section(self.app.currentTabSection, section)

    def load_model_by_section(self, tab_section, section):
        requested_section = "txt2img" if section == "txt2vid" else section
        models = self.app.application_data.available_model_names(tab_section, requested_section, enabled_only=True)
        self.data[tab_section][section]["model_dropdown_widget"].addItems(models)

    def add_controlnet_settings_widget(self, tab_section, tab):
        if tab_section not in ["kandinsky", "shapegif"] and tab in ["txt2img", "img2img", "outpaint", "txt2vid"]:
            controlnet_settings_widget = ControlNetSettingsWidget(app=self.app)
            self.data[self.tab_section][self.tab]["controlnet_settings_widget"] = controlnet_settings_widget
            self.add_widget_to_grid(controlnet_settings_widget)

    def add_model_scheduler_widgets(self):
        widget = uic.loadUi(os.path.join(f"pyqt/widgets/model_scheduler_widget.ui"))
        model_dropdown = widget.model_dropdown

        scheduler_dropdown = widget.scheduler_dropdown
        scheduler_action = self.tab
        if self.tab_section == "kandinsky":
            scheduler_action = f"kandinsky_{self.tab}"
        elif self.tab_section == "shapegif":
            scheduler_action = f"shapegif_{self.tab}"
        scheduler_dropdown.addItems(AVAILABLE_SCHEDULERS_BY_ACTION[scheduler_action])
        scheduler_dropdown.setCurrentText(self.app.scheduler)
        scheduler_dropdown.currentTextChanged.connect(
            partial(self.handle_value_change, "scheduler", widget=scheduler_dropdown))

        self.data[self.tab_section][self.tab]["model_dropdown_widget"] = model_dropdown
        self.data[self.tab_section][self.tab]["scheduler_dropdown_widget"] = scheduler_dropdown

        self.load_model_by_section(self.tab_section, self.tab)

        current_model = self.app.model
        model_dropdown.setCurrentText(current_model)
        model_dropdown.currentTextChanged.connect(
            partial(self.handle_value_change, "model", widget=model_dropdown))

        self.add_widget_to_grid(widget)

    def update_available_models(self):
        for section in self.data.keys():
            for tab in self.data[section].keys():
                self.data[section][tab]["model_dropdown_widget"].clear()
                self.load_model_by_section(section, tab)

    def add_steps_widget(self):
        steps_slider = SliderWidget(
            app=self.app,
            label_text="Steps",
            slider_callback=partial(self.handle_value_change, "steps"),
            current_value=int(self.app.steps),
            slider_maximum=200,
            spinbox_maximum=200.0,
            display_as_float=False,
            spinbox_single_step=1,
            spinbox_page_step=1,
            spinbox_minimum=1,
            slider_minimum=1
        )
        self.data[self.tab_section][self.tab]["steps_slider_widget"] = steps_slider
        self.add_widget_to_grid(steps_slider)

    def get_scale_slider(self, label_text="Scale"):
        return SliderWidget(
            app=self.app,
            label_text=label_text,
            slider_callback=partial(self.handle_value_change, "scale"),
            current_value=int(self.app.scale),
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
        self.data[self.tab_section][self.tab]["scale_slider_widget"] = scale_slider
        self.add_widget_to_grid(scale_slider)

    @property
    def current_section_data(self):
        return self.data[self.app.currentTabSection][self.app.current_section]

    def update_seed(self):
        self.current_section_data["seed_widget"].update_seed()
        self.current_section_data["seed_widget_latents"].update_seed()

    def add_seed_widgets(self):
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setLayout(hbox)

        seed_widget = SeedWidget(app=self.app)
        seed_widget_latents = LatentsSeedWidget(app=self.app)
        hbox.addWidget(seed_widget)
        hbox.addWidget(seed_widget_latents)

        self.add_widget_to_grid(container)
        self.data[self.tab_section][self.tab]["seed_widget"] = seed_widget
        self.data[self.tab_section][self.tab]["seed_widget_latents"] = seed_widget_latents

    def load_clip_skip_slider(self):
        """
        The following block will load the clip skip slider for any tab
        that is not kandinsky or shapegif (essentially just stablediffusion tab)
        """
        clip_skip_widget = SliderWidget(
            app=self.app,
            label_text="Clip Skip",
            slider_callback=partial(self.handle_value_change, "clip_skip"),
            current_value=self.app.clip_skip,
            slider_maximum=11,
            spinbox_maximum=12.0,
            display_as_float=False,
            spinbox_single_step=1,
            spinbox_page_step=1,
            spinbox_minimum=0,
            slider_minimum=0
        )
        self.data[self.tab_section][self.tab]["clip_skip_slider_widget"] = clip_skip_widget
        self.add_widget_to_grid(clip_skip_widget)

    def add_samples_widgets(self):
        if self.tab == "txt2vid":
            return
        samples_widget = SliderWidget(
            app=self.app,
            label_text="Samples",
            slider_callback=partial(self.handle_value_change, "samples"),
            current_value=self.app.samples,
            slider_maximum=500,
            spinbox_maximum=500.0,
            display_as_float=False,
            spinbox_single_step=1,
            spinbox_page_step=1,
            spinbox_minimum=1,
            slider_minimum=1
        )
        self.data[self.tab_section][self.tab]["samples_slider_widget"] = samples_widget

        if self.tab_section not in self.clip_skip_disabled_tabs and self.tab not in self.clip_skip_disabled_sections:
            self.load_clip_skip_slider()

        self.add_widget_to_grid(samples_widget)

        if self.tab_section == "kandinsky":
            # show a checkbox for self.app.variation
            variation_checkbox = QCheckBox("Variation")
            variation_checkbox.setObjectName("variation_checkbox")
            variation_checkbox.setChecked(self.app.variation)
            variation_checkbox.toggled.connect(
                partial(self.handle_value_change, "variation", widget=variation_checkbox))
            self.add_widget_to_grid(variation_checkbox)

    def add_frames_widgets(self):
        if self.tab != "txt2vid":
            return
        samples_widget = SliderWidget(
            app=self.app,
            label_text="Frames",
            slider_callback=partial(self.handle_value_change, "samples"),
            current_value=self.app.samples,
            slider_maximum=200,
            spinbox_maximum=200.0,
            display_as_float=False,
            spinbox_single_step=1,
            spinbox_page_step=1,
            spinbox_minimum=1,
            slider_minimum=1
        )
        self.data[self.tab_section][self.tab]["samples_slider_widget"] = samples_widget
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
        self.data[self.tab_section][self.tab]["input_image_widget"].add_slider_to_scale_frame(scale_slider)

    def add_generate_widgets(self):
        widget_a = QWidget()
        widget_b = QWidget()
        horizontal_layout_a = QFormLayout(widget_a)
        horizontal_layout_b = QHBoxLayout(widget_b)
        horizontal_layout_a.setContentsMargins(0, 0, 0, 0)
        horizontal_layout_a.setSpacing(10)
        horizontal_layout_b.setContentsMargins(0, 0, 0, 0)
        horizontal_layout_b.setSpacing(5)
        generate_button = QPushButton("Generate")
        generate_button.setObjectName("generate_button")
        progressBar = QProgressBar(self)
        progressBar.setMaximum(100)
        progressBar.setMinimum(0)
        progressBar.setValue(0)
        self.data[self.tab_section][self.tab]["progressBar"] = progressBar
        self.data[self.tab_section][self.tab]["progress_bar_started"] = False
        self.data[self.tab_section][self.tab]["generate_button"] = generate_button

        interrupt_button = QPushButton("Interrupt")
        interrupt_button.setObjectName("interrupt_button")
        interrupt_button.clicked.connect(self.app.interrupt)
        self.interrupt_button = interrupt_button

        # horizontal_layout_a.addRow(to_canvas_radio, deterministic_radio)
        horizontal_layout_b.addWidget(generate_button)
        horizontal_layout_b.addWidget(progressBar)
        horizontal_layout_b.addWidget(interrupt_button)
        self.add_widget_to_grid(widget_a)
        self.add_widget_to_grid(widget_b)
        generate_button.clicked.connect(partial(self.app.generate, progressBar))

    def set_progress_bar_value(self, tab_section, section, value):
        # check if progressbar in stablediffusion is running
        try:
            progressbar = self.data[tab_section][section]["progressBar"]
        except KeyError:
            progressbar = None
        if not progressbar:
            return
        if progressbar.maximum() == 0:
            progressbar.setRange(0, 100)
        progressbar.setValue(value)

    def stop_progress_bar(self, tab_section, section):
        try:
            progressbar = self.data[tab_section][section]["progressBar"]
        except KeyError:
            progressbar = None
        if not progressbar:
            print("failed to find progress bar")
            return
        progressbar.setRange(0, 100)
        progressbar.setValue(100)
        self.data[tab_section][section]["progress_bar_started"] = False

    def start_progress_bar(self, tab_section, section):
        if self.data[tab_section][section]["progress_bar_started"]:
            return
        self.data[tab_section][section]["progress_bar_started"] = True
        self.data[tab_section][section]["tqdm_callback_triggered"] = False
        self.data[tab_section][section]["progressBar"].setRange(0, 0)
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
        self.app.override_tab_section = tab_section
        self.app.override_section = tab

    def release_tab_section(self):
        self.app.override_tab_section = None
        self.app.override_section = None

    def handle_value_change(self, attr_name, value=None, widget=None):
        attr = getattr(self.app, f"{attr_name}_var")

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
            widget.setText(str(value))
        elif attr_name == "controlnet":
            value = value.lower()

        if value is not None:
            attr.set(value)
        else:
            try:
                attr.set(widget.toPlainText())
            except AttributeError:
                try:
                    attr.set(widget.currentText())
                except AttributeError:
                    try:
                        attr.set(widget.value())
                    except AttributeError:
                        print("something went wrong while setting the value")

    def set_stylesheet(self):
        super().set_stylesheet()
        self.sectionTabWidget.setStyleSheet(self.app.css("section_tab_widget"))
        self.stableDiffusionTabWidget.setStyleSheet(self.app.css("pipeline"))
        self.kandinskyTabWidget.setStyleSheet(self.app.css("pipeline"))
        self.shapegifTabWidget.setStyleSheet(self.app.css("pipeline"))

        for tab_section in self.data.keys():
            for tab in self.data[tab_section].keys():
                if "controlnet_scale_slider" in self.data[tab_section][tab]:
                    self.data[tab_section][tab]["controlnet_scale_slider"].set_stylesheet()
                if "steps_slider_widget" in self.data[tab_section][tab]:
                    self.data[tab_section][tab]["steps_slider_widget"].set_stylesheet()
                if "scale_slider_widget" in self.data[tab_section][tab]:
                    self.data[tab_section][tab]["scale_slider_widget"].set_stylesheet()
                if "samples_slider_widget" in self.data[tab_section][tab]:
                    self.data[tab_section][tab]["samples_slider_widget"].set_stylesheet()

    def set_prompt(self, prompt):
        self.current_section_data["prompt_widget"].setPlainText(prompt)

    def set_negative_prompt(self, prompt):
        self.current_section_data["negative_prompt_widget"].setPlainText(prompt)