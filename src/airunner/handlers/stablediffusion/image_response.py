from typing import List, Optional, Any, Dict
from PIL.Image import Image
from dataclasses import dataclass

from airunner.handlers.stablediffusion.rect import Rect


@dataclass
class ImageResponse:
    images: Optional[List[Image]]
    data: Dict[str, Any]
    nsfw_content_detected: bool
    active_rect: Rect
    is_outpaint: bool

    def to_dict(self) -> Dict:
        return {
            "images": self.images,
            "data": self.data,
            "nsfw_content_detected": self.nsfw_content_detected,
            "active_rect": {
                "x": self.active_rect.x,
                "y": self.active_rect.y,
                "width": self.active_rect.width,
                "height": self.active_rect.height,
            },
            "is_outpaint": self.is_outpaint,
        }
