from PySide6.QtCore import Slot
from PySide6.QtWidgets import QInputDialog, QMessageBox

from airunner.models.chatbot import Chatbot
from airunner.models.target_files import TargetFiles
from airunner.models.voice_settings import VoiceSettings
from airunner.enums import Gender
from airunner.utils.os.open_file_path import open_file_path
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.llm.gui.widgets.document_widget import DocumentWidget
from airunner.components.llm.gui.widgets.templates.bot_preferences_ui import (
    Ui_bot_preferences,
)
from airunner.settings import (
    AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT,
    AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT,
)
from airunner.enums import SignalCode


class BotPreferencesWidget(BaseWidget):
    widget_class_ = Ui_bot_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._configure_agent_type_dropdown()

    def showEvent(self, event):
        self.load_saved_chatbots()
        super().showEvent(event)

    def load_form_elements(self):
        elements = [
            "botname",
            "bot_personality",
            "names_groupbox",
            "personality_groupbox",
            "system_instructions",
            "system_instructions_groupbox",
            "guardrails_prompt",
            "guardrails_groupbox",
            "target_files",
            "use_weather_prompt",
            "use_datetime",
        ]
        self.toggle_signals(self.ui, elements)
        self.ui.botname.setText(self.chatbot.botname)
        self.ui.bot_personality.setPlainText(self.chatbot.bot_personality)
        self.ui.names_groupbox.setChecked(self.chatbot.assign_names)
        self.ui.personality_groupbox.setChecked(self.chatbot.use_personality)
        self.ui.system_instructions.setPlainText(
            self.chatbot.system_instructions
        )
        self.ui.system_instructions_groupbox.setChecked(
            self.chatbot.use_system_instructions
        )
        self.ui.guardrails_prompt.setPlainText(self.chatbot.guardrails_prompt)
        self.ui.guardrails_groupbox.setChecked(self.chatbot.use_guardrails)
        self.ui.use_weather_prompt.setChecked(self.chatbot.use_weather_prompt)
        self.ui.use_datetime.setChecked(self.chatbot.use_datetime)
        self.ui.gender.setCurrentText(self.chatbot.gender)
        self.load_documents()
        self.load_voices()
        self._load_system_prompt_editor()
        self._apply_agent_type_state()
        self.toggle_signals(self.ui, elements, False)

    @staticmethod
    def toggle_signals(ui: object, elements: list, block: bool = True):
        for element in elements:
            getattr(ui, element).blockSignals(block)

    def botname_changed(self, val):
        self.update_chatbot("botname", val)

    def bot_personality_changed(self):
        self.update_chatbot(
            "bot_personality", self.ui.bot_personality.toPlainText()
        )

    def guardrails_prompt_changed(self):
        self.update_chatbot(
            "guardrails_prompt", self.ui.guardrails_prompt.toPlainText()
        )

    def system_instructions_changed(self):
        prompt = self.ui.system_instructions.toPlainText()
        self.update_chatbot("system_instructions", prompt)

    def toggle_use_names(self, val):
        self.update_chatbot("assign_names", val)

    def toggle_use_personality(self, val):
        self.update_chatbot("use_personality", val)

    def toggle_use_guardrails(self, val):
        self.update_chatbot("use_guardrails", val)

    def toggle_use_system_instructions(self, val):
        self.update_chatbot("use_system_instructions", val)

    def create_new_chatbot_clicked(self):
        # Display a dialog asking for the name of the new chatbot
        chatbot_name, ok = QInputDialog.getText(
            self, "New Chatbot", "Enter the name of the new chatbot:"
        )

        # If the user clicked "OK" and entered a name
        if ok and chatbot_name:
            self.create_chatbot(chatbot_name)
            self.update_llm_generator_settings(current_chatbot=chatbot_name)
            self.load_saved_chatbots()

    @Slot(str)
    def saved_chatbots_changed(self, val: str):
        chatbot = Chatbot.objects.filter_first(Chatbot.name == val)
        chatbot_id = chatbot.id
        self.update_llm_generator_settings(current_chatbot=chatbot_id)
        self.load_form_elements()
        self.api.llm.chatbot_changed()

    def load_saved_chatbots(self):
        names = [chatbot.name for chatbot in self.chatbots]
        self.ui.saved_chatbots.blockSignals(True)
        self.ui.saved_chatbots.clear()
        self.ui.saved_chatbots.addItems(names)
        self.ui.saved_chatbots.setCurrentIndex(
            self.ui.saved_chatbots.findText(self.chatbot.name)
        )
        self.load_form_elements()
        self.ui.saved_chatbots.blockSignals(False)

    def delete_clicked(self):
        # show confirmation before deleting
        if self.chatbot.name == "Default":
            return
        msg = f"Are you sure you want to delete {self.chatbot.name}?"
        reply = self.show_confirmation_dialog(msg)
        if reply == 0:
            self.delete_chatbot_by_name(self.chatbot.name)
            self.chatbot.name = "Chatbot"
            self.load_saved_chatbots()

    def show_confirmation_dialog(self, msg):
        return self.show_dialog(msg, "Confirmation", buttons=["Yes", "No"])

    @staticmethod
    def show_dialog(msg, title, buttons=["OK"]):
        dialog = QMessageBox()
        dialog.setText(msg)
        dialog.setWindowTitle(title)
        for button in buttons:
            dialog.addButton(button, QMessageBox.ButtonRole.AcceptRole)
        return dialog.exec()

    @Slot(bool)
    def toggle_use_image_generator(self, val: bool):
        self.ui.use_image_generator_checkbox.blockSignals(True)
        self.ui.use_image_generator_checkbox.setChecked(val)
        self.ui.use_image_generator_checkbox.blockSignals(False)

    @Slot(bool)
    def agent_type_changed(self, val: str):
        del val
        self.load_form_elements()

    @Slot(bool)
    def use_weather_prompt_toggled(self, val: bool):
        self.update_chatbot("use_weather_prompt", val)

    @Slot(bool)
    def toggle_use_datetime(self, val: bool):
        self.update_chatbot("use_datetime", val)

    @Slot(str)
    def gender_changed(self, gender: str):
        try:
            gender_enum = Gender[gender.upper()]
        except KeyError:
            self.logger.error("Failed to set gender with " + gender)
            return
        self.update_chatbot("gender", gender_enum.value)

    @Slot()
    def browse_documents(self):
        file_path, _ = open_file_path(
            self,
            label="Select Document",
            file_type=(
                "Text Files (*.md *.html *.htm *.epub *.mobi *.pdf *.txt)"
            ),
        )

        # validate file path
        if (
            not file_path
            or not file_path.strip()
            or not file_path.endswith(
                (
                    ".md",
                    ".html",
                    ".htm",
                    ".epub",
                    ".mobi",
                    ".pdf",
                    ".txt",
                )
            )
        ):
            self.logger.error(f"Invalid file path: {file_path}")
            return

        self.add_chatbot_document_to_chatbot(self.chatbot, file_path)
        self.api.llm.reload_rag()
        self.load_documents()

    def load_documents(self):
        # Get the layout of the scroll area's widget
        layout = self.ui.target_files.widget().layout()

        # Clear the existing widgets in the layout
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)

        for target_file in self.chatbot.target_files:
            widget = DocumentWidget(target_file, self.delete_document)
            layout.addWidget(widget)

    def delete_document(self, target_file: TargetFiles):
        TargetFiles.objects.delete(target_file.id)

        self.load_documents()
        self.api.llm.reload_rag()

    def update_chatbot(self, key, val):
        chatbot = self.chatbot
        try:
            setattr(chatbot, key, val)
        except TypeError:
            self.logger.error(f"Attribute {key} does not exist in Chatbot")
            return
        Chatbot.objects.update(
            chatbot.id,
            **{key: val},
        )

    def load_voices(self):
        voices = VoiceSettings.objects.all()
        self.ui.voice_combobox.blockSignals(True)
        self.ui.voice_combobox.clear()

        # Add voices to combobox if any exist
        for voice in voices:
            self.ui.voice_combobox.addItem(voice.name, voice.id)

        # Handle the case when there are no voices available
        if not voices:
            self.ui.voice_combobox.addItem("No voices available", None)
            self.ui.voice_combobox.setCurrentIndex(0)
        else:
            self.ui.voice_combobox.setCurrentIndex(
                self.ui.voice_combobox.findData(
                    self.chatbot.voice_id or voices[0].id
                )
            )
        self.ui.voice_combobox.blockSignals(False)

    @Slot(int)
    def voice_changed(self, index):
        voice_id = self.ui.voice_combobox.itemData(index)
        if voice_id is None:
            return
        self.update_chatbot("voice_id", voice_id)
        voice = VoiceSettings.objects.get(pk=voice_id)
        if voice is not None:
            self.emit_signal(
                SignalCode.TTS_MODEL_CHANGED,
                {"voice_id": voice.id, "model": voice.model_type},
            )

    @Slot()
    def on_reset_system_instructions_button_clicked(self):
        self.ui.system_instructions.setPlainText(
            AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT
        )

    @Slot()
    def on_reset_guardrails_button_clicked(self):
        self.ui.guardrails_prompt.setPlainText(
            AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT
        )

    def _configure_agent_type_dropdown(self) -> None:
        """Populate the agent-type dropdown with the supported profile."""
        dropdown = self.ui.comboBox
        dropdown.blockSignals(True)
        dropdown.clear()
        dropdown.addItem("Chatbot", "chatbot")
        dropdown.setCurrentIndex(0)
        dropdown.setEnabled(False)
        dropdown.blockSignals(False)

    def _selected_agent_type_key(self) -> str:
        """Return the selected agent-type key from the dropdown."""
        value = self.ui.comboBox.currentData()
        return str(value or "chatbot")

    def _load_system_prompt_editor(self) -> None:
        """Load the prompt text shown in the system prompt editor."""
        self.ui.system_instructions_groupbox.setCheckable(True)
        self.ui.system_instructions_groupbox.setChecked(
            self.chatbot.use_system_instructions
        )
        self.ui.system_instructions_groupbox.setTitle(
            "System Instructions"
        )
        self.ui.system_instructions.setPlainText(
            self.chatbot.system_instructions
        )

    def _apply_agent_type_state(self) -> None:
        """Enable chatbot fields only when the chatbot profile is selected."""
        widget_names = [
            "saved_chatbots",
            "create_new_button",
            "delete_button",
            "names_groupbox",
            "personality_groupbox",
            "groupBox_3",
            "guardrails_groupbox",
            "groupBox_4",
            "voice_groupbox",
            "use_weather_prompt",
            "use_datetime",
        ]
        for name in widget_names:
            widget = getattr(self.ui, name, None)
            if widget is not None:
                widget.setEnabled(True)
