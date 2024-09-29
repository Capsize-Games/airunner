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
        font_setting = self.get_font_setting_by_name(self.section)
        self.ui.font_family.blockSignals(True)
        self.ui.font_family.clear()
        self.ui.font_family.addItems(QFontDatabase().families())
        self.ui.font_family.setCurrentText(font_setting.font_family)
        self.ui.font_family.blockSignals(False)

    def initialize_font_size(self):
        font_setting = self.get_font_setting_by_name(self.section)
        self.ui.size.blockSignals(True)
        self.ui.size.setValue(font_setting.font_size)
        self.ui.size.blockSignals(False)

    @Slot(int)
    def size_changed(self, size: int):
        font_setting = self.get_font_setting_by_name(self.section)
        font_setting.font_size = size
        self.update_font_setting(font_setting)

    @Slot(str)
    def font_family_changed(self, family: str):
        font_setting = self.get_font_setting_by_name(self.section)
        font_setting.font_family = family
        self.update_font_setting(font_setting)
