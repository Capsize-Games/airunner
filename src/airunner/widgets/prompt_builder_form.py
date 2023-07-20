import random
from functools import partial
from PyQt6 import uic
from PyQt6.QtWidgets import QGridLayout
from airunner.widgets.base_widget import BaseWidget


class PromptBuilderForm(BaseWidget):
    name = "prompt_builder_form"
    prompt_types = None
    unprocessed_prompts = {}

    # this is the parent tab widget which initializes this widget
    prompt_builder_widget = None

    @property
    def prompt_data(self):
        return self.prompt_builder_widget.prompt_data

    def process_prompt(self):
        """
        A pass-through function for the prompt builder widget to call
        :return:
        """
        self.prompt_builder_widget.process_prompt()

    def __init__(self, *args, **kwargs):
        self.prompt_builder_widget = kwargs.pop("prompt_builder_widget")
        super().__init__(*args, **kwargs)
        self.set_stylesheet()
        self.scroll_layout = QGridLayout(self.scrollArea.widget())
        self.initialize_category_dropdowns()
        self.initialize_genre_dropdowns()
        self.initialize_color_dropdowns()
        self.initialize_style_dropdowns()
        self.initialize_dropdown_values()
        self.initialize_prefix_suffix_inputs()
        self.initialize_buttons()
        self.initialize_radio_buttons()

    def initialize_category_dropdowns(self):
        # initialize category dropdowns
        self.prompt_category_current_index = 0
        self.prompt_category.addItems(self.prompt_data.categories)
        self.prompt_category.currentIndexChanged.connect(partial(self.set_prompts, "advanced"))

    def initialize_genre_dropdowns(self):
        # initialize genre dropdowns
        self.prompt_genre.addItems(self.prompt_data.genres)
        self.prompt_genre.currentIndexChanged.connect(partial(self.set_genre))

    def initialize_color_dropdowns(self):
        # initialize color dropdowns
        self.prompt_color.addItems(self.prompt_data.colors)
        self.prompt_color.currentIndexChanged.connect(partial(self.set_color))

    def initialize_style_dropdowns(self):
        # initialize style dropdowns
        self.prompt_style.addItems(self.prompt_data.styles)
        self.prompt_style.currentIndexChanged.connect(partial(self.set_style))

    def initialize_dropdown_values(self):
        # check for index in
        prompt_category = self.settings_manager.settings.prompt_generator_category.get()
        prompt_genre = self.settings_manager.settings.prompt_generator_prompt_genre.get()
        prompt_color = self.settings_manager.settings.prompt_generator_prompt_color.get()
        prompt_style = self.settings_manager.settings.prompt_generator_prompt_style.get()

        # initialize dropdown values
        prompt_category_index = self.prompt_category.findText(prompt_category)
        prompt_genre_index = self.prompt_genre.findText(prompt_genre)
        prompt_color_index = self.prompt_color.findText(prompt_color)
        prompt_style_index = self.prompt_style.findText(prompt_style)
        self.prompt_category.setCurrentIndex(prompt_category_index)
        self.prompt_genre.setCurrentIndex(prompt_genre_index)
        self.prompt_color.setCurrentIndex(prompt_color_index)
        self.prompt_style.setCurrentIndex(prompt_style_index)

    def initialize_prefix_suffix_inputs(self):
        self.prompt_prefix.setText(self.settings_manager.settings.prompt_generator_prefix.get())
        self.prompt_suffix.setText(self.settings_manager.settings.prompt_generator_suffix.get())
        self.prompt_prefix.textChanged.connect(self.handle_prompt_prefix_change)
        self.prompt_suffix.textChanged.connect(self.handle_prompt_suffix_change)

        self.negative_prompt_prefix.setText(self.settings_manager.settings.negative_prompt_generator_prefix.get())
        self.negative_prompt_suffix.setText(self.settings_manager.settings.negative_prompt_generator_suffix.get())
        self.negative_prompt_prefix.textChanged.connect(self.handle_negative_prompt_prefix_change)
        self.negative_prompt_suffix.textChanged.connect(self.handle_negative_prompt_suffix_change)

    def handle_prompt_prefix_change(self, text):
        self.settings_manager.settings.prompt_generator_prefix.set(text)
        self.process_prompt()

    def handle_prompt_suffix_change(self, text):
        self.settings_manager.settings.prompt_generator_suffix.set(text)
        self.process_prompt()

    def handle_negative_prompt_prefix_change(self, text):
        self.settings_manager.settings.negative_prompt_generator_prefix.set(text)
        self.process_prompt()

    def handle_negative_prompt_suffix_change(self, text):
        self.settings_manager.settings.negative_prompt_generator_suffix.set(text)
        self.process_prompt()

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
        self.handle_advanced_basic_radio_change()

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
        category = self.prompt_category.currentText()
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                variable = widget.groupbox.title().lower()
                try:
                    weight = self.prompt_data.variable_weights_by_category(category, variable)
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
            for index, variable in enumerate(self.prompt_data.available_variables_by_category(category)):
                if category in data and variable in data[category]:
                    weighted_value = data[category][variable]
                else:
                    weighted_value = {
                        "value": "",
                        "weight": self.prompt_data.variable_weights_by_category(category, variable)
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
        items = self.prompt_data.variable_values_by_category(category, variable)
        if isinstance(items, dict):
            if items["type"] == "range":
                items = [str(n) for n in range(items["min"], items["max"] + 1)]
                self.prompt_data.set_variable_values_by_category(category, variable, items)
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
        data[category][variable]["weight"] = self.prompt_data.variable_weights_by_category(category, variable)
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

    def set_prompts(self, prompt_type):
        category = self.prompt_category.currentText()
        try:
            prompts = list(self.prompt_data.available_prompts_by_category(category))
        except KeyError:
            prompts = []
        self.prompt_types = prompts
        self.settings_manager.settings.prompt_generator_category.set(category)
        try:
            self.settings_manager.settings.prompt_generator_prompt.set(prompts[0])
        except IndexError:
            pass
        if prompt_type == "advanced":
            self.populate_prompt_widgets(category)
        self.process_prompt()

    def set_style(self):
        self.settings_manager.settings.prompt_generator_prompt_style.set(
            self.prompt_style.currentText())
        self.process_prompt()

    def set_color(self):
        self.settings_manager.settings.prompt_generator_prompt_color.set(
            self.prompt_color.currentText())
        self.process_prompt()

    def set_genre(self):
        self.settings_manager.settings.prompt_generator_prompt_genre.set(
            self.prompt_genre.currentText())
        self.process_prompt()
