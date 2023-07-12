import json
import random
import re
from functools import partial
from PyQt6 import uic
from PyQt6.QtWidgets import QVBoxLayout, QGridLayout
from aihandler.prompt_parser import PromptParser
from airunner.build_prompt import BuildPrompt
from airunner.widgets.base_widget import BaseWidget


class PromptBuilderWidget(BaseWidget):
    name = "prompt_builder"
    data = {}
    prompt_variables = {}
    auto_prompt_weight = 0.5
    text_prompt_weight = 0.5
    negative_auto_prompt_weight = 0.5
    negative_text_prompt_weight = 0.5
    advanced_prompts = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.load_data("prompts")
        self.tabs.setStyleSheet(self.app.css("prompt_builder_widget"))
        self.scroll_layout = QGridLayout(self.scrollArea.widget())
        self.initialize_category_dropdowns()
        self.initialize_style_dropdowns()
        self.initialize_dropdown_values()
        self.initialize_buttons()
        self.initialize_radio_buttons()
        self.initialize_weight_sliders()
        self.initialize_weights()

    def initialize_category_dropdowns(self):
        # initialize category dropdowns
        self.categories = list(self.data["categories"].keys())
        self.categories.sort()
        self.advanced_category_current_index = 0
        self.advanced_category.addItems(self.categories)
        self.advanced_category.currentIndexChanged.connect(partial(self.set_prompts, "advanced"))

    def initialize_style_dropdowns(self):
        # initialize style dropdowns
        styles = []
        for style_category in self.data["styles"].keys():
            styles += self.data["styles"][style_category]["styles"]
        self.styles = styles
        self.styles.sort()
        self.advanced_style.addItems(self.styles)
        self.advanced_style.currentIndexChanged.connect(partial(self.set_style, "advanced"))

    def initialize_weights(self):
        auto_prompt_weight = self.settings_manager.settings.auto_prompt_weight.get()
        auto_negative_prompt_weight = self.settings_manager.settings.negative_auto_prompt_weight.get()
        self.prompt_weight_distribution_slider.setValue(int(auto_prompt_weight * 100))
        self.negative_prompt_weight_distribution_slider.setValue(int(auto_negative_prompt_weight * 100))

    def initialize_dropdown_values(self):
        # check for index in
        advanced_category = self.settings_manager.settings.prompt_generator_advanced_category.get()
        advanced_style = self.settings_manager.settings.prompt_generator_advanced_style.get()
        advanced_prompt = self.settings_manager.settings.prompt_generator_advanced_prompt.get()

        # initialize dropdown values
        advanced_category_index = self.advanced_category.findText(advanced_category)
        advanced_style_index = self.advanced_style.findText(advanced_style)
        self.advanced_category.setCurrentIndex(advanced_category_index)

        advanced_prompt_index = self.advanced_prompt.findText(advanced_prompt)
        self.advanced_prompt.setCurrentIndex(advanced_prompt_index)

        self.advanced_style.setCurrentIndex(advanced_style_index)

    def initialize_buttons(self):
        # initialize buttons
        self.randomize_values_button.clicked.connect(self.randomize_values)
        self.values_to_random_button.clicked.connect(self.values_to_random)
        self.reset_weights_button.clicked.connect(self.reset_weights)
        self.clear_values_button.clicked.connect(self.clear_values)
        self.set_prompts("advanced")

    def initialize_radio_buttons(self):
        self.basic_radio.setChecked(self.settings_manager.settings.prompt_generator_advanced.get() == False)
        self.advanced_radio.setChecked(self.settings_manager.settings.prompt_generator_advanced.get() == True)
        self.basic_radio.toggled.connect(self.handle_advanced_basic_radio_change)
        self.advanced_radio.toggled.connect(self.handle_advanced_basic_radio_change)

    def initialize_weight_sliders(self):
        self.prompt_weight_distribution_slider.valueChanged.connect(
            self.handle_weight_distribution_slider_change)
        self.negative_prompt_weight_distribution_slider.valueChanged.connect(
            self.handle_negative_weight_distribution_slider_change)
        self.app.generate_signal.connect(self.inject_prompt)

    def handle_advanced_basic_radio_change(self):
        self.app.settings_manager.settings.prompt_generator_advanced.set(self.advanced_radio.isChecked())
        if self.advanced_radio.isChecked():
            self.scrollArea.show()
        else:
            self.scrollArea.hide()
        self.process_prompt()

    def randomize_values(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.combobox.setCurrentIndex(random.randrange(0, widget.combobox.count()))

    def values_to_random(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.combobox.setCurrentIndex(1)

    def clear_values(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.combobox.setCurrentIndex(0)

    def reset_weights(self):
        category = self.advanced_category.currentText()
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                variable = widget.groupbox.title().lower()
                try:
                    weight = self.data["categories"][category]["weights"][variable]
                    widget.spinbox.setValue(weight)
                except Exception as e:
                    print(e)

    def clear_scroll_grid(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def populate_prompt_widgets(self, category):
        # clear items from self.scroll_grid
        self.clear_scroll_grid()
        data = self.settings_manager.settings.prompt_generator_weighted_values.get()
        try:
            for index, variable in enumerate(self.data["categories"][category]["variables"].keys()):
                if category in data and variable in data[category]:
                    weighted_value = data[category][variable]
                else:
                    weighted_value = {
                        "value": "",
                        "weight": self.data["categories"][category]["weights"][variable]
                    }
                self.create_prompt_widget(category, variable, weighted_value, index)
        except KeyError:
            pass
        # self.scroll_layout.layout().addStretch()

    def create_prompt_widget(self, category, variable, weighted_value, index):
        widget = uic.loadUi(f"pyqt/widgets/prompt_builder_variable_widget.ui")
        widget.label.setText(variable.capitalize())

        # set default weights
        weight = weighted_value["weight"]
        widget.spinbox.setValue(weight)
        widget.spinbox.valueChanged.connect(partial(
            self.handle_weight_spinbox_change, category, variable, widget))
        items = self.data["categories"][category]["variables"][variable]
        if isinstance(items, dict):
            if items["type"] == "range":
                items = [str(n) for n in range(items["min"], items["max"] + 1)]
                self.data["categories"][category]["variables"][variable] = items
        else:
            items.sort()
        # do not scroll the slider on mouse wheel, instead scroll the scroll area
        widget.combobox.addItems(["", "Random"] + items)
        try:
            widget.combobox.setCurrentText(weighted_value["value"])
        except Exception as e:
            pass
        widget.combobox.currentIndexChanged.connect(partial(
            self.handle_combobox_change, category, variable, widget))
        self.scroll_layout.layout().addWidget(widget, index // 2, index % 2, 1, 1)

    def weighted_values(self, category, variable):
        data = self.settings_manager.settings.prompt_generator_weighted_values.get()
        if category not in data:
            data[category] = {}
        if variable not in data[category]:
            data[category][variable] = {}
        return data

    def handle_combobox_change(self, category, variable, widget):
        data = self.weighted_values(category, variable)
        value = widget.combobox.currentText()
        data[category][variable]["value"] = value
        data[category][variable]["weight"] = self.data["categories"][category]["weights"][variable]
        self.settings_manager.settings.prompt_generator_weighted_values.set(data)
        self.process_prompt()

    def handle_weight_spinbox_change(self, category, variable, widget, value):
        data = self.weighted_values(category, variable)
        self.update_weight_slider(category, variable, widget)
        data[category][variable]["weight"] = value

    def update_weight_spinbox(self, category, variable, widget):
        data = self.weighted_values(category, variable)
        widget.spinbox.setValue(data[category][variable]["weight"])
        self.process_prompt()

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
            return
        if not self.advanced_prompts:
            return

        prompt = self.app.prompt
        negative_prompt = self.app.negative_prompt

        category = self.categories[self.advanced_category.currentIndex()]
        if category == "" or category is None:
            return

        prompt_type = self.advanced_prompts[self.advanced_prompt.currentIndex()]
        if prompt_type == "" or prompt_type is None:
            return

        image_style = self.styles[self.advanced_style.currentIndex()]
        if image_style == "" or image_style is None:
            return

        weighted_variables = self.settings_manager.settings.prompt_generator_weighted_values.get()
        if category in weighted_variables:
            weighted_variables = weighted_variables[category]

        styles = self.styles.copy()
        variables = self.data["categories"][category]["variables"].copy()
        variables["image_style"] = styles if image_style in ["", "Random"] else [image_style]

        if not self.settings_manager.settings.prompt_generator_advanced.get():
            generated_prompt = self.data["categories"][category]["prompts"][prompt_type]
        else:
            # iterate over each widget in the scroll area
            # and force the value of each variable to whatever is set
            # in the combobox for that variable.
            for i in range(self.scroll_layout.count()):
                widget = self.scroll_layout.itemAt(i).widget()
                if widget:
                    variable = widget.label.text().lower()
                    value = widget.combobox.currentText()
                    if variable in variables:
                        if value == "":
                            del variables[variable]
                        elif value != "Random":
                            variables[variable] = [value]
            generated_prompt = BuildPrompt.build_prompt(
                conditionals=self.data["categories"][category]["builder"],
                image_style=image_style,
                vars=variables,
                category=category
            )

        # get prompt vs generated prompt weights for prompt and negative prompt
        text_weight = self.text_prompt_weight
        auto_weight = self.auto_prompt_weight
        negative_text_weight = self.negative_text_prompt_weight
        negative_auto_weight = self.negative_auto_prompt_weight

        # combine prompt_variables with variables
        # and pass to PromptParser.parse
        variables = {**self.prompt_variables, **variables}

        # clean the generated_prompt before parsing
        generated_prompt = generated_prompt.strip()
        generated_prompt.replace("( ", "(")

        # build the negative prompt
        negative_prompt_style_prefix = ""
        for style_category in self.data["styles"].keys():
            if image_style in self.data["styles"][style_category]["styles"]:
                negative_prompt_style_prefix = self.data["styles"][style_category]["negative_prompt"]
                break
        generated_negative_prompt = self.data["categories"][category]["negative_prompt"]
        generated_negative_prompt = f"{negative_prompt_style_prefix} {generated_negative_prompt}"

        # parse twice for $$ double variables
        for n in range(2):
            if prompt != "" and text_weight > 0:
                prompt = PromptParser.parse(
                    variables=variables,
                    prompt_type=category,
                    prompt=prompt,
                    weights=weighted_variables,
                    seed=self.app.seed)
            if negative_prompt != "" and negative_text_weight > 0:
                negative_prompt = PromptParser.parse(
                    variables=self.prompt_variables,
                    prompt_type=category,
                    prompt=negative_prompt,
                    weights=weighted_variables,
                    seed=self.app.seed)
            if generated_prompt != "" and auto_weight > 0:
                generated_prompt = PromptParser.parse(
                    variables=variables,
                    prompt_type=category,
                    prompt=generated_prompt,
                    weights=weighted_variables,
                    seed=self.app.seed)
            if generated_negative_prompt != "" and negative_auto_weight > 0:
                generated_negative_prompt = PromptParser.parse(
                    variables=variables,
                    prompt_type=category,
                    prompt=generated_negative_prompt,
                    weights=weighted_variables,
                    seed=self.app.seed)

        # trim prompts
        prompt = prompt.strip()
        negative_prompt = negative_prompt.strip()
        generated_prompt = generated_prompt.strip()
        generated_negative_prompt = generated_negative_prompt.strip()

        if prompt != "" and text_weight > 0 and auto_weight > 0:
            prompt = f'("{prompt}", "{generated_prompt}").blend({text_weight:.2f}, {auto_weight:.2f})'
        elif text_weight == 0 or prompt == "":
            prompt = generated_prompt

        if negative_prompt != "" and negative_text_weight > 0 and negative_auto_weight > 0:
            negative_prompt = f'("{negative_prompt}", "{generated_negative_prompt}").blend({negative_text_weight:.2f}, {negative_auto_weight:.2f})'
        elif negative_text_weight == 0 or negative_prompt == "":
            negative_prompt = generated_negative_prompt

        self.advanced_prompt_text.setPlainText(prompt)
        self.advanced_negative_prompt_text.setPlainText(negative_prompt)

    def inject_prompt(self, options):
        self.process_prompt()
        if self.app.use_prompt_builder_checkbox:
            options[f"{self.app.action}_prompt"] = self.advanced_prompt_text.toPlainText()
            options[f"{self.app.action}_negative_prompt"] = self.advanced_negative_prompt_text.toPlainText()

    def set_prompts(self, prompt_type):
        category = self.advanced_category.currentText()
        try:
            prompts = list(self.data["categories"][category]["prompts"].keys())
        except KeyError:
            prompts = []
        self.advanced_prompt.clear()
        self.advanced_prompt.addItems(prompts)
        self.advanced_prompts = prompts
        self.settings_manager.settings.prompt_generator_advanced_category.set(category)
        try:
            self.settings_manager.settings.prompt_generator_advanced_prompt.set(prompts[0])
        except IndexError:
            pass
        if prompt_type == "advanced":
            self.populate_prompt_widgets(category)
        self.process_prompt()

    def load_data(self, file_name):
        file = f"data/{file_name}.json"
        with open(file, "r") as f:
            data = json.load(f)
            self.data = data
            self.prompt_variables = self.data["extra_variables"]
            self.prompt_variables["age"] = [str(n) for n in range(18, 100)]

    def set_style(self, style_type):
        self.settings_manager.settings.prompt_generator_advanced_style.set(
            self.advanced_style.currentText())
        self.process_prompt()
