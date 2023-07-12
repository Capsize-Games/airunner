import json
import random
import re
from functools import partial
from PyQt6 import uic
from PyQt6.QtWidgets import QVBoxLayout, QGridLayout
from aihandler.prompt_parser import PromptParser
from airunner.widgets.base_widget import BaseWidget


class PromptBuilderWidget(BaseWidget):
    name = "prompt_builder"
    data = {}
    prompt_variables = {}
    auto_prompt_weight = 0.5
    text_prompt_weight = 0.5
    negative_auto_prompt_weight = 0.5
    negative_text_prompt_weight = 0.5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # remove border of tab container
        self.tabs.setStyleSheet(self.app.css("prompt_builder_widget"))

        # load data
        self.data = self.load_data("prompts")
        self.prompt_variables = self.load_data("prompt_variables")
        self.prompt_variables["age"] = [str(n) for n in range(18, 100)]

        self.scroll_layout = QVBoxLayout(self.scrollArea.widget())

        # initialize category dropdowns
        self.categories = list(self.data["categories"].keys())
        self.categories.sort()
        self.basic_category_current_index = 0
        self.advanced_category_current_index = 0
        self.basic_category.addItems(self.categories)
        self.advanced_category.addItems(self.categories)
        self.basic_category.currentIndexChanged.connect(partial(self.set_prompts, "basic"))
        self.advanced_category.currentIndexChanged.connect(partial(self.set_prompts, "advanced"))

        # initialize style dropdowns
        self.styles = self.data["styles"]
        self.styles.sort()
        self.basic_style.addItems(self.styles)
        self.advanced_style.addItems(self.styles)
        self.basic_style.currentIndexChanged.connect(partial(self.set_style, "basic"))
        self.advanced_style.currentIndexChanged.connect(partial(self.set_style, "advanced"))

        # initialize sliders
        self.prompt_weight_distribution_slider.valueChanged.connect(
            self.handle_weight_distribution_slider_change)
        self.negative_prompt_weight_distribution_slider.valueChanged.connect(
            self.handle_negative_weight_distribution_slider_change)
        self.app.generate_signal.connect(self.inject_prompt)

        # set auto_prompt_weight and text_prompt_weight
        auto_prompt_weight = self.settings_manager.settings.auto_prompt_weight.get()
        auto_negative_prompt_weight = self.settings_manager.settings.negative_auto_prompt_weight.get()
        self.prompt_weight_distribution_slider.setValue(int(auto_prompt_weight * 100))
        self.negative_prompt_weight_distribution_slider.setValue(int(auto_negative_prompt_weight * 100))
        self.handle_weight_distribution_slider_change(int(auto_prompt_weight * 100))
        self.handle_negative_weight_distribution_slider_change(int(auto_negative_prompt_weight * 100))

        # check for index in
        basic_category = self.settings_manager.settings.prompt_generator_basic_category.get()
        advanced_category = self.settings_manager.settings.prompt_generator_advanced_category.get()
        basic_style = self.settings_manager.settings.prompt_generator_basic_style.get()
        advanced_style = self.settings_manager.settings.prompt_generator_advanced_style.get()
        basic_prompt = self.settings_manager.settings.prompt_generator_basic_prompt.get()
        advanced_prompt = self.settings_manager.settings.prompt_generator_advanced_prompt.get()

        # initialize dropdown values
        basic_category_index = self.basic_category.findText(basic_category)
        advanced_category_index = self.advanced_category.findText(advanced_category)
        basic_style_index = self.basic_style.findText(basic_style)
        advanced_style_index = self.advanced_style.findText(advanced_style)
        self.basic_category.setCurrentIndex(basic_category_index)
        self.advanced_category.setCurrentIndex(advanced_category_index)

        basic_prompt_index = self.basic_prompt.findText(basic_prompt)
        advanced_prompt_index = self.advanced_prompt.findText(advanced_prompt)
        self.basic_prompt.setCurrentIndex(basic_prompt_index)
        self.advanced_prompt.setCurrentIndex(advanced_prompt_index)

        self.basic_style.setCurrentIndex(basic_style_index)
        self.advanced_style.setCurrentIndex(advanced_style_index)

        # initialize buttons
        self.randomize_values_button.clicked.connect(self.randomize_values)
        self.values_to_random_button.clicked.connect(self.values_to_random)
        self.reset_weights_button.clicked.connect(self.reset_weights)
        self.clear_values_button.clicked.connect(self.clear_values)

        self.basic_randomize_checkbox.stateChanged.connect(
            lambda val: self.settings_manager.settings.prompt_generator_basic_randomize_checkbox.set(val)
        )
        self.basic_randomize_checkbox.setChecked(self.settings_manager.settings.prompt_generator_basic_randomize_checkbox.get())
        self.set_prompts("basic")
        self.set_prompts("advanced")

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
                    widget.slider.setValue(int(weight * 100))
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
        self.scroll_layout.layout().addStretch()

    def create_prompt_widget(self, category, variable, weighted_value, index):
        widget = uic.loadUi(f"pyqt/widgets/prompt_builder_variable_widget.ui")
        widget.groupbox.setTitle(variable.capitalize())

        # set default weights
        weight = weighted_value["weight"]
        widget.slider.setValue(int(weight * 100))
        widget.spinbox.setValue(weight)
        widget.slider.valueChanged.connect(partial(
            self.handle_weight_slider_change, category, variable, widget))
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
        widget.slider.wheelEvent = lambda event: self.scrollArea.wheelEvent(event)
        widget.combobox.addItems(["", "Random"] + items)
        try:
            widget.combobox.setCurrentText(weighted_value["value"])
        except Exception as e:
            pass
        widget.combobox.currentIndexChanged.connect(partial(
            self.handle_combobox_change, category, variable, widget))
        self.scroll_layout.layout().addWidget(widget)

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

    def handle_weight_slider_change(self, category, variable, widget, value):
        data = self.weighted_values(category, variable)
        self.update_weight_spinbox(category, variable, widget)
        data[category][variable]["weight"] = value / 100
        self.settings_manager.settings.prompt_generator_weighted_values.set(data)

    def handle_weight_spinbox_change(self, category, variable, widget, value):
        data = self.weighted_values(category, variable)
        self.update_weight_slider(category, variable, widget)
        data[category][variable]["weight"] = value

    def update_weight_slider(self, category, variable, widget):
        data = self.weighted_values(category, variable)
        widget.slider.setValue(int(data[category][variable]["weight"] * 100))

    def update_weight_spinbox(self, category, variable, widget):
        data = self.weighted_values(category, variable)
        widget.spinbox.setValue(data[category][variable]["weight"])

    def handle_weight_distribution_slider_change(self, value):
        self.auto_prompt_weight = 0.0 + (value / 100.0)
        self.text_prompt_weight = 1.0 - self.auto_prompt_weight
        self.auto_prompt_weight = round(self.auto_prompt_weight, 2)
        self.text_prompt_weight = round(self.text_prompt_weight, 2)
        self.auto_prompt_weight_label.setText(f"{self.auto_prompt_weight:.2f}")
        self.text_prompt_weight_label.setText(f"{self.text_prompt_weight:.2f}")
        self.settings_manager.settings.auto_prompt_weight.set(self.auto_prompt_weight)

    def handle_negative_weight_distribution_slider_change(self, value):
        self.negative_auto_prompt_weight = 0.0 + (value / 100.0)
        self.negative_text_prompt_weight = 1.0 - self.negative_auto_prompt_weight
        self.negative_auto_prompt_weight = round(self.negative_auto_prompt_weight, 2)
        self.negative_text_prompt_weight = round(self.negative_text_prompt_weight, 2)
        self.negative_auto_prompt_weight_label.setText(f"{self.negative_auto_prompt_weight:.2f}")
        self.negative_text_prompt_weight_label.setText(f"{self.negative_text_prompt_weight:.2f}")
        self.settings_manager.settings.negative_auto_prompt_weight.set(self.negative_auto_prompt_weight)

    def inject_prompt(self, options):
        if not self.settings_manager.settings.use_prompt_builder_checkbox.get():
            return
        prompt = self.app.prompt
        negative_prompt = self.app.negative_prompt
        active_tab_index = self.tabs.currentIndex()
        if active_tab_index == 0:
            prompt_category = "basic"
            if self.settings_manager.settings.prompt_generator_basic_randomize_checkbox.get():
                self.basic_category.setCurrentIndex(random.randint(0, len(self.categories) - 1))
                self.basic_prompt.setCurrentIndex(random.randint(0, len(self.basic_prompts) - 1))
                self.basic_style.setCurrentIndex(random.randint(0, len(self.styles) - 1))
            category = self.categories[self.basic_category.currentIndex()]
            prompt_index = self.basic_prompt.currentIndex()
            prompt_type = self.basic_prompts[prompt_index]
            style = self.styles[self.basic_style.currentIndex()]
        else:
            prompt_category = "advanced"
            category = self.categories[self.advanced_category.currentIndex()]
            prompt_index = self.advanced_prompt.currentIndex()
            prompt_type = self.advanced_prompts[prompt_index]
            style = self.styles[self.advanced_style.currentIndex()]

        weighted_variables = self.settings_manager.settings.prompt_generator_weighted_values.get()
        if category in weighted_variables:
            weighted_variables = weighted_variables[category]

        styles = self.styles.copy()
        variables = self.data["categories"][category]["variables"].copy()
        variables["image_style"] = styles if style in ["", "Random"] else [style]

        if prompt_category == "basic":
            generated_prompt = self.data["categories"][category]["prompts"][prompt_category][prompt_type]["prompt"]
        else:
            # iterate over each widget in the scroll area
            # and force the value of each variable to whatever is set
            # in the combobox for that variable.
            for i in range(self.scroll_layout.count()):
                widget = self.scroll_layout.itemAt(i).widget()
                if widget:
                    variable = widget.groupbox.title().lower()
                    value = widget.combobox.currentText()
                    if variable in variables:
                        if value == "":
                            del variables[variable]
                        elif value != "Random":
                            variables[variable] = [value]
            generated_prompt = self.build_appearance_prompt(style, variables, category)

        if category:
            generated_prompt = PromptParser.parse(
                self.prompt_variables,
                category,
                generated_prompt,
                variables,
                weighted_variables,
                self.app.seed)
            generated_prompt = PromptParser.parse(
                self.prompt_variables,
                category,
                generated_prompt,
                variables,
                weighted_variables,
                self.app.seed)
            # extract style from prompt - find |{style:style_name}| and replace with empty string,
            # then split the found string and assign to style variable
            style = re.findall(r"\|style:(.*?)\|", generated_prompt)
            if len(style) > 0:
                style = style[0]
                generated_prompt = generated_prompt.replace(f"|style:{style}|", "")

            negative_prompt_style = "realistic"
            if style in [
                "photograph",
                "professional photograph",
                "amateur photograph",
                "candid photograph",
                "portrait",
                "street photography",
                "photo journalism",
                "cctv footage",
                "bodycam footage",
                "found footage",
                "VHS footage",
            ]:
                negative_prompt_style = "realistic"
            elif style in [
                "landscape",
                "still life",
                "painting",
                "mixed media",
                "sculpture",
                "drawing",
            ]:
                negative_prompt_style = "artistic"
            elif style in [
                "caricature",
                "cartoon",
                "illustration",
                "digital art",
                "anime",
                "comic book",
                "graphic novel",
            ]:
                negative_prompt_style = "cartoon"


            prompt = PromptParser.parse(
                self.prompt_variables,
                category,
                prompt,
                variables,
                weighted_variables,
                self.app.seed)
            text_weight = self.text_prompt_weight
            auto_weight = self.auto_prompt_weight
            generated_prompt = generated_prompt.strip()
            generated_prompt.replace("( ", "(")
            if prompt != "" and text_weight > 0 and auto_weight > 0:
                prompt = f'("{prompt}", "{generated_prompt}").blend({text_weight}, {auto_weight})'
            elif text_weight == 0 or prompt == "":
                prompt = generated_prompt
            text_weight = self.negative_text_prompt_weight
            auto_weight = self.negative_auto_prompt_weight
            generated_negative_prompt = self.data["categories"][category]["prompts"][prompt_category][prompt_type]["negative_prompt"][negative_prompt_style]
            generated_negative_prompt = PromptParser.parse(self.prompt_variables, category, generated_negative_prompt, seed=self.app.seed)
            generated_negative_prompt = generated_negative_prompt.strip()
            if negative_prompt != "" and text_weight > 0 and auto_weight > 0:
                negative_prompt = PromptParser.parse(self.prompt_variables, category, negative_prompt, seed=self.app.seed)
                negative_prompt = f'("{negative_prompt}", "{generated_negative_prompt}").blend({text_weight}, {auto_weight})'
            elif text_weight == 0 or negative_prompt == "":
                negative_prompt = generated_negative_prompt
        options[f"{self.app.action}_prompt"] = prompt
        options[f"{self.app.action}_negative_prompt"] = negative_prompt

    def has_variable(self, variable, available_variables):
        return variable in available_variables and available_variables[variable] != [""]

    def process_variable(self, var):
        if isinstance(var, dict):
            if "range" in var:
                if "type" in var and var["type"] == "range":
                    var = random.randint(var["min"], var["max"])
        return var

    def build_conditional_prompt(self, conditionals, style, vars, category, appearance):
        for conditional in conditionals:
            text = None
            cond = None
            not_cond = None
            next = None
            else_value = None
            if "text" in conditional:
                text = conditional["text"]
            if "cond" in conditional:
                cond = conditional["cond"]
            if "not_cond" in conditional:
                not_cond = conditional["not_cond"]
            if "next" in conditional:
                next = conditional["next"]
            if "else" in conditional:
                else_value = conditional["else"]
            has_cond = True
            not_cond_val = True
            if text and cond:
                if isinstance(cond, list):
                    for cond_var in cond:
                        if not self.has_variable(cond_var, vars):
                            has_cond = False
                else:
                    if not self.has_variable(cond, vars):
                        has_cond = False
            if text and not_cond:
                if isinstance(not_cond, list):
                    for not_cond_var in not_cond:
                        if self.has_variable(not_cond_var, vars):
                            not_cond_val = False
                else:
                    if self.has_variable(not_cond, vars):
                        not_cond_val = False
            if text and not_cond_val and has_cond:
                text = self.process_variable(text)
                appearance += text
            elif else_value:
                appearance += self.process_variable(text)
            if next:
                if cond and not text:
                    if self.has_variable(cond, vars):
                        appearance = self.build_conditional_prompt(next, style, vars, category, appearance)
                else:
                    appearance = self.build_conditional_prompt(next, style, vars, category, appearance)
        return appearance

    def build_appearance_prompt(self, style, vars, category):
        appearance = self.build_conditional_prompt(
            self.data["categories"][category]["builder"],
            style,
            vars,
            category,
            ""
        )
        return f"($style, $color, ({style})++), {appearance}"

    def set_prompts(self, prompt_type):
        if prompt_type == "basic":
            category = self.basic_category.currentText()
        elif prompt_type == "advanced":
            category = self.advanced_category.currentText()
        try:
            prompts = list(self.data["categories"][category]["prompts"][prompt_type].keys())
        except KeyError:
            prompts = []
        if prompt_type == "basic":
            self.basic_prompt.clear()
            self.basic_prompt.addItems(prompts)
            self.basic_prompts = prompts
            self.settings_manager.settings.prompt_generator_basic_category.set(category)
            try:
                self.settings_manager.settings.prompt_generator_basic_prompt.set(prompts[0])
            except IndexError:
                pass
        else:
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

    def load_data(self, file_name):
        file = f"data/{file_name}.json"
        with open(file, "r") as f:
            data = json.load(f)
            return data

    def set_style(self, style_type):
        if style_type == "basic":
            self.settings_manager.settings.prompt_generator_basic_style.set(
                self.basic_style.currentText())
        else:
            self.settings_manager.settings.prompt_generator_advanced_style.set(
                self.advanced_style.currentText())
