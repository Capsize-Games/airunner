import importlib


from airunner.data.models import ImageFilter
from airunner.components.art.data.image_filter_value import ImageFilterValue
from airunner.components.application.gui.widgets.slider.filter_slider_widget import FilterSliderWidget
from airunner.gui.windows.base_window import BaseWindow
from airunner.components.art.gui.windows.filter_window.filter_window_ui import Ui_filter_window
from PySide6.QtCore import QTimer


class FilterWindow(BaseWindow):
    """
    FilterWindow is used as a base class for all filters.
    """

    template_class_ = Ui_filter_window
    window_title = ""
    _filter_values = {}

    class FilterValueData:
        def __init__(self, d):
            self.__dict__.update(d)

        def save(self):
            ImageFilterValue.objects.update(self.id, value=self.value)

    def __init__(self, image_filter_id):
        """
        :param image_filter_id: The ID of the filter to load.
        """
        super().__init__(exec=False)

        # Eagerly load all filter values as dicts to avoid DetachedInstanceError
        self.image_filter = ImageFilter.objects.get(
            image_filter_id, eager_load=["image_filter_values"]
        )
        self.image_filter_model_name = self.image_filter.name
        self.window_title = self.image_filter.display_name
        self._filter = None

        # Convert filter values to dicts to avoid ORM detachment issues
        self._filter_values = []
        filter_values = ImageFilterValue.objects.filter_by(
            image_filter_id=image_filter_id
        )
        for fv in filter_values:
            self._filter_values.append(
                self.FilterValueData(
                    {
                        "id": fv.id,
                        "name": fv.name,
                        "value": fv.value,
                        "value_type": fv.value_type,
                        "min_value": fv.min_value,
                        "max_value": fv.max_value,
                    }
                )
            )

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(250)  # 250ms debounce
        self._debounce_timer.timeout.connect(self._do_preview_filter)

        self.exec()

    def showEvent(self, event):
        for filter_value in self._filter_values:
            if filter_value.value_type in ("float", "int"):
                min_value = (
                    int(filter_value.min_value)
                    if filter_value.min_value is not None
                    else 0
                )
                max_value = (
                    int(filter_value.max_value)
                    if filter_value.max_value is not None
                    else 100
                )

                if filter_value.value_type == "float":
                    spinbox_value = float(filter_value.value)
                    slider_value = int(spinbox_value * max_value)
                else:
                    slider_value = int(filter_value.value)

                spinbox_minimum = min_value
                spinbox_maximum = max_value

                if filter_value.value == "float":
                    spinbox_minimum = float(min_value) / max_value
                    spinbox_maximum = float(max_value) / max_value

                slider_spinbox_widget = FilterSliderWidget(
                    filter_value=filter_value,
                    preview_filter=self.preview_filter,
                )
                settings_property = ".".join(
                    ["image_filter_values", filter_value.name, "value"]
                )
                slider_spinbox_widget.init(
                    slider_minimum=min_value,
                    slider_maximum=max_value,
                    spinbox_minimum=spinbox_minimum,
                    spinbox_maximum=spinbox_maximum,
                    current_value=slider_value,
                    settings_property=settings_property,
                    label_text=filter_value.name.replace("_", " ").title(),
                    display_as_float=filter_value.value_type == "float",
                )
                self.ui.content.layout().addWidget(slider_spinbox_widget)

        self.setWindowTitle(self.window_title)
        self.preview_filter()

    def keyPressEvent(self, event):
        if event.key() == 16777216:
            self.reject()

    def filter_object(self):
        filter_name = self.image_filter.name
        module = importlib.import_module(
            f"airunner.components.art.filters.{filter_name}"
        )
        class_ = getattr(module, self.image_filter.filter_class)
        kwargs = {}

        filter_values = ImageFilterValue.objects.filter_by(
            image_filter_id=self.image_filter.id
        )

        for image_filter_value in filter_values:
            val_type = image_filter_value.value_type
            val = image_filter_value.value
            if val_type == "int":
                val = int(val)
            elif val_type == "float":
                val = float(val)
            elif val_type == "bool":
                val = val == "True"
            kwargs[image_filter_value.name] = val
        self._filter = class_(**kwargs)
        return self._filter

    def reject(self):
        self.api.art.image_filter.cancel()
        super().reject()

    def accept(self):
        self.api.art.image_filter.apply(self.filter_object())
        super().accept()

    def preview_filter(self):
        # Debounce the preview call
        self._debounce_timer.stop()
        self._debounce_timer.start()

    def _do_preview_filter(self):
        self.api.art.image_filter.preview(self.filter_object())
