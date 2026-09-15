"""Service-owned image-filter API signal adapter."""

from __future__ import annotations

from airunner_services.api.api_service_base import APIServiceBase
from airunner_services.api.services._art_signal_code import get_art_signal_code


class ImageFilterAPIServices(APIServiceBase):
    """Route image-filter actions through the shared signal bus."""

    def cancel(self) -> None:
        self.emit_signal(get_art_signal_code("CANVAS_CANCEL_FILTER_SIGNAL"))

    def apply(self, filter_object) -> None:
        self.emit_signal(
            get_art_signal_code("CANVAS_APPLY_FILTER_SIGNAL"),
            {"filter_object": filter_object},
        )

    def preview(self, filter_object) -> None:
        self.emit_signal(
            get_art_signal_code("CANVAS_PREVIEW_FILTER_SIGNAL"),
            {"filter_object": filter_object},
        )


__all__ = ["ImageFilterAPIServices"]