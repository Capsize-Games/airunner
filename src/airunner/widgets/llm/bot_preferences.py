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
        self.ui.username.setText(self.llm_generator_settings["username"])
        self.ui.botname.setText(self.llm_generator_settings["botname"])
        self.ui.bot_personality.setPlainText(self.llm_generator_settings["bot_personality"])
        self.ui.bot_mood.setPlainText(self.llm_generator_settings["bot_mood"])
        self.ui.username.blockSignals(False)
        self.ui.botname.blockSignals(False)
        self.ui.bot_personality.blockSignals(False)
        self.ui.bot_mood.blockSignals(False)

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