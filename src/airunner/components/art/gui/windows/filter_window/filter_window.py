import importlib

from airunner.components.art.data.image_filter import ImageFilter
from airunner.components.art.utils.image_filter_utils import (
    FilterValueData,
    get_filter_values,
    build_filter_instance,
)
from airunner.components.art.gui.widgets.filter_parameter_widget import (
    create_filter_parameter_widgets,
)
from airunner.components.application.gui.windows.base_window import BaseWindow
from airunner.components.art.gui.windows.filter_window.filter_window_ui import (
    Ui_filter_window,
)
from PySide6.QtCore import QTimer


class FilterWindow(BaseWindow):
    """
    FilterWindow is used as a base class for all filters.
    Uses shared utilities to avoid code duplication with filter nodes.
    """

    template_class_ = Ui_filter_window
    window_title = ""
    _filter_values = []
    _parameter_widgets = []

    def __init__(self, image_filter_id):
        """
        :param image_filter_id: The ID of the filter to load.
        """
        super().__init__(exec=False)

        # Load the filter definition
        self.image_filter = ImageFilter.objects.get(
            image_filter_id, eager_load=["image_filter_values"]
        )
        self.image_filter_model_name = self.image_filter.name
        self.window_title = self.image_filter.display_name
        self._filter = None

        # Load filter values using shared utility
        self._filter_values = get_filter_values(image_filter_id)

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(250)  # 250ms debounce
        self._debounce_timer.timeout.connect(self._do_preview_filter)

        self.exec()

    def showEvent(self, event):
        """Create parameter widgets using shared utility."""
        # Use shared utility to create parameter widgets
        self._parameter_widgets = create_filter_parameter_widgets(
            filter_values=self._filter_values,
            on_value_changed=self.preview_filter,
            parent=self.ui.content,
        )

        # Add widgets to layout
        for widget in self._parameter_widgets:
            self.ui.content.layout().addWidget(widget)

        self.setWindowTitle(self.window_title)
        self.preview_filter()

    def keyPressEvent(self, event):
        if event.key() == 16777216:
            self.reject()

    def filter_object(self):
        """Build filter instance using shared utility."""
        # Get current parameter values from widgets
        param_overrides = {}
        for widget in self._parameter_widgets:
            value = widget.get_value()
            if value is not None:
                param_overrides[widget.filter_value.name] = value

        # Build filter instance using shared utility
        self._filter = build_filter_instance(
            filter_name=self.image_filter.name,
            overrides=param_overrides,
        )
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
