from PySide6.QtCore import Slot
from PySide6.QtGui import QFontDatabase

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.font_settings.templates.font_setting_ui import Ui_font_setting_widget


class FontSettingWidget(BaseWidget):
    widget_class_ = Ui_font_setting_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.section = None

    def initialize(self):
        super().initialize()
        self.section = self.property("section")
        self.initialize_font_family()
        self.initialize_font_size()
        self.ui.section.setTitle(self.section.capitalize() + " Font")

    def initialize_font_family(self):
        self.ui.font_family.blockSignals(True)
        self.ui.font_family.clear()
        self.ui.font_family.addItems(QFontDatabase().families())
        print(self.settings["font_settings"])
        print(self.section)
        print(self.settings["font_settings"][self.section]["font_family"])
        self.ui.font_family.setCurrentText(self.settings["font_settings"][self.section]["font_family"])
        self.ui.font_family.blockSignals(False)

    def initialize_font_size(self):
        self.ui.size.blockSignals(True)
        self.ui.size.setValue(self.settings["font_settings"][self.section]["size"])
        self.ui.size.blockSignals(False)

    @Slot(int)
    def size_changed(self, size: int):
        settings = self.settings
        settings["font_settings"][self.section]["size"] = size
        self.settings = settings

    @Slot(str)
    def font_family_changed(self, family: str):
        settings = self.settings
        settings["font_settings"][self.section]["font_family"] = family
        self.settings = settings
