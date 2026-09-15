"""Service-owned image generation response container."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from PIL.Image import Image

from airunner_services.art.managers.stablediffusion.rect import Rect


@dataclass
class ImageResponse:
    """Response payload returned by art generation code."""

    images: Optional[List[Image]]
    data: Optional[Dict[str, Any]]
    active_rect: Optional[Rect]
    is_outpaint: bool
    node_id: Optional[str] = None
    post_display_callback: Optional[Callable[[], None]] = None

    def to_dict(self) -> Dict:
        """Convert the image response into a plain dictionary."""
        return {
            "images": self.images,
            "data": self.data,
            "active_rect": {
                "x": self.active_rect.x,
                "y": self.active_rect.y,
                "width": self.active_rect.width,
                "height": self.active_rect.height,
            },
            "is_outpaint": self.is_outpaint,
        }