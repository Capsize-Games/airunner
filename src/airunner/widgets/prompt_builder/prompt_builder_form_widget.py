import random
from functools import partial
from PyQt6 import uic
from PyQt6.QtWidgets import QGridLayout, QSpacerItem, QSizePolicy

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.prompt_builder.templates.prompt_builder_form_ui import Ui_prompt_builder_form


class PromptBuilderForm(BaseWidget):
    widget_class_ = Ui_prompt_builder_form
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
        self.parent.process_prompt()

    def __init__(self, *args, **kwargs):
        self.prompt_builder_widget = kwargs.pop("prompt_builder_widget")
        super().__init__(*args, **kwargs)
        self.parent = kwargs.get("parent")
        self.scroll_layout = QGridLayout(self.ui.scrollArea.widget())
        self.initialize_category_dropdowns()
        self.initialize_genre_dropdowns()
        self.initialize_color_dropdowns()
        self.initialize_style_dropdowns()
        self.initialize_dropdown_values()
        self.initialize_prefix_suffix_inputs()
        self.initialize_buttons()
        self.initialize_radio_buttons()

    def variables_by_category(self, name):
        variable_objects = self.settings_manager.variables_by_category(name)
        return list(filter(None, [v.value for v in variable_objects]))

    def prompts_by_category(self, name):
        prompt_objects = self.settings_manager.prompts_by_category(name)
        return list(filter(None, [p.name for p in prompt_objects]))

    def initialize_category_dropdowns(self):
        # initialize category dropdowns
        self.prompt_category_current_index = 0
        self.ui.prompt_category.addItems(self.variables_by_category("composition_category"))
        self.ui.prompt_category.currentIndexChanged.connect(partial(self.set_prompts, "advanced"))
        self.ui.prompt_category.lineEdit().setReadOnly(True)

    def initialize_genre_dropdowns(self):
        # initialize genre dropdowns
        self.ui.prompt_genre.addItems(self.variables_by_category("composition_genre"))
        self.ui.prompt_genre.currentIndexChanged.connect(partial(self.set_genre))
        self.ui.prompt_genre.lineEdit().setReadOnly(True)

    def initialize_color_dropdowns(self):
        # initialize color dropdowns
        self.ui.prompt_color.addItems(self.variables_by_category("composition_color"))
        self.ui.prompt_color.currentIndexChanged.connect(partial(self.set_color))
        self.ui.prompt_color.lineEdit().setReadOnly(True)

    def initialize_style_dropdowns(self):
        # initialize style dropdowns
        self.ui.prompt_style.addItems(self.variables_by_category("composition_style"))
        self.ui.prompt_style.currentIndexChanged.connect(partial(self.set_style))
        self.ui.prompt_style.lineEdit().setReadOnly(True)

    def initialize_dropdown_values(self):
        # check for index in
        prompt_category = self.settings_manager.current_prompt_generator_settings.category
        prompt_genre = self.settings_manager.current_prompt_generator_settings.prompt_genre
        prompt_color = self.settings_manager.current_prompt_generator_settings.prompt_color
        prompt_style = self.settings_manager.current_prompt_generator_settings.prompt_style

        # initialize dropdown values
        prompt_category_index = self.ui.prompt_category.findText(prompt_category)
        prompt_genre_index = self.ui.prompt_genre.findText(prompt_genre)
        prompt_color_index = self.ui.prompt_color.findText(prompt_color)
        prompt_style_index = self.ui.prompt_style.findText(prompt_style)
        self.ui.prompt_category.setCurrentIndex(prompt_category_index)
        self.ui.prompt_genre.setCurrentIndex(prompt_genre_index)
        self.ui.prompt_color.setCurrentIndex(prompt_color_index)
        self.ui.prompt_style.setCurrentIndex(prompt_style_index)

    def initialize_prefix_suffix_inputs(self):
        self.ui.prompt_prefix.setText(self.settings_manager.current_prompt_generator_settings.prefix)
        self.ui.prompt_suffix.setText(self.settings_manager.current_prompt_generator_settings.suffix)
        self.ui.prompt_prefix.textChanged.connect(self.handle_prompt_prefix_change)
        self.ui.prompt_suffix.textChanged.connect(self.handle_prompt_suffix_change)

        self.ui.negative_prompt_prefix.setText(self.settings_manager.current_prompt_generator_settings.negative_prefix)
        self.ui.negative_prompt_suffix.setText(self.settings_manager.current_prompt_generator_settings.negative_suffix)
        self.ui.negative_prompt_prefix.textChanged.connect(self.handle_negative_prompt_prefix_change)
        self.ui.negative_prompt_suffix.textChanged.connect(self.handle_negative_prompt_suffix_change)

    def handle_prompt_prefix_change(self, text):
        self.settings_manager.set_value("current_prompt_generator_settings.prefix", text)
        self.process_prompt()

    def handle_prompt_suffix_change(self, text):
        self.settings_manager.set_value("current_prompt_generator_settings.suffix", text)
        self.process_prompt()

    def handle_negative_prompt_prefix_change(self, text):
        self.settings_manager.set_value("current_prompt_generator_settings.negative_prompt_generator_prefix", text)
        self.process_prompt()

    def handle_negative_prompt_suffix_change(self, text):
        self.settings_manager.set_value("current_prompt_generator_settings.negative_prompt_generator_suffix", text)
        self.process_prompt()

    def initialize_buttons(self):
        # initialize buttons
        self.ui.randomize_values_button.clicked.connect(self.randomize_values)
        self.ui.values_to_random_button.clicked.connect(self.values_to_random)
        self.ui.reset_weights_button.clicked.connect(self.reset_weights)
        self.ui.clear_values_button.clicked.connect(self.clear_values)
        self.set_prompts("advanced")

    def initialize_radio_buttons(self):
        self.ui.basic_radio.setChecked(self.settings_manager.current_prompt_generator_settings.advanced_mode is False)
        self.ui.advanced_radio.setChecked(self.settings_manager.current_prompt_generator_settings.advanced_mode is True)
        self.ui.basic_radio.toggled.connect(self.handle_advanced_basic_radio_change)
        self.ui.advanced_radio.toggled.connect(self.handle_advanced_basic_radio_change)
        self.handle_advanced_basic_radio_change()

    def handle_advanced_basic_radio_change(self):
        self.settings_manager.set_value("current_prompt_generator_settings.advanced_mode", self.ui.advanced_radio.isChecked())
        if self.ui.advanced_radio.isChecked():
            self.ui.scrollArea.show()
        else:
            self.ui.scrollArea.hide()
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
        category = self.ui.prompt_category.currentText()
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                variable = widget.label.text().lower()
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
        data = self.settings_manager.current_prompt_generator_settings.weighted_values
        try:
            for index, variable in enumerate(self.variables_by_category(category)):
                if category in data and variable in data[category]:
                    weighted_value = data[category][variable]
                else:
                    weighted_value = {
                        "value": "",
                        "weight": self.settings_manager.variable_weights_by_category(category, variable).weight
                    }
                self.create_prompt_widget(category, variable, weighted_value, index)
        except KeyError:
            pass
        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        total_rows = self.scroll_layout.layout().rowCount()
        self.scroll_layout.layout().addItem(spacer, total_rows+1, 0)

    def create_prompt_widget(self, category, variable, weighted_value, index):
        widget = uic.loadUi(f"widgets/prompt_builder/templates/prompt_builder_variable_widget.ui")
        widget.label.setText(variable.capitalize())

        # set default weights
        weight = weighted_value["weight"]
        widget.spinbox.setValue(weight)
        widget.spinbox.valueChanged.connect(partial(
            self.handle_weight_spinbox_change, category, variable, widget))
        items = self.variables_by_category(category)
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
        # prevent widget.combobox from being edited, but leave it editable
        widget.combobox.lineEdit().setReadOnly(True)
        self.scroll_layout.layout().addWidget(widget, index // 2, index % 2, 1, 1)

    def weighted_values(self, category, variable):
        data = self.settings_manager.current_prompt_generator_settings.weighted_values
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
        self.settings_manager.set_value("current_prompt_generator_settings.weighted_values", data)
        self.process_prompt()

    def handle_weight_spinbox_change(self, category, variable, widget, value):
        data = self.weighted_values(category, variable)
        value = round(value, 2)
        data[category][variable]["weight"] = value
        self.settings_manager.set_value("current_prompt_generator_settings.weighted_values", data)
        self.process_prompt()

    def update_weight_spinbox(self, category, variable, widget):
        data = self.weighted_values(category, variable)
        widget.spinbox.setValue(data[category][variable]["weight"])
        self.process_prompt()

    def set_prompts(self, prompt_type):
        category = self.ui.prompt_category.currentText()
        try:
            prompts = list(self.prompts_by_category(category))
        except KeyError:
            prompts = []
        self.prompt_types = prompts
        self.settings_manager.set_value("current_prompt_generator_settings.category", category)

        try:
            self.settings_manager.set_value("current_prompt_generator_settings.prompt", prompts[0])

        except IndexError:
            pass
        if prompt_type == "advanced":
            self.populate_prompt_widgets(category)
        self.process_prompt()

    def set_style(self):
        self.settings_manager.set_value(
            "current_prompt_generator_settings.prompt_style",
            self.ui.prompt_style.currentText())
        self.process_prompt()

    def set_color(self):
        self.settings_manager.set_value(
            "current_prompt_generator_settings.prompt_color",
            self.ui.prompt_color.currentText())
        self.process_prompt()

    def set_genre(self):
        self.settings_manager.set_value(
            "current_prompt_generator_settings.prompt_genre",
            self.ui.prompt_genre.currentText())
        self.process_prompt()
