from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import (
    QStandardItemModel,
    QStandardItem,
    QBrush,
    QColor,
    QPainter,
)
from PySide6.QtWidgets import (
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QLabel,
    QWidget,
    QVBoxLayout,
    QPlainTextEdit,
)

from airunner.enums import SignalCode
from airunner.gui.widgets.api_token.api_token_widget import APITokenWidget
from airunner.gui.widgets.export_preferences.export_preferences_widget import (
    ExportPreferencesWidget,
)
from airunner.gui.widgets.keyboard_shortcuts.keyboard_shortcuts_widget import (
    KeyboardShortcutsWidget,
)
from airunner.gui.widgets.llm.bot_preferences import BotPreferencesWidget
from airunner.gui.widgets.llm.prompt_templates_widget import (
    PromptTemplatesWidget,
)
from airunner.gui.widgets.memory_preferences.memory_preferences_widget import (
    MemoryPreferencesWidget,
)
from airunner.gui.widgets.paths.paths_widget import PathsWidget
from airunner.gui.widgets.tts.voice_settings_widget import VoiceSettingsWidget
from airunner.gui.widgets.user.user_settings_widget import UserSettingsWidget
from airunner.gui.widgets.huggingface_settings.huggingface_settings_widget import (
    HuggingfaceSettingsWidget,
)
from airunner.gui.widgets.rag_settings.rag_settings_widget import (
    RAGSettingsWidget,
)
from airunner.gui.widgets.openrouter_settings.openrouter_settings_widget import (
    OpenrouterSettingsWidget,
)
from airunner.gui.windows.settings.templates.airunner_settings_ui import (
    Ui_airunner_settings,
)
from airunner.gui.windows.base_window import BaseWindow
from airunner.utils.settings import get_qsettings

try:
    from airunner.gui.widgets.sound_settings.sound_settings_widget import (
        SoundSettingsWidget,
    )
except OSError as e:
    SoundSettingsWidget = None
    print("Error loading sound settings widget:", e)


class HighlightDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_indexes = []

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        if index in self.selected_indexes:
            painter.save()
            painter.fillRect(
                option.rect, QBrush(QColor(0, 0, 255, 50))
            )  # Blue background color
            painter.restore()

        super().paint(painter, option, index)

    def add_selected_index(self, index):
        self.selected_indexes.append(index)

    def remove_selected_index(self, index):
        self.selected_indexes.remove(index)


