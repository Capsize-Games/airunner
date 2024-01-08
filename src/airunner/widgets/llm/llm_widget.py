"""
This class should be used to create a window widget for the LLM.
"""
from airunner.utils import get_session
from airunner.data.models import LLMGenerator, LLMGeneratorSetting
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.llm_widget_ui import Ui_llm_widget
from airunner.aihandler.logger import Logger


class LLMWidget(BaseWidget):
    widget_class_ = Ui_llm_widget
    generator = None
    _generator = None
    _generator_settings = None

    @property
    def generator(self):
        if self._generator is None:
            session = get_session()
            try:
                self._generator = session.query(LLMGenerator).filter(
                    LLMGenerator.name == self.ui.llm_settings_widget.current_generator
                ).first()
                if self._generator is None:
                    Logger.error("Unable to locate generator by name " + self.ui.llm_settings_widget.current_generator if self.ui.llm_settings_widget.current_generator else "None")
            except Exception as e:
                Logger.error(e)
        return self._generator
    
    @property
    def generator_settings(self):
        try:
            return self.generator.generator_settings[0]
        except Exception as e:
            Logger.error(e)
            return None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # After the app is loaded, initialize other widgets
        self.app.loaded.connect(self.initialize)