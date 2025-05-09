from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Slot
from airunner.gui.widgets.tts.templates.voice_settings_ui import (
    Ui_voice_settings,
)
from airunner.data.models.voice_settings import VoiceSettings
from airunner.data.models.espeak_settings import EspeakSettings
from airunner.data.models.speech_t5_settings import SpeechT5Settings
from airunner.gui.widgets.tts.espeak_preferences_widget import (
    EspeakPreferencesWidget,
)
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.tts.speecht5_preferences_widget import (
    SpeechT5PreferencesWidget,
)
from airunner.settings import AIRUNNER_ENABLE_OPEN_VOICE
from airunner.gui.widgets.tts.open_voice_preferences_widget import (
    OpenVoicePreferencesWidget,
)
from airunner.enums import TTSModel
from airunner.data.models.openvoice_settings import OpenVoiceSettings


class VoiceSettingsWidget(BaseWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_voice_settings()
        self.ui.setupUi(self)
        self.ui.create_voice_button.clicked.connect(self.create_voice)
        self.selected_voice = None
        self.load_voices()

    def load_voices(self):
        self.clear_voice_item()
        self.initalize_voice_item()
        self.initialize_voice_combobox()

    def initalize_voice_item(self):
        # Get voice from current bot
        if self.selected_voice is not None:
            voice = VoiceSettings.objects.get(self.selected_voice)
        if self.chatbot and self.chatbot.voice_id:
            voice = VoiceSettings.objects.get(self.chatbot.voice_id)
        else:
            voice = VoiceSettings.objects.first()
        if voice is not None:
            self.add_voice_item(voice)

    def initialize_voice_combobox(self):
        # set voices combobox
        self.ui.voice.blockSignals(True)
        self.ui.voice.clear()
        voices = VoiceSettings.objects.all()
        if voices:
            for voice in voices:
                self.ui.voice.addItem(f"{voice.name}")
        if self.selected_voice is not None:
            voice = VoiceSettings.objects.get(self.selected_voice)
            if voice is not None:
                # set the current voice
                self.ui.voice.setCurrentText(voice.name)
        elif self.chatbot and self.chatbot.voice_id:
            voice = VoiceSettings.objects.get(self.chatbot.voice_id)
            if voice is not None:
                # set the current voice
                self.ui.voice.setCurrentText(voice.name)
        self.ui.voice.blockSignals(False)

    @Slot(str)
    def on_voice_currentTextChanged(self, text):
        """Handle the change in the voice combobox."""
        if text:
            voices = VoiceSettings.objects.filter(VoiceSettings.name == text)
            if len(voices) > 0:
                self.selected_voice = voices[0].id
                self.clear_voice_item()
                self.load_voices()

    def clear_voice_item(self):
        """Clear the current voice item from the layout."""
        layout = self.ui.voice_list_layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def add_voice_item(self, voice):
        container = QWidget()
        container_layout = QVBoxLayout(container)

        name_edit = QLineEdit(voice.name)
        name_edit.textChanged.connect(
            lambda val, v=voice: self.update_voice_name(v, val)
        )
        container_layout.addWidget(name_edit)

        model_combobox = QComboBox()
        model_combobox.addItems(
            [TTSModel.SPEECHT5.value, TTSModel.ESPEAK.value]
        )
        if AIRUNNER_ENABLE_OPEN_VOICE:
            model_combobox.addItem(TTSModel.OPENVOICE.value)
        model_combobox.setCurrentText(voice.model_type)
        model_combobox.currentTextChanged.connect(
            lambda val, v=voice: self.update_voice_model(
                v, val, container_layout
            )
        )
        container_layout.addWidget(model_combobox)

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda _, v=voice: self.delete_voice(v))
        container_layout.addWidget(delete_button)

        # Add the corresponding settings widget
        self.add_settings_widget(voice, container_layout)

        self.ui.voice_list_layout.addWidget(container)

    def add_settings_widget(self, voice, layout):
        """Add the appropriate settings widget (Espeak, SpeechT5, or OpenVoice) to the layout."""
        # Remove any existing settings widget
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if isinstance(
                widget,
                (
                    EspeakPreferencesWidget,
                    SpeechT5PreferencesWidget,
                    OpenVoicePreferencesWidget,
                ),
            ):
                widget.deleteLater()

        # Add the appropriate settings widget
        if voice.model_type == TTSModel.SPEECHT5.value:
            widget = SpeechT5PreferencesWidget(id=voice.settings_id)
        elif voice.model_type == TTSModel.ESPEAK.value:
            widget = EspeakPreferencesWidget(id=voice.settings_id)
        elif (
            AIRUNNER_ENABLE_OPEN_VOICE
            and voice.model_type == TTSModel.OPENVOICE.value
        ):
            widget = OpenVoicePreferencesWidget(id=voice.settings_id)
        else:
            return

        layout.addWidget(widget)

    def create_voice(self):
        name = "New Voice"
        voices = VoiceSettings.objects.filter(VoiceSettings.name == name)
        total = len(voices)
        name = f"{name} ({total + 1})" if total > 0 else name
        voice = VoiceSettings.objects.create(
            name=name,
            model_type=(
                TTSModel.SPEECHT5.value
                if not AIRUNNER_ENABLE_OPEN_VOICE
                else TTSModel.OPENVOICE.value
            ),
            settings_id=1,
        )
        # if voice.model_type == TTSModel.SPEECHT5.value:
        #     settings = SpeechT5Settings.objects.create()
        # elif voice.model_type == TTSModel.ESPEAK.value:
        #     settings = EspeakSettings.objects.create()
        # elif (
        #     AIRUNNER_ENABLE_OPEN_VOICE
        #     and voice.model_type == TTSModel.OPENVOICE.value
        # ):
        #     settings = OpenVoiceSettings.objects.create()
        # else:
        #     return
        # VoiceSettings.objects.update(
        #     voice.id,
        #     settings_id=settings.id,
        # )
        # voice.settings_id = settings.id
        self.add_voice_item(voice)
        self.initialize_voice_combobox()

    def update_voice_name(self, voice, name):
        voice.name = name
        VoiceSettings.objects.update(voice.id, name=name)
        self.initialize_voice_combobox()

    def update_voice_model(self, voice, model_type, layout):
        if voice.model_type != model_type:
            # Delete the old settings
            if voice.model_type == TTSModel.SPEECHT5:
                SpeechT5Settings.objects.delete(voice.settings_id)
            elif voice.model_type == TTSModel.ESPEAK:
                EspeakSettings.objects.delete(voice.settings_id)
            elif (
                AIRUNNER_ENABLE_OPEN_VOICE
                and voice.model_type == TTSModel.OPENVOICE
            ):
                OpenVoiceSettings.objects.delete(voice.settings_id)

            # Create new settings
            if model_type == TTSModel.SPEECHT5.value:
                settings = SpeechT5Settings.objects.create()
            elif model_type == TTSModel.ESPEAK.value:
                settings = EspeakSettings.objects.create()
            elif (
                AIRUNNER_ENABLE_OPEN_VOICE
                and model_type == TTSModel.OPENVOICE.value
            ):
                settings = OpenVoiceSettings.objects.create()
            else:
                return

            voice.settings_id = settings.id
            voice.model_type = model_type
            VoiceSettings.objects.update(
                voice.id, settings_id=settings.id, model_type=model_type
            )

        # Update the settings widget
        self.add_settings_widget(voice, layout)
        self.initialize_voice_combobox()

    def delete_voice(self, voice):
        confirm = QMessageBox.question(
            self,
            "Delete Voice",
            f"Are you sure you want to delete '{voice.name}'?",
        )
        if confirm == QMessageBox.Yes:
            # Delete the associated settings
            if voice.model_type == TTSModel.SPEECHT5.value:
                SpeechT5Settings.objects.delete(voice.settings_id)
            elif voice.model_type == TTSModel.ESPEAK.value:
                EspeakSettings.objects.delete(voice.settings_id)
            elif (
                AIRUNNER_ENABLE_OPEN_VOICE
                and voice.model_type == TTSModel.OPENVOICE.value
            ):
                OpenVoiceSettings.objects.delete(voice.settings_id)

            VoiceSettings.objects.delete(voice.id)
            self.load_voices()
        self.initialize_voice_combobox()