class SettingsWindow(BaseWindow):
    is_modal = True
    template_class_ = Ui_airunner_settings

    def __init__(self, **kwargs):
        self.widgets = {}
        self.qsettings = get_qsettings()
        super().__init__(**kwargs)
        self.model = None
        self.scroll_widget = None
        self.scroll_layout = None
        self.highlight_delegate = None
        self.emit_signal(SignalCode.APPLICATION_SETTINGS_LOADED_SIGNAL)

    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowTitle("AI Runner Preferences")

    @staticmethod
    def available_widgets(name):
        if name == "paths":
            return PathsWidget
        elif name == "keyboard_shortcuts":
            return KeyboardShortcutsWidget
        elif name == "memory":
            return MemoryPreferencesWidget
        elif name == "hf_api_key":
            return APITokenWidget
        elif name == "voice_settings":
            return VoiceSettingsWidget
        elif name == "prompt_templates":
            return PromptTemplatesWidget
        elif name == "bot_preferences":
            return BotPreferencesWidget
        elif name == "user_settings":
            return UserSettingsWidget
        elif name == "export_preferences":
            return ExportPreferencesWidget
        elif name == "sound_settings":
            return SoundSettingsWidget
        elif name == "huggingface_settings":
            return HuggingfaceSettingsWidget
        elif name == "rag_settings":
            return RAGSettingsWidget
        elif name == "openrouter_settings":
            return OpenrouterSettingsWidget
        # elif name == "stt_preferences":
        #     return STTSettingsWidget

    def get_callback_for_slider(self, callback_name):
        return getattr(self, callback_name)

    def initialize_window(self):
        self.model = QStandardItemModel()
        self.ui.directory.setModel(self.model)
        self.ui.directory.setHeaderHidden(True)
        self.ui.directory.setIndentation(20)

        directory = [
            {
                "section": "Image Export Preferences",
                "files": [
                    {
                        "name": "export_preferences",
                        "display_name": "Export Preferences",
                        "checkable": False,
                    }
                ],
            },
            {
                "section": "Memory Preferences",
                "files": [
                    {
                        "name": "memory",
                        "display_name": "Memory",
                        "checkable": False,
                    }
                ],
            },
            {
                "section": "Keyboard Shortcuts",
                "files": [
                    {
                        "name": "keyboard_shortcuts",
                        "display_name": "Keyboard Shortcuts",
                        "checkable": False,
                    }
                ],
            },
            {
                "section": "Chatbot, prompt templates, text-to-speech",
                "files": [
                    {
                        "name": "bot_preferences",
                        "display_name": "Agent Preferences",
                        "checkable": False,
                    },
                    {
                        "name": "user_settings",
                        "display_name": "User Settings",
                        "checkable": False,
                    },
                    {
                        "name": "voice_settings",
                        "display_name": "Text-to-Speech",
                        "checkable": False,
                    },
                    {
                        "name": "prompt_templates",
                        "display_name": "Prompt Templates",
                        "checkable": False,
                    },
                    # {
                    #     "name": "stt_preferences",
                    #     "display_name": "Speech-to-Text",
                    #     "checkable": False
                    # },
                ],
            },
            {
                "section": "Miscellaneous Preferences",
                "files": [
                    {
                        "name": "dark_mode",
                        "display_name": "Dark Mode",
                        "checkable": True,
                        "description": "If enabled, AI Runner will use a dark theme.",
                    },
                    {
                        "name": "override_system_theme",
                        "display_name": "Override System Theme",
                        "checkable": True,
                        "description": "If enabled, override the system theme with the selected theme.",
                    },
                    {
                        "name": "check_for_updates",
                        "display_name": "Check for updates",
                        "checkable": True,
                        "description": "If enabled, AI Runner will check for updates on startup.",
                    },
                    {
                        "name": "enable_workflows",
                        "display_name": "Enable Workflows",
                        "checkable": True,
                        "description": "Enable experimental agent workflows.",
                    },
                    {
                        "name": "sound_settings",
                        "display_name": "Sound Settings",
                        "checkable": False,
                    },
                    {
                        "name": "huggingface_settings",
                        "display_name": "Huggingface Settings",
                        "checkable": False,
                    },
                    {
                        "name": "rag_settings",
                        "display_name": "RAG Settings",
                        "checkable": False,
                    },
                    {
                        "name": "openrouter_settings",
                        "display_name": "Openrouter Settings",
                        "checkable": False,
                    },
                ],
            },
        ]
        for index, section in enumerate(directory):
            self.add_directory(section["section"])
            for file in section["files"]:
                self.add_file(
                    self.model.item(index),
                    file["name"],
                    file["display_name"],
                    file["checkable"],
                    file["description"] if "description" in file else None,
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

        self.connect_signals()

    def connect_signals(self):
        self.register(SignalCode.VOICE_SAVED, self.refresh_bot_preferences)

    def refresh_bot_preferences(self):
        if "bot_preferences" in self.widgets:
            self.widgets["bot_preferences"].load_voices()

    def add_directory(self, name, checkable=False):
        item = QStandardItem(name)
        item.setCheckable(checkable)
        if checkable:
            checked = False
            if name == "enable_workflows":
                checked = self.enable_workflows
            item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setData(name, Qt.ItemDataRole.DisplayRole)
        item.setSizeHint(QSize(0, 24))
        self.model.appendRow(item)

    def add_file(
        self,
        parent_item,
        name,
        display_name,
        checkable=False,
        description=None,
    ):
        file_item = QStandardItem(display_name)
        file_item.setCheckable(checkable)
        if checkable:
            checked = False
            if name == "resize_on_import":
                checked = self.application_settings.resize_on_paste
            elif name == "image_to_new_layer":
                checked = self.application_settings.image_to_new_layer is True
            elif name == "dark_mode":
                checked = self.application_settings.dark_mode_enabled
            elif name == "override_system_theme":
                checked = self.application_settings.override_system_theme
            elif name == "check_for_updates":
                checked = self.application_settings.latest_version_check
            elif name == "enable_workflows":
                checked = self.enable_workflows
            elif name == "allow_online_mode":
                checked = self.application_settings.allow_online_mode

            file_item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
        # prevent file_item from being edited
        file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        file_item.setData(name, Qt.ItemDataRole.UserRole)
        file_item.setData(display_name, Qt.ItemDataRole.DisplayRole)
        file_item.setData(description, Qt.ItemDataRole.ToolTipRole)
        file_item.setSizeHint(QSize(0, 24))
        parent_item.appendRow(file_item)

    @property
    def enable_workflows(self) -> bool:
        return self.qsettings.value("enable_workflows") == "true"

    @enable_workflows.setter
    def enable_workflows(self, val: bool):
        self.qsettings.setValue("enable_workflows", val)
        self.emit_signal(SignalCode.ENABLE_WORKFLOWS_TOGGLED, {"enabled": val})
        self.qsettings.sync()

    def on_item_clicked(self, index):
        item = self.model.itemFromIndex(index)
        if item.parent() is None:
            return

        section = item.parent().data(Qt.ItemDataRole.DisplayRole)
        name = item.data(Qt.ItemDataRole.UserRole)
        display_name = item.data(Qt.ItemDataRole.DisplayRole)
        description = item.data(Qt.ItemDataRole.ToolTipRole)

        if name == "resize_on_import":
            checked = item.checkState() == Qt.CheckState.Checked
            self.update_application_settings("resize_on_paste", checked)
        elif name == "image_to_new_layer":
            checked = item.checkState() == Qt.CheckState.Checked
            self.update_application_settings("image_to_new_layer", checked)
        elif name == "dark_mode":
            checked = item.checkState() == Qt.CheckState.Checked
            self.update_application_settings("dark_mode_enabled", checked)
            self.emit_signal(SignalCode.REFRESH_STYLESHEET_SIGNAL)
        elif name == "override_system_theme":
            checked = item.checkState() == Qt.CheckState.Checked
            self.update_application_settings("override_system_theme", checked)
            self.emit_signal(SignalCode.REFRESH_STYLESHEET_SIGNAL)
        elif name == "check_for_updates":
            checked = item.checkState() == Qt.CheckState.Checked
            self.update_application_settings("latest_version_check", checked)
        elif name == "enable_workflows":
            checked = item.checkState() == Qt.CheckState.Checked
            self.enable_workflows = checked
        elif name == "allow_online_mode":
            checked = item.checkState() == Qt.CheckState.Checked
            self.update_application_settings("allow_online_mode", checked)
        elif name == "reset_settings":
            self.emit_signal(SignalCode.APPLICATION_RESET_SETTINGS_SIGNAL)

        self.show_content(section, display_name, name, description)
        self.set_stylesheet()

    def show_content(self, section, display_name, name, description):
        # create a label widget
        label = QLabel(f"<p><b>{section} > {display_name}</b></p>")

        widget_object = None
        if widget_object is None:
            _widget_class = self.available_widgets(name)
            if _widget_class is not None:
                widget_object = _widget_class()
        if widget_object is None:
            return

        self.clear_scroll_area()
        self.scroll_layout.addWidget(label)
        if widget_object:
            self.scroll_layout.addWidget(widget_object)
        elif description:
            description_text_edit = QPlainTextEdit()
            description_text_edit.setReadOnly(True)
            description_text_edit.setPlainText(description)
            description_text_edit.setFrameStyle(0)
            description_text_edit.setStyleSheet(
                "QPlainTextEdit { background-color: transparent; border: none; }"
            )
            self.scroll_layout.addWidget(description_text_edit)

    def clear_scroll_area(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
