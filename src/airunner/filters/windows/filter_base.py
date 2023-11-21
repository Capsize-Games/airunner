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
        module = importlib.import_module(f"airunner.filters.{self.image_filter_data.name}")
        class_ = getattr(module, self.image_filter_data.filter_class)
        kwargs = {}
        for k, v in self._filter_values.items():
            kwargs[k] = getattr(self, k)
        self._filter = class_(**kwargs)
        return self._filter

    @property
    def current_canvas(self):
        if self.parent.image_editor_tab_name == "Canvas":
            return self.canvas
        return self.standard_image_panel

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
        self.standard_image_panel = parent.standard_image_panel
        self.load_image_filter_data()

    def update_value(self, name, value):
        self._filter_values[name].value = str(value)
        self.parent.settings_manager.save()

    def update_canvas(self):
        if self.parent.image_editor_tab_name == "Canvas":
            self.canvas.update()

    def load_image_filter_data(self):
        self.image_filter_data = self.parent.settings_manager.get_image_filter(self.image_filter_model_name)
        for filter_value in self.image_filter_data.image_filter_values:
            self._filter_values[filter_value.name] = filter_value

    def show(self):
        self.filter_window = uic.loadUi(os.path.join(f"widgets/base_filter/templates/base_filter.ui"))
        self.filter_window.label.setText(self.image_filter_data.display_name)
        self.reject = self.filter_window.reject
        self.accept = self.filter_window.accept
        self.filter_window.reject = self.cancel_filter
        self.filter_window.accept = self.apply_filter
        
        for key, filter_value in self._filter_values.items():
            if filter_value.value_type in ["float", "int"]:
                min_value = filter_value.min_value
                max_value = filter_value.max_value
                if not min_value:
                    min_value = 0
                if not max_value:
                    max_value = 100

                if filter_value.value_type == "float":
                    spinbox_value = float(filter_value.value)
                    slider_value = int(spinbox_value * max_value)
                else:
                    slider_value = int(filter_value.value)
                
                spinbox_minimum = min_value
                spinbox_maximum = max_value

                if filter_value.value_type == "float":
                    spinbox_minimum = float(min_value) / max_value
                    spinbox_maximum = float(max_value) / max_value

                slider_spinbox_widget = SliderWidget()
                slider_spinbox_widget.initialize_properties(
                    slider_callback=self.handle_slider_change,
                    slider_minimum=min_value,
                    slider_maximum=max_value,
                    spinbox_minimum=spinbox_minimum,
                    spinbox_maximum=spinbox_maximum,
                    current_value=slider_value,
                    settings_property=filter_value.name,
                    label_text=key.replace("_", " ").title(),
                    display_as_float=filter_value.value_type == "float",
                )
                self.filter_window.content.layout().addWidget(slider_spinbox_widget)

        self.filter_window.auto_apply.setChecked(self.image_filter_data.auto_apply)
        self.filter_window.auto_apply.clicked.connect(partial(self.handle_auto_apply_toggle))

        self.filter_window.setWindowTitle(self.window_title)
        # on escape, call the "cancel" button on the QDialogButtonBox
        self.filter_window.keyPressEvent = lambda event: self.cancel_filter() if event.key() == 16777216 else None

        self.preview_filter()
        self.filter_window.exec()

    def handle_auto_apply_toggle(self):
        self.image_filter_data.auto_apply = self.filter_window.auto_apply.isChecked()
        self.parent.settings_manager.save()

    def handle_slider_change(self, val, settings_property):
        self.update_value(settings_property, val)
        self.preview_filter()
        self.update_canvas()

    def cancel_filter(self):
        self.reject()
        #self.filter_window.close()
        self.current_canvas.cancel_filter()
        self.update_canvas()

    def apply_filter(self):
        self.accept()
        self.current_canvas.apply_filter(self.filter)
        self.filter_window.close()
        self.update_canvas()

    def preview_filter(self):
        self.current_canvas.preview_filter(self.filter)
        self.update_canvas()
