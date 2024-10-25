from PySide6.QtCore import Slot

from airunner.data.models.settings_models import PromptTemplate
from airunner.settings import DEFAULT_IMAGE_SYSTEM_PROMPT, DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT, \
    DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT, DEFAULT_RAG_SEARCH_SYSTEM_PROMPT, DEFAULT_CHATBOT_SYSTEM_PROMPT, \
    DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT, DEFAULT_IMAGE_LLM_GUARDRAILS, DEFAULT_CHATBOT_GUARDRAILS_PROMPT
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.prompt_templates_ui import Ui_prompt_templates_widget


class PromptTemplatesWidget(BaseWidget):
    widget_class_ = Ui_prompt_templates_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        session = self.session
        self._prompt_templates = session.query(PromptTemplate).all()
        self.ui.template_name.clear()
        self.current_template_index = 0
        for template in self._prompt_templates:
            self.ui.template_name.addItem(template.template_name)
        self.ui.template_name.setCurrentIndex(0)

    @Slot(int)
    def template_changed(self, index:int):
        self.current_template_index = index
        template = self._prompt_templates[index]
        self.ui.system_prompt.blockSignals(True)
        self.ui.guardrails_prompt.blockSignals(True)
        self.ui.use_guardrails.blockSignals(True)
        self.ui.use_datetime.blockSignals(True)
        self.ui.system_prompt.setPlainText(template.system)
        self.ui.guardrails_prompt.setPlainText(template.guardrails)
        self.ui.use_guardrails.setChecked(template.use_guardrails)
        self.ui.use_datetime.setChecked(template.use_system_datetime_in_system_prompt)
        self.ui.system_prompt.blockSignals(False)
        self.ui.guardrails_prompt.blockSignals(False)
        self.ui.use_guardrails.blockSignals(False)
        self.ui.use_datetime.blockSignals(False)

    @Slot()
    def system_prompt_changed(self):
        session = self.session
        template = self._prompt_templates[self.current_template_index]
        template.system = self.ui.system_prompt.toPlainText()
        self._prompt_templates[self.current_template_index] = template
        session.commit()

    @Slot()
    def guardrails_prompt_changed(self):
        session = self.session
        template = self._prompt_templates[self.current_template_index]
        template.guardrails = self.ui.guardrails_prompt.toPlainText()
        self._prompt_templates[self.current_template_index] = template
        session.commit()

    @Slot(bool)
    def toggle_use_guardrails(self, val:bool):
        session = self.session
        template = self._prompt_templates[self.current_template_index]
        template.use_guardrails = val
        self._prompt_templates[self.current_template_index] = template
        session.commit()

    @Slot(bool)
    def toggle_use_datetime(self, val:bool):
        session = self.session
        template = self._prompt_templates[self.current_template_index]
        template.use_system_datetime_in_system_prompt = val
        self._prompt_templates[self.current_template_index] = template
        session.commit()

    Slot()
    def reset_system_prompt(self):
        session = self.session
        template = self._prompt_templates[self.current_template_index]

        if template.template_name == "image":
            default = DEFAULT_IMAGE_SYSTEM_PROMPT
        elif template.template_name == "application_command":
            default = DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT
        elif template.template_name == "update_mood":
            default = DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT
        elif template.template_name == "rag_search":
            default = DEFAULT_RAG_SEARCH_SYSTEM_PROMPT
        elif template.template_name == "chatbot":
            default = DEFAULT_CHATBOT_SYSTEM_PROMPT
        elif template.template_name == "summarize":
            default = DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT
        else:
            default = ""

        template.system = default
        self.ui.system_prompt.setPlainText(default)
        self._prompt_templates[self.current_template_index] = template
        session.commit()

    Slot()
    def reset_guardrails_prompt(self):
        session = self.session
        template = self._prompt_templates[self.current_template_index]

        if template.template_name == "image":
            default = DEFAULT_IMAGE_LLM_GUARDRAILS
        elif template.template_name == "chatbot":
            default = DEFAULT_CHATBOT_GUARDRAILS_PROMPT
        else:
            default = ""

        template.guardrails = default
        self.ui.guardrails_prompt.setPlainText(default)
        self._prompt_templates[self.current_template_index] = template
        session.commit()
