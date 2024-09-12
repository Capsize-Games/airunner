from PySide6.QtCore import Slot
from PySide6.QtWidgets import QInputDialog, QMessageBox, QLabel, QPushButton, QHBoxLayout, QWidget

from airunner.enums import SignalCode
from airunner.settings import DEFAULT_CHATBOT
from airunner.utils.get_current_chatbot import get_current_chatbot
from airunner.utils.open_file_path import open_file_path
from airunner.utils.toggle_signals import toggle_signals
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.document_widget import DocumentWidget
from airunner.widgets.llm.templates.bot_preferences_ui import Ui_bot_preferences


class BotPreferencesWidget(BaseWidget):
    widget_class_ = Ui_bot_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def llm_generator_settings(self):
        return self.settings["llm_generator_settings"]

    @property
    def current_chatbot_name(self):
        chatbot = self.llm_generator_settings["current_chatbot"]
        if chatbot == "":
            chatbot = "Default"
        return chatbot

    @current_chatbot_name.setter
    def current_chatbot_name(self, val):
        if val == "":
            val = "Default"
        settings = self.settings
        settings["llm_generator_settings"]["current_chatbot"] = val
        self.settings = settings

    @property
    def current_chatbot(self):
        return get_current_chatbot(self.settings)

    def showEvent(self, event):
        self.load_saved_chatbots()

    def load_form_elements(self):
        elements = [
            "username",
            "botname",
            "bot_personality",
            "bot_mood",
            "names_groupbox",
            "personality_groupbox",
            "mood_groupbox",
            "system_instructions",
            "system_instructions_groupbox",
            "guardrails_prompt",
            "guardrails_groupbox",
            "target_files",
        ]
        toggle_signals(self.ui, elements)
        self.ui.username.setText(self.current_chatbot.get("username", "User"))
        self.ui.botname.setText(self.current_chatbot.get("botname", "AIRunner"))
        self.ui.bot_personality.setPlainText(self.current_chatbot.get("bot_personality", ""))
        self.ui.bot_mood.setPlainText(self.current_chatbot.get("bot_mood", ""))
        self.ui.names_groupbox.setChecked(self.current_chatbot.get("assign_names", True))
        self.ui.personality_groupbox.setChecked(self.current_chatbot.get("use_personality", True))
        self.ui.mood_groupbox.setChecked(self.current_chatbot.get("use_mood", True))
        self.ui.system_instructions.setPlainText(self.current_chatbot.get("system_instructions", ""))
        self.ui.system_instructions_groupbox.setChecked(self.current_chatbot.get("use_system_instructions", True))
        self.ui.guardrails_prompt.setPlainText(self.current_chatbot.get("guardrails_prompt", ""))
        self.ui.guardrails_groupbox.setChecked(self.current_chatbot.get("use_guardrails", True))
        self.load_documents()
        toggle_signals(self.ui, elements, False)

    def update_chatbot(self, key, val):
        settings = self.settings
        chatbot = self.current_chatbot
        chatbot[key] = val
        settings["llm_generator_settings"]["saved_chatbots"][self.current_chatbot_name] = chatbot
        self.settings = settings

    def username_changed(self, val):
        self.update_chatbot("username", val)

    def botname_changed(self, val):
        self.update_chatbot("botname", val)
    
    def bot_mood_changed(self):
        self.update_chatbot("bot_mood", self.ui.bot_mood.toPlainText())

    def bot_personality_changed(self):
        self.update_chatbot("bot_personality", self.ui.bot_personality.toPlainText())

    def guardrails_prompt_changed(self):
        self.update_chatbot("guardrails_prompt", self.ui.guardrails_prompt.toPlainText())

    def system_instructions_changed(self):
        self.update_chatbot("system_instructions", self.ui.system_instructions.toPlainText())

    def toggle_use_names(self, val):
        self.update_chatbot("assign_names", val)

    def toggle_use_personality(self, val):
        self.update_chatbot("use_personality", val)

    def toggle_use_mood(self, val):
        self.update_chatbot("use_mood", val)

    def toggle_use_guardrails(self, val):
        self.update_chatbot("use_guardrails", val)

    def toggle_use_system_instructions(self, val):
        self.update_chatbot("use_system_instructions", val)

    def create_new_chatbot_clicked(self):
        # Display a dialog asking for the name of the new chatbot
        chatbot_name, ok = QInputDialog.getText(self, "New Chatbot", "Enter the name of the new chatbot:")

        # If the user clicked "OK" and entered a name
        if ok and chatbot_name:
            settings = self.settings
            settings["llm_generator_settings"]["saved_chatbots"][chatbot_name] = DEFAULT_CHATBOT
            self.settings = settings
            self.current_chatbot_name = chatbot_name
            self.load_saved_chatbots()

    def saved_chatbots_changed(self, val):
        self.current_chatbot_name = val
        self.load_form_elements()
        self.ui.llm_settings_widget.initialize_form()

    def load_saved_chatbots(self):
        names = self.settings["llm_generator_settings"]["saved_chatbots"].keys()
        self.ui.saved_chatbots.blockSignals(True)
        self.ui.saved_chatbots.clear()
        self.ui.saved_chatbots.addItems(names)
        self.ui.saved_chatbots.setCurrentIndex(self.ui.saved_chatbots.findText(self.current_chatbot_name))
        self.load_form_elements()
        self.ui.saved_chatbots.blockSignals(False)

    def delete_clicked(self):
        # show confirmation before deleting
        if self.current_chatbot_name == "Default":
            return
        msg = f"Are you sure you want to delete {self.current_chatbot_name}?"
        reply = self.show_confirmation_dialog(msg)
        if reply == 0:
            settings = self.settings
            del settings["llm_generator_settings"]["saved_chatbots"][self.current_chatbot_name]
            self.settings = settings
            self.current_chatbot_name = "Default"
            self.load_saved_chatbots()

    def show_confirmation_dialog(self, msg):
        return self.show_dialog(msg, "Confirmation", buttons=["Yes", "No"])

    def show_dialog(self, msg, title, buttons=["OK"]):
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

    @Slot()
    def browse_documents(self):
        file_path = open_file_path(self, file_type="Text Files (*.md *.html *.htm *.epub *.pdf *.txt)")

        # validate file path
        if not file_path or not file_path[0] or not file_path[0].strip() or not file_path[0].endswith((
            ".md",
            ".html",
            ".htm",
            ".epub",
            ".pdf",
            ".txt",
        )):
            self.logger.error(f"Invalid file path: {file_path}")
            return

        documents = self.current_chatbot.get("target_files", [])
        documents.append(file_path[0])
        self.update_chatbot("target_files", documents)
        self.emit_signal(SignalCode.RAG_RELOAD_INDEX_SIGNAL, {
            "target_files": documents
        })
        self.load_documents()

    def load_documents(self):
        # Get the layout of the scroll area's widget
        layout = self.ui.target_files.widget().layout()

        # Clear the existing widgets in the layout
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)

        documents = self.current_chatbot.get("target_files", [])
        for doc in documents:
            widget = DocumentWidget(doc, self.delete_document)
            layout.addWidget(widget)

    def delete_document(self, document):
        documents = self.current_chatbot.get("target_files", [])
        if document in documents:
            documents.remove(document)
            self.update_chatbot("target_files", documents)
            self.load_documents()  # Refresh the document list
        self.emit_signal(SignalCode.RAG_RELOAD_INDEX_SIGNAL, {
            "target_files": documents
        })
