import importlib
import os
from functools import partial

from PyQt6 import uic
from airunner.data.session_scope import session_scope

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
        with self.parent.settings_manager.image_filter_by_name(self.image_filter_model_name) as image_filter:
            module = importlib.import_module(f"airunner.filters.{image_filter.name}")
            class_ = getattr(module, image_filter.filter_class)
        kwargs = {}
        for k, v in self._filter_values.items():
            kwargs[k] = getattr(self, k)
        self._filter = class_(**kwargs)
        return self._filter
    
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
        self.load_image_filter_data()

    def update_value(self, name, value):
        self._filter_values[name].value = str(value)
        self.parent.settings_manager.save()

    def update_canvas(self):
        pass

    def load_image_filter_data(self):
        print("LOAD FILTER DATA")
        with self.parent.settings_manager.image_filter_by_name(self.image_filter_model_name) as image_filter:
            for filter_value in image_filter.image_filter_values:
                self._filter_values[filter_value.name] = filter_value
        print(self._filter_values)

    def show(self):
        self.filter_window = uic.loadUi(os.path.join(f"widgets/base_filter/templates/base_filter.ui"))
        with self.parent.settings_manager.image_filter_by_name(self.image_filter_model_name) as image_filter:
            self.filter_window.label.setText(image_filter.display_name)
        self.reject = self.filter_window.reject
        self.accept = self.filter_window.accept
        self.filter_window.reject = self.cancel_filter
        self.filter_window.accept = self.apply_filter
        
        with session_scope() as session:
            for key, filter_value in self._filter_values.items():
                session.add(filter_value)
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

        with self.parent.settings_manager.image_filter_by_name(self.image_filter_model_name) as image_filter:
            self.filter_window.auto_apply.setChecked(image_filter.auto_apply)
        self.filter_window.auto_apply.clicked.connect(partial(self.handle_auto_apply_toggle))

        self.filter_window.setWindowTitle(self.window_title)
        # on escape, call the "cancel" button on the QDialogButtonBox
        self.filter_window.keyPressEvent = lambda event: self.cancel_filter() if event.key() == 16777216 else None

        self.preview_filter()
        self.filter_window.exec()

    def handle_auto_apply_toggle(self):
        with self.parent.settings_manager.image_filter_by_name(self.image_filter_model_name) as image_filter:
            image_filter.auto_apply = self.filter_window.auto_apply.isChecked()
        self.parent.settings_manager.save()

    def handle_slider_change(self, settings_property, val):
        self.update_value(settings_property, val)
        self.preview_filter()
        self.update_canvas()

    def cancel_filter(self):
        self.reject()
        self.parent.canvas_widget.cancel_filter()
        self.update_canvas()

    def apply_filter(self):
        self.accept()
        self.parent.canvas_widget.apply_filter(self.filter)
        self.filter_window.close()
        self.update_canvas()

    def preview_filter(self):
        self.parent.canvas_widget.preview_filter(self.filter)
        self.update_canvas()
