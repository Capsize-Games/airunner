from typing import Dict, List, Optional, Tuple
from abc import ABC, ABCMeta
from abc import abstractmethod
import os

from PySide6 import QtGui
from PySide6.QtWidgets import QWidget

from airunner.enums import CanvasToolName
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.mediator_mixin import MediatorMixin
from airunner.utils import create_worker
from airunner.utils.widgets import (
    save_splitter_settings, 
    load_splitter_settings
)
from airunner.enums import SignalCode


class BaseABCMeta(type(QWidget), ABCMeta):
    pass


class AbstractBaseWidget(
    MediatorMixin,
    SettingsMixin,
    QWidget,
    ABC,
    metaclass=BaseABCMeta
):
    @abstractmethod
    def save_state(self):
        """
        Save the state of the widget.
        """

    @abstractmethod
    def restore_state(self):
        """
        Restore the state of the widget.
        """


class BaseWidget(AbstractBaseWidget):
    """
    Base class for all widgets.
    """
    widget_class_: Optional[object] = None
    icons: List[Optional[Tuple[str, str]]] = []
    ui: Optional[object] = Optional[None]
    _splitters: List[str] = []

    def __init__(self, *args, **kwargs):
        self.signal_handlers = self.signal_handlers or {}
        self.signal_handlers.update({
            SignalCode.QUIT_APPLICATION: self.handle_close
        })
        super().__init__(*args, **kwargs)
        if self.widget_class_:
            self.ui = self.widget_class_()
        if self.ui:
            self.ui.setupUi(self)
            self.set_icons()

        self.services: Dict = {}
        self.worker_class_map: Dict = {}
    
    @property
    def splitters(self) -> List[str]:
        """
        Return a list of splitter names as they appear in the UI.
        """
        return self._splitters
    
    @splitters.setter
    def splitters(self, value: List[str]):
        """
        Set the list of splitter names as they appear in the UI.
        """
        self._splitters = value

    @property
    def current_tool(self) -> CanvasToolName:
        return CanvasToolName(self.application_settings.current_tool)

    @property
    def is_dark(self) -> bool:
        return self.application_settings.dark_mode_enabled
    
    def initialize(self):
        """
        Call this function to initialize the widget.
        :return:
        """
        self.initialize_workers()
        self.initialize_form()

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
    
    def showEvent(self, event):
        super().showEvent(event)
        """
        Triggered when the app is loaded.
        Override this function in order to initialize the widget rather than
        using __init__.
        """
        self.initialize()
        self.restore_state()
    
    def save_state(self):
        """
        Called on close and saves the state of all splitter widgets
        """
        save_splitter_settings(
            self.ui,
            self.splitters
        )
    
    def restore_state(self):
        """
        Restore the state of the widget.
        """
        load_splitter_settings(
            self.ui,
            self.splitters
        )
    
    def handle_close(self):
        """
        Callback for the QUIT_APPLICATION signal.
        """
        self.save_state()

    def set_icons(self):
        """
        Set the icons for the widget which alternate between 
        light and dark mode.
        """
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
                    os.path.join(
                        f"src/icons/{icon}{'-light' if is_dark else ''}.png"
                    )
                )
            )
        except AttributeError as _e:
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
