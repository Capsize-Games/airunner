from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor, QPainter
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QLabel, QWidget, QVBoxLayout, QPlainTextEdit

from airunner.enums import SignalCode
from airunner.widgets.api_token.api_token_widget import APITokenWidget
from airunner.widgets.export_preferences.export_preferences_widget import ExportPreferencesWidget
from airunner.widgets.grid_preferences.grid_preferences_widget import GridPreferencesWidget
from airunner.widgets.image_generator_preferences.image_generator_preferences_widget import ImageGeneratorPreferencesWidget

from airunner.widgets.keyboard_shortcuts.keyboard_shortcuts_widget import KeyboardShortcutsWidget
from airunner.widgets.llm.bot_preferences import BotPreferencesWidget
from airunner.widgets.llm.llm_settings_widget import LLMSettingsWidget
from airunner.widgets.memory_preferences.memory_preferences_widget import MemoryPreferencesWidget
from airunner.widgets.paths.paths_widget import PathsWidget
from airunner.widgets.tts.templates.tts_prefernces_widget import TTSPreferencesWidget
from airunner.windows.settings.templates.airunner_settings_ui import Ui_airunner_settings
from airunner.windows.base_window import BaseWindow


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
    is_modal = False
    template_class_ = Ui_airunner_settings
    # template_name = "airunner_settings"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = None
        self.scroll_widget = None
        self.scroll_layout = None
        self.highlight_delegate = None

    def initialize_window(self):
        self.model = QStandardItemModel()
        self.ui.directory.setModel(self.model)
        self.ui.directory.setHeaderHidden(True)
        self.ui.directory.setIndentation(20)

        directory = [
            {
                "section": "Image Generator Preferences",
                "files": [
                    {
                        "name": "image_generator_preferences",
                        "display_name": "Image Generator",
                        "checkable": False
                    }
                ]
            },
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
                        "checkable": True,
                        "description": "If enabled, images will be resized to the active grid area size when pasted."
                    },
                    {
                        "name": "image_to_new_layer",
                        "display_name": "Image to new layer",
                        "checkable": True,
                        "description": "If enabled, images will be pasted to a new layer."
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
                "section": "Keyboard Shortcuts",
                "files": [
                    {
                        "name": "keyboard_shortcuts",
                        "display_name": "Keyboard Shortcuts",
                        "checkable": False
                    }
                ]
            },
            {
                "section": "LLM Preferences",
                "files": [
                    {
                        "name": "llm_preferences",
                        "display_name": "LLM Preferences",
                        "checkable": False
                    },
                ]
            },
            {
                "section": "Text and Speech Preferences",
                "files": [
                    {
                        "name": "tts_preferences",
                        "display_name": "Text-to-Speech",
                        "checkable": False
                    },
                    {
                        "name": "bot_preferences",
                        "display_name": "Chatbot Preferences",
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
                        "checkable": True,
                        "description": "If enabled, AI Runner will use a dark theme."
                    },
                    {
                        "name": "check_for_updates",
                        "display_name": "Check for updates",
                        "checkable": True,
                        "description": "If enabled, AI Runner will check for updates on startup."
                    }
                ]
            },
            {
                "section": "Huggingface.co settings",
                "files": [
                    {
                        "name": "allow_online_mode",
                        "display_name": "Allow online connection",
                        "checkable": True,
                        "description": "Allow online connection to Huggingface.co to download missing models. If disabled, you will only be able to use models that are already downloaded. Requires a restart."
                    },
                    {
                        "name": "hf_api_key",
                        "display_name": "API Key",
                        "checkable": False
                    },
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
                    file["checkable"],
                    file["description"] if "description" in file else None
                )

        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.ui.preferences.setWidget(self.scroll_widget)

        self.highlight_delegate = HighlightDelegate(self.ui.directory)
        self.ui.directory.setItemDelegate(self.highlight_delegate)

        self.ui.directory.clicked.connect(self.on_item_clicked)

        # expand all directories
        for i in range(self.model.rowCount()):
            index = self.model.index(i, 0)
            self.ui.directory.setExpanded(index, True)

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

    def add_file(self, parent_item, name, display_name, checkable=False, description=None):
        file_item = QStandardItem(display_name)
        file_item.setCheckable(checkable)
        if checkable:
            checked = False
            if name == "resize_on_import":
                checked = self.settings["resize_on_paste"]
            elif name == "image_to_new_layer":
                checked = self.settings["image_to_new_layer"] is True
            elif name == "dark_mode":
                checked = self.settings["dark_mode_enabled"]
            elif name == "check_for_updates":
                checked = self.settings["latest_version_check"]
            elif name == "allow_online_mode":
                checked = self.settings["allow_online_mode"]

            file_item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        # prevent file_item from being edited
        file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        file_item.setData(name, Qt.ItemDataRole.UserRole)
        file_item.setData(display_name, Qt.ItemDataRole.DisplayRole)
        file_item.setData(description, Qt.ItemDataRole.ToolTipRole)
        file_item.setSizeHint(QSize(0, 24))
        parent_item.appendRow(file_item)

    def on_item_clicked(self, index):
        item = self.model.itemFromIndex(index)
        if item.parent() is None:
            return

        section = item.parent().data(Qt.ItemDataRole.DisplayRole)
        name = item.data(Qt.ItemDataRole.UserRole)
        display_name = item.data(Qt.ItemDataRole.DisplayRole)
        description = item.data(Qt.ItemDataRole.ToolTipRole)

        settings = self.settings

        if name == "resize_on_import":
            checked = item.checkState() == Qt.CheckState.Checked
            settings["resize_on_paste"] = checked
        elif name == "image_to_new_layer":
            checked = item.checkState() == Qt.CheckState.Checked
            settings["image_to_new_layer"] = checked
        elif name == "dark_mode":
            checked = item.checkState() == Qt.CheckState.Checked
            settings["dark_mode_enabled"] = checked
        elif name == "check_for_updates":
            checked = item.checkState() == Qt.CheckState.Checked
            settings["latest_version_check"] = checked
        elif name == "allow_online_mode":
            checked = item.checkState() == Qt.CheckState.Checked
            settings["allow_online_mode"] = checked
        elif name == "reset_settings":
            self.emit(SignalCode.APPLICATION_RESET_SETTINGS_SIGNAL)
        
        self.settings = settings
        self.show_content(section, display_name, name, description)

    def show_content(self, section, display_name, name, description):
        # create a label widget
        label = QLabel(f"<p><b>{section} > {display_name}</b></p>")

        widget_object = None
        widgets = {
            "image_generator_preferences": ImageGeneratorPreferencesWidget,
            "paths": PathsWidget,
            "keyboard_shortcuts": KeyboardShortcutsWidget,
            "export_preferences": ExportPreferencesWidget,
            "grid": GridPreferencesWidget,
            "memory": MemoryPreferencesWidget,
            "hf_api_key": APITokenWidget,
            "tts_preferences": TTSPreferencesWidget,
            "bot_preferences": BotPreferencesWidget,
            "llm_preferences": LLMSettingsWidget
        }
        if name in widgets:
            widget_object = widgets[name]()

        self.clear_scroll_area()
        self.scroll_layout.addWidget(label)
        if widget_object:
            self.scroll_layout.addWidget(widget_object)
        elif description:
            description_text_edit = QPlainTextEdit()
            description_text_edit.setReadOnly(True)
            description_text_edit.setPlainText(description)
            description_text_edit.setFrameStyle(0)
            description_text_edit.setStyleSheet("QPlainTextEdit { background-color: transparent; border: none; }")
            self.scroll_layout.addWidget(description_text_edit)

    def clear_scroll_area(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
