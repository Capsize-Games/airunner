from PyQt6 import QtWidgets

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.bot_preferences_ui import Ui_bot_preferences


class BotPreferencesWidget(BaseWidget):
    widget_class_ = Ui_bot_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.username.blockSignals(True)
        self.ui.botname.blockSignals(True)
        self.ui.bot_personality.blockSignals(True)
        self.ui.bot_mood.blockSignals(True)
        self.ui.names_groupbox.blockSignals(True)
        self.ui.personality_groupbox.blockSignals(True)
        self.ui.mood_groupbox.blockSignals(True)
        self.ui.system_instructions.blockSignals(True)
        self.ui.guardrails_prompt.blockSignals(True)
        self.ui.system_instructions_groupbox.blockSignals(True)
        self.ui.guardrails_groupbox.blockSignals(True)
        self.ui.username.setText(self.settings["llm_generator_settings"]["username"])
        self.ui.botname.setText(self.settings["llm_generator_settings"]["botname"])
        self.ui.bot_personality.setPlainText(self.settings["llm_generator_settings"]["bot_personality"])
        self.ui.bot_mood.setPlainText(self.settings["llm_generator_settings"]["bot_mood"])
        self.ui.names_groupbox.setChecked(self.settings["llm_generator_settings"]["assign_names"])
        self.ui.personality_groupbox.setChecked(self.settings["llm_generator_settings"]["use_personality"])
        self.ui.mood_groupbox.setChecked(self.settings["llm_generator_settings"]["use_mood"])
        self.ui.system_instructions.setPlainText(self.settings["llm_generator_settings"]["system_instructions"])
        self.ui.system_instructions_groupbox.setChecked(self.settings["llm_generator_settings"]["use_system_instructions"])
        self.ui.guardrails_prompt.setPlainText(self.settings["llm_generator_settings"]["guardrails_prompt"])
        self.ui.guardrails_groupbox.setChecked(self.settings["llm_generator_settings"]["use_guardrails"])
        self.ui.username.blockSignals(False)
        self.ui.botname.blockSignals(False)
        self.ui.names_groupbox.blockSignals(False)
        self.ui.personality_groupbox.blockSignals(False)
        self.ui.mood_groupbox.blockSignals(False)
        self.ui.system_instructions.blockSignals(False)
        self.ui.guardrails_prompt.blockSignals(False)
        self.ui.system_instructions_groupbox.blockSignals(False)
        self.ui.guardrails_groupbox.blockSignals(False)

    def toggle_self_reflection_category(self, state):
        checkbox = self.sender()
        label = checkbox.text()
        settings = self.settings
        llm_generator_settings = settings["llm_generator_settings"]
        self_reflection_categories = llm_generator_settings["self_reflection_categories"]
        for index, category in enumerate(self_reflection_categories):
            cat = category["category"]
            if cat.value == label:
                category["active"] = state
                self_reflection_categories[index] = category
                llm_generator_settings["self_reflection_categories"] = self_reflection_categories
                settings["llm_generator_settings"] = llm_generator_settings
                self.settings = settings
                break

    def username_changed(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["username"] = val
        self.settings = settings

    def botname_changed(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["botname"] = val
        self.settings = settings
    
    def bot_mood_changed(self):
        settings = self.settings
        settings["llm_generator_settings"]["bot_mood"] = self.ui.bot_mood.toPlainText()
        self.settings = settings

    def bot_personality_changed(self):
        settings = self.settings
        settings["llm_generator_settings"]["bot_personality"] = self.ui.bot_personality.toPlainText()
        self.settings = settings

    def guardrails_prompt_changed(self):
        val = self.ui.guardrails_prompt.toPlainText()
        settings = self.settings
        settings["llm_generator_settings"]["guardrails_prompt"] = val
        self.settings = settings

    def system_instructions_changed(self):
        val = self.ui.system_instructions.toPlainText()
        settings = self.settings
        settings["llm_generator_settings"]["system_instructions"] = val
        self.settings = settings

    def toggle_use_names(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["assign_names"] = val
        self.settings = settings

    def toggle_use_personality(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["use_personality"] = val
        self.settings = settings

    def toggle_use_mood(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["use_mood"] = val
        self.settings = settings

    def toggle_use_guardrails(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["use_guardrails"] = val
        self.settings = settings

    def toggle_use_system_instructions(self, val):
        settings = self.settings
        settings["llm_generator_settings"]["use_system_instructions"] = val
        self.settings = settings
