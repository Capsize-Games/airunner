"""Service-owned adapter for the model-side whisper.cpp client."""

from __future__ import annotations

from airunner_model.runtimes.sidecar_stt_client import (
	SidecarSTTClient as _SidecarSTTClient,
)

from airunner_services.runtimes.whisper_cpp_runtime_settings import (
	resolve_whisper_cpp_runtime_settings,
)


class SidecarSTTClient(_SidecarSTTClient):
	"""Resolve persisted service settings before delegating to the model."""

	def __init__(self, *args, **kwargs) -> None:
		kwargs.setdefault(
			"settings_resolver",
			resolve_whisper_cpp_runtime_settings,
		)
		super().__init__(*args, **kwargs)


__all__ = ["SidecarSTTClient"]