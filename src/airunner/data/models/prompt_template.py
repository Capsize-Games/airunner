from sqlalchemy import Column, Integer, String, Boolean, Text

from airunner.data.models.base import BaseModel


class PromptTemplate(BaseModel):
    __tablename__ = "prompt_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String, nullable=False, default="")
    use_guardrails = Column(Boolean, default=True)
    guardrails = Column(Text, default="")
    system = Column(Text, default="")
    use_system_datetime_in_system_prompt = Column(Boolean, default=False)
