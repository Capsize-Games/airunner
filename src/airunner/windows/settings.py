from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor, QPainter
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QLabel, QWidget, QVBoxLayout

from airunner.windows.base_window import BaseWindow
# open the version file from the root of the project and get the VERSION variable string from it
from airunner.windows.export_preferences_widget import ExportPreferencesWidget
from airunner.windows.grid_widget import GridWidget
from airunner.windows.hf_api_key_widget import HFAPIKeyWidget
from airunner.windows.memory_widget import MemoryWidget
from airunner.windows.paths_widget import PathsWidget


class HighlightDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_indexes = []

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        if index in self.selected_indexes:
            painter.save()
            painter.fillRect(option.rect, QBrush(QColor(0, 0, 255, 50)))  # Blue background color
            painter.restore()

        super().paint(painter, option, index)

    def add_selected_index(self, index):
        self.selected_indexes.append(index)

    def remove_selected_index(self, index):
        self.selected_indexes.remove(index)


class SettingsWindow(BaseWindow):
    template_name = "settings"
    window_title = "AI Runner Settings"
    is_modal = True

    def initialize_window(self):
        self.model = QStandardItemModel()
        self.template.directory.setModel(self.model)
        self.template.directory.setHeaderHidden(True)
        self.template.directory.setIndentation(20)

        directory = [
            {
                "section": "Import / Export Preferences",
                "files": [
                    {
                        "name": "paths",
                        "display_name": "Paths",
                        "checkable": False
                    },
                    {
                        "name": "export_preferences",
                        "display_name": "Image import / export",
                        "checkable": False
                    },
                    {
                        "name": "resize_on_import",
                        "display_name": "Resize on import",
                        "checkable": True
                    },
                    {
                        "name": "image_to_new_layer",
                        "display_name": "Image to new layer",
                        "checkable": True
                    }
                ]
            },
            {
                "section": "Grid & Canvas Preferences",
                "files": [
                    {
                        "name": "grid",
                        "display_name": "Grid",
                        "checkable": False
                    }
                ]
            },
            {
                "section": "Memory Preferences",
                "files": [
                    {
                        "name": "memory",
                        "display_name": "Memory",
                        "checkable": False
                    }
                ]
            },
            {
                "section": "Miscellaneous Preferences",
                "files": [
                    {
                        "name": "dark_mode",
                        "display_name": "Dark Mode",
                        "checkable": True
                    },
                    {
                        "name": "check_for_updates",
                        "display_name": "Check for updates",
                        "checkable": True
                    },
                    {
                        "name": "hf_api_key",
                        "display_name": "API Key",
                        "checkable": False
                    }
                    # {
                    #     "name": "reset_settings",
                    #     "display_name": "Reset settings to default",
                    #     "checkable": False
                    # }
                ]
            }
        ]
        for index, section in enumerate(directory):
            self.add_directory(section["section"])
            for file in section["files"]:
                self.add_file(
                    self.model.item(index),
                    file["name"],
                    file["display_name"],
                    file["checkable"]
                )

        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.template.preferences.setWidget(self.scroll_widget)

        self.highlight_delegate = HighlightDelegate(self.template.directory)
        self.template.directory.setItemDelegate(self.highlight_delegate)

        self.template.directory.clicked.connect(self.on_item_clicked)

        # expand all directories
        for i in range(self.model.rowCount()):
            index = self.model.index(i, 0)
            self.template.directory.setExpanded(index, True)

    def add_directory(self, name, checkable=False):
        item = QStandardItem(name)
        item.setCheckable(checkable)
        if checkable:
            checked = False
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setData(name, Qt.ItemDataRole.DisplayRole)
        item.setSizeHint(QSize(0, 24))
        self.model.appendRow(item)

    def add_file(self, parent_item, name, display_name, checkable=False):
        file_item = QStandardItem(display_name)
        file_item.setCheckable(checkable)
        if checkable:
            checked = False
            if name == "resize_on_import":
                checked = self.settings_manager.settings.resize_on_paste.get()
            elif name == "image_to_new_layer":
                checked = self.settings_manager.settings.image_to_new_layer.get()
            elif name == "dark_mode":
                checked = self.settings_manager.settings.dark_mode_enabled.get()
            elif name == "check_for_updates":
                checked = self.settings_manager.settings.latest_version_check.get()

            file_item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        # prevent file_item from being edited
        file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        file_item.setData(name, Qt.ItemDataRole.UserRole)
        file_item.setData(display_name, Qt.ItemDataRole.DisplayRole)
        file_item.setSizeHint(QSize(0, 24))
        parent_item.appendRow(file_item)

    def on_item_clicked(self, index):
        item = self.model.itemFromIndex(index)
        if item.parent() is None:
            return
        section = item.parent().data(Qt.ItemDataRole.DisplayRole)
        name = item.data(Qt.ItemDataRole.UserRole)
        display_name = item.data(Qt.ItemDataRole.DisplayRole)

        if name == "resize_on_import":
            checked = item.checkState() == Qt.CheckState.Checked
            self.settings_manager.settings.resize_on_paste.set(checked)
        elif name == "image_to_new_layer":
            checked = item.checkState() == Qt.CheckState.Checked
            self.settings_manager.settings.image_to_new_layer.set(checked)
        elif name == "dark_mode":
            checked = item.checkState() == Qt.CheckState.Checked
            self.settings_manager.settings.dark_mode_enabled.set(checked)
            self.app.toggle_darkmode()
        elif name == "check_for_updates":
            checked = item.checkState() == Qt.CheckState.Checked
            self.settings_manager.settings.latest_version_check.set(checked)
        elif name == "reset_settings":
            self.app.reset_settings()
        else:
            self.show_content(section, display_name, name)

    def show_content(self, section, display_name, name):
        # create a label widget
        label = QLabel(f"<p><b>{section} > {display_name}</b></p>")

        widget_object = None
        widgets = {
            "paths": PathsWidget,
            "export_preferences": ExportPreferencesWidget,
            "grid": GridWidget,
            "memory": MemoryWidget,
            "hf_api_key": HFAPIKeyWidget,
        }
        if name in widgets:
            widget_object = widgets[name](
                app=self.app,
                settings_manager=self.settings_manager
            )

        self.clear_scroll_area()
        self.scroll_layout.addWidget(label)
        if widget_object:
            self.scroll_layout.addWidget(widget_object)

    def clear_scroll_area(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
