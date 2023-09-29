import importlib
import os
from functools import partial

from PyQt6 import uic

from airunner.widgets.slider.slider_widget import SliderWidget


class FilterBase:
    """
    FilterBase is used as a base class for all filters.
    """
    ui_name = ""
    window_title = ""
    _filter = None
    _filter_values = {}

    def __getattr__(self, item):
        if item in self._filter_values:
            val = self._filter_values[item].value
            val_type = self._filter_values[item].value_type
            if val_type == "int":
                return int(val)
            elif val_type == "float":
                return float(val)
            elif val_type == "bool":
                return val == "True"
            elif val_type == "str":
                return str(val)
            else:
                return val
        else:
            return super().__getattribute__(item)

    def __setattr__(self, key, value):
        if key in self._filter_values:
            self._filter_values[key].value = str(value)
            self.parent.settings_manager.save()
        else:
            super().__setattr__(key, value)

    @property
    def filter(self):
        if self._filter is None:
            module = importlib.import_module(f"airunner.filters.{self.image_filter_data.name}")
            class_ = getattr(module, self.image_filter_data.filter_class)
            kwargs = {}
            for k, v in self._filter_values.items():
                kwargs[k] = getattr(self, k)
            self._filter = class_(**kwargs)
        return self._filter

    def update_value(self, name, value):
        self._filter_values[name].value = str(value)
        self.parent.settings_manager.save()

    def update_canvas(self):
        self.canvas.update()

    def __init__(self, parent, model_name):
        """
        :param parent: the parent window (MainWindow instance)
        """
        # filter_values are the names of the ImageFilterValue objects in the database.
        # when the filter is shown, the values are loaded from the database
        # and stored in this dictionary.
        self._filter_values = {}

        self.filter_window = None
        self.parent = parent
        self.image_filter_model_name = model_name
        self.canvas = parent.canvas
        self.load_image_filter_data()

    def load_image_filter_data(self):
        self.image_filter_data = self.parent.settings_manager.get_image_filter(self.image_filter_model_name)
        for filter_value in self.image_filter_data.image_filter_values:
            self._filter_values[filter_value.name] = filter_value

    def show(self):
        self.filter_window = uic.loadUi(os.path.join(f"widgets/base_filter/templates/base_filter.ui"))
        self.filter_window.label.setText(self.image_filter_data.display_name)

        for key, filter_value in self._filter_values.items():
            if filter_value.value_type in ["float", "int"]:
                min_value = filter_value.min_value
                max_value = filter_value.max_value
                if not min_value:
                    min_value = 0
                if not max_value:
                    max_value = 100
                if filter_value.value_type == "float":
                #     path = "widgets/slider_spinbox_double.ui"
                    spinbox_value = float(filter_value.value)
                    slider_value = int(spinbox_value * max_value)
                else:
                #     path = "widgets/slider_spinbox.ui"
                    slider_value = int(filter_value.value)
                #     spinbox_value = int(filter_value.value)

                slider_spinbox_widget = SliderWidget(
                    slider_minimum=min_value,
                    slider_maximum=max_value,
                    spinbox_minimum=min_value / max_value,
                    spinbox_maximum=max_value / max_value,
                    current_value=slider_value
                )

                # slider_spinbox_widget = uic.loadUi(os.path.join(path))
                # slider_spinbox_widget.label.setText(filter_value.name.replace("_", " ").title())
                # slider_spinbox_widget.slider.setMinimum(min_value)
                # slider_spinbox_widget.slider.setMaximum(max_value)
                # slider_spinbox_widget.slider.setValue(slider_value)
                # spinbox_min_value = min_value / max_value
                # spinbox_max_value = max_value / max_value
                # if filter_value.value_type == "int":
                #     spinbox_min_value = int(spinbox_min_value)
                #     spinbox_max_value = int(spinbox_max_value)
                # slider_spinbox_widget.spinbox.setMinimum(spinbox_min_value)
                # slider_spinbox_widget.spinbox.setMaximum(spinbox_max_value)
                # slider_spinbox_widget.spinbox.setValue(spinbox_value)
                # slider_spinbox_widget.slider.valueChanged.connect(
                #     partial(self.handle_slider_change, slider_spinbox_widget, filter_value))
                # slider_spinbox_widget.spinbox.valueChanged.connect(
                #     partial(self.handle_spinbox_change, slider_spinbox_widget, filter_value))
                self.filter_window.content.layout().addWidget(slider_spinbox_widget)

        self.filter_window.auto_apply.setChecked(self.image_filter_data.auto_apply)
        self.filter_window.auto_apply.clicked.connect(partial(self.handle_auto_apply_toggle))

        self.filter_window.setWindowTitle(self.window_title)
        # on escape, call the "cancel" button on the QDialogButtonBox
        self.filter_window.keyPressEvent = lambda event: self.cancel_filter() if event.key() == 16777216 else None

        self.parent.current_filter = self.filter
        self.preview_filter()
        self.filter_window.exec()

    def handle_auto_apply_toggle(self):
        self.image_filter_data.auto_apply = self.filter_window.auto_apply.isChecked()
        self.parent.settings_manager.save()

    def handle_slider_change(self, slider_spinbox_widget, filter_value, val):
        if filter_value.value_type == "float":
            self.update_value(filter_value.name, val / filter_value.max_value)
        else:
            self.update_value(filter_value.name, val)
        slider_spinbox_widget.spinbox.setValue(float(val / filter_value.max_value))
        self.preview_filter()
        self.canvas.update()

    def handle_spinbox_change(self, slider_spinbox_widget, filter_value, val):
        if filter_value.value_type == "float":
            self.update_value(filter_value.name, val)
        else:
            self.update_value(filter_value.name, val * filter_value.max_value)
        slider_spinbox_widget.slider.setValue(int(val * filter_value.max_value))
        self.preview_filter()
        self.canvas.update()

    def cancel_filter(self):
        self.filter_window.close()
        self.parent.canvas.cancel_filter()
        self.update_canvas()

    def apply_filter(self):
        self.parent.canvas.apply_filter(self.filter)
        self.filter_window.close()
        self.update_canvas()

    def preview_filter(self):
        self.parent.canvas.preview_filter(self.filter)
        self.update_canvas()
