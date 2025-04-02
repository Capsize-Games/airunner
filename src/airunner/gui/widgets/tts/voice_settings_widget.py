from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QMessageBox,
)
from airunner.gui.widgets.tts.templates.voice_settings_ui import (
    Ui_voice_settings,
)
from airunner.data.models.voice_settings import VoiceSettings
from airunner.data.models.espeak_settings import EspeakSettings
from airunner.data.models.speech_t5_settings import SpeechT5Settings
from airunner.gui.widgets.tts.espeak_preferences_widget import (
    EspeakPreferencesWidget,
)
from airunner.gui.widgets.tts.speecht5_preferences_widget import (
    SpeechT5PreferencesWidget,
)


class VoiceSettingsWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_voice_settings()
        self.ui.setupUi(self)
        self.ui.create_voice_button.clicked.connect(self.create_voice)
        self.load_voices()

    def load_voices(self):
        layout = self.ui.voice_list_layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        voices = VoiceSettings.objects.all()
        for voice in voices:
            self.add_voice_item(voice)

    def add_voice_item(self, voice):
        container = QWidget()
        container_layout = QVBoxLayout(container)

        name_edit = QLineEdit(voice.name)
        name_edit.textChanged.connect(
            lambda val, v=voice: self.update_voice_name(v, val)
        )
        container_layout.addWidget(name_edit)

        model_combobox = QComboBox()
        model_combobox.addItems(["SpeechT5", "Espeak"])
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
        """Add the appropriate settings widget (Espeak or SpeechT5) to the layout."""
        # Remove any existing settings widget
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if isinstance(
                widget, (EspeakPreferencesWidget, SpeechT5PreferencesWidget)
            ):
                widget.deleteLater()

        # Add the appropriate settings widget
        if voice.model_type == "SpeechT5":
            settings = SpeechT5Settings.objects.get(voice.settings_id)
            widget = SpeechT5PreferencesWidget()
            widget.load_settings(settings)
        else:
            settings = EspeakSettings.objects.get(voice.settings_id)
            widget = EspeakPreferencesWidget()
            widget.load_settings(settings)

        layout.addWidget(widget)

    def create_voice(self):
        voice = VoiceSettings.objects.create(
            name="New Voice",
            model_type="SpeechT5",
            settings_id=0,
        )
        if voice.model_type == "SpeechT5":
            settings = SpeechT5Settings.objects.create()
        else:
            settings = EspeakSettings.objects.create()
        VoiceSettings.objects.update(
            voice.id,
            settings_id=settings.id,
        )
        voice.settings_id = settings.id
        self.add_voice_item(voice)

    def update_voice_name(self, voice, name):
        voice.name = name
        VoiceSettings.objects.update(voice.id, name=name)

    def update_voice_model(self, voice, model_type, layout):
        if voice.model_type != model_type:
            # Delete the old settings
            if voice.model_type == "SpeechT5":
                SpeechT5Settings.objects.delete(voice.settings_id)
            else:
                EspeakSettings.objects.delete(voice.settings_id)

            # Create new settings
            if model_type == "SpeechT5":
                settings = SpeechT5Settings.objects.create()
            else:
                settings = EspeakSettings.objects.create()

            voice.settings_id = settings.id
            voice.model_type = model_type
            VoiceSettings.objects.update(
                voice.id, settings_id=settings.id, model_type=model_type
            )

        # Update the settings widget
        self.add_settings_widget(voice, layout)

    def delete_voice(self, voice):
        confirm = QMessageBox.question(
            self,
            "Delete Voice",
            f"Are you sure you want to delete '{voice.name}'?",
        )
        if confirm == QMessageBox.Yes:
            # Delete the associated settings
            if voice.model_type == "SpeechT5":
                SpeechT5Settings.objects.delete(voice.settings_id)
            else:
                EspeakSettings.objects.delete(voice.settings_id)

            VoiceSettings.objects.delete(voice.id)
            self.load_voices()
