import random
from functools import partial
from PyQt6 import uic
from PyQt6.QtWidgets import QGridLayout
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
        prompt_builder_form_a = PromptBuilderForm(
            app=self.app,
            prompt_builder_widget=self)

        prompt_builder_form_b = PromptBuilderForm(
            app=self.app,
            prompt_builder_widget=self)
        # add to tab
        self.tabs.addTab(prompt_builder_form_a, "Prompt A")
        self.tabs.addTab(prompt_builder_form_b, "Prompt B")


        self.initialize_weight_sliders()
        self.initialize_weights()
        self.app.generate_signal.connect(self.inject_prompt)

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
            # self.advanced_prompt_text.setPlainText("")
            # self.advanced_negative_prompt_text.setPlainText("")
            return

        # get composition values from dropdowns in current tab
        # get widget from current tab
        current_tab = self.tabs.currentWidget()
        if current_tab is None:
            return
        category = self.settings_manager.settings.prompt_generator_category.get()
        image_genre = self.settings_manager.settings.prompt_generator_prompt_genre.get()
        image_color = self.settings_manager.settings.prompt_generator_prompt_color.get()
        image_style = self.settings_manager.settings.prompt_generator_prompt_style.get()
        if category == "" or category is None:
            category = "Random"

        prompt_prefix = self.settings_manager.settings.prompt_generator_prefix.get()
        prompt_suffix = self.settings_manager.settings.prompt_generator_suffix.get()
        negative_prompt_prefix = self.settings_manager.settings.negative_prompt_generator_prefix.get()
        negative_prompt_suffix = self.settings_manager.settings.negative_prompt_generator_suffix.get()

        weighted_variables = self.settings_manager.settings.prompt_generator_weighted_values.get()
        prompt, negative_prompt = self.prompt_data.build_prompts(
            prompt=self.app.prompt,
            negative_prompt=self.app.negative_prompt,
            text_prompt_weight=self.text_prompt_weight,
            auto_prompt_weight=self.auto_prompt_weight,
            prompt_prefix=prompt_prefix,
            prompt_suffix=prompt_suffix,
            negative_prompt_prefix=negative_prompt_prefix,
            negative_prompt_suffix=negative_prompt_suffix,
            negative_text_prompt_weight=self.negative_text_prompt_weight,
            negative_auto_prompt_weight=self.negative_auto_prompt_weight,
            weighted_variables=weighted_variables,
            seed=self.app.seed,
            category=category,
            image_genre=image_genre,
            image_color=image_color,
            image_style=image_style,
            advanced=self.settings_manager.settings.prompt_generator_advanced.get()
        )

        # save processed prompts
        current_tab.advanced_prompt_text.setPlainText(prompt)
        current_tab.advanced_negative_prompt_text.setPlainText(negative_prompt)

    def inject_prompt(self, options):
        """
        Injects the prompts into the options dictionary which is
        passed to the runner.
        :param options:
        :return:
        """
        self.process_prompt()
        if self.app.use_prompt_builder_checkbox:
            options[f"prompt"] = self.advanced_prompt_text.toPlainText()
            options[f"negative_prompt"] = self.advanced_negative_prompt_text.toPlainText()
            options[f"prompt_data"] = self.prompt_data

    def set_stylesheet(self):
        super().set_stylesheet()
        self.tabs.setStyleSheet(self.app.css("prompt_builder_widget"))
