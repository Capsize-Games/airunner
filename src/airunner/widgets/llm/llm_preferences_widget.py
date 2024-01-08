from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.llm_preferences_ui import Ui_llm_preferences_widget
from airunner.utils import get_session, save_session
from airunner.data.models import LLMPromptTemplate
from airunner.widgets.base_widget import BaseWidget
from airunner.aihandler.logger import Logger



class LLMPreferencesWidget(BaseWidget):
    widget_class_ = Ui_llm_preferences_widget

    @property
    def generator(self):
        try:
            return self.app.ui.llm_widget.generator
        except Exception as e:
            Logger.error(e)
            import traceback
            traceback.print_exc()
    
    @property
    def generator_settings(self):
        try:
            return self.app.ui.llm_widget.generator_settings
        except Exception as e:
            Logger.error(e)

    def initialize(self):
        self.ui.prefix.blockSignals(True)
        self.ui.suffix.blockSignals(True)
        self.ui.personality_type.blockSignals(True)
        if self.generator:
            self.ui.prefix.setPlainText(self.generator.prefix)
            self.ui.suffix.setPlainText(self.generator.suffix)
            self.ui.personality_type.setCurrentText(self.generator.bot_personality)
        self.ui.prefix.blockSignals(False)
        self.ui.suffix.blockSignals(False)
        self.ui.personality_type.blockSignals(False)

    def action_button_clicked_generate_characters(self):
        pass
    
    def personality_type_changed(self, val):
        self.generator.bot_personality = val
        save_session()
    
    def prefix_text_changed(self):
        self.generator.prefix = self.ui.prefix.toPlainText()
        save_session()

    def suffix_text_changed(self):
        self.generator.suffix = self.ui.suffix.toPlainText()
        save_session()

    def username_text_changed(self, val):
        self.generator.username = val
        save_session()

    def botname_text_changed(self, val):
        self.generator.botname = val
        save_session()