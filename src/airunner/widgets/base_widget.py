import os
from PyQt6 import QtGui
from PyQt6.QtWidgets import QWidget

from airunner.utils import get_main_window


class BaseWidget(QWidget):
    widget_class_ = None
    icons = ()
    ui = None
    qss_filename = None

    @property
    def is_dark(self):
        return self.app.settings["dark_mode_enabled"]

    @property
    def canvas(self):
        return self.app.canvas

    def add_to_grid(self, widget, row, column, row_span=1, column_span=1):
        self.layout().addWidget(widget, row, column, row_span, column_span)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = get_main_window()
        self.app.loaded.connect(self.initialize)
        
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
    
    def handle_settings_manager_changed(self, key, val, settings_manager):
        """
        Handle the change in settings manager.

        Args:
            key (str): The key of the changed setting.
            val: The new value of the changed setting.
            settings_manager: The settings manager object.

        Returns:
            None
        """
        print("handle_settings_manager_changed")
        pass
    
    def initialize(self):
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
            print(icon_name, widget_name)
            print(self.icons)
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
        target_val = self.app.settings_manager.get_value(settings_key_name)

        if val != target_val:
            if not self.set_plain_text(element, target_val):
                if not self.set_text(element, target_val):
                    if not self.set_value(element, target_val):
                        if not self.set_is_checked(element, target_val):
                            raise Exception(f"Could not set value for {element} to {target_val}")

