import re
from functools import partial
from PyQt6.QtWidgets import QWidget, QGridLayout, QPlainTextEdit, QLabel, QComboBox, QHBoxLayout, QRadioButton, \
    QPushButton, QProgressBar, QFormLayout, QCheckBox, QSpinBox, QLineEdit, QGroupBox
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.slider_widget import SliderWidget
from airunner.aihandler.settings import MAX_SEED, AVAILABLE_SCHEDULERS_BY_ACTION
from airunner.aihandler.enums import MessageCode


class GeneratorTabWidget(BaseWidget):
    name = "generator_tab"
    data = {}
    queue_label = None
    clip_skip_disabled_tabs = ["kandinsky", "shapegif"]
    _random_image_embed_seed = False

    @property
    def random_image_embed_seed(self):
        return self._random_image_embed_seed

    @random_image_embed_seed.setter
    def random_image_embed_seed(self, value):
        self._random_image_embed_seed = value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.row = 0
        self.col = 0
        self.layout = None
        self.app.settings_manager.settings.model_base_path.my_signal.connect(self.refresh_model_list)
        # add all tabs
        # get the current tab name and pass it as section
        self.sectionTabWidget.currentChanged.connect(partial(
            self.app.handle_generator_tab_changed
        ))
        for tab_section in self.app._tabs.keys():
            self.force_tab_section(tab_section, None)
            self.data[tab_section] = {}
            for tab in self.app.tabs.keys():
                self.add_tab(section=tab_section, tab=tab)
        self.release_tab_section()

    def clear_prompts(self, tab_section, tab):
        self.data[tab_section][tab]['prompt_widget'].setPlainText("")
        self.data[tab_section][tab]['negative_prompt_widget'].setPlainText("")

    def add_tab(self, section, tab):
        self.app.override_section = tab
        self.data[section][tab] = {}
        tab_section = getattr(
            self,
            f"{'stableDiffusion' if section == 'stablediffusion' else section}TabWidget"
        )
        tab_section.addTab(
            self.generate_form(section, tab),
            "inpaint / outpaint" if tab == "outpaint" else tab
        )
        # on tab change
        tab_section.currentChanged.connect(partial(
            self.app.handle_tab_section_changed
        ))

    def generate_form(self, tab_section, tab):
        self.tab_section = tab_section
        self.tab = tab
        self.force_tab_section(tab_section, tab)
        self.row = 0
        self.col = 0
        self.layout = None
        widget = QWidget(self)
        widget.setStyleSheet("font-size: 9pt;")
        self.layout = QGridLayout(widget)
        self.add_prompt_widgets()
        self.add_zeroshot_widget()
        self.add_model_widgets()
        self.add_scheduler_widgets()
        self.add_seed_widgets()
        self.add_steps_widget()
        self.add_scale_widgets()
        self.add_image_scale_widgets()
        self.add_strength_widgets()
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
        use_prompt_builder_checkbox = QCheckBox()
        use_prompt_builder_checkbox.setObjectName("use_prompt_builder_checkbox")
        use_prompt_builder_checkbox.setText("Use Prompt Builder")
        use_prompt_builder_checkbox.setChecked(self.app.use_prompt_builder_checkbox)
        use_prompt_builder_checkbox.stateChanged.connect(
            partial(self.handle_value_change, "use_prompt_builder_checkbox", widget=use_prompt_builder_checkbox))
        self.data[self.tab_section][self.tab]["use_prompt_builder_checkbox"] = use_prompt_builder_checkbox
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
            horizontal_layout.addWidget(use_prompt_builder_checkbox)
            self.data[self.tab_section][self.tab]["negative_prompt_widget"] = negative_prompt_widget
            self.add_widget_to_grid(negative_label)
            self.add_widget_to_grid(negative_prompt_widget)

    def toggle_all_prompt_builder_checkboxes(self, state):
        for tab_section in self.data.keys():
            for section in self.data[tab_section].keys():
                self.data[tab_section][section]["use_prompt_builder_checkbox"].setChecked(state)

    def refresh_model_list(self):
        for i, section in enumerate(self.app._tabs[self.app.currentTabSection].keys()):
            self.data[self.app.currentTabSection][section]["model_dropdown"].clear()
            self.load_model_by_section(self.app.currentTabSection, section)

    def load_model_by_section(self, tab_section, section):
        models = self.app.application_data.available_model_names(tab_section, section, enabled_only=True)
        self.data[tab_section][section]["model_dropdown"].addItems(models)

    def add_model_widgets(self):
        model_label = QLabel(self)
        model_label.setObjectName("model_label")
        model_label.setText("Model")
        model_widget = QComboBox(self)
        model_widget.setObjectName("model_dropdown")
        model_widget.currentTextChanged.connect(
            partial(self.handle_value_change, "model", widget=model_widget))
        self.data[self.tab_section][self.tab]["model_dropdown"] = model_widget
        current_model = self.app.model
        self.load_model_by_section(self.tab_section, self.tab)
        model_widget.setCurrentText(current_model)
        self.data[self.tab_section][self.tab]["model_dropdown_widget"] = model_widget
        self.add_widget_to_grid(model_label)
        self.add_widget_to_grid(model_widget)

    def update_available_models(self):
        for section in self.data.keys():
            for tab in self.data[section].keys():
                self.data[section][tab]["model_dropdown_widget"].clear()
                self.load_model_by_section(section, tab)

    def add_scheduler_widgets(self):
        scheduler_action = self.tab
        if self.tab_section == "kandinsky":
            scheduler_action = f"kandinsky_{self.tab}"
        elif self.tab_section == "shapegif":
            scheduler_action = f"shapegif_{self.tab}"
        scheduler_label = QLabel(self)
        scheduler_label.setObjectName("scheduler_label")
        scheduler_label.setText("Scheduler")
        scheduler_widget = QComboBox(self)
        scheduler_widget.setObjectName("scheduler_dropdown")
        scheduler_widget.addItems(AVAILABLE_SCHEDULERS_BY_ACTION[scheduler_action])
        scheduler_widget.setCurrentText(self.app.scheduler)
        scheduler_widget.currentTextChanged.connect(
            partial(self.handle_value_change, "scheduler", widget=scheduler_widget))
        self.data[self.tab_section][self.tab]["scheduler_dropdown_widget"] = scheduler_widget
        self.add_widget_to_grid(scheduler_label)
        self.add_widget_to_grid(scheduler_widget)

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

    def add_scale_widgets(self):
        scale_slider = SliderWidget(
            app=self.app,
            label_text="Scale",
            slider_callback=partial(self.handle_value_change, "scale"),
            current_value=int(self.app.scale),
            slider_maximum=10000,
            spinbox_maximum=100.0,
            display_as_float=True,
            spinbox_single_step=0.01,
            spinbox_page_step=0.01
        )
        self.data[self.tab_section][self.tab]["scale_slider_widget"] = scale_slider
        self.add_widget_to_grid(scale_slider)

    def add_image_scale_widgets(self):
        if self.tab in ["txt2img", "img2img", "outpaint", "depth2img", "superresolution", "txt2vid"]:
            return
        image_scale_slider = SliderWidget(
            app=self.app,
            label_text="Image Scale",
            slider_callback=partial(self.handle_value_change, "image_scale"),
            current_value=int(self.app.image_scale),
            slider_maximum=10000,
            spinbox_maximum=100.0,
            display_as_float=True,
            spinbox_single_step=0.01,
            spinbox_page_step=0.01
        )
        self.data[self.tab_section][self.tab]["image_scale_slider"] = image_scale_slider
        self.add_widget_to_grid(image_scale_slider)

    def add_strength_widgets(self):
        if self.tab in ["txt2img", "outpaint", "pix2pix", "upscale", "superresolution", "txt2vid"]:
            return
        strength_slider = SliderWidget(
            app=self.app,
            label_text="Strength",
            slider_callback=partial(self.handle_value_change, "strength"),
            current_value=self.app.strength,
            slider_maximum=100,
            spinbox_maximum=1.0,
            display_as_float=True,
            spinbox_single_step=0.01,
            spinbox_page_step=0.01
        )
        self.data[self.tab_section][self.tab]["strength_slider"] = strength_slider
        self.add_widget_to_grid(strength_slider)

    def add_seed_widgets(self):
        group_box = QGroupBox(self)
        group_box.setObjectName("seed_groupbox")
        group_box.setTitle("Manual Seed")
        group_box.setCheckable(True)
        group_box.setChecked(not self.app.random_seed)
        group_box.toggled.connect(
            partial(self.handle_value_change, "random_seed", widget=group_box))
        grid_layout = QGridLayout(group_box)

        seed_spinbox = QLineEdit(self)
        seed_spinbox.setObjectName("seed_spinbox")
        seed_spinbox.setText(str(self.app.seed))
        seed_spinbox.textChanged.connect(
            partial(self.handle_value_change, "seed", widget=seed_spinbox))

        self.data[self.tab_section][self.tab]["seed"] = seed_spinbox

        grid_layout.addWidget(seed_spinbox)

        self.data[self.tab_section][self.tab]["seed_widget"] = seed_spinbox

        self.add_widget_to_grid(group_box)

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
        interrupt_button = QPushButton("Interrupt")
        interrupt_button.setObjectName("interrupt_button")
        interrupt_button.clicked.connect(self.app.interrupt)
        self.interrupt_button = interrupt_button
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

        if self.tab_section not in self.clip_skip_disabled_tabs:
            self.load_clip_skip_slider()

        self.data[self.tab_section][self.tab]["queue_label"] = QLabel("Items in queue: 0")
        widget = QWidget()
        horizontal_layout = QHBoxLayout(widget)
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.setSpacing(10)
        horizontal_layout.addWidget(samples_widget)
        horizontal_layout.addWidget(interrupt_button)
        self.add_widget_to_grid(widget)
        self.add_widget_to_grid(self.data[self.tab_section][self.tab]["queue_label"])

        if self.tab_section == "kandinsky":
            # show a checkbox for self.app.variation
            variation_checkbox = QCheckBox("Variation")
            variation_checkbox.setObjectName("variation_checkbox")
            variation_checkbox.setChecked(self.app.variation)
            variation_checkbox.toggled.connect(
                partial(self.handle_value_change, "variation", widget=variation_checkbox))
            self.add_widget_to_grid(variation_checkbox)

    def update_queue_label(self):
        for section in self.data.keys():
            for tab in self.data[section].keys():
                try:
                    self.data[section][tab]["queue_label"].setText(f"Items in queue: {self.app.client.queue.qsize()}")
                except KeyError:
                    pass

    def add_zeroshot_widget(self):
        if self.tab != "txt2vid":
            return
        # create a checkbox for zeroshot
        zeroshot_checkbox = QCheckBox("Zero Shot")
        zeroshot_checkbox.setObjectName("zeroshot_checkbox")
        zeroshot_checkbox.setChecked(self.app.zeroshot)
        zeroshot_checkbox.toggled.connect(
            partial(self.handle_value_change, "zeroshot", widget=zeroshot_checkbox))

        self.add_widget_to_grid(zeroshot_checkbox)

    def add_frames_widgets(self):
        if self.tab != "txt2vid":
            return
        interrupt_button = QPushButton("Interrupt")
        interrupt_button.setObjectName("interrupt_button")
        interrupt_button.clicked.connect(self.app.interrupt)
        self.interrupt_button = interrupt_button
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
        horizontal_layout.addWidget(interrupt_button)
        self.add_widget_to_grid(widget)

    def add_upscale_widgets(self):
        pass

    def add_generate_widgets(self):
        widget_a = QWidget()
        widget_b = QWidget()
        horizontal_layout_a = QFormLayout(widget_a)
        horizontal_layout_b = QHBoxLayout(widget_b)
        horizontal_layout_a.setContentsMargins(0, 0, 0, 0)
        horizontal_layout_a.setSpacing(10)
        horizontal_layout_b.setContentsMargins(0, 0, 0, 0)
        horizontal_layout_b.setSpacing(0)
        to_canvas_radio = QRadioButton("Single")
        to_canvas_radio.setChecked(not self.app.deterministic)
        to_canvas_radio.toggled.connect(
            partial(self.handle_value_change, "deterministic", widget=to_canvas_radio, value=False))
        deterministic_radio = QRadioButton("Batch")
        deterministic_radio.setChecked(self.app.deterministic)
        deterministic_radio.toggled.connect(
            partial(self.handle_value_change, "deterministic", widget=deterministic_radio))
        generate_button = QPushButton("Generate")
        generate_button.setObjectName("generate_button")
        progressBar = QProgressBar(self)
        progressBar.setMaximum(100)
        progressBar.setMinimum(0)
        progressBar.setValue(0)
        self.data[self.tab_section][self.tab]["progressBar"] = progressBar
        self.data[self.tab_section][self.tab]["progress_bar_started"] = False
        self.data[self.tab_section][self.tab]["generate_button"] = generate_button

        horizontal_layout_a.addRow(to_canvas_radio, deterministic_radio)
        horizontal_layout_b.addWidget(generate_button)
        horizontal_layout_b.addWidget(progressBar)
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
        print("stop progress bar", tab_section, section)
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

        if attr_name == "zeroshot":
            self.refresh_model_list()

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
                if "image_scale_slider" in self.data[tab_section][tab]:
                    self.data[tab_section][tab]["image_scale_slider"].set_stylesheet()
                if "strength_slider" in self.data[tab_section][tab]:
                    self.data[tab_section][tab]["strength_slider"].set_stylesheet()
                if "samples_slider_widget" in self.data[tab_section][tab]:
                    self.data[tab_section][tab]["samples_slider_widget"].set_stylesheet()

    def set_prompt(self, prompt):
        self.data[self.app.currentTabSection][self.app.current_section]["prompt_widget"].setPlainText(prompt)

    def set_negative_prompt(self, prompt):
        self.data[self.app.currentTabSection][self.app.current_section]["negative_prompt_widget"].setPlainText(prompt)