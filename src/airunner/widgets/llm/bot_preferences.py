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
        self.ui.username.setText(self.app.llm_generator["username"])
        self.ui.botname.setText(self.app.llm_generator["botname"])
        self.ui.bot_personality.setPlainText(self.app.llm_generator["bot_personality"])
        self.ui.bot_mood.setPlainText(self.app.llm_generator["bot_mood"])
        self.ui.username.blockSignals(False)
        self.ui.botname.blockSignals(False)
        self.ui.bot_personality.blockSignals(False)
        self.ui.bot_mood.blockSignals(False)

    def username_changed(self, val):
        llm_generator = self.app.llm_generator
        llm_generator["username"] = val
        self.app.llm_generator = llm_generator

    def botname_changed(self, val):
        llm_generator = self.app.llm_generator
        llm_generator["botname"] = val
        self.app.llm_generator = llm_generator
    
    def bot_mood_changed(self):
        llm_generator = self.app.llm_generator
        llm_generator["bot_mood"] = self.ui.bot_mood.toPlainText()
        self.app.llm_generator = llm_generator

    def bot_personality_changed(self):
        llm_generator = self.app.llm_generator
        llm_generator["bot_personality"] = self.ui.bot_personality.toPlainText()
        self.app.llm_generator = llm_generator