import os

from PySide6 import QtGui
from PySide6.QtWidgets import QWidget

from airunner.enums import CanvasToolName
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.mediator_mixin import MediatorMixin
from airunner.utils.create_worker import create_worker


class BaseWidget(
    QWidget,
    MediatorMixin,
    SettingsMixin
):
    widget_class_ = None
    icons = ()
    ui = None
    qss_filename = None
    threads = []

    @property
    def current_tool(self):
        return CanvasToolName(self.application_settings.current_tool)

    @property
    def is_dark(self):
        return self.application_settings.dark_mode_enabled

    def __init__(self, *args, **kwargs):
        MediatorMixin.__init__(self)
        
        super().__init__(*args, **kwargs)
        if self.widget_class_:
            self.ui = self.widget_class_()
        if self.ui:
            self.ui.setupUi(self)
            self.set_icons()

        self.signal_handlers: dict = {}
        self.services: dict = {}
        self.worker_class_map: dict = {}

    def initialize(self):
        """
        Call this function to initialize the widget.
        :return:
        """
        self.register_signals()
        self.initialize_workers()
        self.initialize_form()

    def register_signals(self):
        """
        Set signal_handlers dict in order to register signals.

        signal_handlers should be a dictionary of SignalCode enums and functions.
        Example:
        signal_handlers = {
            SignalCode.GET_SETTINGS: self.get_settings,
            SignalCode.SET_SETTINGS: self.set_settings
        }
        :return:
        """
        for signal, handler in self.signal_handlers.items():
            self.register(signal, handler)

    def initialize_workers(self):
        """
        Override this function to initialize workers.

        worker_class_map should be a dictionary of property names and worker classes.
        Example:
        worker_class_map = {
            "worker": WorkerClass
        }
        :return:
        """
        for property_name, worker_class_name_ in self.worker_class_map.items():
            worker = create_worker(worker_class_name_)
            setattr(self, property_name, worker)

    def initialize_form(self):
        pass

    def add_to_grid(self, widget, row, column, row_span=1, column_span=1):
        self.layout().addWidget(widget, row, column, row_span, column_span)
    
    def showEvent(self, event):
        super().showEvent(event)
        """
        Triggered when the app is loaded.
        Override this function in order to initialize the widget rather than
        using __init__.
        """
        self.initialize()

    def set_icons(self):
        theme = "dark" if self.is_dark else "light"
        for icon_data in self.icons:
            icon_name = icon_data[0]
            widget_name = icon_data[1]
            icon = QtGui.QIcon()
            icon.addPixmap(
                QtGui.QPixmap(f":/icons/{theme}/{icon_name}.svg"),
                QtGui.QIcon.Mode.Normal,
                QtGui.QIcon.State.Off)
            getattr(self.ui, widget_name).setIcon(icon)
        self.update()

    def set_button_icon(self, is_dark, button_name, icon):
        try:
            getattr(self, button_name).setIcon(
                QtGui.QIcon(
                    os.path.join(f"src/icons/{icon}{'-light' if is_dark else ''}.png")
                )
            )
        except AttributeError as e:
            pass

    def get_form_element(self, element):
        return getattr(self.ui, element)

    def get_plain_text(self, element):
        try:
            return self.get_form_element(element).toPlainText()
        except AttributeError:
            return None

    def get_text(self, element):
        try:
            return self.get_form_element(element).text()
        except AttributeError:
            return None

    def get_value(self, element):
        try:
            return self.get_form_element(element).value()
        except AttributeError:
            return None

    def get_is_checked(self, element):
        try:
            return self.get_form_element(element).isChecked()
        except AttributeError:
            return None

    def set_plain_text(self, element, val):
        try:
            self.get_form_element(element).setPlainText(val)
            return True
        except AttributeError:
            return False

    def set_text(self, element, val):
        try:
            self.get_form_element(element).setText(val)
            return True
        except AttributeError:
            return False
        except TypeError:
            return False

    def set_value(self, element, val):
        try:
            self.get_form_element(element).setValue(val)
            return True
        except AttributeError:
            return False

    def set_is_checked(self, element, val):
        try:
            self.get_form_element(element).setChecked(val)
            return True
        except AttributeError:
            return False
