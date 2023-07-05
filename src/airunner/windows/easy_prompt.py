import json
import random
import re
from functools import partial

from PyQt6 import uic
from PyQt6.QtWidgets import QPushButton, QWidget, QGridLayout

from aihandler.prompt_variable import PromptVariable
from airunner.windows.base_window import BaseWindow

class EasyPromptWindow(BaseWindow):
    template_name = "easy_prompt"
    window_title = "Easy Prompt"
    is_modal = True
    auto_prompt_weight = 0.5
    text_prompt_weight = 0.5
    negative_auto_prompt_weight = 0.5
    negative_text_prompt_weight = 0.5
    age_list = [str(n) for n in range(18, 101)]
    data = {}
    prompt_category = {}
    prompt_type = {}

    @property
    def current_tab_index(self):
        return self.template.tabWidget.currentIndex()

    def initialize_window(self):
        self.initialize_auto_prompt_tab()
        self.initialize_prompt_builder_tabs()
        self.app.generate_signal.connect(self.inject_prompt)
        self.template.closeEvent = self.handle_close

    def handle_close(self, event):
        self.app.generate_signal.disconnect(self.inject_prompt)

    def handle_category_change(self, tab_index, widget):
        category = widget.category_combobox.currentText()
        self.prompt_category = category
        widget.prompt_combobox.clear()
        prompts = list(self.data[tab_index]["prompts"][category].keys())
        self.prompt_type = prompts[0]
        widget.prompt_combobox.addItems(prompts)

    def handle_prompt_change(self, tab_index, widget):
        self.prompt_type = widget.prompt_combobox.currentText()

    def initialize_prompt_builder_tabs(self):
        max_col = 5
        for index, name in enumerate(["people", "animal", "architecture", "vehicle", "food"]):
            column = 0
            row = 1
            # add a tab to the QTabWidget
            tab_index = self.template.tabWidget.addTab(QWidget(), f"{name.capitalize()} generator")
            self.load_data(tab_index, name)

            # create grid layout in tab
            self.template.tabWidget.widget(tab_index).setLayout(QGridLayout())

            # load header
            header = uic.loadUi("pyqt/widgets/prompt_builder_header.ui")

            # add values to dropdowns
            prompt_categories = list(self.data[tab_index]["prompts"].keys())
            self.prompt_category[tab_index] = prompt_categories[0]
            prompts = list(self.data[tab_index]["prompts"][self.prompt_category[tab_index]].keys())
            header.category_combobox.addItems(prompt_categories)
            header.prompt_combobox.addItems(prompts)
            self.prompt_type[tab_index] = prompts[0]

            # add header to layout
            header.category_combobox.currentTextChanged.connect(partial(self.handle_category_change, tab_index, header))
            header.prompt_combobox.currentTextChanged.connect(partial(self.handle_prompt_change, tab_index, header))
            self.template.tabWidget.widget(tab_index).layout().addWidget(header, 0, 0, 1, max_col)

            # get all the categories
            categories = self.data[tab_index]["categories"].keys()

            # create widgets for all sections in the data file
            for category in categories:
                # use uic to load the prompt_builder_variable_widget.ui widget file
                widget = uic.loadUi(
                    f"pyqt/widgets/prompt_builder_variable_widget.ui"
                )
                widget.groupbox.setTitle(category.capitalize())

                # set default weights
                weight = self.data[tab_index]["weights"][category]
                widget.slider.setValue(int(weight * 100))
                widget.spinbox.setValue(weight)
                widget.slider.valueChanged.connect(partial(self.handle_weight_slider_change, category, tab_index, widget))
                widget.spinbox.valueChanged.connect(partial(self.handle_weight_spinbox_change, category, tab_index, widget))

                # set combobox values
                items = self.data[tab_index]["categories"][category]
                if category != "age":
                    items.sort()
                if isinstance(items, dict):
                    if items["type"] == "range":
                        items = [str(n) for n in range(items["min"], items["max"] + 1)]
                        self.data[tab_index]["categories"][category] = items
                widget.combobox.addItems(["", "Random"] + items)
                # add the widget to the tab
                # add grid layout to self.template.tabWidget.widget(tab_index)

                # add the widget to
                if column >= max_col:
                    column = 0
                    row += 1
                self.template.tabWidget.widget(tab_index).layout().addWidget(widget, row, column)
                column += 1

            # load the widget/prompt_builder_buttons.ui widget and add to the tab
            buttons = uic.loadUi("pyqt/widgets/prompt_builder_buttons.ui")
            buttons.generate_person_button.clicked.connect(partial(self.handle_generate_button_click, tab_index))
            buttons.reset_weights_button.clicked.connect(partial(self.reset_weights, tab_index))
            buttons.reset_weights_button.clicked.connect(partial(self.reset_weights, tab_index))
            buttons.reset_values_button.clicked.connect(partial(self.reset_values, tab_index))
            buttons.set_all_random_button.clicked.connect(partial(self.set_all_random, tab_index))
            buttons.randomize_all_button.clicked.connect(partial(self.randomize_all, tab_index))
            self.template.tabWidget.widget(tab_index).layout().addWidget(buttons, row + 1, 0, 1, max_col)
            # add stretch to the bottom of the tab
            self.template.tabWidget.widget(tab_index).layout().setRowStretch(row + 2, 1)


    def load_data(self, tab_index, name):
        file = f"data/{name}.json"
        with open(file, "r") as f:
            data = json.load(f)
            data["default_weights"] = data["weights"].copy()
            self.data[tab_index] = data

    def reset_values(self, tab_index):
        for i in range(self.template.tabWidget.widget(tab_index).layout().count()):
            widget = self.template.tabWidget.widget(tab_index).layout().itemAt(i).widget()
            try:
                widget.combobox.setCurrentIndex(0)
            except:
                pass

    def set_all_random(self, tab_index):
        for i in range(self.template.tabWidget.widget(tab_index).layout().count()):
            widget = self.template.tabWidget.widget(tab_index).layout().itemAt(i).widget()
            try:
                widget.combobox.setCurrentIndex(1)
            except:
                pass

    def randomize_all(self, tab_index):
        for i in range(self.template.tabWidget.widget(tab_index).layout().count()):
            widget = self.template.tabWidget.widget(tab_index).layout().itemAt(i).widget()
            try:
                widget.combobox.setCurrentIndex(random.randint(2, widget.combobox.count() - 1))
            except:
                pass

    def handle_weight_slider_change(self, category, tab_index, widget, value):
        self.data[tab_index]["weights"][category] = value / 100
        self.update_weight_spinbox(category, tab_index, widget)

    def handle_weight_spinbox_change(self, category, tab_index, widget, value):
        self.data[tab_index]["weights"][category] = value
        self.update_weight_slider(category, tab_index, widget)

    def update_weight_spinbox(self, category, tab_index, widget):
        widget.spinbox.setValue(self.data[tab_index]["weights"][category])

    def update_weight_slider(self, category, tab_index, widget):
        widget.slider.setValue(int(self.data[tab_index]["weights"][category] * 100))

    def random_item(self, item, list):
        if item == "Random":
            item = random.choice(list)
            if item == "Random":
                return self.get_random_item(list)
        return item

    def reset_weights(self, name, tab_index):
        # iterate through all widgets in the self.template.tabWidget.widget(tab_index).layout()
        for i in range(self.template.tabWidget.widget(tab_index).layout().count()):
            widget = self.template.tabWidget.widget(tab_index).layout().itemAt(i).widget()
            try:
                category = widget.groupbox.title().lower()
                self.data[name]["weights"][category] = self.data[name]["default_weights"][category]
                self.update_weight_spinbox(category, name, widget)
                self.update_weight_slider(category, name, widget)
            except:
                pass

    def get_available_variables(self, values, tab_index, prompt_builder=False):
        available_variables = self.data[tab_index]["categories"].copy()
        for k, v in values.items():
            if v != "":
                if k == "age":
                    v = f"{v} years old"
                available_variables[k] = [v]
            else:
                if prompt_builder:
                    available_variables[k] = [""]
        return available_variables

    def get_values(self, tab_index):
        values = {}
        for i in range(self.template.tabWidget.widget(tab_index).layout().count()):
            widget = self.template.tabWidget.widget(tab_index).layout().itemAt(i).widget()
            try:
                category = widget.groupbox.title().lower()
                values[category] = widget.combobox.currentText()
                values[category] = self.random_item(values[category], self.data[tab_index]["categories"][category])
            except:
                pass
        return values

    def handle_generate_button_click(self, tab_index):
        random.seed(self.app.seed)
        values = self.get_values(tab_index)
        prompt_builder = self.template.tabWidget.currentIndex() != 0
        available_variables = self.get_available_variables(values, tab_index, prompt_builder)
        weights = self.data[tab_index]["weights"]

        category = self.prompt_category[tab_index]
        if prompt_builder:
            prompt = self.build_intro_prompt(available_variables, category)
            prompt = self.build_appearance_prompt(available_variables, category, prompt)
        else:
            prompt = self.data[tab_index]["prompts"][category][self.prompt_type[tab_index]]["prompt"]
        prompt = PromptVariable.parse(prompt=prompt, available_variables=available_variables, weights=weights)
        self.prompt = PromptVariable.parse(prompt=prompt, available_variables=available_variables, weights=weights)
        self.prompt = prompt
        self.app.generate_callback()

    def has_variable(self, variable, available_variables):
        return variable in available_variables and available_variables[variable] != [""]

    def build_intro_prompt(self, available_variables, category):
        if category == "person":
            return f"A photograph of a $ethnicity $gender named $$gender_name who is $age"

    def build_appearance_prompt(self, vars, category, prompt):
        appearance = ""
        if category == "person":
            has_hair_length = self.has_variable("hair_length", vars)
            has_hair_color = self.has_variable("hair_color", vars)
            has_eye_color = self.has_variable("eye_color", vars)
            has_skin_tone = self.has_variable("skin_tone", vars)
            has_body_type = self.has_variable("body_type", vars)
            has_height = self.has_variable("height", vars)
            has_facial_hair = self.has_variable("facial_hair", vars)
            has_glasses = self.has_variable("glasses", vars)
            has_hat = self.has_variable("hat", vars)
            has_shirt = self.has_variable("shirt", vars)
            has_pants = self.has_variable("pants", vars)
            has_shoes = self.has_variable("shoes", vars)
            has_accessories = self.has_variable("accessories", vars)
            has_tattoos = self.has_variable("tattoos", vars)
            has_piercings = self.has_variable("piercings", vars)
            has_scars = self.has_variable("scars", vars)
            has_birthmarks = self.has_variable("birthmarks", vars)
            has_disabilities = self.has_variable("disabilities", vars)
            has_personality = self.has_variable("personality", vars)
            has_occupation = self.has_variable("occupation", vars)
            has_descriptive_traits = self.has_variable("descriptive_traits", vars)
            has_emotion = self.has_variable("emotion", vars)
            if has_hair_length:
                appearance = f"($hair_length"
            if has_hair_color:
                appearance = f"{appearance} {'(' if not has_hair_length else ''}$hair_color"
            appearance = f"{appearance} {'hair)' if has_hair_length or has_hair_color else ''}"
            if has_eye_color:
                appearance = f"{appearance} $eye_color eyes"
            if has_skin_tone:
                appearance = f"{appearance} {'and' if appearance != '' else ''} $skin_tone skin"
            if has_body_type:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name has a ($body_type body-type)"
            if has_height:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name's (height is $height)"
            if has_facial_hair:
                if vars["facial_hair"][0] == "Clean-shaven":
                    appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name is clean-shaven"
                else:
                    appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name has a $facial_hair"
            if has_glasses:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name (wears $glasses)"
            if has_hat:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name is (wearing a $hat)"
            if has_shirt:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name is (wearing a $shirt)"
            if has_pants:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name is (wearing $pants)"
            if has_shoes:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name is (wearing $shoes)"
            if has_accessories:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name is (wearing $accessories)"
            if has_tattoos:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name has ($tattoos tattoos)"
            if has_piercings:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name has ($piercings piercings)"
            if has_scars:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name has ($scars scars)"
            if has_birthmarks:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name has ($birthmarks birthmarks)"
            if has_occupation:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name is (dressed like a $occupation)"
            if has_descriptive_traits:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name is $descriptive_traits"
            if has_emotion:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name is $emotion"
            if has_personality:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name is $personality"
            if has_disabilities:
                appearance = f"{appearance}{'.' if appearance != '' else ''} $$gender_name has $disabilities"
            if appearance != "":
                return f"{prompt} {f'with ({appearance})'}"
        return prompt

    def inject_prompt(self, options):
        # determine which tab we are on
        if self.template.tabWidget.currentIndex() == 0:
            tab_index = 1
            values = self.get_values(tab_index)
            available_variables = self.get_available_variables(values, tab_index)

            prompt = self.template.prompt.toPlainText()
            negative_prompt = self.template.negative_prompt.toPlainText()
            prompt = PromptVariable.parse(prompt=prompt, available_variables=available_variables, weights={})
            negative_prompt = PromptVariable.parse(prompt=negative_prompt, available_variables=available_variables, weights={})

            options[f"{self.app.action}_prompt"] = prompt
            options[f"{self.app.action}_negative_prompt"] = negative_prompt
            options["autoprompt"] = {
                "name": self.autoprompt.lower(),
                "weight": {
                    "prompt": {
                        "auto": self.auto_prompt_weight,
                        "text": self.text_prompt_weight
                    },
                    "negative_prompt": {
                        "auto": self.negative_auto_prompt_weight,
                        "text": self.negative_text_prompt_weight
                    }
                }
            }
        else:
            tab_index = self.template.tabWidget.currentIndex()
            options[f"{self.app.action}_prompt"] = self.prompt
            options[f"{self.app.action}_negative_prompt"] = self.data[tab_index]["prompts"][self.prompt_category[tab_index]][self.prompt_type[tab_index]]["negative_prompt"]

    def initialize_auto_prompt_tab(self):
        # iterate through all the QPushButtons in the window
        for button in self.template.findChildren(QPushButton):
            # connect the button to the handle_generator_button_click function
            button.clicked.connect(partial(self.handle_generator_button_click, button.text()))

        self.template.prompt_weight_distribution_slider.valueChanged.connect(self.handle_weight_distribution_slider_change)
        self.handle_weight_distribution_slider_change(self.template.prompt_weight_distribution_slider.value())
        self.template.negative_prompt_weight_distribution_slider.valueChanged.connect(self.handle_negative_weight_distribution_slider_change)
        self.handle_negative_weight_distribution_slider_change(self.template.negative_prompt_weight_distribution_slider.value())


    def handle_weight_distribution_slider_change(self, value):
        self.auto_prompt_weight = 0.0 + (value / 100.0)
        self.text_prompt_weight = 1.0 - self.auto_prompt_weight
        self.auto_prompt_weight = round(self.auto_prompt_weight, 2)
        self.text_prompt_weight = round(self.text_prompt_weight, 2)
        self.template.auto_prompt_weight_label.setText(f"{self.auto_prompt_weight:.2f}")
        self.template.text_prompt_weight_label.setText(f"{self.text_prompt_weight:.2f}")

    def handle_negative_weight_distribution_slider_change(self, value):
        self.negative_auto_prompt_weight = 0.0 + (value / 100.0)
        self.negative_text_prompt_weight = 1.0 - self.negative_auto_prompt_weight
        self.negative_auto_prompt_weight = round(self.negative_auto_prompt_weight, 2)
        self.negative_text_prompt_weight = round(self.negative_text_prompt_weight, 2)
        self.template.negative_auto_prompt_weight_label.setText(f"{self.negative_auto_prompt_weight:.2f}")
        self.template.negative_text_prompt_weight_label.setText(f"{self.negative_text_prompt_weight:.2f}")

    def handle_generator_button_click(self, name):
        self.autoprompt = name
        self.app.generate_callback()