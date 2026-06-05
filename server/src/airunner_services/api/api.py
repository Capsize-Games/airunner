"""Service-owned API singleton for daemon and daemon execution."""

from __future__ import annotations

from typing import Optional

from airunner_services.app.service_app import ServiceApp


class API(ServiceApp):
	"""Reuse the service-owned app shell as the API singleton."""

	_instance: Optional["API"] = None

	def __new__(cls, *args, **kwargs):
		"""Return one process-wide service API singleton."""
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def __init__(self, *args, **kwargs) -> None:
		"""Initialize the service API singleton once."""
		if getattr(self, "_api_initialized", False):
			return
		super().__init__(*args, **kwargs)
		self._api_initialized = True

	def cleanup(self) -> None:
		"""Release service resources and allow future singleton recreation."""
		super().cleanup()
		type(self)._instance = None
		self._api_initialized = False


__all__ = ["API"]