"""Service-owned prompt template model."""

from sqlalchemy import Boolean, Column, Integer, String, Text

from airunner_services.database.base import BaseModel


class PromptTemplate(BaseModel):
    """Persisted prompt template rows."""

    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String, nullable=False, default="")
    use_guardrails = Column(Boolean, default=True)
    guardrails = Column(Text, default="")
    system = Column(Text, default="")
    use_system_datetime_in_system_prompt = Column(Boolean, default=False)


__all__ = ["PromptTemplate"]
