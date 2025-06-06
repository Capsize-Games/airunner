from .api_service_base import APIServiceBase
from airunner.enums import SignalCode
from PySide6.QtCore import QPoint
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)


class BrowserAPIService(APIServiceBase):
    def navigate_to_url(self, url: str):
        print("BROWSER API SERVICE NAVIGATE TO URL", url)
        self.emit_signal(SignalCode.BROWSER_NAVIGATE_SIGNAL, {"url": url})
