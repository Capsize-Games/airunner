"""Service-owned art model metadata model."""

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from airunner_model.base import BaseModel


class AIModels(BaseModel):
	"""Persisted metadata for installed art and LLM-capable models."""

	trigger_words = Column(String, default="")
	__tablename__ = "aimodels"

	id = Column(Integer, primary_key=True, autoincrement=True)
	name = Column(String, nullable=False, default="Model")
	path = Column(String, nullable=False, default="")
	branch = Column(String, nullable=False, default="")
	version = Column(String, nullable=False, default="")
	category = Column(String, nullable=False, default="")
	pipeline_action = Column(String, nullable=False, default="")
	enabled = Column(Boolean, nullable=False, default=True)
	model_type = Column(String, nullable=False, default="")
	is_default = Column(Boolean, nullable=False, default=False)
	generator_settings = relationship(
		"GeneratorSettings", back_populates="aimodel"
	)


__all__ = ["AIModels"]