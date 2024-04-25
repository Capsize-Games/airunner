from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.facehugger.nullscream.templates.nullscream_ui import Ui_nullscream
from airunner.widgets.llm.templates.message_ui import Ui_message

from PySide6.QtCore import Signal, Slot


class NullscreamWidget(BaseWidget):
    widget_class_ = Ui_nullscream

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL,
            self.on_application_main_window_loaded_signal
        )
        self.__data: dict = {}
        self.__filter_blocked = ""
        self.__filter_allowed = ""
        self.__formatted_blocked = ""
        self.__formatted_allowed = ""

    @Slot(str)
    def filter_blocked(self, val: str):
        self.ui.blocked.setPlainText(val)
        self.__filter_blocked = val
        self.display_lists()

    @Slot(str)
    def filter_allowed(self, val: str):
        self.ui.allowed.setPlainText(val)
        self.__filter_allowed = val
        self.display_lists()

    @property
    def data(self):
        data = self.__data.copy()
        if self.__filter_blocked != "":
            data["blocked"] = {k: v for k, v in data["blocked"].items() if self.__filter_blocked in k}
        if self.__filter_allowed != "":
            data["allowed"] = {k: v for k, v in data["allowed"].items() if self.__filter_allowed in k}
        return data

    def on_application_main_window_loaded_signal(self, data: dict):
        self.__data = data["main_window"].defendatron.nullscream_tracker.data
        self.display_lists()

    def display_lists(self):
        self.clear_lists()
        for root, data in self.data["allowed"].items():
            total = data["total"]
            self.__formatted_allowed += f"{root} total: {total}\n"
            for module in data["modules"]:
                if "airunner" not in module:
                    self.__formatted_allowed += f"    {module}\n"
        for root, data in self.data["blocked"].items():
            total = data["total"]
            self.__formatted_blocked += f"{root} total: {total}\n"
            for module in data["modules"]:
                if "airunner" not in module:
                    self.__formatted_blocked += f"    {module}\n"
        self.ui.allowed.setText(self.__formatted_allowed)
        self.ui.blocked.setText(self.__formatted_blocked)

    def clear_lists(self):
        self.__formatted_blocked = ""
        self.__formatted_allowed = ""
        self.ui.blocked.clear()
        self.ui.allowed.clear()
        self.ui.blocked.setPlainText("")
        self.ui.allowed.setPlainText("")
