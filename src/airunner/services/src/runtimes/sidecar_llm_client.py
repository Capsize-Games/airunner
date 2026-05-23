"""Service-owned adapter for the model-side llama.cpp client."""

from __future__ import annotations

from airunner_model.runtimes.sidecar_llm_client import (
	SidecarLLMClient as _SidecarLLMClient,
)

from airunner_services.runtimes.llama_cpp_runtime_settings import (
	resolve_llama_cpp_runtime_settings,
)


class SidecarLLMClient(_SidecarLLMClient):
	"""Resolve persisted service settings before delegating to the model."""

	def __init__(self, *args, **kwargs) -> None:
		kwargs.setdefault(
			"settings_resolver",
			resolve_llama_cpp_runtime_settings,
		)
		super().__init__(*args, **kwargs)


__all__ = ["SidecarLLMClient"]
