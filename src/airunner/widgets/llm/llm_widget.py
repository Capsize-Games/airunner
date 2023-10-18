"""
This class should be used to create a window widget for the LLM.
"""
from PyQt6.QtCore import pyqtSlot

from airunner.aihandler.enums import MessageCode
from airunner.data.db import session
from airunner.data.models import LLMGenerator
from airunner.utils import save_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.llm_widget_ui import Ui_llm_widget


class LLMWidget(BaseWidget):
    widget_class_ = Ui_llm_widget
    generator = None
    is_modal = True
    prefix = ""
    prompt = ""
    suffix = ""
    current_generator = "Flan"

    def load_data(self):
        self.generator = session.query(LLMGenerator).filter(
            LLMGenerator.name == self.current_generator
        ).first()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_data()
        self.ui.response.blockSignals(True)
        self.ui.prompt.blockSignals(True)
        self.ui.botname.blockSignals(True)
        self.ui.username.blockSignals(True)
        self.ui.prefix.blockSignals(True)
        self.ui.suffix.blockSignals(True)
        self.ui.model_version.blockSignals(True)
        self.ui.username.setText(self.generator.username)
        self.ui.botname.setText(self.generator.botname)

        model_versions = [version.name for version in self.generator.model_versions]
        self.ui.model_version.addItems(model_versions)
        self.ui.model_version.setCurrentText(self.generator.generator_settings[0].model_version)

        self.ui.response.blockSignals(False)
        self.ui.prompt.blockSignals(False)
        self.ui.botname.blockSignals(False)
        self.ui.username.blockSignals(False)
        self.ui.prefix.blockSignals(False)
        self.ui.suffix.blockSignals(False)
        self.ui.model_version.blockSignals(False)

        self.app.message_var.my_signal.connect(self.message_handler)

    @pyqtSlot(dict)
    def message_handler(self, response: dict):
        print("message_handler", response)
        try:
            code = response["code"]
        except TypeError:
            return
        message = response["message"]
        {
            MessageCode.TEXT_GENERATED: self.handle_text_generated,
        }.get(code, lambda *args: None)(message)

    def handle_text_generated(self, message):
        current_text = self.ui.response.toPlainText()
        current_text += "\n" + message
        self.ui.response.setPlainText(message)
    
    def prefix_text_changed(self, val):
        self.generator.prefix = val
        save_session()

    def prompt_text_changed(self, val):
        self.prompt = val
    
    def suffix_text_changed(self, val):
        self.generator.suffix = val
        save_session()

    def action_button_clicked_generated(self):
        prompt = "\n\n".join([self.prefix, self.prompt, self.suffix])
        data = {
            "llm_request": True,
            "request_data": (
                "Flan",
                "google/flan-t5-xl",
                prompt
            )
        }
        self.app.client.message = data
        self.clear_prompt()
        self.start_progress_bar()

    def clear_prompt(self):
        self.ui.prompt.setText("")

    def start_progress_bar(self):
        self.ui.progressBar.setRange(0, 0)
        self.ui.progressBar.setValue(0)

    def seed_changed(self, val):
        self.generator.generator_settings[0].seed = val
        save_session()

    def response_text_changed(self):
        pass

    def username_text_changed(self, val):
        self.generator.username = val
        save_session()

    def random_seed_toggled(self, val):
        self.generator.generator_settings[0].random_seed = val
        save_session()

    def model_version_changed(self, val):
        self.generator.generator_settings[0].model_version = val
        save_session()

    def early_stopping_toggled(self, val):
        self.generator.generator_settings[0].early_stopping = val
        save_session()

    def do_sample_toggled(self, val):
        self.generator.generator_settings[0].do_sample = val
        save_session()

    def botname_text_changed(self, val):
        self.generator.botname = val
        save_session()