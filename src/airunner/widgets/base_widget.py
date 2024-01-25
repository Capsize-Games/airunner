import os
from PyQt6 import QtGui
from PyQt6.QtWidgets import QWidget
from airunner.aihandler.logger import Logger

from airunner.utils import get_main_window
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator
from airunner.windows.main.settings_mixin  import SettingsMixin

class BaseWidget(QWidget, SettingsMixin, MediatorMixin):
    widget_class_ = None
    icons = ()
    ui = None
    qss_filename = None

    def register_service(self, name, service):
        ServiceLocator.register(name, service)
    
    def get_service(self, name):
        return ServiceLocator.get(name)

    @property
    def is_dark(self):
        if not "dark_mode_enabled" in self.settings:
            return False
        return self.settings["dark_mode_enabled"]

    threads = []

    def add_to_grid(self, widget, row, column, row_span=1, column_span=1):
        self.layout().addWidget(widget, row, column, row_span, column_span)

    def __init__(self, *args, **kwargs):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super().__init__(*args, **kwargs)
        self.logger = Logger(prefix=self.__class__.__name__)
        
        if self.widget_class_:
            self.ui = self.widget_class_()
        if self.ui:
            self.ui.setupUi(self)
            # if self.qss_filename:
            #     theme_name = "dark_theme"
            #     here = os.path.dirname(os.path.realpath(__file__))
            #     with open(os.path.join(here, "..", "styles", theme_name, self.qss_filename), "r") as f:
            #         stylesheet = f.read()
            #     self.setStyleSheet(stylesheet)
            self.set_icons()
    
    def showEvent(self, event):
        super().showEvent(event)
        """
        Triggered when the app is loaded.
        Override this function in order to initialize the widget rather than
        using __init__.
        """
        pass
    
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

    def set_form_value(self, element, settings_key_name):
        val = self.get_plain_text(element)
        if val is None:
            val = self.get_text(element)
        if val is None:
            val = self.get_value(element)
        if val is None:
            val = self.get_is_checked(element)
        print("TODO: finish this")

