from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode


class ImageFilterAPIServices(APIServiceBase):
    def cancel(self):
        self.emit_signal(SignalCode.CANVAS_CANCEL_FILTER_SIGNAL)

    def apply(self, filter_object):
        self.emit_signal(
            SignalCode.CANVAS_APPLY_FILTER_SIGNAL,
            {"filter_object": filter_object},
        )

    def preview(self, filter_object):
        self.emit_signal(
            SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL,
            {"filter_object": filter_object},
        )
