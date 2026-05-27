"""Compatibility wrapper for the service-owned LLM request model."""

from airunner_services.llm.llm_request import (
	LLMRequest,
	OpenrouterMistralRequest,
)

__all__ = ["LLMRequest", "OpenrouterMistralRequest"]
