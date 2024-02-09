import importlib
from functools import partial

from airunner.enums import SignalCode
from airunner.widgets.slider.slider_widget import SliderWidget
from airunner.windows.base_window import BaseWindow
from airunner.windows.filter_window_ui import Ui_filter_window


class FilterWindow(BaseWindow):
    """
    FilterWindow is used as a base class for all filters.
    """
    template_class_ = Ui_filter_window
    window_title = ""
    _filter_values = {}

    def __init__(self, model_name):
        """
        :param model_name: The name of the filter model to use.
        """
        # filter_values are the names of the ImageFilterValue objects in the database.
        # when the filter is shown, the values are loaded from the database
        # and stored in this dictionary.
        super().__init__(exec=False)

        self.reject = None
        self.accept = None
        self._filter = None
        self._filter_values = {}
        self.image_filter_model_name = model_name
        self.load_image_filter_data()
        self.init()
        self.exec()

    # def __getattr__(self, item):
    #     if item in self._filter_values:
    #         val = self._filter_values[item].value
    #         val_type = self._filter_values[item].value_type
    #         if val_type == "int":
    #             return int(val)
    #         elif val_type == "float":
    #             return float(val)
    #         elif val_type == "bool":
    #             return val == "True"
    #         elif val_type == "str":
    #             return str(val)
    #         else:
    #             return val
    #     else:
    #         try:
    #             return super().__getattribute__(item)
    #         except AttributeError:
    #             print(f"Attribute {item} not found")

    # def __setattr__(self, key, value):
    #     if key in self._filter_values:
    #         self._filter_values[key].value = str(value)
    #         print("TODO: save filter value")
    #     else:
    #         super().__setattr__(key, value)

    def filter_object(self):
        image_filter = self.image_filter_by_name(self.image_filter_model_name)
        filter_name = image_filter['name']
        module = importlib.import_module(f"airunner.filters.{filter_name}")
        class_ = getattr(module, image_filter["filter_class"])
        kwargs = {}
        for k, v in self._filter_values[filter_name]["image_filter_values"].items():
            val_type = v["value_type"]
            val = v["value"]
            if val_type == "int":
                val = int(val)
            elif val_type == "float":
                val = float(val)
            elif val_type == "bool":
                val = val == "True"
            kwargs[k] = val
        self._filter = class_(**kwargs)
        return self._filter

    def image_filter_by_name(self, name):
        data = self.settings["image_filters"]
        return [filter_data for filter_name, filter_data in data.items() if filter_name == name][0]

    def update_value(self, settings_property, value):
        settings_property = settings_property.replace('image_filters.', '')
        keys = settings_property.split(".")
        data = self._filter_values
        for index, k in enumerate(keys):
            if index == len(keys) - 1:
                data[k] = str(value)
            else:
                data = data[k]

    def load_image_filter_data(self):
        filter_data = self.image_filter_by_name(self.image_filter_model_name)
        self._filter_values[filter_data["name"]] = filter_data

    def init(self):
        image_filters = self.settings["image_filters"]
        image_filter = None
        for filter_name, filter_data in image_filters.items():
            if filter_data['name'] == self.image_filter_model_name:
                image_filter = filter_data
                break

        self.reject = self.reject
        self.accept = self.accept
        self.reject = self.cancel_filter
        self.accept = self.apply_filter

        for filter_name, filter_data in image_filter['image_filter_values'].items():
            self._filter_values[filter_name] = filter_data
            if filter_data['value_type'] in ["float", "int"]:
                min_value = int(filter_data['min_value']) if filter_data['min_value'] else 0
                max_value = int(filter_data['max_value']) if filter_data['max_value'] else 100

                if filter_data['value_type'] == "float":
                    spinbox_value = float(filter_data['value'])
                    slider_value = int(spinbox_value * max_value)
                else:
                    slider_value = int(filter_data['value'])

                spinbox_minimum = min_value
                spinbox_maximum = max_value

                if filter_data['value_type'] == "float":
                    spinbox_minimum = float(min_value) / max_value
                    spinbox_maximum = float(max_value) / max_value

                slider_spinbox_widget = SliderWidget()
                settings_property = ".".join([
                    "image_filters",
                    image_filter["name"],
                    "image_filter_values",
                    filter_data["name"],
                    "value"
                ])
                slider_spinbox_widget.init(
                    slider_callback=self.handle_slider_change,
                    slider_minimum=min_value,
                    slider_maximum=max_value,
                    spinbox_minimum=spinbox_minimum,
                    spinbox_maximum=spinbox_maximum,
                    current_value=slider_value,
                    settings_property=settings_property,
                    label_text=filter_data['name'].replace("_", " ").title(),
                    display_as_float=filter_data['value_type'] == "float",
                )
                self.ui.content.layout().addWidget(slider_spinbox_widget)

        self.ui.auto_apply.setChecked(image_filter['auto_apply'])
        self.ui.auto_apply.clicked.connect(partial(self.handle_auto_apply_toggle))

        self.setWindowTitle(self.window_title)
        # on escape, call the "cancel" button on the QDialogButtonBox
        self.keyPressEvent = lambda event: self.cancel_filter() if event.key() == 16777216 else None

        self.preview_filter()

    def handle_auto_apply_toggle(self):
        image_filter = self.image_filter_by_name(self.image_filter_model_name)
        image_filter["auto_apply"] = self.ui.auto_apply.isChecked()

    def handle_slider_change(self, settings_property, val):
        self.update_value(settings_property, val)
        self.preview_filter()

    def cancel_filter(self):
        self.emit(
            SignalCode.CANVAS_CANCEL_FILTER_SIGNAL
        )
        self.close()

    def apply_filter(self):
        self.emit(
            SignalCode.CANVAS_APPLY_FILTER_SIGNAL,
            self.filter_object()
        )
        self.close()

    def preview_filter(self):
        self.emit(
            SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL,
            self.filter_object()
        )