from PySide6.QtCore import Slot
from PySide6.QtWidgets import QInputDialog, QMessageBox

from airunner.data.models import TargetFiles, Chatbot
from airunner.data.models.voice_settings import VoiceSettings
from airunner.enums import SignalCode, Gender
from airunner.utils.os import open_file_path
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.llm.document_widget import DocumentWidget
from airunner.gui.widgets.llm.templates.bot_preferences_ui import (
    Ui_bot_preferences,
)


class BotPreferencesWidget(BaseWidget):
    widget_class_ = Ui_bot_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        self.update_chatbot(
            "system_instructions", self.ui.system_instructions.toPlainText()
        )

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
            self.update_llm_generator_settings("current_chatbot", chatbot_name)
            self.load_saved_chatbots()

    @Slot(str)
    def saved_chatbots_changed(self, val: str):
        chatbot = Chatbot.objects.filter_first(Chatbot.name == val)
        chatbot_id = chatbot.id
        self.update_llm_generator_settings("current_chatbot", chatbot_id)
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
        print("agent type changed", val)

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
        file_path = open_file_path(
            self, file_type="Text Files (*.md *.html *.htm *.epub *.pdf *.txt)"
        )

        # validate file path
        if (
            not file_path
            or not file_path[0]
            or not file_path[0].strip()
            or not file_path[0].endswith(
                (
                    ".md",
                    ".html",
                    ".htm",
                    ".epub",
                    ".pdf",
                    ".txt",
                )
            )
        ):
            self.logger.error(f"Invalid file path: {file_path}")
            return

        self.add_chatbot_document_to_chatbot(self.chatbot, file_path[0])
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
        for voice in voices:
            self.ui.voice_combobox.addItem(voice.name, voice.id)
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
