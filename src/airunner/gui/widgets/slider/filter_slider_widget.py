from typing import Any

from airunner.gui.widgets.slider.slider_widget import SliderWidget


class FilterSliderWidget(SliderWidget):
    def __init__(self, *args, filter_value, preview_filter, **kwargs):
        self._filter_value = filter_value
        self.preview_filter = preview_filter
        super().__init__(*args, **kwargs)

    def init(self, **kwargs):
        if kwargs is not None and kwargs != {}:
            super().init(**kwargs)
        return

    def get_settings_value(self, settings_property):
        value_type = self._filter_value.value_type
        if value_type == "float":
            return float(self._filter_value.value)
        elif value_type == "int":
            return int(self._filter_value.value)
        else:
            return self._filter_value.value

    def set_settings_value(self, settings_property: str, val: Any):
        self._filter_value.value = val
        self._filter_value.save()
        self.preview_filter()
