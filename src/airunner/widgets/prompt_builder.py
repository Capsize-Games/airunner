import random

from airunner.aihandler.settings import MAX_SEED
from airunner.data.prompt_data import PromptData
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.prompt_builder_form import PromptBuilderForm


class PromptBuilderWidget(BaseWidget):
    name = "prompt_builder"
    prompt_data = None
    auto_prompt_weight = 0.5
    text_prompt_weight = 0.5
    negative_auto_prompt_weight = 0.5
    negative_text_prompt_weight = 0.5
    prompt_types = None
    unprocessed_prompts = {}
    current_tab = "a"

    @property
    def prompt_generator_category(self):
        if self.current_tab == "a":
            return self.settings_manager.settings.prompt_generator_category_a.get()
        else:
            return self.settings_manager.settings.prompt_generator_category_b.get()

    @prompt_generator_category.setter
    def prompt_generator_category(self, value):
        if self.current_tab == "a":
            self.settings_manager.settings.prompt_generator_category_a.set(value)
        else:
            self.settings_manager.settings.prompt_generator_category_b.set(value)

    @property
    def prompt_generator_prompt(self):
        if self.current_tab == "a":
            return self.settings_manager.settings.prompt_generator_prompt_a.get()
        else:
            return self.settings_manager.settings.prompt_generator_prompt_b.get()

    @prompt_generator_prompt.setter
    def prompt_generator_prompt(self, value):
        if self.current_tab == "a":
            self.settings_manager.settings.prompt_generator_prompt_a.set(value)
        else:
            self.settings_manager.settings.prompt_generator_prompt_b.set(value)

    @property
    def prompt_generator_weighted_values(self):
        if self.current_tab == "a":
            return self.settings_manager.settings.prompt_generator_weighted_values_a.get()
        else:
            return self.settings_manager.settings.prompt_generator_weighted_values_b.get()

    @prompt_generator_weighted_values.setter
    def prompt_generator_weighted_values(self, value):
        if self.current_tab == "a":
            self.settings_manager.settings.prompt_generator_weighted_values_a.set(value)
        else:
            self.settings_manager.settings.prompt_generator_weighted_values_b.set(value)

    @property
    def prompt_generator_prompt_genre(self):
        if self.current_tab == "a":
            return self.settings_manager.settings.prompt_generator_prompt_genre_a.get()
        else:
            return self.settings_manager.settings.prompt_generator_prompt_genre_b.get()

    @prompt_generator_prompt_genre.setter
    def prompt_generator_prompt_genre(self, value):
        if self.current_tab == "a":
            self.settings_manager.settings.prompt_generator_prompt_genre_a.set(value)
        else:
            self.settings_manager.settings.prompt_generator_prompt_genre_b.set(value)

    @property
    def prompt_generator_prompt_color(self):
        if self.current_tab == "a":
            return self.settings_manager.settings.prompt_generator_prompt_color_a.get()
        else:
            return self.settings_manager.settings.prompt_generator_prompt_color_b.get()

    @prompt_generator_prompt_color.setter
    def prompt_generator_prompt_color(self, value):
        if self.current_tab == "a":
            self.settings_manager.settings.prompt_generator_prompt_color_a.set(value)
        else:
            self.settings_manager.settings.prompt_generator_prompt_color_b.set(value)

    @property
    def prompt_generator_prompt_style(self):
        if self.current_tab == "a":
            return self.settings_manager.settings.prompt_generator_prompt_style_a.get()
        else:
            return self.settings_manager.settings.prompt_generator_prompt_style_b.get()

    @prompt_generator_prompt_style.setter
    def prompt_generator_prompt_style(self, value):
        if self.current_tab == "a":
            self.settings_manager.settings.prompt_generator_prompt_style_a.set(value)
        else:
            self.settings_manager.settings.prompt_generator_prompt_style_b.set(value)

    @property
    def prompt_generator_prefix(self):
        if self.current_tab == "a":
            return self.settings_manager.settings.prompt_generator_prefix_a.get()
        else:
            return self.settings_manager.settings.prompt_generator_prefix_b.get()

    @prompt_generator_prefix.setter
    def prompt_generator_prefix(self, value):
        if self.current_tab == "a":
            self.settings_manager.settings.prompt_generator_prefix_a.set(value)
        else:
            self.settings_manager.settings.prompt_generator_prefix_b.set(value)

    @property
    def prompt_generator_suffix(self):
        if self.current_tab == "a":
            return self.settings_manager.settings.prompt_generator_suffix_a.get()
        else:
            return self.settings_manager.settings.prompt_generator_suffix_b.get()

    @prompt_generator_suffix.setter
    def prompt_generator_suffix(self, value):
        if self.current_tab == "a":
            self.settings_manager.settings.prompt_generator_suffix_a.set(value)
        else:
            self.settings_manager.settings.prompt_generator_suffix_b.set(value)

    @property
    def negative_prompt_generator_prefix(self):
        if self.current_tab == "a":
            return self.settings_manager.settings.negative_prompt_generator_prefix_a.get()
        else:
            return self.settings_manager.settings.negative_prompt_generator_prefix_b.get()

    @negative_prompt_generator_prefix.setter
    def negative_prompt_generator_prefix(self, value):
        if self.current_tab == "a":
            self.settings_manager.settings.negative_prompt_generator_prefix_a.set(value)
        else:
            self.settings_manager.settings.negative_prompt_generator_prefix_b.set(value)

    @property
    def negative_prompt_generator_suffix(self):
        if self.current_tab == "a":
            return self.settings_manager.settings.negative_prompt_generator_suffix_a.get()
        else:
            return self.settings_manager.settings.negative_prompt_generator_suffix_b.get()

    @negative_prompt_generator_suffix.setter
    def negative_prompt_generator_suffix(self, value):
        if self.current_tab == "a":
            self.settings_manager.settings.negative_prompt_generator_suffix_a.set(value)
        else:
            self.settings_manager.settings.negative_prompt_generator_suffix_b.set(value)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_stylesheet()
        self.prompt_data = PromptData(file_name="prompts")
        self.initialize_tab_forms()

    def initialize_tab_forms(self):
        """
        Prompt blender allows multiple generated prompts to be blended together.
        This function initializes the tab forms for each prompt blender tab.
        :return:
        """
        self.current_tab = "a"
        self.prompt_builder_form_a = PromptBuilderForm(
            parent=self,
            app=self.app,
            prompt_builder_widget=self)

        self.current_tab = "b"
        self.prompt_builder_form_b = PromptBuilderForm(
            parent=self,
            app=self.app,
            prompt_builder_widget=self)
        self.current_tab = "a"
        # add to tab
        self.tabs.addTab(self.prompt_builder_form_a, "Prompt A")
        self.tabs.addTab(self.prompt_builder_form_b, "Prompt B")
        self.prompt_builder_form_a.initialize_dropdown_values()
        self.prompt_builder_form_b.initialize_dropdown_values()

        # on self.tabs change, update the prompt builder form
        self.tabs.currentChanged.connect(self.handle_tab_changed)

        self.initialize_weight_sliders()
        self.initialize_weights()
        self.app.generate_signal.connect(self.inject_prompt)

        self.prompt_blend_type.setCurrentIndex(self.settings_manager.settings.prompt_blend_type.get())
        self.prompt_blend_type.currentIndexChanged.connect(self.handle_prompt_blend_type_change)
        self.update_blend_sliders()

    def handle_tab_changed(self):
        self.current_tab = "a" if self.tabs.currentIndex() == 0 else "b"
        self.process_prompt()

    def handle_prompt_blend_type_change(self, index):
        self.settings_manager.settings.prompt_blend_type.set(index)
        self.update_blend_sliders()
        self.process_prompt()

    def update_blend_sliders(self):
        if self.settings_manager.settings.prompt_blend_type.get() == 0:
            # disable the blending weight sliders
            self.prompt_weight_distribution_slider.setEnabled(False)
            self.negative_prompt_weight_distribution_slider.setEnabled(False)
        else:
            # enable the blending weight sliders
            self.prompt_weight_distribution_slider.setEnabled(True)
            self.negative_prompt_weight_distribution_slider.setEnabled(True)

    def initialize_weights(self):
        auto_prompt_weight = self.settings_manager.settings.auto_prompt_weight.get()
        auto_negative_prompt_weight = self.settings_manager.settings.negative_auto_prompt_weight.get()
        self.prompt_weight_distribution_slider.setValue(int(auto_prompt_weight * 100))
        self.negative_prompt_weight_distribution_slider.setValue(int(auto_negative_prompt_weight * 100))

    def initialize_weight_sliders(self):
        self.prompt_weight_distribution_slider.valueChanged.connect(
            self.handle_weight_distribution_slider_change)
        self.negative_prompt_weight_distribution_slider.valueChanged.connect(
            self.handle_negative_weight_distribution_slider_change)

    def handle_weight_distribution_slider_change(self, value):
        self.auto_prompt_weight = 0.0 + (value / 100.0)
        self.text_prompt_weight = 1.0 - self.auto_prompt_weight
        self.auto_prompt_weight = round(self.auto_prompt_weight, 2)
        self.text_prompt_weight = round(self.text_prompt_weight, 2)
        self.auto_prompt_weight_label.setText(f"{self.auto_prompt_weight:.2f}")
        self.text_prompt_weight_label.setText(f"{self.text_prompt_weight:.2f}")
        self.settings_manager.settings.auto_prompt_weight.set(self.auto_prompt_weight)
        self.process_prompt()

    def handle_negative_weight_distribution_slider_change(self, value):
        self.negative_auto_prompt_weight = 0.0 + (value / 100.0)
        self.negative_text_prompt_weight = 1.0 - self.negative_auto_prompt_weight
        self.negative_auto_prompt_weight = round(self.negative_auto_prompt_weight, 2)
        self.negative_text_prompt_weight = round(self.negative_text_prompt_weight, 2)
        self.negative_auto_prompt_weight_label.setText(f"{self.negative_auto_prompt_weight:.2f}")
        self.negative_text_prompt_weight_label.setText(f"{self.negative_text_prompt_weight:.2f}")
        self.settings_manager.settings.negative_auto_prompt_weight.set(self.negative_auto_prompt_weight)
        self.process_prompt()

    def process_prompt(self):
        if not self.settings_manager.settings.use_prompt_builder_checkbox.get():
            # self.prompt_text.setPlainText("")
            # self.negative_prompt_text.setPlainText("")
            return

        # get composition values from dropdowns in current tab
        # get widget from current tab
        current_tab = self.tabs.currentWidget()
        if current_tab is None:
            return

        prompt_a = ""
        negative_prompt_a = ""
        seed = self.app.seed if not self.app.seed_override else self.app.seed_override
        if self.settings_manager.settings.prompt_blend_type.get() == 1:
            prompt_a = self.app.prompt
            negative_prompt_a = self.app.negative_prompt
        elif self.settings_manager.settings.prompt_blend_type.get() == 2:
            prev_tab = self.current_tab
            self.current_tab = "b" if prev_tab == "a" else "a"
            prompt_a, negative_prompt_a = self.build_prompts("", "", seed)
            self.current_tab = prev_tab
            random.seed(seed)
            seed = random.randint(0, MAX_SEED)

        prompt, negative_prompt = self.build_prompts(prompt_a, negative_prompt_a, seed)

        # save processed prompts
        current_tab.prompt_text.setPlainText(prompt)
        current_tab.negative_prompt_text.setPlainText(negative_prompt)

    def build_prompts(self, prompt_a="", negative_prompt_a="", seed=None):
        if seed is None:
            seed = self.app.seed if not self.app.seed_override else self.app.seed_override
        category = self.prompt_generator_category
        image_genre = self.prompt_generator_prompt_genre
        image_color = self.prompt_generator_prompt_color
        image_style = self.prompt_generator_prompt_style
        if category == "" or category is None:
            category = "Random"
        prompt_prefix = self.prompt_generator_prefix
        prompt_suffix = self.prompt_generator_suffix
        negative_prompt_prefix = self.negative_prompt_generator_prefix
        negative_prompt_suffix = self.negative_prompt_generator_suffix
        weighted_variables = self.prompt_generator_weighted_values

        return self.prompt_data.build_prompts(
            prompt=prompt_a,
            negative_prompt=negative_prompt_a,
            text_prompt_weight=self.text_prompt_weight,
            auto_prompt_weight=self.auto_prompt_weight,
            prompt_prefix=prompt_prefix,
            prompt_suffix=prompt_suffix,
            negative_prompt_prefix=negative_prompt_prefix,
            negative_prompt_suffix=negative_prompt_suffix,
            negative_text_prompt_weight=self.negative_text_prompt_weight,
            negative_auto_prompt_weight=self.negative_auto_prompt_weight,
            weighted_variables=weighted_variables,
            seed=seed,
            category=category,
            image_genre=image_genre,
            image_color=image_color,
            image_style=image_style,
            advanced=self.settings_manager.settings.prompt_generator_advanced.get()
        )

    def inject_prompt(self, options):
        """
        Injects the prompts into the options dictionary which is
        passed to the runner.
        :param options:
        :return:
        """
        self.process_prompt()
        current_tab = self.tabs.currentWidget()
        if self.app.use_prompt_builder_checkbox:
            options[f"prompt"] = current_tab.prompt_text.toPlainText()
            options[f"negative_prompt"] = current_tab.negative_prompt_text.toPlainText()
            options[f"prompt_data"] = self.prompt_data

    def set_stylesheet(self):
        super().set_stylesheet()
        self.tabs.setStyleSheet(self.app.css("prompt_builder_widget"))
